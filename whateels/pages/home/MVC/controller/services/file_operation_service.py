"""
File Operation Service for handling all file-related operations.

Centralizes file upload, removal, and state management logic.
Coordinates between file processing and UI updates.
"""

import traceback, panel as pn

from .eels_file_processor_service import EELSFileProcessorService
from .eels_data_processor_service import EELSDataProcessorService
from ..eels_plot_factory import EELSPlotFactory
from whateels.shared_state import AppState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model
    from .. import Controller
    from xarray import Dataset

class FileOperationService:
    """
    Service responsible for coordinating all file operations.
    
    Handles:
    - File upload workflow (processing, validation, UI updates)
    - File removal workflow (cleanup, UI reset)
    - Error handling and recovery
    - Coordination between file processing and plot creation
    """

    def __init__(self, model: "Model", controller: "Controller"):
        """
        Initialize the FileOperationService.
        
        Args:
            model: The Model instance containing application state
            controller: Reference to the controller for accessing layout manager
        """
        self._model = model
        self._controller = controller
        
        # Initialize file processing services
        self._file_processor = EELSFileProcessorService(model)
        self._data_processor = EELSDataProcessorService(model)
    
    def handle_file_upload(self, filename: str, file_content: bytes) -> bool:
        """
        Handle the complete file upload workflow.
        
        Args:
            filename: Name of the uploaded file
            file_content: Binary content of the uploaded file
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            # Show loading state
            self._controller.layout.show_loading_placeholder_in_main_layout()
            
            dataset: Dataset | None
            all_datasets: list[Dataset] = []
            
            # Process the file
            dataset, all_datasets = self._file_processor.process_upload(filename, file_content)

            # TODO - DELETE IT
            if dataset is None:
                self._handle_file_upload_error(filename)
                return False
            
            if not all_datasets:
                self._handle_file_upload_error(filename)
                return False
            
            # Update model with new dataset
            self._model.dataset = dataset
            self._model.all_datasets = all_datasets
            
            # TODO - DELETE IT
            # Create plots and UI components
            # success = self._create_and_display_plots(dataset)
            # TODO - DELETE IT
            # if not success:
                # self._handle_file_upload_error(filename)
                # return False

            print("all datasets is a tuple:", isinstance(all_datasets, tuple))
            all_success = self._create_and_display_all_plots(all_datasets)

            if not all_success:
                self._handle_file_upload_error(filename)
                return False
            
            return True

        except Exception as e:
            print(f"Error during file upload: {e}")
            traceback.print_exc()
            self._handle_file_upload_error(filename)
            return False
    
    def handle_file_removal(self, filename: str) -> None:
        """
        Handle the complete file removal workflow.
        
        Args:
            filename: Name of the removed file
        """
        try:            
            # Clear the dataset from model
            self._model.dataset = None
            
            # Clear UI components
            self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.reset_main_layout()
            
            # Reset AppState metadata
            app_state = AppState()
            app_state.metadata = None
            
            # Clear any active spectrum reference
            if hasattr(self._controller.view, 'chosen_spectrum'):
                self._controller.view.chosen_spectrum = None
                
        except Exception as e:
            print(f"Error during file removal: {e}")
            traceback.print_exc()
            
    def _create_and_display_all_plots(self, all_datasets: list["Dataset"]) -> bool:
        DATASET_TYPE = 'dataset_type'

        try:
            eels_plot_factory = EELSPlotFactory(self._model, self._controller)
            plots_tab = pn.Tabs()

            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, None)

                # Create plots using the factory
                chosen_spectrum = eels_plot_factory.choose_spectrum(dataset_type, dataset)
                
                if chosen_spectrum is None:
                    return False
                
                # Store reference and create components
                self._controller.view.chosen_spectrum = chosen_spectrum
                spectrum_plots = chosen_spectrum.create_plots()
                
                plots_tab.append((dataset_type, spectrum_plots))
                
                
                # spectrum_dataset_info = chosen_spectrum.create_dataset_info()
                
            # Update UI
            # self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.update_main_layout(plots_tab)
            # self._controller.layout.add_component_to_sidebar_layout(spectrum_dataset_info)

            return True
        except Exception as e:
            print(f"Error creating all plots: {e}")
            traceback.print_exc()
            return False

    def _create_and_display_plots(self, dataset) -> bool:
        """
        Create EELS plots and update the UI.
        
        Args:
            dataset: The processed EELS dataset
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            dataset_type = dataset.attrs.get('dataset_type', None)
            
            # Create plots using the factory
            eels_plot_factory = EELSPlotFactory(self._model, self._controller)
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
            print(f"Error creating plots: {e}")
            traceback.print_exc()
            return False
    
    def _handle_file_upload_error(self, filename: str) -> None:
        """Handle file upload error by resetting UI state."""
        self._controller.layout.show_error_placeholder_in_main_layout()
