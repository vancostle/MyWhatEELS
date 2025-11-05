from typing import TYPE_CHECKING, Optional
from whateels.helpers import HTML_ROOT, CSS_ROOT
from whateels.helpers import LoadCSS
from .layouts import ClusteringMainLayout, ClusteringLeftSidebarLayout, ClusteringRightSidebarLayout

import panel as pn

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

        if css_files and len(css_files) > 0:
            LoadCSS(css_files)
                
        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None
        
        self._kmeans_input = None # Dictionary to hold K-Means input widgets
        self._agglomerative_input = None # Dictionary to hold Agglomerative input widgets
        self._spectral_input = None # Dictionary to hold Spectral input widgets

        self._kmeans_run_button = None # Button to run K-Means clustering
        self._background_subtraction_switch = None # Switch for background-subtraction option
        self._store_button = None # Button to store clustering results
        
        self._agglomerative_run_button = None # Button to run Agglomerative clustering
        
        self._spectral_run_button = None # Button to run Spectral clustering
        
        self._main = ClusteringMainLayout(model)
        self._left_sidebar = ClusteringLeftSidebarLayout(model)
        self._right_sidebar = ClusteringRightSidebarLayout(model)

    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @main.setter
    def main(self, layout: pn.Column):
        """Set the main content area layout."""
        self._main = layout
    @main.deleter
    def main(self):
        """Delete the main content area layout."""
        self._main.clear()

    @property
    def left_sidebar(self) -> pn.Column:
        """Left sidebar layout for controls and options."""
        return self._left_sidebar
    @left_sidebar.setter
    def left_sidebar(self, layout: pn.Column):
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

    @property
    def background_subtraction_switch(self) -> Optional[pn.widgets.Switch]:
        """Access the background-subtraction switch widget."""
        return self._right_sidebar.background_subtraction_switch

    @property
    def kmeans_input(self):
        """Access the K-Means input widgets."""
        return self._kmeans_input
    @property
    def kmeans_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the K-Means input widgets."""
        return self._kmeans_run_button      
    
    @property
    def agglomerative_input(self):
        """Access the Agglomerative input widgets."""
        return self._agglomerative_input   
    @property
    def agglomerative_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Agglomerative run button."""
        return self._agglomerative_run_button
    
    @property
    def spectral_input(self):
        """Access the Spectral input widgets."""
        return self._spectral_input
    @property
    def spectral_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Spectral run button."""
        return self._spectral_run_button

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def store_button(self):
        """Access the store button widget."""
        return self._store_button
    
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component