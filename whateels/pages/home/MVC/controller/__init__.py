import weakref
import panel as pn
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

    # Track sessions that already have a cleanup callback registered.
    # Prevents accumulation of one callback per reload (N reloads → N callbacks).
    _sessions_with_cleanup: set = set()

    def __init__(self, model: "HomePageModel", view: "HomePageView"):
        self._model = model
        self._view = view
        
        # Register this controller as the active one on the (cached) model so
        # the next HomePage instantiation can call cleanup() before creating a new one.
        model.active_controller = self

        # Register a session-end cleanup once per session (not once per reload).
        # On session end, cleans up whatever controller is currently active on the model.
        self._register_session_cleanup_once(model)

        # Initialize file processing services
        self._file_processor = FileProcessorService(model)
        
        # Set up callbacks for file uploader events
        self._view.left_sidebar.file_uploader.on_file_uploaded_callback = self._handle_file_upload
        self._view.left_sidebar.file_uploader.on_file_removed_callback = self._handle_file_removal
        
        if all_datasets := getattr(self._model.app_state, "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._view.create_tab_and_dataset_info(all_datasets)

    @staticmethod
    def _register_session_cleanup_once(model: "HomePageModel") -> None:
        """Register a session-end cleanup callback at most once per session.

        Uses the Bokeh session ID so that multiple reloads within the same
        session don't keep piling up callbacks in Panel's internal list.
        """
        try:
            from bokeh.io import curdoc
            doc = curdoc()
            session_id = doc.session_context.id if doc.session_context else None
            if session_id is None:
                return
            if session_id in HomePageController._sessions_with_cleanup:
                return
            HomePageController._sessions_with_cleanup.add(session_id)
            _model_ref = weakref.ref(model)

            def _on_session_end(session_context):
                # Remove session from tracking set to free memory
                HomePageController._sessions_with_cleanup.discard(session_id)
                m = _model_ref()
                if m is not None and m.active_controller is not None:
                    m.active_controller.cleanup()
                    m.active_controller = None

            pn.state.on_session_destroyed(_on_session_end)
        except Exception:
            pass
            
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
            # Stop streams and release dataset refs on all active plot instances
            # before clearing the UI — this is what actually frees the numpy memory.
            self._view.cleanup_plots()

            # Clear UI components
            self._view.left_sidebar.remove_dataset_info()
            self._view.main.empty_placeholder()
            
            # Clear in-memory file to free resources
            del self._model.in_memory_file
            
            # Clear global AppState data
            self._model.app_state.clear_all()

            # Clear homepage-specific AppState fields that other pages may also
            # write to, but which must be released here to free the numpy data.
            self._model.app_state.plot_dataset = None
            self._model.app_state.multifit = None

        except Exception as e:
            raise DMFileRemovalError(e)
    
    def cleanup(self):
        """Clean up resources before page reload or session end."""
        self._view.cleanup()
