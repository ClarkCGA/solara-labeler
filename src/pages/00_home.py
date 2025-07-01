import solara
from pathlib import Path
import solara.website

@solara.component
def Page():
    router = solara.use_router()
    with solara.Columns(1,1):
        with solara.Column():
            markdown = """
            # Solara Interface for Labeling Rooftop Solar in Massachusetts

            ## Before Labeling

            In the 'Current User' texbox on the top left of the interface, enter your username for this labeling project. Then you will be able to start labeling.

            ## Using the Interface

            1. Use the polygon tool and the mouse to draw polygons covering all solar arrays within the red region as accurately as possible.
                - Use the scroll wheel or the zoom buttons on the top left to zoom to each solar array.
                - If there are gaps in the solar array, draw two intersecting polygons that overlap all panels, leaving gaps empty.
                - If there are no solar arrays, continue to step 2.
            2. Click the Green 'Save Labels to Disk' button in the bottom right of the map. This automatically loads the next task.
            
            ## Redoing Tasks
            **Redoing the Previous Year after Saving:** If you want to redo the previous year of the current chip, click the yellow **'Redo Previous Year'** button.
            **Redoing the Previous Chip after Saving:** If you want to redo the previous chip, click the Red **'Redo Previous Chip'** button.  
            
            ## Exiting the Interface
            Any time you wnat to exit the interface, click the red **'Exit'** button on the left of the page.

            ## Ready to Start?
            When you click 'Start Labeling!' you will navigate to the labeling interface. Thank you for contributing your time to this project!

            """
            
            solara.Markdown(markdown)
            solara.Button("Start Labeling!", on_click=lambda *_: router.push("/interface"))
        
        with solara.Column():
            #image_path = Path('/home/jovyan/solara-labeler/src/pages/assets/')
            image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"
            solara.Markdown('Placeholder Image:')
            solara.Image(image_path)
            

