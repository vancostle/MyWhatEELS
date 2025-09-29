"""
Dataset Workflow Manager for EELS data processing and visualization.

Orchestrates file upload → processing → validation → visualization workflows.
Coordinates between file processing, data processing, and visualization services.
"""

from .file_processor_service import FileProcessorService
from .data_processor_service import DataProcessorService
from whateels.shared_state import AppState
from whateels.errors.dm.data import (
    DMFileLoadingError, 
    DMFileUploadError, 
    DMShapeMismatchError,
    DMFileRemovalError,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model
    from .. import Controller
    from xarray import Dataset

class FileWorkflowService:
    """
    Orchestrates EELS dataset workflows from file upload to visualization.
    
    Coordinates file processing, data processing, and visualization services.
    Manages UI state transitions and error handling for the complete pipeline.
    """

    def __init__(self, model: "Model", controller: "Controller"):
        """
        Initialize with model and controller dependencies.
        
        Args:
            model: Application model for state and data access
            controller: Controller for layout manager access
        """
        self._model = model
        self._controller = controller

        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        self._data_processor = DataProcessorService(model)
    
    def handle_file_upload(self, filename: str, file_content: bytes) -> bool:
        """
        Handle complete file upload workflow: process file → create visualizations → update UI.
        
        Args:
            filename: Uploaded file name
            file_content: Binary file content
            
        Returns:
            bool: True if successful, False if failed
            
        Raises:
            DMFileLoadingError, DMFileUploadError, DMShapeMismatchError
        """

        try:
            # Clear previous dataset info panels to prevent caching old data
            AppState().all_datasets = []

            all_datasets: list[Dataset] = []
            
            # Show loading state
            self._controller.layout.show_loading_placeholder_in_main_layout()
            
            # Process the file
            all_datasets = self._file_processor.process_upload(filename, file_content)

            # Update AppState with all loaded datasets for global access
            AppState().all_datasets = all_datasets
            
            if not all_datasets:
                self._handle_file_upload_error(filename)
                return False
            
            self._controller.layout.create_tab_and_dataset_info(all_datasets)
            
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
        Handle file removal: cleanup UI, clear datasets, reset application state.
        
        Args:
            filename: Name of removed file
            
        Raises:
            DMFileRemovalError: When cleanup operations fail
        """

        try:
            # Clear UI components
            self._controller.layout.remove_dataset_info_from_sidebar()
            self._controller.layout.reset_main_layout()
            
            # Clear previous dataset info panels to prevent caching old data
            self._model.all_datasets = []
            
            # Clear in-memory file to free resources
            del self._model.in_memory_file
            
            # Reset AppState metadata
            AppState().metadata = None
            # Reset AppState datasets
            AppState().all_datasets = []
                
        except Exception as e:
            raise DMFileRemovalError(e)

    
    def _handle_file_upload_error(self, filename: str) -> None:
        """Handle file upload errors by showing error UI state."""
        self._controller.layout.show_error_placeholder_in_main_layout()
