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
from whateels.helpers.logging import Logger

_logger = Logger.get_logger("dm_file_reader.log", __name__)

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
        filename: str,
    ):
        """
        Initialize reader with file validation and component injection.

        Parameters
        ----------
        filename : str
            Path to DM3/DM4 file to read
        parser : DM_InfoParser, optional
            Custom parser (default: DM_InfoParser)
        handler : DM_EELS_data, optional  
            Custom handler (default: DM_EELS_data)
        """

        self._file_metadata = None
        self._processed_all_eels_spectrums = None

        self._read_data(filename)

    def _read_data(self, filename: str) -> None:
        """
        Read and process EELS data from the DM file.
        """

        FILE_MODE_READ_BINARY = "rb"

        LOG_OPENING_FILE = "Opening file {filename}"
        LOG_SEPARATOR = "##############"
        LOG_START_PARSING = "Starting file parsing for {filename}"
        LOG_USING_PARSER = "Using parser: {parser}"
        LOG_PARSING_SUCCESS = "File parsing completed successfully"
        LOG_EELS_DATA_EXTRACTION = "Starting EELS data extraction using: {handler}"
        LOG_EELS_DATA_EXTRACTION_SUCCESS = "EELS data extraction completed successfully"

        parser = DM_InfoParser()
        handler = DM_EELS_data()

        file_metadata_dictionary = None

        _logger.info(LOG_OPENING_FILE.format(filename=filename))

        with open(filename, FILE_MODE_READ_BINARY) as binary_file_stream:
            # Step 1: Parse file structure and extract metadata
            _logger.info(LOG_START_PARSING.format(filename=filename))
            _logger.info(LOG_USING_PARSER.format(parser=parser.__module__))

            parser.file = binary_file_stream
            file_metadata_dictionary = parser.parse_file()

            _logger.info(LOG_PARSING_SUCCESS)
            _logger.info(LOG_SEPARATOR)

            # Step 2: Extract and process EELS data
            _logger.info(LOG_EELS_DATA_EXTRACTION.format(handler=handler.__module__))

            handler.get_file_data(binary_file_stream, infoDict=file_metadata_dictionary)
            processed_all_eels_spectrums: DM_EELS_data = handler.handle_eels_data()

            _logger.info(LOG_EELS_DATA_EXTRACTION_SUCCESS)
            _logger.info(LOG_SEPARATOR)

        self._file_metadata = file_metadata_dictionary
        self._processed_all_eels_spectrums = processed_all_eels_spectrums

    @property
    def file_metadata(self):
        return self._file_metadata
    
    @property
    def processed_all_eels_spectrums(self) -> DM_EELS_data:
        return self._processed_all_eels_spectrums
