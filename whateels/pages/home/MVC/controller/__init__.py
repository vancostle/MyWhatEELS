import weakref
import panel as pn
import gc
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

        # Register view cleanup when this session ends.
        # HomePageModel is created fresh each navigation (new Bokeh session each time),
        # so this registers exactly once per session — no duplicate guard needed.
        _view_ref = weakref.ref(view)
        pn.state.on_session_destroyed(lambda _: (v := _view_ref()) and v.cleanup())

        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        
        # Set up callbacks for file uploader events
        self._view.left_sidebar.file_uploader.on_file_uploaded_callback = self._handle_file_upload
        self._view.left_sidebar.file_uploader.on_file_removed_callback = self._handle_file_removal
        
        if all_datasets := getattr(self._model.app_state, "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._view.create_tab_and_dataset_info(all_datasets)
            
    def _handle_file_upload(self, filename: str, file_content: str):
        """
        Handle complete file upload workflow: process file → create visualizations → update UI.
        
        Args:
            filename: Uploaded file name
            file_content: Full local path to the selected file on disk
            
        Returns:
            bool: True if successful, False if failed
            
        Raises:
            DMFileLoadingError, DMFileUploadError, DMShapeMismatchError
        """

        try:
            # Release previous plot resources before loading a new file.
            self._view.cleanup_plots()

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
            # Stop streams and release dataset refs on all active plot instances
            # before clearing the UI — this is what actually frees the numpy memory.
            self._view.cleanup_plots()

            # Clear UI components
            self._view.left_sidebar.remove_dataset_info()
            self._view.main.empty_placeholder()
            self._view.right_sidebar.preprocessed_settings.clear()
            
            # Clear global AppState data
            self._model.app_state.clear_all()

            # Clear homepage-specific AppState fields that other pages may also
            # write to, but which must be released here to free the numpy data.
            self._model.app_state.plot_dataset = None
            self._model.app_state.multifit = None

            # Force GC to reclaim numpy arrays and HoloViews objects immediately
            gc.collect()

        except Exception as e:
            raise DMFileRemovalError(e)
    
    def cleanup(self):
        """Clean up resources before page reload or session end."""
        self._view.cleanup()
