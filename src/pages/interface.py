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

data_dir = Path('/home/jovyan/data/')

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
    "/home/jovyan/data/2023/vrt_output_mosaic.tif",
    port=8888,
    host="0.0.0.0",
)

zoom = solara.reactive(20)
center = solara.reactive((42.251504, -71.823585))
current_chip = solara.reactive(None)
chip_buffer = solara.reactive([])  # Store multiple chips
buffer_position = solara.reactive(0)  # Current position in buffer

def load_buffer(m, data_dir, styledict, hover_style_dict, buffer_size=5):
    """Load initial chip buffer with pending chips"""
    chips = pd.read_csv(data_dir / 'chip_tracker.csv')
    pending_chips = chips[chips['status'] == 'pending'].head(buffer_size).copy()
    
    # Update status for these chips
    chips.loc[pending_chips.index, 'status'] = 'active'
    chips.to_csv(data_dir / 'chip_tracker.csv', index=False)
    
    buffer = []
    for _, chip_row in pending_chips.iterrows():
        chip_data = chip_row.copy()
        chip_data['geometry'] = Polygon(eval(chip_data['bbox']))
        chip_gdf = gpd.GeoDataFrame(pd.DataFrame([chip_data]), geometry='geometry', crs='EPSG:6348').to_crs('EPSG:3857')
        buffer.append(chip_gdf)
    
    chip_buffer.set(buffer)
    
    # If buffer has chips, display the first one
    if buffer:
        display_chip(m, buffer[0], styledict, hover_style_dict)
        buffer_position.set(0)
    
def display_chip(m, chip_gdf, styledict, hover_style_dict):
    """Display a chip on the map"""
    current_chip.set(chip_gdf)
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

    def next_chip(b):
        chips = pd.read_csv(data_dir / 'chip_tracker.csv')
        
        # Get current buffer and position
        buffer = chip_buffer.value
        pos = buffer_position.value
        
        # Move to next position in buffer or cycle back to start
        next_pos = (pos + 1) % len(buffer)
        buffer_position.set(next_pos)
        
        # Display the chip at the new position
        display_chip(m, buffer[next_pos], styledict, hover_style_dict)
        
        # Add a new chip to the end of the buffer
        labeled_chips = chips[chips['status'] == 'pending']
        if not labeled_chips.empty:
            new_chip = labeled_chips.head(1).copy()
            chips.loc[new_chip.index, 'status'] = 'active'
            chips.to_csv(data_dir / 'chip_tracker.csv', index=False)
            
            new_chip['geometry'] = new_chip['bbox'].apply(lambda coord_str: Polygon(eval(coord_str)))
            new_chip_gdf = gpd.GeoDataFrame(new_chip, geometry='geometry', crs='EPSG:6348').to_crs('EPSG:3857')
            
            # Add to end of buffer
            new_buffer = buffer.copy()
            new_buffer.append(new_chip_gdf)
            chip_buffer.set(new_buffer)

    # Load initial buffer when widget is added
    load_buffer(m, data_dir, styledict, hover_style_dict)
    
    chip_button.on_click(next_chip)
    m.add_widget(chip_button)

class LabelMap(leafmap.Map):
    def __init__(self, **kwargs):
        kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        for layer in self.layers:
            layer.visible = False
        file_url = quote("/home/jovyan/data/2023/vrt_output_mosaic.tif", safe='')
        tile_url = f'http://140.232.230.80:8000/api/tiles/{{z}}/{{x}}/{{y}}.png?&filename={file_url}'
        #tile_url = 'http://140.232.230.8000/api/tiles/20/315086/388261.png?&filename=%2Fhome%2Fjovyan%2Fdata%2F2023%2Fvrt_output_mosaic.tif'
        self.add_tile_layer(url=tile_url, 
                            name="Local Tiles", 
                            attribution="Local Tile Server",
                            max_native_zoom=21,
                            min_native_zoom=21)
        add_widgets(self, data_dir, styledict, hover_style_dict)

@solara.component
def TilePreloaderFromChip(chip_gdf):
    if chip_gdf is None or chip_gdf.empty:
        return
    bounds = chip_gdf.to_crs(4326).iloc[0].geometry.bounds
    tile_coords = bbox_to_tiles(bounds, zoom=21)

    tile_urls = []
    for z, x, y in tile_coords:
        tile_url = f"http://140.232.230.80:8000/api/tiles/{z}/{x}/{y}.png?&filename=%2Fhome%2Fjovyan%2Fdata%2F2023%2Fvrt_output_mosaic.tif"
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
        # Preload tiles for all chips in the buffer
        if chip_buffer.value:
            for chip_gdf in chip_buffer.value:
                TilePreloaderFromChip(chip_gdf)
    