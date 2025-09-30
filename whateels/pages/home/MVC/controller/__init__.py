from .services import *
from .managers import LayoutManager
from whateels.shared_state import AppState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import Model
    from ..view.__init__OLD import View

class Controller:
    """
    Controller class for the home page of the WhatEELS application.

    Responsibilities:
    - Orchestrate file upload and removal events
    - Coordinate between services (file processing, data processing, interaction handling)
    - Manage workflow and UI state transitions by instructing the View
    - Delegate business logic to specialized services
    """
    def __init__(self, model: "Model", view: "View"):
        self.model = model
        self.view = view

        # Initialize services
        self._file_workflow_service = FileWorkflowService(model, self)
        # Initialize manager
        self._layout_manager = LayoutManager(view, self, model)

        # Set up callbacks for file dropper events directly
        self.view.file_dropper.on_file_uploaded_callback = self._file_workflow_service.handle_file_upload
        self.view.file_dropper.on_file_removed_callback = self._file_workflow_service.handle_file_removal
        
        # Initial layout setup based on existing datasets
        all_datasets = AppState().all_datasets
        if all_datasets:
            self._layout_manager.create_tab_and_dataset_info(all_datasets)

    @property
    def layout(self) -> LayoutManager:
        """Expose the layout manager for external use."""
        return self._layout_manager