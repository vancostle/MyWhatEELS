import panel as pn
from typing import TYPE_CHECKING, override

from whateels.errors.dm.data import DMPlotCreationError
from ..visualizer_factory import VisualizerFactory
from panel.viewable import Viewable
if TYPE_CHECKING:
    from ...view import HomePageView
    from ...model import HomePageModel
    from ...controller import HomePageController
    from xarray import Dataset

class HomePageLayoutManager:
    """
    Manager class responsible for handling all layout operations in the WhatEELS application.
    
    This class encapsulates all UI layout management functionality, including:
    - Main layout state management (loading, error, content, placeholder states)
    - Sidebar component management
    - Float panel operations
    
    By separating layout concerns from the main Controller, we achieve better
    code organization and single responsibility principle.
    """
    
    def __init__(self, view: "HomePageView", controller: "HomePageController", model: "HomePageModel"):
        """
        Initialize the LayoutManager with a reference to the HomePageView.
        
        Args:
            view: The HomePageView instance that contains the UI components to manage
        """        
        self._view = view
        self._controller = controller
        self._model = model

        # Store all dataset information
        self._all_dataset_info: list[Viewable] = []
    
    @override
    def add_component_to_sidebar_layout(self, component: Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self._view.sidebar.append(component)
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
            plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, None)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_visualizer = visualizer_factory.choose_visualizer(dataset_type, dataset)
                
                if chosen_visualizer is None:
                    return
                
                visualizer_plots = chosen_visualizer.create_plots()
                
                plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE)
                
            # Update UI
            self._controller.base_layout.update_main(plots_tab)
            self.remove_dataset_info_from_sidebar()
            self.add_component_to_sidebar_layout(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)

    def _on_tab_with_visualizers_change(self, event):
        """Handle tab changes by updating sidebar with selected dataset info."""

        new_tab = event.new
        print(new_tab)
        self._controller.layout.remove_dataset_info_from_sidebar()
        self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[new_tab])