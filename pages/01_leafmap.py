import leafmap
import solara
from urllib.parse import quote
from localtileserver import TileClient

zoom = solara.reactive(2)
center = solara.reactive((20, 0))


server = TileClient(
    "/home/jovyan/data/vrt_output_mosaic.tif",
    port=8888,
    host="0.0.0.0",
)

class Map(leafmap.Map):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        file_url = quote("/home/jovyan/data/vrt_output_mosaic.tif", safe='')
        tile_url = f'http://140.232.230.80:8851/api/tiles/{{z}}/{{x}}/{{y}}.png?&filename={file_url}'

        self.add_tile_layer(url=tile_url, name="Local Tiles", attribution="Local Tile Server")

        self.add_stac_gui()

@solara.component
def Page():
    with solara.Column(style={"min-width": "500px"}):
        # solara components support reactive variables
        # solara.SliderInt(label="Zoom level", value=zoom, min=1, max=20)
        # using 3rd party widget library require wiring up the events manually
        # using zoom.value and zoom.set
        Map.element(  # type: ignore
            zoom=zoom.value,
            on_zoom=zoom.set,
            center=center.value,
            on_center=center.set,
            scroll_wheel_zoom=True,
            toolbar_ctrl=False,
            data_ctrl=False,
            height="780px",
        )
        # solara.Text(f"Zoom: {zoom.value}")
        # solara.Text(f"Center: {center.value}")
