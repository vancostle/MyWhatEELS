from .services import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import HomePageModel
    from ..view import HomePageView

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

        # Initialize services
        self._filedropper_workflow_service = FileDropperWorkflowService(model, self, view)

        if file_dropper := getattr(self._view.left_sidebar, "file_dropper", None):
            # Set up callbacks for file dropper events directly
            file_dropper.on_file_uploaded_callback = self._filedropper_workflow_service.handle_file_upload
            file_dropper.on_file_removed_callback = self._filedropper_workflow_service.handle_file_removal
        else:
            raise AttributeError("HomePageView is missing 'file_dropper' attribute.")
        
        if all_datasets := getattr(self._model.app_state, "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._view.create_tab_and_dataset_info(all_datasets)