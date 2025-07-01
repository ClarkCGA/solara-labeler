import leafmap
import solara
from urllib.parse import quote
from localtileserver import TileClient
import os
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely import Polygon
import rioxarray as rxr
import ipywidgets as widgets
import requests
from urllib.parse import quote
import math
import yaml

with open('/home/jovyan/solara-labeler/src/settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

data_dir = Path(settings['data_dir'])
years = settings['years']
pre_render = settings['pre_render']
host_base_port = settings['tileserver']['host_base_port']
container_base_port = settings['tileserver']['container_base_port']
preload_chips = settings['preload_chips']
chip_buffer_size = settings['chip_buffer_size']
show_buffer = settings['show_buffer']

if not pre_render:
    servers = {}
    for year in years:
        servers[year] = TileClient(
            f"/home/jovyan/solara-labeler/src/public/{year}/{year}_orthophoto_cog.tif",
            port=container_base_port + years.index(year),  # use different ports
            host="0.0.0.0",
        )

#Display Styles
styledict = {
            "stroke": True,
            "color": "#FF0000",
            "weight": 3,
            "opacity": 1,
            "fill": False,
        }
hover_style_dict = {
    "weight": styledict["weight"],
    "fillOpacity": 0,
    "color": styledict["color"],
}

zoom = solara.reactive(settings['map']['zoom'])
center = solara.reactive(settings['map']['center'])
current_chip = solara.reactive(None)
current_chip_start_time = solara.reactive(None)
previous_chip = solara.reactive(None)
chip_buffer = solara.reactive(None)
current_year_index = solara.reactive(0)
current_user = solara.reactive("")
success_visible = solara.reactive(False)
error_visible = solara.reactive(False)
success_message = solara.reactive("")
error_message = solara.reactive("")

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def bbox_to_tiles(bbox, zoom):
    # bbox = (min_lon, min_lat, max_lon, max_lat)
    min_x, max_y = deg2num(bbox[1], bbox[0], zoom)  # north-west corner
    max_x, min_y = deg2num(bbox[3], bbox[2], zoom)  # south-east corner
    tiles = []
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            tiles.append((zoom, x, y))
    return tiles
    
def display_chip(m, styledict, hover_style_dict):
    """Display a chip on the map"""
    chip_gdf = current_chip.value
    c = [c[0] for c in chip_gdf.to_crs('EPSG:4326').iloc[0].geometry.centroid.coords.xy]
    
    # Remove existing chip layer
    for layer in list(m.layers):
        if layer.name == 'chip':
            m.remove_layer(layer)
    
    # Add new chip to map
    m.add_gdf(
        chip_gdf,
        zoom_to_layer=False,
        style=styledict,
        hover_style=hover_style_dict,
        layer_name='chip',
        info_mode=None
    )
    
    center.set((c[1], c[0]))
    zoom.set(settings['map']['zoom'])
    setattr(m, "gdf", chip_gdf)

def add_widgets(m, data_dir, styledict, hover_style_dict):

    def get_previous_chip(b):
        current_chip.set(previous_chip.value)
        display_chip(m, styledict, hover_style_dict)

    def initialize_chip_buffer():
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        labeled_chips = chips[chips['status'] == 'pending']
        new_chips = labeled_chips.head(settings['chip_buffer_size']).copy()
        # mark these chips as active and save to tracker on disk
        chips.loc[new_chips.index, 'status'] = 'active'
        chips.to_csv(data_dir / 'chip_tracker.csv', index=False)      
        # re-constitute the geometry
        new_chips['geometry'] = new_chips['bbox'].apply(lambda coord_str: Polygon(eval(coord_str)))
        
        # create the full geodataframe
        chip_gdf = gpd.GeoDataFrame(new_chips, geometry='geometry', crs=settings['crs']).to_crs('EPSG:3857')
        
        # split into individual geodataframes (one per chip)
        chip_list = []
        for idx, row in chip_gdf.iterrows():
            single_chip_gdf = gpd.GeoDataFrame([row], geometry='geometry', crs='EPSG:3857')
            chip_list.append(single_chip_gdf)
        
        # set the chip buffer to the list of individual geodataframes
        chip_buffer.set(chip_list)

    def next_chip(b):
        # Initialize buffer if it's None or empty
        if chip_buffer.value is None and preload_chips:
            initialize_chip_buffer()

        # save the previous chip for re-doing
        if current_chip.value is not None:
            previous_chip.set(current_chip.value)

        # read in chip tracker
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        
        # get all chips with pending status
        labeled_chips = chips[chips['status'] == 'pending']

        # get the first chip
        new_chip = labeled_chips.head(1).copy()

        # mark this chip as active and save to tracker on disk
        chips.loc[new_chip.index, 'status'] = 'active'
        chips.to_csv(data_dir / 'chip_tracker.csv', index=False)
        
        # re-constitute the geometry
        new_chip['geometry'] = new_chip['bbox'].apply(lambda coord_str: Polygon(eval(coord_str)))
        
        # set the current chip equal to the new chip gdf
        chip_gdf = gpd.GeoDataFrame(new_chip, geometry='geometry', crs=settings['crs']).to_crs('EPSG:3857')

        if preload_chips:
            chip_buffer.value.append(chip_gdf) # add the new chip to the end of the buffer
            current_chip.set(chip_buffer.value[0]) # set the current chip to the next in line
            chip_buffer.set(chip_buffer.value[1:]) # remove the chip that was just labeled from the buffer  
        
        else:
            current_chip.set(chip_gdf)

        current_chip_start_time.set(pd.Timestamp.now().isoformat())

        # display the chip on the map
        display_chip(m, styledict, hover_style_dict)

    def clear_rois(b):
        m.draw_control.clear()
       
    def save_rois(b):
        # Get the current chip information
        if current_chip.value is None:
            print("No active chip to save ROIs for")
            return
        
        chip_id = current_chip.value.iloc[0]['id']
        
        # Get all drawn features from the map
        drawn_features = m.user_rois
        
        if not drawn_features:
            print("No ROIs drawn on the map")
            return
        
        # Create a GeoDataFrame from the drawn features
        features = []
        for feature in drawn_features['features']:
            geom = feature['geometry']
            feat_type = geom['type']
            
            # Convert to shapely geometry
            if feat_type == 'Polygon':
                coords = geom['coordinates'][0]  # First ring is exterior
                features.append({
                    'chip_id': chip_id,
                    'geometry': Polygon(coords),
                    'timestamp': pd.Timestamp.now().isoformat(),
                    'user' : current_user.value,
                    'year': years[current_year_index.value],
                })
        
        if features:
            # Create GeoDataFrame and save to file
            rois_gdf = gpd.GeoDataFrame(features, geometry='geometry', crs='EPSG:3857')
            
            # Convert to appropriate CRS if needed
            rois_gdf = rois_gdf.to_crs(settings['crs'])
            
            # Save to file
            output_path = data_dir / 'outputs' / f'{chip_id}_labels_{years[current_year_index.value]}.geojson'
            
            rois_gdf.to_file(output_path, driver='GeoJSON')
            
            print(f"Saved {len(features)} ROIs to {output_path}")

    def mark_chip_labeled(b):
        chip_id = current_chip.value.iloc[0]['id']
        # Update chip status to labeled in tracker
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        chip_idx = chips[chips['id'] == chip_id].index
        if len(chip_idx) > 0:
            chips.loc[chip_idx, ['status', 'user', 'start_time', 'end_time']] = [
                'labeled', 
                current_user.value, 
                current_chip_start_time.value, 
                pd.Timestamp.now().isoformat()
            ]
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False) 

    def mark_chip_active(b):
        chip_id = current_chip.value.iloc[0]['id']
        # Update chip status to labeled in tracker
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        chip_idx = chips[chips['id'] == chip_id].index
        if len(chip_idx) > 0:
            chips.loc[chip_idx, 'status'] = 'active'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False) 

    def mark_chip_pending(b):
        chip_id = current_chip.value.iloc[0]['id']
        # Update chip status to labeled in tracker
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        chip_idx = chips[chips['id'] == chip_id].index
        if len(chip_idx) > 0:
            chips.loc[chip_idx, 'status'] = 'pending'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False)

    def remove_chip_labels(b):
        # Remove rois for the current chip
        # Get the current chip information
        if current_chip.value is None:
            print("No active chip to delete ROIs for")
            return
        chip_id = current_chip.value.iloc[0]['id']

        for year in years:
            remove_year_labels(b, chip_id, year)
        
        # Update chip status to labeled in tracker
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        chip_idx = chips[chips['id'] == chip_id].index
        if len(chip_idx) > 0:
            chips.loc[chip_idx, 'status'] = 'active'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False)

    def remove_year_labels(b, chip_id, year):
        output_path = data_dir / 'outputs' / f'{chip_id}_labels_{year}.geojson'
        output_path.unlink(missing_ok=True)


    def add_year_raster(year):
        url = f'http://140.232.230.80:8600/static/public/{year}/tiles/{{z}}/{{x}}/{{y}}.png'
        m.add_tile_layer(url=url, 
                    name=f"{year} Orthos", 
                    attribution=settings['data_attribution'],
                    max_native_zoom=settings['map']['zoom']+1,
                    min_native_zoom=settings['map']['zoom']+1,
                    min_zoom=settings['map']['zoom']-2,
                    )
            

    def back_to_last_chip(b):
        mark_chip_pending(b)
        clear_rois(b)
        get_previous_chip(b)
        remove_chip_labels(b)
        mark_chip_active(b)
        current_year_index.set(0)

    def back_to_last_year(b):
        clear_rois(b)

        if current_year_index.value != 0:
            current_year_index.set(current_year_index.value - 1)
        if pre_render:
            m.clear_layers()
            add_year_raster(years[current_year_index.value])
        remove_year_labels(b, current_chip.value.iloc[0]['id'], years[current_year_index.value])
        

    def sumbit_year(b):
        if current_user.value == "":
            error_message.set("Error: Please enter something in the Current User text box!")
            error_visible.set(True)
            return
        try:
            save_rois(b)
            success_message.set(
                f"Saved {len(m.user_rois) if m.user_rois else 0} features for chip {current_chip.value.iloc[0]['id']} in year {years[current_year_index.value]} under user {current_user.value}"
            )
            success_visible.set(True)
            error_visible.set(False)
            clear_rois(b)
            if current_year_index.value == (len(years) - 1):
                if pre_render:
                    m.clear_layers()
                current_year_index.set(0)
                mark_chip_labeled(b)
                next_chip(b)
                if pre_render:
                    add_year_raster(years[current_year_index.value])
            else:
                current_year_index.set(current_year_index.value + 1)
                if pre_render:
                    add_year_raster(years[current_year_index.value])
        except Exception as e:
            error_message.set(e)
            error_visible.set(True)
            
            


    back_to_last_year_button = widgets.Button(description="Redo Previous Year",
                                              button_style='danger')
        
    back_to_last_chip_button = widgets.Button(description="Redo Previous Chip",
                                              button_style='warning')
    
    submit_year_button = widgets.Button(description="Save Labels to Disk", 
                            button_style='success',
                            tooltip='Save drawn regions to file')
    
    
    back_to_last_year_button.on_click(back_to_last_year)    
    back_to_last_chip_button.on_click(back_to_last_chip)
    submit_year_button.on_click(sumbit_year)

    m.add_widget(back_to_last_chip_button)
    m.add_widget(back_to_last_year_button)
    m.add_widget(submit_year_button)
    
    next_chip(None)

    if pre_render:
        add_year_raster(years[current_year_index.value])

