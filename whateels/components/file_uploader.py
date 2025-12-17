import panel as pn

from whateels.helpers import LoadCSS, CSS_ROOT
from typing import Callable, Optional, Tuple

class FileUploader(pn.Column):
    
    _FILE_UPDLOADER_HEIGHT = 67
    
    def __init__(
        self,
        on_file_uploaded_callback: Optional[Callable[[str, bytes], None]] = None,
        on_file_removed_callback: Optional[Callable[[str], None]] = None,
        # success_message: str = "File uploaded successfully.",
        reject_message: str = "File upload failed.",
        valid_extensions: tuple = (".dm3", ".dm4"),
        multiple_files: bool = False,
        force_success: bool = False,
        initial_filename: Optional[str] = None,
        **kwargs
    ):
        self._on_file_uploaded_callback = on_file_uploaded_callback
        self._on_file_removed_callback = on_file_removed_callback
        # self._success_message = success_message
        self._reject_message = reject_message
        self._valid_extensions = valid_extensions
        self._multiple_files = multiple_files
        
        # Load the CSS for the file uploader component
        LoadCSS([str(CSS_ROOT / "file_uploader.css")])
        
        # Track the currently uploaded filename for removal callback
        self._current_filename = None
        
        # self._feedback_message_panel = self._create_feedback_pane()
        
        (
            self._filedropper, # The main file dropper widget
            self._success_message_panel, # The success message panel
            self._success_message_text, # The success message text pane
            self._error_message_panel, # The error message panel
            file_widget # The complete file uploader widget
        ) = self._create_file_widget()
        
        super().__init__(
            file_widget, # Initialize the Column with the file uploader widget
            # self._feedback_message_panel,
            margin=(0, 0, 0, 5),
            sizing_mode="stretch_width",
            **kwargs
        )
        
        self._setup_event_handlers()
        if force_success:
            self._current_filename = initial_filename
            self._show_success_message()
    
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
    
    def _create_file_widget(self) -> Tuple[pn.widgets.FileDropper, pn.Column, pn.pane.HTML, pn.Column, pn.Column]:
        """Create the main file dropper widget."""
        STRETCH_WIDTH = "stretch_width"
        STRETCH_BOTH = "stretch_both"
        
        filedropper = pn.widgets.FileDropper(
            sizing_mode=STRETCH_BOTH,
            multiple=self._multiple_files,  # Only allow single file uploads
            css_classes=['filedropper'],
        )

        filedroppper_container = pn.Column(
            filedropper,
            css_classes=['filedropper-container'],
            sizing_mode=STRETCH_WIDTH,
            height=self._FILE_UPDLOADER_HEIGHT
        )
        
        def clear_message_handler(type: str = "both"):
            # Call removal callback if a file was present
            if self._current_filename and callable(self._on_file_removed_callback):
                self._on_file_removed_callback(self._current_filename)

            # Completely reset by replacing the FileDropper widget
            filedroppper_container.clear()
            new_filedropper = pn.widgets.FileDropper(
                sizing_mode=STRETCH_WIDTH,
                multiple=self._multiple_files,
                css_classes=['filedropper'],
            )
            filedroppper_container.append(new_filedropper)
            filedroppper_container.height = self._FILE_UPDLOADER_HEIGHT
            self._filedropper = new_filedropper
            self._current_filename = None
            self._setup_event_handlers()

            if type in ("error", "both"):
                self._clear_error_message()
            if type in ("success", "both"):
                self._clear_success_message()

        error_message_button = pn.widgets.Button(
            name="-",
            margin=0,
            css_classes=['remove-file-button'],
        )
        error_message_button.on_click(lambda _: clear_message_handler("error"))
        
        error_message = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    self._reject_message,
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
        
        success_message_button = pn.widgets.Button(
            name="-",
            margin=0,
            css_classes=['remove-file-button'],
        )
        success_message_button.on_click(lambda _: clear_message_handler("success"))
        
        success_message_text = pn.pane.HTML(
            "No file uploaded yet.",
            margin=0,
            css_classes=['success-message-text']
        )
                
        success_message = pn.Column(
            pn.Row(
                success_message_text,
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
        
        widget = pn.Column(
            file_widget,
            sizing_mode=STRETCH_BOTH,
        )
        
        return filedropper, success_message, success_message_text, error_message, widget

    # def _create_feedback_pane(self) -> pn.pane.HTML:
    #     """Create the feedback message pane for status updates."""
    #     return pn.pane.HTML(
    #         f"<p style='text-align:center;margin:10px 0 0 0;color:gray;'>{self._current_filename or "No file uploaded yet... :("}</p>", 
    #         sizing_mode='stretch_width', 
    #     )
    
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
        # self._loading_message_panel.styles = {'opacity': '1', 'pointer-events': 'auto'}
        
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
        self._success_message_panel.styles = {'transform': 'translateX(0%)', 'pointer-events': 'auto'}
        # Use CSS for 2-line clamp and ellipsis
        self._success_message_text.object = (
            f"""
            <p title="{self._current_filename}" style='text-align:center;margin:0;color:white;font-weight:normal;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden;text-overflow:ellipsis;max-width:100%;'>
                {self._current_filename}
            </p>
            """
        )
        # self._feedback_message_panel.object = f"<p style='text-align:center;margin:10px 0 0 0;color:green;font-weight:bold;'>{self._current_filename}</p>"
    def _show_error_message(self):
        self._error_message_panel.styles = {'transform': 'translateX(0%)', 'pointer-events': 'auto'}
        # self._feedback_message_panel.object = f"<p style='text-align:center;margin:10px 0 0 0;color:red;font-weight:bold;'>What is that...? :(</p>"
    
    def _clear_success_message(self):
        self._success_message_panel.styles = {'transform': 'translateX(100%)', 'pointer-events': 'none'}
        # self._clear_feedback("success")
                
    def _clear_error_message(self):
        self._error_message_panel.styles = {'transform': 'translateX(-100%)', 'pointer-events': 'none'}
        # self._clear_feedback("error")
        
    # def _clear_feedback(self, type: str = "success"):
    #     """
    #     Clear the feedback message and reset to default state.
        
    #     Useful for programmatically resetting the component state
    #     or clearing previous upload status messages.
    #     """
    #     if type == "success":
    #         self._feedback_message_panel.object = f"<p style='text-align:center;margin:10px 0 0 0;color:gray;'>File was removed... :(</p>"
    #     elif type == "error":
    #         self._feedback_message_panel.object = f"<p style='text-align:center;margin:10px 0 0 0;color:gray;'>Glad you remove it... :(</p>"