import solara


@solara.component
def Page():
    router = solara.use_router()

    with solara.Column(align="center"):
        markdown = """
        ## A Solara Template for Geospatial Applications
        
        ### Introduction

        **A collection of [Solara](https://github.com/widgetti/solara) web apps for geospatial applications.**

        - Web App: <https://giswqs-solara-template.hf.space>
        - GitHub: <https://github.com/opengeos/solara-template>
        - Hugging Face: <https://huggingface.co/spaces/giswqs/solara-template>

        """

        solara.Markdown(markdown)
        solara.Button("Start Labeling!", on_click=lambda *_: router.push("/interface")),

