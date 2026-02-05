import panel as pn, pickle, re
from bokeh.models import Tooltip

from whateels.components import FileUploader

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Clustering2PageModel
    from .. import Clustering2PageView

class Clustering2LeftSidebarLayout(pn.Column):
    def __init__(self, model: "Clustering2PageModel", view: "Clustering2PageView", **kwargs):
        self._model = model
        self._view = view
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
    
    def _on_file_uploaded(self, filename: str, content: bytes):
        """Handle .pkl file upload and display content."""
        try:
            self._model.loaded_umap_data = pickle.loads(content)
            
            if not hasattr(self._model.loaded_umap_data, 'embedding_'):
                raise ValueError("The loaded data does not contain a valid UMAP embedding.")
            
            # Extract parameters from the loaded UMAP object
            umap_obj = self._model.loaded_umap_data
            min_dist = umap_obj.min_dist
            n_neighbors = umap_obj.n_neighbors
            
            # Create dict with the same format as computed data
            umap_data_dict = {
                f'umap_data_{min_dist}_{n_neighbors}': umap_obj
            }
            
            # Display info
            info_text = f"""
**Loaded UMAP Data:**
- **min_dist**: {min_dist}
- **n_neighbors**: {n_neighbors}
- **n_components**: {umap_obj.n_components}
- **metric**: {umap_obj.metric}
- **Embedding shape**: {umap_obj.embedding_.shape}
            """
            self._data_info_panel.object = info_text
            
            # Display the loaded data using view methods if view is available
            if self._view:
                combinations = [(min_dist, n_neighbors)]
                self._view.display_all_combination_placeholders(combinations)
                self._view.replace_placeholder_with_umap_embedding(0, min_dist, n_neighbors, umap_data_dict)
                pn.state.notifications.success(f"UMAP data displayed from {filename}", duration=5000)  # type: ignore
            
            print(f"✓ Loaded and displayed UMAP result from {filename}")
                        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self._data_info_panel.object = f"**Error processing file**: {str(e)}"
            print(f"Error processing pickle file: {e}")
            print(f"Full traceback:\n{error_details}")
    
    def _on_file_removed(self, _: str):
        """Handle file removal."""
        self._model.loaded_umap_data = None
        self._data_info_panel.object = ""
