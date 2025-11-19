

import leafmap
import solara
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely import wkt
import ipywidgets as widgets
import yaml
import duckdb
import logging
import sys
from contextlib import contextmanager
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # Log to stdout, which is standard for containers
)
logger = logging.getLogger(__name__)

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
host_ip = settings['host_ip']
crs = settings['crs']
db_path = data_dir / 'chip_tracker.duckdb'

fgb_path = data_dir/ "chip_tracker.fgb"


status_map = {
    "pending": "red",
    "active": "yellow",    
    "labeled": "green",
}


def get_color_from_status(chip_status: str):
    color = status_map.get(chip_status)
    return color


callback = lambda feat: {
    "color": feat['properties']['color'],
    "weight": 2,
    "fillOpacity": 0
}

center = solara.reactive(settings['map']['center'])
zoom = solara.reactive(15)

gdf_data = solara.reactive(gpd.GeoDataFrame())
@contextmanager
def connect_to_db():
    con = None
    while con is None:
        try:
            con=duckdb.connect(str(db_path))
            con.execute("INSTALL spatial;")
            con.execute("LOAD spatial;") 
        except duckdb.IOException:
            time.sleep(0.1)
    try:
        yield con
    finally:
        con.close()


def add_widgets(m):
    def refresh_data(b):
        with connect_to_db() as con:
            query_result = con.execute("SELECT status, user, ST_AsText(geom) as wkt_geom FROM chip_tracker").fetchdf()
        query_result_gdf = gpd.GeoDataFrame(query_result)
        query_result_gdf['geometry'] = query_result_gdf['wkt_geom'].apply(wkt.loads)
        query_result_gdf.geometry = query_result_gdf['geometry']
        query_result_gdf.set_crs(crs, inplace=True)
        query_result_gdf.to_crs('EPSG:4326', inplace=True)
        query_result_gdf['color'] = query_result_gdf['status'].apply(lambda x: get_color_from_status(x))
        query_result_gdf.to_file(fgb_path, driver="FlatGeobuf")
        logger.info(f"chip tracker written to {fgb_path}")
        for layer in list(m.layers):
            if layer.name == 'chip_tracker':
                m.remove_layer(layer)
        m.add_vector(
            str(fgb_path),
            style_callback=callback,
            layer_name='chip_tracker',
        )
    refresh_data_button = widgets.Button(description="Refresh Data")
    refresh_data_button.on_click(refresh_data)
    m.add_widget(refresh_data_button)


class DisplayMap(leafmap.Map):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        add_widgets(self)
    
@solara.component
def Page():
    with solara.Column(style={"min-width": "500px"}):
        DisplayMap.element(
                zoom=zoom.value,
                on_zoom=zoom.set,
                center=center.value,
                on_center=center.set,
                scroll_wheel_zoom=True,
                toolbar_ctrl=False,
                data_ctrl=False,
                height="780px"   
            )