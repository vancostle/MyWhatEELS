import panel as pn

class PeriodicTableOfElementsModal(pn.Column):
    
    def __init__(self):
        super().__init__(
            pn.pane.Markdown("## Periodic Table of Elements"),
            pn.pane.Markdown("This is a placeholder for the periodic table modal content."),
            sizing_mode="stretch_both",
            styles={"padding": "16px"}
        )