from .services import *

from whateels.errors.dm.data import (
    DMFileLoadingError,
    DMFileUploadError,
    DMShapeMismatchError,
    DMFileRemovalError,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import HomePageModel
    from ..view import HomePageView
    from xarray import Dataset

class HomePageController:
    """
    Controller class for the home page of the WhatEELS application.

    Responsibilities:
    - Orchestrate file upload and removal events
    - Coordinate between services (file processing, data processing, interaction handling)
    - Manage workflow and UI state transitions by instructing the View
    - Delegate business logic to specialized services
    """
    def __init__(self, model: "HomePageModel", view: "HomePageView"):
        self._model = model
        self._view = view
        
        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        self._data_processor = DataProcessorService(model)

        if file_uploader := getattr(self._view.left_sidebar, "file_uploader", None):
            # Set up callbacks for file uploader events directly
            file_uploader.on_file_uploaded_callback = self._handle_file_upload
            file_uploader.on_file_removed_callback = self._handle_file_removal
        else:
            raise AttributeError("HomePageView is missing 'file_uploader' attribute.")
        
        if all_datasets := getattr(self._model.app_state, "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._view.create_tab_and_dataset_info(all_datasets)
            
    def _handle_file_upload(self, filename: str, file_content: bytes):
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
                self._view.main.error_placeholder()
                return
            
            self._view.create_tab_and_dataset_info(all_datasets)

        except DMFileLoadingError as e:
            self._view.main.error_placeholder()
            raise e
        except DMFileUploadError as e:
            self._view.main.error_placeholder()
            raise e
        except DMShapeMismatchError as e:
            self._view.main.error_placeholder()
            raise e
        except Exception as e:
            self._view.main.error_placeholder()
            raise DMFileUploadError(e)
        
        
    def _handle_file_removal(self, filename: str) -> None:
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
            
            # Reset FileUploader to initial state (hide success/error panels)
            
            # Clear in-memory file to free resources
            del self._model.in_memory_file
            
            # Clear global AppState data
            self._model.app_state.clear_all()

        except Exception as e:
            raise DMFileRemovalError(e)