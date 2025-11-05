from typing import TYPE_CHECKING
from whateels.helpers import CSS_ROOT, LoadCSS
from .layouts import ClusteringMainLayout, ClusteringLeftSidebarLayout, ClusteringRightSidebarLayout

if TYPE_CHECKING:
    from ..model import ClusteringModel
    from .layouts.right_sidebar_layout import ClusteringRightSidebarLayout

class ClusteringView:
    
    def __init__(self, model: "ClusteringModel"):
        self._model = model
        
        # Load any provided CSS files
        css_files = [
            str(CSS_ROOT / "clustering.css"),
            str(CSS_ROOT / "dataset_info.css")
        ]

        LoadCSS(css_files)

        self._main = ClusteringMainLayout(model)
        self._left_sidebar = ClusteringLeftSidebarLayout(model)
        self._right_sidebar = ClusteringRightSidebarLayout(model)

    @property
    def main(self) -> "ClusteringMainLayout":
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @main.setter
    def main(self, layout: "ClusteringMainLayout"):
        """Set the main content area layout."""
        self._main = layout
    @main.deleter
    def main(self):
        """Delete the main content area layout."""
        self._main.clear()

    @property
    def left_sidebar(self) -> "ClusteringLeftSidebarLayout":
        """Left sidebar layout for controls and options."""
        return self._left_sidebar
    @left_sidebar.setter
    def left_sidebar(self, layout: "ClusteringLeftSidebarLayout"):
        """Set the left sidebar layout."""
        self._left_sidebar = layout
    @left_sidebar.deleter
    def left_sidebar(self):
        """Delete the left sidebar layout."""
        self._left_sidebar.clear()

    @property
    def right_sidebar(self) -> "ClusteringRightSidebarLayout":
        """Right sidebar layout for additional controls and options."""
        return self._right_sidebar
    @right_sidebar.setter
    def right_sidebar(self, layout: "ClusteringRightSidebarLayout"):
        """Set the right sidebar layout."""
        self._right_sidebar = layout
    @right_sidebar.deleter
    def right_sidebar(self):
        """Delete the right sidebar layout."""
        self._right_sidebar.clear()