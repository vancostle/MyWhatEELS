from .services import *
from .managers import HomePageLayoutManager
from whateels.shared_state import AppState
from whateels.base.mvc.base_controller import BaseController

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import HomePageModel
    from ..view import HomePageView

class HomePageController(BaseController):
    """
    Controller class for the home page of the WhatEELS application.

    Responsibilities:
    - Orchestrate file upload and removal events
    - Coordinate between services (file processing, data processing, interaction handling)
    - Manage workflow and UI state transitions by instructing the View
    - Delegate business logic to specialized services
    """
    def __init__(self, model: "HomePageModel", view: "HomePageView"):
        super().__init__(model, view)

        # Initialize services
        self._filedorpper_workflow_service = FileDropperWorkflowService(model, self)
        # Initialize manager
        self._layout_manager = HomePageLayoutManager(view, self, model)

        if file_dropper := getattr(self.view, "file_dropper", None):
            # Set up callbacks for file dropper events directly
            file_dropper.on_file_uploaded_callback = self._filedorpper_workflow_service.handle_file_upload
            file_dropper.on_file_removed_callback = self._filedorpper_workflow_service.handle_file_removal
        
        if all_datasets := getattr(AppState(), "all_datasets", None):
            # Initial layout setup based on existing datasets
            self._layout_manager.create_tab_and_dataset_info(all_datasets)

    @property
    def layout(self) -> HomePageLayoutManager:
        """Expose the layout manager for external use."""
        return self._layout_manager