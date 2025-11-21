from whateels.base.mvc.base_view import BaseView
from whateels.helpers import LoadCSS
from typing import TYPE_CHECKING
from whateels.components import FileDropper
from whateels.helpers import CSS_ROOT

import panel as pn

if TYPE_CHECKING:
    from ..model import HomePageModel
    
class HomePageView:
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"
    
    def __init__(self, model: "HomePageModel"):
        self._model = model
        
        # Load any provided CSS files
        css_files = [
            str(CSS_ROOT / "home.css"),
            str(CSS_ROOT / "dataset_info.css")
        ]

        LoadCSS(css_files)
        
        # Initialize placeholders
        self._loading_placeholder = pn.pane.HTML(
            model.placeholders.LOADING_FILE,
            sizing_mode=self._STRETCH_BOTH
        )
        self._no_file_placeholder = pn.pane.HTML(
            model.placeholders.NO_FILE_LOADED,
            sizing_mode=self._STRETCH_BOTH
        )
        self._error_placeholder = pn.pane.HTML(
            model.placeholders.ERROR_FILE,
            sizing_mode=self._STRETCH_BOTH
        )
        
        # Initialize layout components
        self._dataset_info_layout = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._file_dropper = FileDropper()
        
        # Layout components
        self._main = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
        self._left_sidebar = self._left_sidebar_layout()

    @property
    def dataset_info(self) -> pn.Column:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    @property
    def file_dropper(self) -> FileDropper:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper
    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def left_sidebar(self) -> pn.Column:
        """Left sidebar layout for controls and options."""
        return self._left_sidebar
    @property
    def loading_placeholder(self) -> pn.pane.HTML:
        """Loading placeholder layout for displaying loading messages."""
        return self._loading_placeholder
    @property
    def no_file_placeholder(self) -> pn.pane.HTML:
        """No-file placeholder layout for displaying no file loaded messages."""
        return self._no_file_placeholder
    @property
    def error_placeholder(self) -> pn.pane.HTML:
        """Error placeholder layout for displaying error messages."""
        return self._error_placeholder

    @dataset_info.setter
    def dataset_info(self, component: pn.Column):
        """Set the last dataset info component (must be a Panel Column)."""
        self._dataset_info_layout = component
        
    def _left_sidebar_layout(self):
        # Set up the FileDropper with model constants
        self._file_dropper: FileDropper = FileDropper(
            valid_extensions=self._model.constants.FILE_DROPPER_VALID_EXTENSIONS,
            reject_message=self._model.constants.FILE_DROPPER_REJECT_MESSAGE,
            success_message=self._model.constants.FILE_DROPPER_SUCCESS_MESSAGE,
            feedback_message=self._model.constants.FILE_DROPPER_FEEDBACK_MESSAGE,
        )     
  
        self._sidebar_container_layout = pn.Column(
            self._file_dropper,
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return self._sidebar_container_layout
    
    @main.deleter
    def main(self):
        """Delete the main content area layout."""
        self._main.clear()