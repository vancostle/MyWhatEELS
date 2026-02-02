import panel as pn
from .placeholders import MainLayoutPlaceholder

class Clustering2MainLayout(pn.Column):
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.placeholder = MainLayoutPlaceholder()
        self.append(self.placeholder)