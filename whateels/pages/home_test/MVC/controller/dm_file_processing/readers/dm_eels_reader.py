"""
DM3/DM4 EELS Data Reader

Reads EELS data from Gatan DigitalMicrograph files using a two-stage process:
1. Parse file structure and metadata
2. Extract and process EELS spectroscopic data

Supports dependency injection for custom parsers and handlers.

Example
-------
    reader = DM_EELS_Reader("spectrum.dm4")
    eels_data = reader.read_data()
"""

from ..parsers import DM_InfoParser, DM_EELS_data

class DM_EELS_Reader:
    """
    Reader for DM3/DM4 files containing EELS data.
    
    Uses dependency injection pattern with separate parser and handler components.
    Processes data through a two-stage pipeline: file parsing then EELS data extraction.
    
    Parameters
    ----------
    filename : str
        Path to DM3/DM4 file
    parser : DM_InfoParser, optional
        File parser (defaults to DM_InfoParser)
    handler : DM_EELS_data, optional
        Data handler (defaults to DM_EELS_data)
    """

    def __init__(
        self,
        file_source,
    ):
        """
        Initialize reader with file validation and component injection.

        Parameters
        ----------
        file_source : str or file-like object
            Path to DM3/DM4 file to read or file-like object (e.g., io.BytesIO)
        """

        self._file_metadata = None
        self._processed_all_eels_spectrums = None

        self._read_data(file_source)

    def _read_data(self, file_source) -> None:
        """
        Read and process EELS data from the DM file.
        
        Args:
            file_source: Either a file path (str) or file-like object (io.BytesIO)
        """

        FILE_MODE_READ_BINARY = "rb"
        LOG_OPENING_FILE = "Opening file {filename}"

        parser = DM_InfoParser()
        handler = DM_EELS_data()

        file_metadata_dictionary = None

        # Handle both file paths and file-like objects
        if isinstance(file_source, str):
            # File path - open it
            file_identifier = file_source
            
            with open(file_source, FILE_MODE_READ_BINARY) as binary_file_stream:
                file_metadata_dictionary, processed_all_eels_spectrums = self._process_file_stream(
                    binary_file_stream, file_identifier, parser, handler
                )
        else:
            # File-like object - ensure it has compatible interface
            file_identifier = getattr(file_source, 'name', 'memory_file')
            
            # Reset file position to beginning and ensure compatibility
            file_source.seek(0)
            
            # Add fileno method if missing (for library compatibility)
            if not hasattr(file_source, 'fileno'):
                file_source.fileno = lambda: -1  # Dummy file descriptor
            
            file_metadata_dictionary, processed_all_eels_spectrums = self._process_file_stream(
                file_source, file_identifier, parser, handler
            )

        self._file_metadata = file_metadata_dictionary
        self._processed_all_eels_spectrums = processed_all_eels_spectrums

    def _process_file_stream(self, binary_file_stream, file_identifier, parser, handler):
        """
        Process the binary file stream with parser and handler.
        
        Args:
            binary_file_stream: Binary file stream to process
            file_identifier: Identifier for logging purposes
            parser: DM_InfoParser instance
            handler: DM_EELS_data instance
            
        Returns:
            tuple: (file_metadata_dictionary, processed_all_eels_spectrums)
        """

        parser.file = binary_file_stream
        file_metadata_dictionary = parser.parse_file()

        handler.get_file_data(binary_file_stream, infoDict=file_metadata_dictionary)
        processed_all_eels_spectrums: DM_EELS_data = handler.handle_eels_data()

        return file_metadata_dictionary, processed_all_eels_spectrums

    @property
    def file_metadata(self):
        return self._file_metadata
    
    @property
    def processed_all_eels_spectrums(self) -> DM_EELS_data:
        return self._processed_all_eels_spectrums
