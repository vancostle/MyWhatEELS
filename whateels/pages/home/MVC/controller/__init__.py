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
from whateels.errors.hspy.data import (
    HSpyFileLoadingError,
    HSpyFileUploadError,
    HSpyShapeMismatchError,
)
from whateels.errors.npy.data import (
    NpyFileLoadingError,
    NpyFileUploadError,
    NpyShapeMismatchError,
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

        # Set up callbacks for file uploader events
        self._view.left_sidebar.file_uploader.on_file_uploaded_callback = self._handle_file_upload
        self._view.left_sidebar.file_uploader.on_file_removed_callback = self._handle_file_removal
        
        if all_datasets := getattr(self._model.app_state, "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._view.create_tab_and_dataset_info(all_datasets)
            
    def _handle_file_upload(self, filename: str, file_path: str):
        """
        Handle complete file upload workflow: process file → create visualizations → update UI.
        """
        self._view.cleanup_plots()

        if filename.endswith('.emd'):
            print('You just uploaded a .emd file.')
        elif filename.endswith(('.npy', '.npz')):
            try:
                self._prepare_for_upload(filename)
                all_datasets = NpyProcessorService(self._model).process_upload(filename, file_path)
                self._finish_upload(all_datasets)
            except (NpyFileLoadingError, NpyFileUploadError, NpyShapeMismatchError) as e:
                self._view.main.error_placeholder()
                raise e
            except Exception as e:
                self._view.main.error_placeholder()
                raise NpyFileUploadError(e)
            
        elif filename.endswith('.hspy'):
            try:
                self._prepare_for_upload(filename)
                all_datasets = RosettaFileProcessorService(self._model).process_upload(filename, file_path)
                self._finish_upload(all_datasets)
            except (HSpyFileLoadingError, HSpyFileUploadError, HSpyShapeMismatchError) as e:
                self._view.main.error_placeholder()
                raise e
            except Exception as e:
                self._view.main.error_placeholder()
                raise HSpyFileUploadError(e)
        elif filename.endswith(('.dm3', '.dm4')):
            try:
                self._prepare_for_upload(filename)
                all_datasets, used_fallback = self._process_with_fallback(filename, file_path)
                self._finish_upload(all_datasets, used_fallback=used_fallback)
            except (DMFileLoadingError, DMFileUploadError, DMShapeMismatchError) as e:
                self._view.main.error_placeholder()
                raise e
            except Exception as e:
                self._view.main.error_placeholder()
                raise DMFileUploadError(e)

    def _prepare_for_upload(self, filename: str) -> None:
        """Clear state and show loading indicator before processing."""
        app_state = self._model.app_state
        app_state.clear_all()
        app_state.filename = filename
        self._view.main.loading_placeholder()

    def _finish_upload(self, all_datasets: "list[Dataset]", used_fallback: bool = False) -> None:
        """Store datasets and update the view after successful processing."""
        app_state = self._model.app_state
        app_state.all_datasets = all_datasets
        if not all_datasets:
            self._view.main.error_placeholder()
            return
        self._view.create_tab_and_dataset_info(all_datasets, used_fallback=used_fallback)

    def _process_with_fallback(self, filename: str, file_path: str) -> "tuple[list[Dataset], bool]":
        """Try own parser first; fall back to RosettaSciIO if it raises.

        Returns:
            (datasets, used_fallback)

        Raises:
            DMFileUploadError: If both parsers fail, with context from both errors.
        """

        try:
            return FileProcessorService(self._model).process_upload(filename, file_path), False
        # except Exception as primary_error:
            # try:
            #     return RosettaFileProcessorService(self._model).process_upload(filename, file_path), True
            # except Exception as fallback_error:
            #     raise DMFileUploadError(
            #         f"Both parsers failed for '{filename}'.\n"
            #         f"  Own parser:  {primary_error}\n"
            #         f"  RosettaSciIO: {fallback_error}"
            #     ) from fallback_error
        except Exception as e:
            raise Exception(f"Error in _process_with_fallback: {e}")

    def _handle_file_removal(self, filename: str) -> None:
        """
        Handle file removal: cleanup UI, clear datasets, reset application state.
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
