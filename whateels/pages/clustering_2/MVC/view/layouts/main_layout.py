from typing import override
import panel as pn
from .placeholders import DMFileUploadedPlaceholder, NoneDMFileUploadedPlaceholder

class Clustering2MainLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs, margin=0)
        self._dm_file_uploaded_placeholder = DMFileUploadedPlaceholder()
        self._none_dm_file_uploaded_placeholder = NoneDMFileUploadedPlaceholder()
        self._umap_wrapper = pn.Column(sizing_mode='stretch_width', margin=0)
        self._hdbscan_wrapper = pn.Column(sizing_mode='stretch_width', margin=0)    
        
        # self.append(self._dm_file_uploaded_placeholder)
        self.append(self._hdbscan_wrapper)    
        self.append(self._umap_wrapper)

    @property
    def dm_file_uploaded_placeholder(self):
        return self._dm_file_uploaded_placeholder
    @property
    def none_dm_file_uploaded_placeholder(self):
        return self._none_dm_file_uploaded_placeholder
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
        
    