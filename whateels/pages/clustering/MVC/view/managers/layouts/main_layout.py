import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .....MVC import ClusteringView, ClusteringModel

class ClusteringMainLayout:
    """Manages the main layout for the Clustering View."""

    def __init__(self, view: 'ClusteringView', model: 'ClusteringModel'):
        self.view = view
        self.model = model

        self._layout = pn.Column(
            self.view._no_file_placeholder,
            sizing_mode=self.view.STRETCH_BOTH
        )
        
    @property
    def layout(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._layout
    
    @layout.setter
    def layout(self, layout: pn.Column):
        """Set the main content area layout."""
        self._layout = layout

    @layout.deleter
    def layout(self):
        """Delete the main content area layout."""
        del self._layout.clear()