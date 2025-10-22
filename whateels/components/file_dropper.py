"""
File Dropper Component for EELS Data Upload

This module provides a Panel-based file upload component specifically designed
for DM3/DM4 EELS data files with validation and feedback.

Features:
- Drag-and-drop file upload interface
- File type validation (DM3/DM4 only)
- Visual feedback for upload status
- File content stored in memory for processing
"""

import panel as pn
from typing import Callable, Optional

class FileDropper(pn.WidgetBox):
    """
    A specialized file upload component for EELS data files.
    
    This class extends Panel's WidgetBox to create a complete file upload
    interface with validation, feedback, and in-memory file handling.

    Attributes:
        valid_extensions (tuple): Allowed file extensions for upload
    """


    def __init__(
        self,
        on_file_uploaded_callback: 'Optional[Callable[[str, bytes], None]]' = None,
        on_file_removed_callback: 'Optional[Callable[[str], None]]' = None,
        valid_extensions: tuple = ('.dm3', '.dm4'),
        reject_message: str = "❌ Rejected",
        success_message: str = "✅ Processed file",
        feedback_message: str = "No file uploaded yet."
    ):
        """
        Initialize the FileDropper component.
        
        Creates the complete UI layout including title, file dropper widget,
        and feedback pane, then sets up event handlers for file uploads.
        
        Args:
            on_file_uploaded_callback: Callback function to call when a file is successfully uploaded
            on_file_removed_callback: Callback function to call when a file is removed
            valid_extensions: Tuple of allowed file extensions (e.g., ('.dm3', '.dm4'))
            reject_message: Message to display when rejecting invalid files
            success_message: Message to display on successful file upload
            feedback_message: Initial message to display before any upload
        """
        # Store configuration parameters
        # This allows easy customization of messages and valid extensions
        self.valid_extensions = valid_extensions
        self.reject_message = reject_message
        self.success_message = success_message
        self.feedback_message = feedback_message
        self._on_file_uploaded_callback = on_file_uploaded_callback
        self._on_file_removed_callback = on_file_removed_callback
        
        # Track the currently uploaded filename for removal callback
        self._current_filename = None

        # Create UI components in logical order
        self.upload_title = self._create_title()
        self.feedback_pane = self._create_feedback_pane()
        self.file_widget = self._create_file_widget()
        
        # Initialize parent WidgetBox with all components
        super().__init__(
            self.upload_title,
            self.file_widget,
            self.feedback_pane,
        )
        
        # Set up event handling after widget creation
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

    def _create_title(self) -> pn.pane.HTML:
        """Create the title header for the upload box."""
        return pn.pane.HTML(
            "<h5 class='fdw-box-title'>Upload EELS data file</h5>"
        )
    
    def _create_feedback_pane(self) -> pn.pane.HTML:
        """Create the feedback message pane for status updates."""
        return pn.pane.HTML(
            f"<p class='feedback-message'>{self.feedback_message}</p>", 
            sizing_mode='stretch_width', 
            css_classes=['feedback-message']
        )
    
    def _create_file_widget(self) -> pn.widgets.FileDropper:
        """Create the main file dropper widget."""
        return pn.widgets.FileDropper(
            sizing_mode='stretch_width',
            multiple=False,  # Only allow single file uploads
        )
    
    def _setup_event_handlers(self):
        """Set up event handlers for file upload events."""
        def handle_file_upload(event):
            """
            Handle file upload events with validation and feedback.

            This nested function has access to the instance's widgets
            and handles the complete upload workflow.

            Args:
                event: Panel parameter change event (unused, but required by Panel)
            """
            file_widget_value = self.file_widget.value

            # If the value is None or not a dict, do nothing
            if not isinstance(file_widget_value, dict) or not file_widget_value:
                return

            # Process each uploaded file (though we only allow single uploads)
            for filename, file_content in file_widget_value.items():
                if self._is_valid_file_extension(filename):
                    self._current_filename = filename  # Store current filename
                    self._show_success()
                    # Call the required callback function if set
                    if callable(self._on_file_uploaded_callback):
                        self._on_file_uploaded_callback(filename, file_content)
                else:
                    self._reject_file_and_show_error()

        # Connect the event handler to the file widget
        self.file_widget.param.watch(handle_file_upload, 'value')

        def handle_file_removal(event):
            # Detect file removal (value changed to None or empty dict)
            file_widget_value = self.file_widget.value
            if (file_widget_value is None or file_widget_value == {}) and self._current_filename:
                # Call the removal callback if set
                if callable(self._on_file_removed_callback):
                    self._on_file_removed_callback(self._current_filename)
                self._current_filename = None
                # Reset feedback message to default
                self.clear_feedback()
        # Watch for file removal (value cleared)
        self.file_widget.param.watch(handle_file_removal, 'value')
    
    # === File Validation Methods ===
    
    def _is_valid_file_extension(self, filename: str) -> bool:
        """
        Validate file extension against allowed EELS data formats.
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            bool: True if file has valid .dm3 or .dm4 extension, False otherwise
        """
        return filename.lower().endswith(self.valid_extensions)
    
    # === File Processing Methods ===
    
    def _show_success(self):
        """
        Display success feedback for a valid file upload.
        
        This method handles the UI feedback for successful file uploads:
        1. Updates the feedback pane with success message
        
        Note: The actual file processing happens in the callback function
        """
        
        # Update UI with success feedback
        success_message = (
            f"<p class='feedback-message success'>"
            f"{self.success_message}"
            f"</p>"
        )
        
        self.feedback_pane.object = success_message

    def _reject_file_and_show_error(self):
        """
        Handle rejection of invalid files and display error feedback.
        
        This method handles the error workflow when files don't meet requirements:
        1. Clear the file widget to remove invalid file (without triggering removal callback)
        2. Display error message to user
        """
                
        # Update UI with error feedback
        error_message = (
            f"<p class='feedback-message error'>"
            f"{self.reject_message}"
            f"</p>"
        )
        self.feedback_pane.object = error_message
        
    # === Public Interface Methods ===
    
    def clear_feedback(self):
        """
        Clear the feedback message and reset to default state.
        
        Useful for programmatically resetting the component state
        or clearing previous upload status messages.
        """
        self.feedback_pane.object = f"<p class='feedback-message'>{self.feedback_message}</p>"