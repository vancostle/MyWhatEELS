from whateels.base.mvc.base_view import BaseView
from typing import TYPE_CHECKING, Optional
from whateels.components import FileDropper
from whateels.helpers import CSS_ROOT

import panel as pn

if TYPE_CHECKING:
    from ..model import HomePageModel
    
class HomePageView(BaseView):
    
    def __init__(self, model: "HomePageModel"):
        super().__init__(
            model,
            css_files=[
                str(CSS_ROOT / "home.css"),
                str(CSS_ROOT / "dataset_info.css")
            ],
        )
        
        # Initialize layout components
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None
        self._file_dropper: Optional[FileDropper] = None

        # Initialize visualization components and layouts
        self._init_components()
        
    from typing import Optional

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    @property
    def file_dropper(self) -> Optional[FileDropper]:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper


    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component
        
    def _init_components(self):
        self.sidebar = self._sidebar_layout()
        self.main = self._main_layout()
        
    def _sidebar_layout(self):
        file_dropper: FileDropper = FileDropper()

        if model_file_dropper := getattr(self._model, 'file_dropper', None):
            file_dropper = FileDropper(
                valid_extensions=model_file_dropper.VALID_EXTENSIONS,
                reject_message=model_file_dropper.REJECT_MESSAGE,
                success_message=model_file_dropper.SUCCESS_MESSAGE,
                feedback_message=model_file_dropper.FEEDBACK_MESSAGE,
            )      
  
        self._file_dropper = file_dropper
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