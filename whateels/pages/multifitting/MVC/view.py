import panel as pn

class View:
    def __init__(self, model):
        self.model = model
        # header and body placeholders; sizing_mode set to stretch for embedding
        self.header = pn.pane.Markdown(f"## {self.model.constants.TITLE}", style={'background': self.model.constants.HEADER_BACKGROUND}, sizing_mode='stretch_width')
        self.body = pn.Column(
            pn.pane.Markdown("Multifitting UI placeholder — implement controls here."),
            sizing_mode='stretch_both'
        )
        self.main = pn.Column(self.header, self.body, sizing_mode='stretch_both')
        # ...existing code...