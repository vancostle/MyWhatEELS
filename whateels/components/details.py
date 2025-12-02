import panel as pn

class Details(pn.Column):
    def __init__(self, **params):
        super().__init__(**params)
        self.title = "Details Component"