class LabelMap(leafmap.Map):
    def __init__(self, **kwargs):
        kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        for layer in self.layers:
            self.remove_layer(layer)
        # Show Massachusetts Orthophotos, for comparison
        # mass_url = 'https://tiles.arcgis.com/tiles/hGdibHYSPO59RG1h/arcgis/rest/services/USGS_Orthos_2019/MapServer/WMTS/tile/1.0.0/USGS_Orthos_2019/default/default028mm/{z}/{y}/{x}'
        # self.add_tile_layer(url=mass_url, 
        #                     name="2019 Orthos WMTS", 
        #                     attribution="MassGIS",
        #                     max_native_zoom=20,
        #                     min_native_zoom=20,
        #                     min_zoom=19)
        if not pre_render:
            for year in years:
                file_url = quote(f"/home/jovyan/solara-labeler/src/public/{year}/{year}_orthophoto_cog.tif", safe='')
                port=container_base_port + years.index(year)
                tile_url = f'http://140.232.230.80:{port}/api/tiles/{{z}}/{{x}}/{{y}}.png?&filename={file_url}'
                self.add_tile_layer(url=tile_url, 
                                    name=f"{year} Orthos", 
                                    attribution="MassGIS",
                                    max_native_zoom=10,
                                    min_native_zoom=10,
                                    min_zoom=10)        
        add_widgets(self, data_dir, styledict, hover_style_dict)


