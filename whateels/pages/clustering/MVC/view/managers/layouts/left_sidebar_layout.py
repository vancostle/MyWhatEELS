import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .....MVC import ClusteringView, ClusteringModel

class ClusteringLeftSidebarLayout:
    
    def __init__(self, view: "ClusteringView", model: "ClusteringModel"):
        self.view = view
        self.model = model

        self._layout = pn.Column(sizing_mode=self.view.STRETCH_WIDTH)
        
    @property
    def layout(self) -> pn.viewable.Viewable:
        """Left sidebar layout for displaying clustering controls."""
        return self._layout
    
    @layout.setter
    def layout(self, layout: pn.viewable.Viewable):
        """Set the left sidebar layout."""
        self._layout = layout
        
    @layout.deleter
    def layout(self):
        """Delete the left sidebar layout."""
        del self._layout