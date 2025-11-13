from whateels.base.mvc.base_view import BaseView
from typing import TYPE_CHECKING
from whateels.components import FileDropper
from whateels.helpers import CSS_ROOT

import panel as pn

if TYPE_CHECKING:
    from ..model import HomePageModel
    
class HomePageView(BaseView):
    
    def __init__(self, model: "HomePageModel"):
        self._model = model

        super().__init__(
            model,
            css_files=[
                str(CSS_ROOT / "home.css"),
                str(CSS_ROOT / "dataset_info.css")
            ],
        )
        
        # Initialize layout components
        self._dataset_info_layout = pn.Column(sizing_mode=self.STRETCH_WIDTH)
        self._file_dropper = FileDropper()

        # Initialize visualization components and layouts
        self._init_components()

    @property
    def dataset_info(self) -> pn.Column:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    @property
    def file_dropper(self) -> FileDropper:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper

    @dataset_info.setter
    def dataset_info(self, component: pn.Column):
        """Set the last dataset info component (must be a Panel Column)."""
        self._dataset_info_layout = component
        
    def _init_components(self):
        self.left_sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        
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
            sizing_mode=self.STRETCH_WIDTH
        )
        return self._sidebar_container_layout

    def _main_layout(self):
        self._main_container_layout = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self.STRETCH_BOTH
        )
        return self._main_container_layout