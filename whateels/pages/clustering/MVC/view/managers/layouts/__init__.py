import panel as pn

from .main_layout import ClusteringMainLayout
from .left_sidebar_layout import ClusteringLeftSidebarLayout
from .right_sidebar_layout import ClusteringRightSidebarLayout

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .....MVC import ClusteringView, ClusteringModel

class ClusteringLayoutManager:
    """Manages the layout of the Clustering MVC View."""

    _STRETCH_BOTH = 'stretch_both'

    def __init__(self, view: "ClusteringView", model: "ClusteringModel"):
        self._view = view
        self._model = model

        self._main = ClusteringMainLayout(view, model).layout
        
    @property
    def main(self) -> pn.viewable.Viewable:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @main.setter
    def main(self, layout: pn.viewable.Viewable):
        """Set the main content area layout."""
        self._main = layout