import panel as pn
from .placeholders import MainLayoutPlaceholder

class Clustering2MainLayout(pn.Column):
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._placeholder = MainLayoutPlaceholder()
        self.append(self._placeholder)
        
    def display_placeholder(self):
        self.clear()
        self.append(self._placeholder)