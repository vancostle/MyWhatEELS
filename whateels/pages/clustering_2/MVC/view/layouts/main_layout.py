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
        
        self._hdbscan_wrapper = pn.Column(
            margin=0,
            sizing_mode='stretch_width',
            styles={
                'width': '100%',
                'aspect-ratio': '1',
                'height': '100%',
            },
            css_classes=['hdbscan-wrapper'],
        )
        self._svm_wrapper = pn.Column(
            margin=0,
            sizing_mode='stretch_width',
            styles={
                'width': '100%',
                'aspect-ratio': '1',
                'height': '100%',
            },
            css_classes=['hdbscan-wrapper'],
        )
        self._svm_umap_embedding_wrapper = pn.Column(
            margin=0,
            styles={
                'width': '100%',
                'aspect-ratio': '1',
                'height': '100%',
            },
            css_classes=['umap-embedding-wrapper'],
        )
        self._heatmap_wrapper = pn.Column(margin=0, sizing_mode=self._STRETCH_WIDTH, css_classes=['heatmap-wrapper'])
        self._umap_wrapper = pn.Column(margin=0, styles={'width': '100%'}, css_classes=['umap-wrapper'])
        self._umap_embedding_wrapper = pn.Column(
            margin=0,
            styles={
                'width': '100%',
                'aspect-ratio': '1',
                'height': '100%',
            },
            css_classes=['umap-embedding-wrapper'],
        )

    @property
    def dm_file_uploaded_placeholder(self):
        return self._dm_file_uploaded_placeholder
    @property
    def none_dm_file_uploaded_placeholder(self):
        return self._none_dm_file_uploaded_placeholder
    @property
    def heatmap_wrapper(self):
        return self._heatmap_wrapper
    @property
    def umap_wrapper(self):
        return self._umap_wrapper
    @property
    def hdbscan_wrapper(self):
        return self._hdbscan_wrapper
    @property
    def svm_wrapper(self):
        return self._svm_wrapper
    @property
    def svm_umap_embedding_wrapper(self):
        return self._svm_umap_embedding_wrapper
    @property
    def umap_embedding_wrapper(self):
        return self._umap_embedding_wrapper

    def append_once(self, viewable):
        """Append a child only if it is not already present in the main column."""
        if not any(child is viewable for child in self.objects):
            self.append(viewable)

    def move_to_top(self, viewable):
        """Ensure a child is present and moved to the first position in the main column."""
        remaining = [child for child in self.objects if child is not viewable]
        self.objects = [viewable, *remaining]
    
    @override
    def clear(self):
        self._umap_wrapper.clear()
        self._hdbscan_wrapper.clear()
        self._svm_wrapper.clear()
        self._svm_umap_embedding_wrapper.clear()
        self._heatmap_wrapper.clear()
        self._umap_embedding_wrapper.clear()
        return super().clear()
        
    