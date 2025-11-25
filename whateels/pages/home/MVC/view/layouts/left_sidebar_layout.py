import panel as pn

from whateels.components import FileDropper

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import HomePageModel

class HomePageLeftSidebar(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel"):
        self._model = model
        
        self._dataset_info = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._file_dropper = FileDropper()
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_WIDTH
        )

    @property
    def file_dropper(self) -> FileDropper:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper
    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info = component
    @dataset_info.deleter
    def dataset_info(self):
        """Delete the dataset info component."""
        self._dataset_info = None

    def _create_layout(self) -> pn.Column:
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