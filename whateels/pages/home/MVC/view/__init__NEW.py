from whateels.base.mvc.base_view import BaseView
from typing import TYPE_CHECKING
from whateels.components import FileDropper
from whateels.helpers import CSS_ROOT

import panel as pn

if TYPE_CHECKING:
    from ..model import Model
    
class HomePageView(BaseView):
    
    def __init__(self, model: "Model"):
        super().__init__(
            css_files=[
                str(CSS_ROOT / "home.css"),
                str(CSS_ROOT / "dataset_info.css")
            ],
        )
        self._model = model
        
        # Initialize layout components to None
        self._dataset_info_layout = None
        self._loading_placeholder = None
        self._no_file_placeholder = None
        self._error_placeholder = None
        self._file_dropper = None
        
        # Initialize visualization components and layouts
        self._init_components()
        
    @property
    def dataset_info(self) -> pn.viewable.Viewable:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    @property
    def file_dropper(self) -> FileDropper:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper
    
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable or None)."""
        if component is not None and not isinstance(component, pn.viewable.Viewable):
            raise ValueError("Component must be a Panel Viewable")
        self._dataset_info_layout = component
        
    def _init_components(self):
        self._no_file_placeholder = pn.pane.HTML(
            self._model.placeholders.NO_FILE_LOADED,
            sizing_mode=self.STRETCH_BOTH
        )
        self._loading_placeholder = pn.Column(
            pn.pane.HTML(
                self._model.placeholders.LOADING_FILE,
                sizing_mode=self.STRETCH_BOTH
            ),
            sizing_mode=self.STRETCH_BOTH,
        )
        self._error_placeholder = pn.pane.HTML(
            self._model.placeholders.ERROR_FILE,
            sizing_mode=self.STRETCH_BOTH
        )
        self.sidebar = self._sidebar_layout()
        self.main = self._main_layout()
        
    def _sidebar_layout(self):
        file_dropper = FileDropper(
            valid_extensions=self._model.file_dropper.VALID_EXTENSIONS,
            reject_message=self._model.file_dropper.REJECT_MESSAGE,
            success_message=self._model.file_dropper.SUCCESS_MESSAGE,
            feedback_message=self._model.file_dropper.FEEDBACK_MESSAGE,
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