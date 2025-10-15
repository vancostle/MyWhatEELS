import os
import time
import threading
import tempfile

# TODO: Consider deleting this file if not needed in favor of using FileCompatibleBytesIO for in-memory file handling.
class TempFile:
    """
    A class to handle temporary file creation and cleanup with optional delayed deletion.
    
    This class provides a context manager to create a temporary file that is automatically deleted
    when the context is exited. It can be used to safely handle temporary files without leaving
    them on the filesystem.
    
    Features:
    - Cross-platform temporary file creation
    - Automatic cleanup on context exit
    - Optional delayed deletion (non-blocking, uses background thread)
    - Retry logic for Windows file locking issues
    - Preserves file extensions for library compatibility
    
    Args:
        suffix (str): File extension (e.g., '.dm3', '.tmp'). Default: ''
        prefix (str): Filename prefix. Default: 'tmp_'
        dir (str, optional): Directory for temp file. Default: system temp directory
        delay_seconds (int): Seconds to wait before deletion. Default: 0 (immediate)
                           If > 0, deletion happens in background thread (non-blocking)
    
    Example:
        # Immediate deletion (recommended for production)
        with TempFile(suffix='.dm3', prefix='eels_') as temp_path:
            # Process file at temp_path
            pass  # File deleted immediately when exiting
        
        # Delayed deletion (useful for debugging)
        with TempFile(suffix='.dm3', prefix='eels_', delay_seconds=5) as temp_path:
            # Process file at temp_path
            pass  # File scheduled for deletion in 5 seconds (non-blocking)
    """
    
    def __init__(self, suffix='', prefix='tmp_', dir=None, delay_seconds=0):
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix, 
            prefix=prefix, 
            dir=dir, 
            delete=False
        )
        self.temp_file.close()  # Close the file handle to avoid permission issues
        self.delay_seconds = delay_seconds  # Store the delay time
    
    # Context manager methods
    # Allows the use of 'with' statement for automatic cleanup
    def __enter__(self):
        return self.temp_file.name
    
    # Exiting the context manager will delete the temporary file
    def __exit__(self, exc_type, exc_value, traceback):
        def delayed_delete():
            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)
            
            # Try to remove the file with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if os.path.exists(self.temp_file.name):
                        os.remove(self.temp_file.name)
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.1)
                        continue
                    else:
                        print(f"⚠️ Warning: Could not remove temporary file {self.temp_file.name}: {e}")
        
        # Start deletion in background thread - doesn't block the main program
        if self.delay_seconds > 0:
            thread = threading.Thread(target=delayed_delete, daemon=True)
            thread.start()
        else:
            delayed_delete()  # Delete immediately if no delay
