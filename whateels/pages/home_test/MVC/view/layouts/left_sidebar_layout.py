import panel as pn

from whateels.helpers.constants import ASSETS_ROOT
from whateels.components import FileDialogUploader

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import HomePageModel  

class HomePageLeftSidebar(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel", **kwargs):
        self._model = model
        
        self._dataset_info = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._welcome_message = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        
        super().__init__(
            self._create_layout(),
            **kwargs
        )

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
        self._file_dialog_uploader = FileDialogUploader(
            default_message="Click to select a dm3 or dm4 file",
            on_file_uploaded_callback=lambda filename, payload: print(f"File uploaded: {filename} ({payload})"),  # Placeholder callback, replace with actual handler
            on_file_removed_callback=lambda filename: print(f"File removed: {filename}"),  # Placeholder callback, replace with actual handler
        )

        self._welcome_message = pn.Column(
            pn.pane.Markdown(
                """
                ### Welcome to WhatEELS!
                
                Relax, get yourself a cup of coffee  
                and get ready to analyse some EELS data.
                """,
                sizing_mode=self._STRETCH_WIDTH
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
            self._file_dialog_uploader,
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
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
            