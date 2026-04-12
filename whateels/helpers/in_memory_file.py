import io

class InMemoryFile(io.BytesIO):
    """
    In-memory file. Acts like a file, stores data in RAM.
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