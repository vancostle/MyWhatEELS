import panel as pn
from bokeh.models import Tooltip

from whateels.components import FileUploader

class Clustering2LeftSidebarLayout(pn.Column):
    def __init__(self, **kwargs):
        self._file_uploader = FileUploader(
            on_file_uploaded_callback=lambda filename, content: print("File uploaded in left sidebar (placeholder callback)"),
            on_file_removed_callback=lambda _ : print("File removed in left sidebar (placeholder callback)"),
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
            **kwargs
        )
