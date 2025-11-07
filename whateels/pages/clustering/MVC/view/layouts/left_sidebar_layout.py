import panel as pn

from whateels.components import UploadedFile
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import ClusteringModel

class ClusteringLeftSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "ClusteringModel"):
        self._model = model
        
        self._dataset_info = None  # Reserve for dataset info component
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_WIDTH
        )
        
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
        """Create the left sidebar layout structure."""
        uploaded_file = UploadedFile(
            filename=str(self._model.get_uploaded_filename()), 
            sizing_mode=self._STRETCH_WIDTH, 
            margin=(0,0,10,0)
        )
        return pn.Column(
            uploaded_file,
            sizing_mode=self._STRETCH_WIDTH
        )
        
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