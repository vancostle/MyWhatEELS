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
        
        print(f"File content received of length: {len(file_content) / (1024 * 1024):.2f} MB")

        try:
            # Show loading state
            self._controller.layout.show_loading_placeholder_in_main_layout()
            
            all_datasets: list[Dataset] = []
            
            # Process the file
            all_datasets = self._file_processor.process_upload(filename, file_content)
            
            # Calculate total size of all datasets in MB
            total_size_bytes = sum(dataset.nbytes for dataset in all_datasets)
            total_size_mb = total_size_bytes / (1024 * 1024)
            print(f"Processed {len(all_datasets)} dataset(s) with total size: {total_size_mb:.2f} MB")
            
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
                
        except Exception as e:
            raise DMFileRemovalError(e)

    
    def _handle_file_upload_error(self, filename: str) -> None:
        """Handle file upload errors by showing error UI state."""
        self._controller.layout.show_error_placeholder_in_main_layout()
