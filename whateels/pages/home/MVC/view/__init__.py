import panel as pn

from whateels.errors.dm.data import DMPlotCreationError
from whateels.helpers import LoadCSS, CSS_ROOT
from .plots_factory import PlotsFactory
from .layouts import HomePageLeftSidebar, HomePageMainLayout

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
        css_files = [
            str(CSS_ROOT / "home.css"),
            str(CSS_ROOT / "dataset_info.css")
        ]

        LoadCSS(css_files)
        
        # Layout components
        self._main = HomePageMainLayout(model)
        self._left_sidebar = HomePageLeftSidebar(model)
        
        # Store all dataset information
        self._all_dataset_info: list[pn.viewable.Viewable] = []

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
    @left_sidebar.setter
    def left_sidebar(self, layout: HomePageLeftSidebar):
        """Set the left sidebar layout."""
        self._left_sidebar = layout
    @left_sidebar.deleter
    def left_sidebar(self):
        """Delete the left sidebar layout."""
        self._left_sidebar.clear()
        
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
            # Clear previous dataset info panels to prevent caching old data
            self._all_dataset_info.clear()
            
            visualizer_factory = PlotsFactory(self._model)
            plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_visualizer = visualizer_factory.choose_plots(str(dataset_type), dataset)
                
                if chosen_visualizer is None:
                    raise DMPlotCreationError(f"No visualizer found for dataset type: {dataset_type}")
                
                visualizer_plots = chosen_visualizer.create_plots()
                
                plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())

            plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE, onlychanged=False)
            # Set the active tab based on shared state or default
            plots_tab.active = app_state.selected_tab_index_dataset or DEFAULT_TAB_INDEX
            
            # Update UI
            self._main.update(plots_tab)
            self._left_sidebar.remove_dataset_info()
            self._left_sidebar.add_component(self._all_dataset_info[DEFAULT_TAB_INDEX])
            
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