@solara.component
def TilePreloaderFromChip(chip_gdf):
    if chip_gdf is None or chip_gdf.empty:
        return
    bounds = chip_gdf.to_crs(4326).iloc[0].geometry.bounds
    tile_coords = bbox_to_tiles(bounds, zoom=21)
    tile_urls = []
    for year in years:
        for z, x, y in tile_coords:
            tile_url = f'http://140.232.230.80:8600/static/public/{year}/tiles/{z}/{x}/{y}.png'
            tile_urls.append(tile_url)

    html_content = (
        "<div style='display:none;'>"
        + "\n".join([f"<img src='{url}' />" for url in tile_urls])
        + "</div>"
    )
    return solara.HTML(tag="div", unsafe_innerHTML=html_content)

@solara.component
def Page():
    router = solara.use_router()

    def mark_chip_pending():
        chip_id = current_chip.value.iloc[0]['id']
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        chip_idx = chips[chips['id'] == chip_id].index
        if len(chip_idx) > 0:
            chips.loc[chip_idx, 'status'] = 'pending'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False)
            print(f"Chip {chip_id} marked as pending.")
            
    def mark_buffer_pending():
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        for gdf in chip_buffer.value:
            chip_id = gdf.iloc[0]['id']
            chip_idx = chips[chips['id'] == chip_id].index
            chips.loc[chip_idx, 'status'] = 'pending'
            print(f"Chip {chip_id} marked as pending.")
        chips.to_csv(data_dir / 'chip_tracker.csv', index=False)

    def exit_interface():
        mark_chip_pending()
        if preload_chips:
            mark_buffer_pending()
        router.push("/")

    with solara.Columns([1, 3]):
        with solara.Column():
            
            solara.Markdown(f"**Current Year:** {years[current_year_index.value]}")
            if preload_chips and chip_buffer.value and show_buffer:
                solara.Markdown(f"Current Buffer IDs: {[gdf.iloc[0]['id'] for gdf in chip_buffer.value]}")
            solara.InputText("Current User:", value=current_user, on_value=current_user.set, continuous_update=True)
            solara.Button("Exit", on_click=exit_interface, color='red')
            if success_visible.value:    
                solara.Success(
                    success_message.value
                )
            if error_visible.value:    
                solara.Error(
                    error_message.value
                )
                
            
        with solara.Column(style={"min-width": "500px"}):
            LabelMap.element(
                zoom=zoom.value,
                on_zoom=zoom.set,
                center=center.value,
                on_center=center.set,
                scroll_wheel_zoom=True,
                toolbar_ctrl=False,
                data_ctrl=False,
                height="780px"   
            )
            if preload_chips:
                TilePreloaderFromChip(current_chip.value)


    