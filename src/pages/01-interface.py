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
from bbox_to_tiles import bbox_to_tiles


data_dir = Path('/home/jovyan/solara-labeler/src/public/')
years = [2019, 2021, 2023]

# Display Styles
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

server = TileClient(
    data_dir / "2021/2021_orthophoto_cog.tif",
    port=8888,
    host="0.0.0.0",
)


zoom = solara.reactive(20)
center = solara.reactive((42.251504, -71.823585))
current_chip = solara.reactive(None)
chip_id = solara.reactive(None)

    
def display_chip(m, chip_gdf, styledict, hover_style_dict):
    """Display a chip on the map"""
    current_chip.set(chip_gdf)
    chip_id.set(chip_gdf.iloc[0]['id'])
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
    zoom.set(20)
    setattr(m, "gdf", chip_gdf)

def add_widgets(m, data_dir, styledict, hover_style_dict):
    chip_button = widgets.Button(description="Next Chip")
    save_button = widgets.Button(description="Save ROIs", 
                            button_style='success',
                            tooltip='Save drawn regions to file')
    

    def next_chip(b):
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        
        # Add a new chip to the end of the buffer
        labeled_chips = chips[chips['status'] == 'pending']
        if not labeled_chips.empty:
            new_chip = labeled_chips.head(1).copy()
            chips.loc[new_chip.index, 'status'] = 'active'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False)
            
            new_chip['geometry'] = new_chip['bbox'].apply(lambda coord_str: Polygon(eval(coord_str)))
            chip_gdf = gpd.GeoDataFrame(new_chip, geometry='geometry', crs='EPSG:6348').to_crs('EPSG:3857')
            
            display_chip(m, chip_gdf, styledict, hover_style_dict)

       
    def save_rois(b):
        # Get the current chip information
        if current_chip.value is None:
            print("No active chip to save ROIs for")
            return

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
                })
        
        if features:
            # Create GeoDataFrame and save to file
            rois_gdf = gpd.GeoDataFrame(features, geometry='geometry', crs='EPSG:3857')
            
            # Convert to appropriate CRS if needed
            rois_gdf = rois_gdf.to_crs('EPSG:6348')
            
            # Save to file
            output_path = data_dir / 'outputs' / f'{chip_id}_labels.geojson'
            
            rois_gdf.to_file(output_path, driver='GeoJSON')
            
            print(f"Saved {len(features)} ROIs to {output_path}")
            
            # Update chip status to labeled in tracker
            chips = pd.read_csv(data_dir / 'chip_tracker.csv')
            chip_idx = chips[chips['id'] == chip_id].index
            if len(chip_idx) > 0:
                chips.loc[chip_idx, 'status'] = 'labeled'
                chips.to_csv(data_dir / 'chip_tracker.csv', index=False)

    chip_button.on_click(next_chip)
    save_button.on_click(save_rois)


    m.add_widget(chip_button)
    m.add_widget(save_button)

class LabelMap(leafmap.Map):
    def __init__(self, **kwargs):
        #kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        for layer in self.layers:
            self.remove_layer(layer)
            #layer.visible = False
        # mass_url = 'https://tiles.arcgis.com/tiles/hGdibHYSPO59RG1h/arcgis/rest/services/USGS_Orthos_2019/MapServer/WMTS/tile/1.0.0/USGS_Orthos_2019/default/default028mm/{z}/{y}/{x}'
        # self.add_tile_layer(url=mass_url, 
        #                     name="2019 Orthos WMTS", 
        #                     attribution="MassGIS",
        #                     max_native_zoom=20,
        #                     min_native_zoom=20,
        #                     min_zoom=19)
        for year in years:
            url = f'http://140.232.230.80:8600/static/public/{year}/tiles/{{z}}/{{x}}/{{y}}.png'
            self.add_tile_layer(url=url, 
                            name=f"{year} Orthos", 
                            attribution="MassGIS",
                            max_native_zoom=21,
                            min_native_zoom=21,
                            min_zoom=19)
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
            tile_url = f'http://140.232.230.80:8600/static/public/{year}/tiles/{{z}}/{{x}}/{{y}}.png'
            tile_urls.append(tile_url)

    html_content = (
        "<div style='display:none;'>"
        + "\n".join([f"<img src='{url}' />" for url in tile_urls])
        + "</div>"
    )
    return solara.HTML(tag="div", unsafe_innerHTML=html_content)

@solara.component
def Page():
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
        # # Preload tiles for all chips in the buffer
        # if chip_buffer.value:
        #     for chip_gdf in chip_buffer.value:
        #         TilePreloaderFromChip(chip_gdf)
    