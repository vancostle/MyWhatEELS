import panel as pn
from typing import TYPE_CHECKING

from whateels.errors.dm.data import DMPlotCreationError
from ..visualizer_factory import VisualizerFactory
from whateels.shared_state import AppState

if TYPE_CHECKING:
    from ...view import QuantificationView
    from ...view.visualizers.abstract_eels_visualizer import AbstractEELSVisualizer
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
        self._chosen_visualizers: list[AbstractEELSVisualizer] = []
        
    def add_component_to_sidebar_layout(self, component: pn.viewable.Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self._view.left_sidebar.append(component)
        self._view.dataset_info = component
        
    def remove_dataset_info_from_sidebar(self):
        """Remove the last dataset info component from the sidebar, if present."""
        if self._view.dataset_info is None:
            return
        if self._view.dataset_info in self._view.left_sidebar:
            self._view.left_sidebar.remove(self._view.dataset_info)
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
        DEFAULT_TAB_INDEX = 0

        app_state = AppState()

        try:
            # Clear previous dataset info panels to prevent caching old data
            self._all_dataset_info.clear()
            
            visualizer_factory = VisualizerFactory(self._model, self._controller)
            self._plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)
            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                print(self._chosen_visualizers)
                chosen_visualizer = visualizer_factory.choose_visualizer(str(dataset_type), dataset)
                self._chosen_visualizers.append(chosen_visualizer)
                print(f"Chosen visualizer for dataset '{image_name}': {type(chosen_visualizer).__name__}")
                if chosen_visualizer is None:
                    return
                visualizer_plots = chosen_visualizer.create_plots()
                
                self._plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            self._plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE, onlychanged=False)
            # Set the active tab based on shared state or default
            self._plots_tab.active = app_state.selected_tab_index_dataset or DEFAULT_TAB_INDEX
            
            # Update UI
            self._controller.base_layout.update_main(self._plots_tab)
            self.remove_dataset_info_from_sidebar()
            self.add_component_to_sidebar_layout(self._all_dataset_info[DEFAULT_TAB_INDEX])

        except Exception as e:
            raise DMPlotCreationError(e)
    def get_energy_range(self) -> list[float]:
        """Get the maximum energy range across all datasets."""
        return self._chosen_visualizers[AppState().selected_tab_index_dataset]._dataset.coords[self._model.constants.ELOSS].values

    
    def get_active_dataset(self):
        return self._chosen_visualizers[AppState().selected_tab_index_dataset]._dataset

    def _on_tab_with_visualizers_change(self, event):
        """Handle tab changes by updating sidebar with selected dataset info."""

        # Get the selected tab index
        selected_tab_index = event.new

        AppState().selected_tab_index_dataset = selected_tab_index  # Update shared state

        # Update sidebar with the corresponding dataset info
        self._controller.layout.remove_dataset_info_from_sidebar()
        self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[selected_tab_index])

    def add_new_element_input(self, element_input_view: pn.viewable.Viewable):
        """Add a new element input component to the sidebar."""
        self._view.element_item_view_container.append(element_input_view)
    
    def plot_quantification_elements(self, element_items: list["ElementItem"], loader_OOS: "Loader_OOS"):
        """Plot the quantification elements using the model's plotting method."""
        self.element_quant_data, shell_start= self._chosen_visualizers[0].plot_quantification_elements(loader_OOS, element_items) # change to active visualitzer later
        self._controller.base_layout.update_main(self._plots_tab)
        return shell_start

    def plot_quantification_element(self, element_item: "ElementItem"):
        """Plot a single quantification element using the model's plotting method."""
        print ("Plotting quantification element...")
        self.element_quant_data= self._chosen_visualizers[0].plot_quantification_element(element_item)

    def plot_shells_cross_section(self, element_item: "ElementItem"):
        print ("Plotting shells")
        self._chosen_visualizers[0].plot_shells_cross_section(element_item)

    def plot_quantification_pie(self):
        """Plot the quantification pie chart using the model's plotting method."""
        print ("Plotting quantification pie chart...")
        self._chosen_visualizers[0].plot_quantification_pie(self._model.app_state.quantification_elements)