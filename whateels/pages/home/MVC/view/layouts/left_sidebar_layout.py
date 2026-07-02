import panel as pn

from whateels.components import FileDialogUploader, InfoPanel
from whateels.helpers.constants import ASSETS_ROOT

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import HomePageModel  

class HomePageLeftSidebar(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel", **kwargs):
        self._model = model
        
        self._dataset_info = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._file_uploader: FileDialogUploader = FileDialogUploader() # Placeholder, will be set up below
        self._welcome_message = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        
        super().__init__(
            self._create_layout(),
            **kwargs,
        )

    @property
    def file_uploader(self) -> FileDialogUploader:
        """FileDialogUploader widget for file upload interactions."""
        return self._file_uploader
    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info
    @property
    def welcome_message(self) -> Optional[pn.viewable.Viewable]:
        """Welcome message component displayed in the sidebar."""
        return self._welcome_message
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info = component
    @dataset_info.deleter
    def dataset_info(self):
        """Delete the dataset info component."""
        self._dataset_info = None

    def _create_layout(self) -> pn.Column:
        """Create the sidebar layout with file uploader and spacing."""
        self._file_uploader = self._create_file_uploader()

        self._welcome_message = pn.Column(
            pn.pane.Markdown(
                """
                # TEST PAGE
                ### Welcome to WhatEELS!
                
                Relax, get yourself a cup of coffee  
                and get ready to analyse some EELS data.
                """,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            pn.pane.SVG(
                str(ASSETS_ROOT / 'img' / 'we_rainbow_logo.svg'),
                height=76,
                align="center"
            ),
            sizing_mode=self._STRETCH_WIDTH,
                margin=(0, 0, 20, 0)
        )

        self._path_input = None  # kept for potential future use
        self._sidebar_container_layout = pn.Column(
            self._file_uploader,
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["sidebar-container-layout"],
        )
        return self._sidebar_container_layout
        
    def add_component(self, component: pn.viewable.Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self.append(component)
        self.dataset_info = component

    def remove_dataset_info(self):
        """Remove the last dataset info component from the sidebar, if present."""
        if self.dataset_info is None:
            return
        if self.dataset_info in self:
            self.remove(self.dataset_info)
            del self.dataset_info
            
    def _create_file_uploader(self) -> FileDialogUploader:
        initial_filepath = ""
        all_datasets = self._model.app_state.all_datasets

        if isinstance(all_datasets, list) and len(all_datasets) > 0:
            # Datasets already in AppState (back-navigation): restore success state.
            # We only have the filename stored, not the full path, so we pass the
            # filename alone — the JS will display it but clipboard-copy won't have a path.
            filename_candidate = self._model.app_state.filename
            if isinstance(filename_candidate, str) and filename_candidate:
                initial_filepath = filename_candidate

        return FileDialogUploader(
            default_message=self._model.constants.FILE_DROPPER_TITLE,
            accepted_file_types=list(self._model.constants.FILE_DROPPER_VALID_EXTENSIONS),
            error_message=self._model.constants.FILE_DROPPER_REJECT_MESSAGE,
            initial_filepath=initial_filepath,
        )