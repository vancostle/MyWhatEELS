import panel as pn

from whateels.errors.dm.data import DMPlotCreationError
from whateels.helpers import CSS_ROOT, LoadCSS
from .layouts import ClusteringMainLayout, ClusteringLeftSidebarLayout, ClusteringRightSidebarLayout
from .plots_factory import PlotsFactory
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from .layouts.right_sidebar_layout import ClusteringRightSidebarLayout
    from xarray import Dataset

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
        
        # Store all dataset information
        self._all_dataset_info: list[pn.viewable.Viewable] = []
        
        # Callback for tab changes (will be set by controller)
        self._on_tab_change_callback = None

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
        
    def create_tab_and_dataset_info(self, all_datasets: list["Dataset"]) -> None:
        """
        Create visualizations for all datasets and setup tabbed UI interface.
        
        Args:
            all_datasets: List of processed datasets to visualize
                         
        Raises:
            DMPlotCreationError: When visualization creation fails
        """
        DATASET_TYPE = 'dataset_type'
        IMAGE_NAME_ATTRIBUTE = 'image_name'
        NOT_AVAILABLE = 'N/A'
        ACTIVE = 'active'
        STRETCH_BOTH = 'stretch_both'

        try:
            # Clear previous dataset info panels to prevent caching old data
            self._all_dataset_info.clear()
            
            visualizer_factory = PlotsFactory(self._model, view=self)
            plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_visualizer = visualizer_factory.choose_visualizer(str(dataset_type), dataset)
                
                if chosen_visualizer is None:
                    return
                
                visualizer_plots = chosen_visualizer.create_plots()
                
                plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            # Register tab change callback if controller provided one
            if self._on_tab_change_callback is not None:
                plots_tab.param.watch(self._on_tab_change_callback, ACTIVE)
                
            # Update UI
            self.main.update(plots_tab)
            self.left_sidebar.remove_dataset_info()
            self.left_sidebar.add_component(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)
    
    def update_sidebar_for_tab(self, tab_index: int):
        """Update sidebar to show dataset info for the specified tab."""
        if 0 <= tab_index < len(self._all_dataset_info):
            self.left_sidebar.remove_dataset_info()
            self.left_sidebar.add_component(self._all_dataset_info[tab_index])
    
    def set_tab_change_callback(self, callback):
        """Set the callback to be called when tabs change."""
        self._on_tab_change_callback = callback