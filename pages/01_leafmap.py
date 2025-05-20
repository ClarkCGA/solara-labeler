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

def add_widgets(m, data_dir, styledict, hover_style_dict):
    chip_button = widgets.Button(description="Next Chip")

    def next_chip(b):
        chips = pd.read_csv(data_dir / 'chips_with_ortho_id.csv')

        # Get a random chip with status 'label'
        labeled_chips = chips[chips['status'] == 'label']

        chip = labeled_chips.sample(1)
        chips.loc[chip.index, 'status'] = 'active'
        chips.to_csv(data_dir / 'chips_with_ortho_id.csv', index=False)

        chip['geometry'] = chip['geometry'].apply(lambda coord_str: Polygon(eval(coord_str)))
        chip['TILENAME'] = chip['TILENAME'].apply(eval)

        chip_gdf = gpd.GeoDataFrame(chip, geometry='geometry', crs='EPSG:6348').to_crs('EPSG:3857')
        c = [c[0] for c in chip_gdf.to_crs('EPSG:4326').iloc[0].geometry.centroid.coords.xy]
        for layer in list(m.layers):
            if layer.name == 'chip':  # Only remove layers with the specific name
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

    chip_button.on_click(next_chip)
    m.add_widget(chip_button)

class LabelMap(leafmap.Map):
    def __init__(self, **kwargs):
        kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        for layer in self.layers:
            layer.visible = False
        file_url = quote("/home/jovyan/data/2023/vrt_output_mosaic.tif", safe='')
        tile_url = f'http://140.232.230.80:8851/api/tiles/{{z}}/{{x}}/{{y}}.png?&filename={file_url}'

        self.add_tile_layer(url=tile_url, name="Local Tiles", attribution="Local Tile Server")
        add_widgets(self, data_dir, styledict, hover_style_dict)

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
            height="780px",
        )
    
    