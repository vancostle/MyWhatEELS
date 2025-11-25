"""
Dataset Workflow Manager for EELS data processing and visualization.

Orchestrates file upload → processing → validation → visualization workflows.
Coordinates between file processing, data processing, and visualization services.
"""

from .file_processor_service import FileProcessorService
from .data_processor_service import DataProcessorService
from whateels.errors.dm.data import (
    DMFileLoadingError, 
    DMFileUploadError, 
    DMShapeMismatchError,
    DMFileRemovalError,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel
    from .. import HomePageController
    from ...view import HomePageView
    from xarray import Dataset

class FileDropperWorkflowService:
    """
    Orchestrates EELS dataset workflows from file upload to visualization.
    
    Coordinates file processing, data processing, and visualization services.
    Manages UI state transitions and error handling for the complete pipeline.
    """

    def __init__(self, model: "HomePageModel", controller: "HomePageController", view: "HomePageView"):
        """
        Initialize with model and controller dependencies.
        
        Args:
            model: Application model for state and data access
            controller: Controller for layout manager access
        """
        self._model = model
        self._controller = controller
        self._view = view

        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        self._data_processor = DataProcessorService(model)
    
    def handle_file_upload(self, filename: str, file_content: bytes):
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
            # Clear any existing datasets and metadata
            app_state = self._model.app_state
            app_state.clear_all()
            
            app_state.filename = filename

            all_datasets: list[Dataset] = []
            
            # Show loading state
            self._view.main.loading_placeholder()
            
            # Process the file
            all_datasets = self._file_processor.process_upload(filename, file_content)

            # Update AppState with all loaded datasets for global access
            app_state.all_datasets = all_datasets
            
            if not all_datasets:
                self._handle_file_upload_error(filename)
                return
            
            self._view.create_tab_and_dataset_info(all_datasets)

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
            self._view.left_sidebar.remove_dataset_info()
            self._view.main.empty_placeholder()
            
            # Clear in-memory file to free resources
            del self._model.in_memory_file
            
            # Clear global AppState data
            self._model.app_state.clear_all()

        except Exception as e:
            raise DMFileRemovalError(e)

    def _handle_file_upload_error(self, filename: str) -> None:
        """Handle file upload errors by showing error UI state."""
        self._view.main.error_placeholder()
