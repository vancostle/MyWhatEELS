import panel as pn
from typing import TYPE_CHECKING

from whateels.errors.dm.data import DMPlotCreationError
from ..visualizer_factory import VisualizerFactory

if TYPE_CHECKING:
    from ...view import QuantificationView
    from ...model import QuantificationModel
    from ...controller import QuantificationController
    from xarray import Dataset
    from ...controller.services.oos_loader_service import Loader_OOS
    from ...controller import ElementItem

class LayoutManager:
    """
    Manager class responsible for handling all layout operations in the WhatEELS application.
    
    This class encapsulates all UI layout management functionality, including:
    - Main layout state management (loading, error, content, placeholder states)
    - Sidebar component management
    - Float panel operations
    
    By separating layout concerns from the main Controller, we achieve better
    code organization and single responsibility principle.
    """
    
    def __init__(self, view: "QuantificationView", controller: "QuantificationController", model: "QuantificationModel"):
        """
        Initialize the LayoutManager with a reference to the View.
        
        Args:
            view: The View instance that contains the UI components to manage
        """
        self._view = view
        self._controller = controller
        self._model = model

        # Store all dataset information
        self._all_dataset_info: list[pn.viewable.Viewable] = []
        self._max_energy_range = [float('inf'), float('-inf')]
        self._plots_tab = None
        self._chosen_visualizers = []
        
    def add_component_to_sidebar_layout(self, component: pn.viewable.Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self._view.left_sidebar.append(component)
        self._view.dataset_info = component
        
    def remove_dataset_info_from_sidebar(self):
        """Remove the last dataset info component from the sidebar, if present."""
        if self._view.dataset_info is None:
            return
        if self._view.dataset_info in self._view.sidebar:
            self._view.sidebar.remove(self._view.dataset_info)
            self._view.dataset_info = None
            
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
            
            visualizer_factory = VisualizerFactory(self._model, self._controller)
            self._plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)
            self._max_energy_range = [float('inf'), float('-inf')]
            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_visualizer = visualizer_factory.choose_visualizer(str(dataset_type), dataset)
                self._chosen_visualizers.append(chosen_visualizer)
                print(f"Chosen visualizer for dataset '{image_name}': {type(chosen_visualizer).__name__}")
                if chosen_visualizer is None:
                    return
                if dataset_type == 'SIm':
                    energy_axis = chosen_visualizer.get_e_axis()
                    self._max_energy_range[0] = min(self._max_energy_range[0], energy_axis[0])
                    self._max_energy_range[1] = max(self._max_energy_range[1], energy_axis[-1])
                visualizer_plots = chosen_visualizer.create_plots()
                
                self._plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            self._plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE)
                
            # Update UI
            self._controller.base_layout.update_main(self._plots_tab)
            self.remove_dataset_info_from_sidebar()
            self.add_component_to_sidebar_layout(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)
    def get_max_energy_range(self) -> list[float]:
        """Get the maximum energy range across all datasets."""
        return self._max_energy_range

    def _on_tab_with_visualizers_change(self, event):
        """Handle tab changes by updating sidebar with selected dataset info."""

        new_tab = event.new
        self._controller.layout.remove_dataset_info_from_sidebar()
        self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[new_tab])

    def add_new_element_input(self, element_input_view: pn.viewable.Viewable):
        """Add a new element input component to the sidebar."""
        self._view.element_item_view_container.append(element_input_view)
    
    def plot_quantification_elements(self, element_items: list["ElementItem"], loader_OOS: "Loader_OOS"):
        """Plot the quantification elements using the model's plotting method."""
        visualizer_plots = self._chosen_visualizers[0].plot_quantification_elements(loader_OOS, element_items)
        self._plots_tab[0][1] = visualizer_plots
        self._plots_tab.__setitem__()
        self._controller.base_layout.update_main(self._plots_tab)