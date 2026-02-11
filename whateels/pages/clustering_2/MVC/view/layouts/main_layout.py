from typing import override
import panel as pn
from .placeholders import MainLayoutPlaceholder

class Clustering2MainLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs, margin=0)
        self._placeholder = MainLayoutPlaceholder()
        self._umap_wrapper = pn.Column(sizing_mode='stretch_width', styles={'border': '1px solid red'}, margin=0)
        self._hdbscan_wrapper = pn.Column(sizing_mode='stretch_width', styles={'border': '1px solid green'}, margin=0)    
        
        self.append(self._placeholder)
        self.append(self._hdbscan_wrapper)    
        self.append(self._umap_wrapper)

    @property
    def placeholder(self):
        return self._placeholder
    @property
    def umap_wrapper(self):
        return self._umap_wrapper
    @property
    def hdbscan_wrapper(self):
        return self._hdbscan_wrapper
    
    @override
    def clear(self):
        self._umap_wrapper.clear()
        self._hdbscan_wrapper.clear()
        cleared = super().clear()
        self.append(self._hdbscan_wrapper)
        self.append(self._umap_wrapper)
        return cleared
        
    