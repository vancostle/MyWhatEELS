import panel as pn, pickle
from bokeh.models import Tooltip

from whateels.components import FileUploader, InfoPanel

from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ...model import Clustering2PageModel

class Clustering2LeftSidebarLayout(pn.Column):
    def __init__(self, model: "Clustering2PageModel", **kwargs):
        self._model = model
        self._on_umap_loaded_callback: Callable = lambda *args, **kwargs: None  # Placeholder for the callback function
        self._on_file_removed_callback: Callable = lambda *args, **kwargs: None  # Placeholder for file removal callback
        self._data_info_panel = pn.Column(margin=(10, 0, 0, 0))
        
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
            pn.Spacer(height=10),
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
            
            # Display info using DatasetInformation component
            info_dict = {
                "min_dist": min_dist,
                "n_neighbors": n_neighbors,
                "n_components": umap_obj.n_components,
                "metric": umap_obj.metric,
                "random_state": umap_obj.random_state,
                "Embedding shape": umap_obj.embedding_.shape
            }
            
            dataset_info = InfoPanel(
                title="Loaded UMAP Data",
                information=info_dict,
                sizing_mode="stretch_width",
                show_metadata_button=False
            )
            
            self._data_info_panel.clear()
            self._data_info_panel.append(dataset_info)
            
            # Call controller callback to handle display
            if self._on_umap_loaded_callback:
                self._on_umap_loaded_callback(min_dist, n_neighbors, umap_data_dict, filename)
                        
        except Exception as e:
            error_html = pn.pane.Markdown(f"**Error processing file**: {str(e)}")
            self._data_info_panel.clear()
            self._data_info_panel.append(error_html)
    
    def _on_file_removed(self, filename: str):
        """Handle file removal."""
        self._model.loaded_umap_data = None
        self._data_info_panel.clear()
        
        # Call controller callback to clear display
        if self._on_file_removed_callback:
            self._on_file_removed_callback()
    
    def set_on_umap_loaded_callback(self, callback: Callable):
        """Register callback to be called when UMAP data is loaded."""
        self._on_umap_loaded_callback = callback
    
    def set_on_file_removed_callback(self, callback: Callable):
        """Register callback to be called when file is removed."""
        self._on_file_removed_callback = callback

    def disable_controls(self):
        """Disable file uploader controls."""
        self._file_uploader.disable()
        
    def enable_controls(self):
        """Enable file uploader controls."""
        self._file_uploader.enable()