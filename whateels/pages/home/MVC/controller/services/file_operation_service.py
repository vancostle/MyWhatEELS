"""
File Operation Service for handling all file-related operations.

Centralizes file upload, removal, and state management logic.
Coordinates between file processing and UI updates.
"""

import panel as pn

from .file_processor_service import FileProcessorService
from .data_processor_service import DataProcessorService
from ..visualizer_factory import VisualizerFactory
from whateels.shared_state import AppState
from whateels.errors.dm.data import (
    DMFileLoadingError, 
    DMFileUploadError, 
    DMShapeMismatchError,
    DMFileRemovalError,
    DMPlotCreationError
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model
    from .. import Controller
    from xarray import Dataset

class FileOperationService():
    """
    Service responsible for coordinating all file operations.
    
    Handles:
    - File upload workflow (processing, validation, UI updates)
    - File removal workflow (cleanup, UI reset)
    - Error handling and recovery
    - Coordination between file processing and plot creation
    """

    # _selected_image_tab = param.Integer(0, doc="Index of the currently selected image tab")

    def __init__(self, model: "Model", controller: "Controller"):
        """
        Initialize the FileOperationService.
        
        Args:
            model: The Model instance containing application state
            controller: Reference to the controller for accessing layout manager
        """
        self._model = model
        self._controller = controller

        # Store all dataset information
        self._all_dataset_info = []

        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        self._data_processor = DataProcessorService(model)
    
    def handle_file_upload(self, filename: str, file_content: bytes) -> bool:
        """
        Handle the complete file upload workflow.
        
        Args:
            filename: Name of the uploaded file
            file_content: Binary content of the uploaded file
            
        Returns:
            bool: True if successful, False if failed
        """

        # Clear previous dataset info panels to prevent caching old data
        self._model.all_datasets = []

        try:
            # Show loading state
            self._controller.layout.show_loading_placeholder_in_main_layout()
            
            all_datasets: list[Dataset] = []
            
            # Process the file
            all_datasets = self._file_processor.process_upload(filename, file_content)
            
            if not all_datasets:
                self._handle_file_upload_error(filename)
                return False
            
            self._model.all_datasets = all_datasets

            self._create_and_display_all_plots(all_datasets)
            
            return True

        except DMFileLoadingError as e:
            self._handle_file_upload_error(filename)
            raise e
        except DMFileUploadError as e:
            self._handle_file_upload_error(filename)
            raise e
        except DMShapeMismatchError as e:
            self._handle_file_upload_error(filename)
            raise e
        except Exception as e:
            self._handle_file_upload_error(filename)
            raise DMFileUploadError(e)
    
    def handle_file_removal(self, filename: str) -> None:
        """
        Handle the complete file removal workflow.
        
        Args:
            filename: Name of the removed file
            
        Raises:
            DMFileRemovalError: When file removal operations fail
        """
        CHOSEN_SPECTRUM = 'chosen_spectrum'

        try:
            # Clear UI components
            self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.reset_main_layout()
            
            # Clear previous dataset info panels to prevent caching old data
            self._model.all_datasets = []
            
            # Reset AppState metadata
            app_state = AppState()
            app_state.metadata = None
            
            # Clear any active spectrum reference
            if hasattr(self._controller.view, CHOSEN_SPECTRUM):
                self._controller.view.chosen_spectrum = None
                
        except Exception as e:
            raise DMFileRemovalError(e)
            
    def _create_and_display_all_plots(self, all_datasets: list["Dataset"]) -> None:
        """
        Create EELS plots and update the UI for all datasets.
        
        Args:
            all_datasets: List of processed datasets to create plots for
            
        Raises:
            DMPlotCreationError: When plot creation fails
        """
        DATASET_TYPE = 'dataset_type'
        IMAGE_NAME_ATTRIBUTE = 'image_name'
        NOT_AVAILABLE = 'N/A'
        ACTIVE = 'active'

        try:
            # Clear previous dataset info panels to prevent caching old data
            self._all_dataset_info.clear()
            
            visualizer_factory = VisualizerFactory(self._model, self._controller)
            plots_tab = pn.Tabs(styles={'border': '2px solid blue'}, sizing_mode='stretch_both')

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, None)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_spectrum = visualizer_factory.choose_spectrum(dataset_type, dataset)
                
                if chosen_spectrum is None:
                    return False
                
                # Store reference and create components
                self._controller.view.chosen_spectrum = chosen_spectrum
                spectrum_plots = chosen_spectrum.create_plots()
                
                plots_tab.append((image_name, spectrum_plots))
                
                # spectrum_dataset_info = chosen_spectrum.create_dataset_info()
                self._all_dataset_info.append(chosen_spectrum.create_dataset_info())
                
            plots_tab.param.watch(self._on_tab_change, ACTIVE)
                
            # Update UI
            self._controller.layout.update_main_layout(plots_tab)

            self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)

    def _on_tab_change(self, event):
        new_tab = event.new
        self._controller.layout.remove_dataset_info_from_sidebar()
        self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[new_tab])

    # TODO - DELETE IT
    def _create_and_display_plots(self, dataset) -> bool:
        """
        Create EELS plots and update the UI.
        
        Args:
            dataset: The processed EELS dataset
            
        Raises:
            DMPlotCreationError: When plot creation fails
        """
        DATASET_TYPE = 'dataset_type'

        try:
            dataset_type = dataset.attrs.get(DATASET_TYPE, None)

            # Create plots using the factory
            eels_plot_factory = VisualizerFactory(self._model, self._controller)
            chosen_spectrum = eels_plot_factory.choose_spectrum(dataset_type)
            
            if chosen_spectrum is None:
                return False
            
            # Store reference and create components
            self._controller.view.chosen_spectrum = chosen_spectrum
            spectrum_plots = chosen_spectrum.create_plots()
            spectrum_dataset_info = chosen_spectrum.create_dataset_info()
            
            # Update UI
            self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.update_main_layout(spectrum_plots)
            self._controller.layout.add_component_to_sidebar_layout(spectrum_dataset_info)
            
            return True
            
        except Exception as e:
            raise DMPlotCreationError(e)
    
    def _handle_file_upload_error(self, filename: str) -> None:
        """Handle file upload error by resetting UI state."""
        self._controller.layout.show_error_placeholder_in_main_layout()
