import panel as pn
import gc
from whateels.errors.dm.data import DMPlotCreationError
import panel as pn
from .plots_factory import PlotsFactory
from .layouts import HomePageLeftSidebar, HomePageMainLayout, HomePageRightSidebar

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import HomePageModel
    from xarray import Dataset

class HomePageView:
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"
    
    def __init__(self, model: "HomePageModel"):
        self._model = model
        
        # Load any provided CSS files
        pn.config.css_files.append('/assets/css/home.css') # type: ignore
        
        # Layout components
        self._main = HomePageMainLayout(model)
        self._left_sidebar = HomePageLeftSidebar(
            model,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._right_sidebar = HomePageRightSidebar(model)
        
        # Store all dataset information
        self._all_dataset_info: list[pn.viewable.Viewable] = []
        
        # Track all created plot instances so cleanup() can stop their callbacks
        self._all_plots: list = []

        # Store reference to plots_tab for cleanup
        self._plots_tab = None
        self._plots_tab_watcher = None

    @property
    def main(self) -> HomePageMainLayout:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @main.setter
    def main(self, layout: HomePageMainLayout):
        """Set the main content area layout."""
        self._main = layout
    @main.deleter
    def main(self):
        """Delete the main content area layout."""
        self._main.clear()
        
    @property
    def left_sidebar(self) -> HomePageLeftSidebar:
        """Left sidebar layout for controls and options."""
        return self._left_sidebar
    @left_sidebar.deleter
    def left_sidebar(self):
        """Delete the left sidebar layout."""
        self._left_sidebar.clear()
        
    @property
    def right_sidebar(self) -> HomePageRightSidebar:
        """Right sidebar layout for dataset information."""
        return self._right_sidebar
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
        DEFAULT_TAB_INDEX = 0

        app_state = self._model.app_state

        try:
            # Stop streams and release old plot instances before creating new ones.
            # This frees numpy arrays and unsubscribes HoloViews stream callbacks.
            self.cleanup_plots()

            # Force garbage collection to free memory from old visualizers
            gc.collect()

            plots_factory = PlotsFactory(self._model)
            plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_plot = plots_factory.choose_plots(str(dataset_type), dataset)
                
                if chosen_plot is None:
                    raise DMPlotCreationError(f"No visualizer found for dataset type: {dataset_type}")
                
                visualizer_plots = chosen_plot.create_plots()
                
                plots_tab.append((image_name, visualizer_plots))
                self._all_plots.append(chosen_plot)
                self._all_dataset_info.append(chosen_plot.create_dataset_info())

            # Store reference to new plots_tab
            self._plots_tab = plots_tab
            
            # Watch for tab changes (new watcher on new tab object)
            self._plots_tab_watcher = self._plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE, onlychanged=False)
            
            # Set the active tab based on shared state or default
            plots_tab.active = app_state.selected_tab_index_dataset or DEFAULT_TAB_INDEX
            
            # Update UI
            self._main.update(plots_tab)
            
        except Exception as e:
            raise DMPlotCreationError(e)

    def _on_tab_with_visualizers_change(self, event):
        """Handle tab changes by updating sidebar with selected dataset info."""

        # Get the selected tab index
        selected_tab_index = event.new

        # Update shared state
        self._model.app_state.selected_tab_index_dataset = selected_tab_index

        # Update sidebar with the corresponding dataset info
        self._left_sidebar.remove_dataset_info()
        self._left_sidebar.add_component(self._all_dataset_info[selected_tab_index])
    
    def cleanup_plots(self):
        """Stop streams and release dataset references on all active plot instances.
        Called on file removal so numpy memory is freed immediately.
        """
        for plot in self._all_plots:
            if hasattr(plot, 'cleanup'):
                plot.cleanup()
        self._all_plots.clear()

        # Also drop the tab widget so Panel releases its children
        if self._plots_tab_watcher is not None and self._plots_tab is not None:
            self._plots_tab.param.unwatch(self._plots_tab_watcher)
            self._plots_tab_watcher = None
        if self._plots_tab is not None:
            self._plots_tab.clear()
            self._plots_tab = None

        self._all_dataset_info.clear()

    def cleanup(self):
        """Clean up resources before page reload or session end."""

        # Release all plot streams, callbacks, and dataset references
        self.cleanup_plots()

        # Clear layouts
        if self._main is not None:
            self._main.clear()
        if self._left_sidebar is not None:
            self._left_sidebar.clear()

        gc.collect()
