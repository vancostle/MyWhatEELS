import panel as pn, pickle, re
from bokeh.models import Tooltip

from whateels.components import FileUploader

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Clustering2PageModel

class Clustering2LeftSidebarLayout(pn.Column):
    def __init__(self, model: "Clustering2PageModel", **kwargs):
        self._model = model
        self._data_info_panel = pn.pane.Markdown("", margin=(10, 0, 0, 0))
        
        self._file_uploader = FileUploader(
            on_file_uploaded_callback=self._on_file_uploaded,
            on_file_removed_callback=self._on_file_removed,
            valid_extensions=(".pkl",),
        )
        
        super().__init__(
            pn.Row(
                pn.pane.Markdown(
                    "### Upload your data here", 
                    margin=(0, 0, 0, 4), 
                    styles={"padding": "0"}
                ),
                pn.widgets.TooltipIcon(
                    value=Tooltip(
                        content="Upload a .pkl file that you have previously downloaded from the 'Download Results' button after computing UMAP embeddings.", 
                        position="right"
                )),
                margin=0
            ),
            pn.Spacer(height=10),
            self._file_uploader,
            self._data_info_panel,
            **kwargs
        )
    
    def _on_file_uploaded(self, _: str, content: bytes):
        """Handle .pkl file upload and display content."""
        self._model.loaded_umap_data = pickle.loads(content)
        
        try:
            if not hasattr(self._model.loaded_umap_data, 'embedding_'):
                raise ValueError("The loaded data does not contain a valid UMAP embedding.")                        
        except Exception as e:
            self._data_info_panel.object = f"**Error processing file**: {str(e)}"
    
    def _on_file_removed(self, _: str):
        """Handle file removal."""
        self._model.loaded_umap_data = None
        self._data_info_panel.object = ""
