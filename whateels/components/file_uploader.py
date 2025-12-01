import panel as pn

from whateels.helpers import LoadCSS, CSS_ROOT
from typing import Callable, Optional

class FileUploader(pn.Column):
    
    def __init__(
        self,
        on_file_uploaded_callback: Optional[Callable[[str, bytes], None]] = None,
        on_file_removed_callback: Optional[Callable[[str], None]] = None,
        success_message: str = "File uploaded successfully.",
        reject_message: str = "File upload failed.",
        valid_extensions: Optional[list[str]] = None,
        multiple_files: bool = False,
    ):
        self._on_file_uploaded_callback = on_file_uploaded_callback
        self._on_file_removed_callback = on_file_removed_callback
        self._success_message = success_message
        self._reject_message = reject_message
        self._valid_extensions = valid_extensions
        self._multiple_files = multiple_files
        
        # Load the CSS for the file uploader component
        LoadCSS([str(CSS_ROOT / "file_uploader.css")])
        
        # Track the currently uploaded filename for removal callback
        self._current_filename = None
        
        super().__init__(
            self._create_layout()
        )
    
    @property
    def on_file_uploaded_callback(self) -> Optional[Callable[[str, bytes], None]]:
        """Callback for file upload events."""
        return self._on_file_uploaded_callback
    
    @property
    def on_file_removed_callback(self) -> Optional[Callable[[str], None]]:
        """Callback for file removal events."""
        return self._on_file_removed_callback
    
    @on_file_uploaded_callback.setter
    def on_file_uploaded_callback(self, callback: Optional[Callable[[str, bytes], None]]):
        """
        Set the callback function for file upload events.
        
        Args:
            callback: Function to call when a file is successfully uploaded
        """
        self._on_file_uploaded_callback = callback
        
    @on_file_removed_callback.setter
    def on_file_removed_callback(self, callback: Optional[Callable[[str], None]]):
        """
        Set the callback function for file removal events.
        
        Args:
            callback: Function to call when a file is removed
        """
        self._on_file_removed_callback = callback
        
    def _create_layout(self):
        
        STRETCH_WIDTH = "stretch_width"
        STRETCH_BOTH = "stretch_both"
        
        error_panel = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    self._success_message,
                    margin=0,
                    css_classes=['error-message-text']
                ),
                pn.widgets.Button(
                    name="X",
                    margin=0,
                    css_classes=['remove-file-button'],
                ),
                sizing_mode=STRETCH_WIDTH,
                css_classes=['error-message'] 
            ),
            sizing_mode=STRETCH_BOTH,
            css_classes=['error-panel']
        )
        
        filedropper = pn.widgets.FileDropper(
            sizing_mode=STRETCH_WIDTH,
            multiple=self._multiple_files,  # Only allow single file uploads
            css_classes=['file-uploader-widget'],
        )
        
        success_panel = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    self._success_message,
                    margin=0,
                    css_classes=['success-message-text']
                ),
                pn.widgets.Button(
                    name="X",
                    margin=0,
                    css_classes=['remove-file-button'],
                ),
                sizing_mode=STRETCH_WIDTH,
                css_classes=['success-message'] 
            ),
            sizing_mode=STRETCH_BOTH,
            css_classes=['success-panel']
        )
        
        slider = pn.Column(
            filedropper,
            error_panel,
            success_panel,
            sizing_mode=STRETCH_BOTH,
            css_classes=['file-uploader-container']
        )
        
        return slider