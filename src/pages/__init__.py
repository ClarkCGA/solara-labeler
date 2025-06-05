import solara
@solara.component
def Layout(children=[]):
    # there will only be 1 child, which is the Page()
    return children[0]
