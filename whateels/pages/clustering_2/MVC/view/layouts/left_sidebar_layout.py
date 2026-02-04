import panel as pn, pickle
from bokeh.models import Tooltip

from whateels.components import FileUploader

class Clustering2LeftSidebarLayout(pn.Column):
    def __init__(self, **kwargs):
        self._loaded_data = None
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
            # Load pickle data
            self._loaded_data = pickle.loads(content)
            
            # Display information about loaded data
            if isinstance(self._loaded_data, dict):
                num_results = len(self._loaded_data)
                keys_preview = list(self._loaded_data.keys())
                keys_list = [f"    {i+1}. {key}" for i, key in enumerate(self._loaded_data.keys())]
                
                info_text = f"""
                    **Loaded Data:**
                    - **Results count**: {num_results}
                    - **Keys preview**: {', '.join(keys_list)}
                """
                
                self._data_info_panel.object = info_text
                print(f"✓ Loaded {num_results} UMAP results from {filename}")
                print(f"  Keys: {list(self._loaded_data.keys())}")
            else:
                self._data_info_panel.object = f"**Warning**: Unexpected data type: {type(self._loaded_data)}"
                
        except Exception as e:
            self._data_info_panel.object = f"**Error loading file**: {str(e)}"
            print(f"Error loading pickle file: {e}")
            self._loaded_data = None
    
    def _on_file_removed(self, filename: str):
        """Handle file removal."""
        self._loaded_data = None
        self._data_info_panel.object = ""
        print(f"✓ Removed {filename}")
    
    @property
    def loaded_data(self):
        """Access the loaded pickle data."""
        return self._loaded_data
