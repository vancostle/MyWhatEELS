import panel as pn

from whateels.components import UploadedFile
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....MVC import ClusteringModel

class ClusteringLeftSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "ClusteringModel"):
        self._model = model
        
        uploaded_file = UploadedFile(
            filename=str(self._model.get_uploaded_filename()), 
            sizing_mode=self._STRETCH_WIDTH, 
            margin=(0,0,10,0)
        )
        
        super().__init__(
            pn.Column(
                uploaded_file,
                sizing_mode=self._STRETCH_WIDTH
            ),
            sizing_mode=self._STRETCH_WIDTH
        )