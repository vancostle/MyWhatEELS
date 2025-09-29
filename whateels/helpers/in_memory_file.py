import io
from whateels.helpers.logging import Logger

_logger = Logger.get_logger("in_memory_file.log", __name__)

class InMemoryFile(io.BytesIO):
    """
    In-memory file for DM processing. Acts like a file, stores data in RAM.
    """
    
    def __init__(self, data: bytes, name: str = "memory_file"):
        """
        Initialize with byte data and filename.
        
        Args:
            data: Binary file content
            name: Filename for compatibility
        """
        super().__init__(data)
        self.name = name
        _logger.info(f"Processing file {name} ({self.getbuffer().nbytes / (1024 * 1024):.2f} MB) in memory")