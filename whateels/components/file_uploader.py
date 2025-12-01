import panel as pn

from whateels.helpers import LoadCSS, CSS_ROOT
from typing import Callable, Optional, Tuple

class FileUploader(pn.Column):
    
    def __init__(
        self,
        on_file_uploaded_callback: Optional[Callable[[str, bytes], None]] = None,
        on_file_removed_callback: Optional[Callable[[str], None]] = None,
        success_message: str = "File uploaded successfully.",
        reject_message: str = "File upload failed.",
        valid_extensions: tuple = (".dm3", ".dm4"),
        multiple_files: bool = False,
        **kwargs
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
        
        (
           self._filedropper, # The main file dropper widget
           self._success_message_panel, # The success message panel
           self._error_message_panel, # The error message panel
           file_widget # The complete file uploader widget
        ) = self._create_file_widget()
        
        super().__init__(
            file_widget, # Initialize the Column with the file uploader widget
            **kwargs
        )
        
        self._setup_event_handlers()
    
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
    
    def _create_file_widget(self) -> Tuple[pn.widgets.FileDropper, pn.Column, pn.Column, pn.Column]:
        """Create the main file dropper widget."""
        STRETCH_WIDTH = "stretch_width"
        STRETCH_BOTH = "stretch_both"
        
        error_message_button = pn.widgets.Button(
            name="X",
            margin=0,
            css_classes=['remove-file-button'],
        )
        error_message_button.on_click(lambda _: self._clear_error_message())
        
        error_message = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    self._success_message,
                    margin=0,
                    css_classes=['error-message-text']
                ),
                error_message_button,
                sizing_mode=STRETCH_WIDTH,
                css_classes=['error-message'] 
            ),
            sizing_mode=STRETCH_BOTH,
            css_classes=['error-panel']
        )
        
        filedropper = pn.widgets.FileDropper(
            sizing_mode=STRETCH_WIDTH,
            multiple=self._multiple_files,  # Only allow single file uploads
            css_classes=['filedropper'],
        )
        
        filedroppper_container = pn.Column(
            filedropper,
            css_classes=['filedropper-container'],
        )
        
        success_message_button = pn.widgets.Button(
            name="X",
            margin=0,
            css_classes=['remove-file-button'],
        )
        def clear_success_message_handler(event):            
            # Completely reset by replacing the FileDropper widget
            filedroppper_container.clear()
            
            new_filedropper = pn.widgets.FileDropper(
                sizing_mode=STRETCH_WIDTH,
                multiple=self._multiple_files,
                css_classes=['filedropper'],
            )
            filedroppper_container.append(new_filedropper)
            
            # Update reference and reconnect handlers
            self._filedropper = new_filedropper
            self._current_filename = None
            
            # Setup handlers for the new widget
            self._setup_event_handlers()
            
            self._clear_success_message()
            print("Clearing success message")
        
        success_message_button.on_click(clear_success_message_handler)
                
        success_message = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    self._success_message,
                    margin=0,
                    css_classes=['success-message-text']
                ),
                success_message_button,
                sizing_mode=STRETCH_WIDTH,
                css_classes=['success-message'] 
            ),
            sizing_mode=STRETCH_BOTH,
            css_classes=['success-panel']
        )
        
        file_widget = pn.Column(
            filedroppper_container,
            error_message,
            success_message,
            sizing_mode=STRETCH_BOTH,
            css_classes=['file-uploader-container']
        )
        
        return filedropper, success_message, error_message, file_widget
    
    def _setup_event_handlers(self):
        """Set up event handlers for file upload events."""

        # Connect the event handler to the file widget
        self._filedropper.param.watch(self._handle_file_upload, 'value')

        # Watch for file removal (value cleared)
        self._filedropper.param.watch(self._handle_file_removal, 'value')
    
    def _handle_file_upload(self, event):
        """
        Handle file upload events with validation and feedback.

        This nested function has access to the instance's widgets
        and handles the complete upload workflow.

        Args:
            event: Panel parameter change event (unused, but required by Panel)
        """
        file_widget_value = self._filedropper.value

        # If the value is None or not a dict, do nothing
        if not isinstance(file_widget_value, dict) or not file_widget_value:
            return

        # Process each uploaded file (though we only allow single uploads)
        for filename, file_content in file_widget_value.items():
            if self._is_valid_file_extension(filename):
                self._current_filename = filename  # Store current filename
                self._show_success_message()
                # Call the required callback function if set
                if callable(self._on_file_uploaded_callback):
                    self._on_file_uploaded_callback(filename, file_content)
            else:
                self._show_error_message()
    
    def _handle_file_removal(self, event):
        # Detect file removal (value changed to None or empty dict)
        file_widget_value = self._filedropper.value
        if (file_widget_value is None or file_widget_value == {}) and self._current_filename:
            # Call the removal callback if set
            if callable(self._on_file_removed_callback):
                self._on_file_removed_callback(self._current_filename)
            self._current_filename = None
            
            print("Clearing messages after file removal")
    
    def _is_valid_file_extension(self, filename: str) -> bool:
        """
        Validate file extension against allowed EELS data formats.
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            bool: True if file has valid .dm3 or .dm4 extension, False otherwise
        """
        return filename.lower().endswith(self._valid_extensions)
    
    def _show_success_message(self):
        # Ensure css_classes is a list before using 'not in'
        self._success_message_panel.styles = {'transform': 'translateX(0%)'}
        print("Showing success message")
    
    def _show_error_message(self):
        self._error_message_panel.styles = {'transform': 'translateX(0%)'}
    
    def _clear_success_message(self):
        self._success_message_panel.styles = {'transform': 'translateX(100%)'}
                
    def _clear_error_message(self):
        self._error_message_panel.styles = {'transform': 'translateX(-100%)'}