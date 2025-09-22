import re
from whateels.errors import *

from ..decoders import decoders as dec
from whateels.errors.dm.parsing import (
    DMVersionError, 
    DMDelimiterCharacterError, 
    DMStructDataTypeError, 
    DMIdentifierError
)
from typing import List, Tuple, TextIO, Callable, Optional, Dict, Any
from whateels.helpers.logging import Logger

_logger = Logger.get_logger("dm_infoparser.log", __name__)

class DM_InfoParser:
    """
    Parses DM3/DM4 files and extracts metadata into a dictionary structure.
    """

    ###
    # Data types read from external plugin
    _simple_data_types = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    # Simple type readers from exteral plugin
    _simple_parsers_dictionary = {
        2: (dec.read_short, 2),
        3: (dec.read_long, 4),
        4: (dec.read_ushort, 2),
        5: (dec.read_ulong, 4),
        6: (dec.read_float, 4),
        7: (dec.read_double, 8),
        8: (dec.read_boolean, 1),
        9: (dec.read_char, 1),
        10: (dec.read_byte, 1),
        11: (dec.read_long_long, 8),
        12: (dec.read_ulong_long, 8),
    }
    # SizeId - Encryption | allowed pairs
    # The pairings are written literaly here ... for more clarity
    _id_pairings = [
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (1, 6),
        (1, 7),
        (1, 8),
        (1, 9),
        (1, 10),
        (1, 11),
        (1, 12),
        (2, 18),
        (3, 20),
    ]

    _id_pairings = tuple(_id_pairings)
    # Valid extensions for the file reading
    _valid_extensions = (".dm3$", ".dm4$")

    def __init__(self) -> None:
        """Initialize parser with empty information dictionary and default values."""
        self.information_dictionary: Dict[str, Any] = dict()
        self._file: Optional[TextIO] = None  # File handle to be set via get_file()
        self.version: Optional[int] = None  # DM file version (3 or 4)
        self.parser: Optional[Callable] = None  # Parser function (read_long or read_long_long)
        self.endianness: Optional[str] = None  # File endianness ('big' or 'little')

    # =============================================================================
    # PUBLIC METHODS
    # =============================================================================

    @property
    def file(self) -> Optional[TextIO]:
        """Get the file handle for parsing operations."""
        return self._file

    @file.setter
    def file(self, file: TextIO) -> None:
        """Set the file handle for parsing operations."""
        self._file = file

    def parse_file(self) -> Dict[str, Any]:
        """Parse the entire DM file and return the information dictionary."""
        self._check_extension_in_fname()
        self._process_file_header()
        nnames = self._read_ParentBlockSize_info()
        self.information_dictionary["root"] = dict()
        self._parse_Blocks(nnames, self.information_dictionary, "root")
        return self.information_dictionary

    # =============================================================================
    # CORE PARSING METHODS
    # =============================================================================

    def _process_file_header(self) -> None:
        """Read and validate DM file header (version, size, endianness)."""
        self._file.seek(0)  # Pointer to the 0 possition
        self.version = dec.read_long(self._file, "big")  # version : <4 bytes> big endian
        if self.version not in [3, 4]:
            # If version != 3 or 4 -> Raises an error -> Unsuported file for DM
            message = f"Expected versions 3 or 4 (.dm3/.dm4). Got {self.version} instead\
            -> from the header of {self._file.name}"
            raise DMVersionError(message)

        # The general parser/reader - reads in chuncks of 4 or 8 bytes returning integer values
        self.parser = dec.read_long if self.version == 3 else dec.read_long_long
        file_size = self.parser(self._file, "big")  # Full size of file <4 or 8 bytes>
        self.endianness = (
            "little" if dec.read_long(self._file, "big") else "big"
        )  # True - little / #False - big

        # logging header read - info level
        msg = f"DM version = {self.version} - File size (Bytes) = {file_size} - {self.endianness} endian"
        _logger.info(msg)

    def _parse_Blocks(self, nnames, info_dictionary, parentBlock_name: str = "root"):
        """
        Recursively parse all blocks in the file structure.
        
        Handles both data blocks (id=21) and parent blocks (id=20) that contain subblocks.
        """
        # Local indices for unnamed data/group Blocks
        noNameData = 0
        noNameBlock = 0

        for _ in range(nnames):
            # NameSpace - Header info
            identifier, childrenBlock_name = self._read_ChildrenBlock_header()
            # This is coupled with the dictionary of callers
            callable_id = (
                2
                if (parentBlock_name == "ImageData" and childrenBlock_name == "Data")
                else 1
            )

            if identifier == 21:
                if not childrenBlock_name:
                    childrenBlock_name = f"DataBlock{noNameData}"  # NoNameData
                    noNameData += 1
                self._read_delimiter()  # Checks the delimiter name - data
                (
                    sizeBlock_id,
                    encryption_type,
                ) = self._read_DataType_info()  # Type of data header
                self._check_sizeID_encryption_pair(
                    sizeBlock_id, encryption_type
                )  # Checking types
                # The type pairings are check, so we can use the size to get the correct callables
                if sizeBlock_id > 3 and encryption_type == 20:  # Array of complex types
                    keyword = "complexArray"
                    pass  # Do something -> implement complex type caller
                else:
                    keyword = self._get_callable_word(encryption_type)

                parsers_dict = self._get_callable_parsers_dictionary()
                catcher = parsers_dict[keyword][0]
                caller = parsers_dict[keyword][callable_id]
                data = self._process_ChildrensDataBlock(catcher, caller)
                # The endgame - creating a dictionary of things ...
                info_dictionary[childrenBlock_name] = data

            elif identifier == 20:  # ChildrenBlock becoming a ParentBlock -> Recursion
                if not childrenBlock_name:
                    childrenBlock_name = f"GroupBlock{noNameBlock}"  # NoNameBlock
                    noNameBlock += 1
                nnames = self._read_ParentBlockSize_info(
                    read_block_size=True
                )  # Number of names inside

                info_dictionary[childrenBlock_name] = dict()
                # Recursion !
                self._parse_Blocks(
                    nnames, info_dictionary[childrenBlock_name], childrenBlock_name
                )

            else:
                raise DMIdentifierError(
                    f"Identifier missread while parsing the file. {identifier =}"
                )

    def _process_ChildrensDataBlock(self, formatCallable, readerCallable):
        """Process data block using format catcher and data reader."""
        format_header = formatCallable()
        data = readerCallable(**format_header)
        return data

    # =============================================================================
    # BLOCK READING METHODS
    # =============================================================================

    def _read_ParentBlockSize_info(self, read_block_size: bool = False) -> int:
        """
        Read number of named subblocks in current block.
        
        For DM4 files, optionally reads block size if read_block_size=True.
        """
        # Skip deprecated boolean flags (ordered/opened)
        self._file.seek(2, 1)

        if self.version == 4 and read_block_size:
            # Read block size for DM4 format
            block_size = self.parser(self._file, "big")

        number_of_names = self.parser(self._file, "big")
        return number_of_names

    def _read_ChildrenBlock_header(self) -> Tuple[int, str]:
        """
        Read header info for current child block.
        
        Returns
        -------
        tuple[int, str]
            (identifier, block_name) where identifier indicates block type:
            - 20: Contains subblocks (parent)
            - 21: Contains data
        """
        identifier = dec.read_byte(self._file, "big")  # a single byte integer used as index
        # Reading the name - a string
        length = dec.read_short(self._file, "big")  # a double byte integer
        block_name = self._read_string(length)
        return identifier, block_name

    def _read_DataType_info(self) -> Tuple[int, int]:
        """
        Read size and encryption type identifiers for data block.
        
        Returns
        -------
        tuple[int, int]
            (size_data_id, encryption_type) where:
            - size_data_id: 1=simple, 2=string, 3=array, >3=structure/complex
            - encryption_type: Points to specific reader method
        """
        size_Data_id = self.parser(self._file, "big")
        # Check data size validity
        if size_Data_id < 1:
            msg = f"Invalid {size_Data_id = } < 1. DM does not support this id (parsing error?)"
            _logger.exception(msg)
            raise IOError(msg)

        encryption_type = self.parser(self._file, "big")

        # Before returning anything, it also checks if the pairings are correct

        return size_Data_id, encryption_type

    def _read_delimiter(self) -> None:
        """Read and validate '%%%%' delimiter between block names and data."""
        if self.version == 4:
            # Skip 8 bytes for DM4 format
            self._file.seek(8, 1)
        delimiter = self._read_string(4)
        if delimiter != "%%%%":
            message = f"Error with the delimiter between blocks.\nExpected %%%%\nGot{delimiter}"
            _logger.exception(message)
            raise DMDelimiterCharacterError(message)

    # =============================================================================
    # UTILITY & HELPER METHODS
    # =============================================================================

    def _check_extension_in_fname(self) -> None:
        """Validate file has dm3 or dm4 extension."""
        # First thing we do is to check is we have an actual valid file
        fname = (
            self._file.name
        )  # It is an opened file, should have a name instance variable ...
        if not any(
            [
                re.search(ext, fname, flags=re.IGNORECASE)
                for ext in self._valid_extensions
            ]
        ):
            msg = f"The file-name given does not have a valid extension - {fname}.\
                The extension should be one of the following : {self._valid_extensions}."
            _logger.error(msg)
            raise DMVersionError(msg)

    def _get_callable_parsers_dictionary(self) -> Dict[str, Tuple[Callable, Callable, Callable]]:
        """Dictionary mapping data type keywords to their respective parser methods."""
        dictio = {
            "simpleType": (
                self._catch_simpleTypeData_format,
                self._read_simpleTypeData,
                self._skip_simpleTypeData,
            ),
            "structure": (
                self._catch_structure_format,
                self._read_structure,
                self._skip_structure,
            ),
            "string": (self._catch_string_format, self._read_string, self._skip_string),
            "array": (
                self._catch_simpleTypesArray_format,
                self._read_simpleTypesArray,
                self._skip_simpleTypesArray,
            ),
            "complexArray": (
                self._catch_complexTypesArray_format,
                self._read_complexTypesArray,
                self._skip_complexTypesArray,
            ),
        }
        return dictio

    def _get_callable_word(self, encryption_type: int) -> str:
        """Get keyword for encryption type to select appropriate callable."""
        if 2 <= encryption_type <= 12:
            return "simpleType"

        dictionary_words = {18: "string", 15: "structure", 20: "array"}
        return dictionary_words[encryption_type]

    def _check_sizeID_encryption_pair(self, size_Data_id: int, encryption_type: int) -> None:
        """Validate that size/encryption pair is supported by DM format."""
        if size_Data_id > 3:
            if encryption_type not in [15, 20]:
                m0 = f"Expected EncryptionTypes of 15 or 20 for the DataSize {size_Data_id}"
                m1 = f"Got {encryption_type} instead."
                message = "\n".join([m0, m1])
                _logger.exception(message)
                raise IOError(message)
        else:
            if (size_Data_id, encryption_type) not in self._id_pairings:
                m0 = f"The pair (DataSize = {size_Data_id}, EncryptionType {encryption_type}) is not correct."
                m1 = f"The possible (DataSize,EncryptionType) pairings are {self._id_pairings}."
                m2 = "Check for possible parsing error and/or data corruption, and report"
                message = "\n".join([m0, m1, m2])
                _logger.exception(message)
                raise IOError(message)

    def _check_multipleElementObjects_DataTypes(self, definition) -> None:
        """Validate that all element types are simple data types (2-12 range)."""
        if any([el not in self._simple_data_types for el in definition]):
            m1 = "Expected id labels of simple data types."
            m2 = f"Got {definition} instead >> numbers outside the [2,12] range"
            message = "\n".join([m1, m2])
            raise DMStructDataTypeError(message)

    def _backtracking_position_in_file(self, nbytes=None) -> None:
        """Move file pointer back by nbytes (4 for dm3, 8 for dm4 if None)."""
        if not nbytes:
            if self.version == 3:
                nbytes = 4
            elif self.version == 4:
                nbytes = 8
            else:
                message = (
                    f"Expected DM versions 3 or 4, got version number = {self.version}"
                )
                _logger.exception(message)
                raise DMVersionError(message)
        current_position = self._file.tell()
        self._file.seek(current_position - nbytes, 0)

    # =============================================================================
    # SIMPLE DATA TYPE METHODS
    # =============================================================================

    def _catch_simpleTypeData_format(self) -> Dict[str, int]:
        """Get simple element type from memory for reader configuration."""

        self._backtracking_position_in_file()
        element_type = self.parser(self._file, "big")
        return {"element_type": element_type}

    def _read_simpleTypeData(self, element_type: int) -> Any:
        """Read simple data type using appropriate decoder."""
        data = self._simple_parsers_dictionary[element_type][0](self._file, self.endianness)
        return data

    def _skip_simpleTypeData(self, element_type: int) -> Dict[str, Any]:
        """Skip simple data type and return position info."""
        sizeB = self._simple_parsers_dictionary[element_type][-1]
        offset = self._file.tell()
        dictionary_simpleDType = {
            "size": 1,
            "bytes_size": sizeB,
            "offset": offset,
            "endian": self.endianness,
        }
        self._file.seek(sizeB, 1)  # Skip data
        return dictionary_simpleDType

    # =============================================================================
    # STRING METHODS
    # =============================================================================

    def _catch_string_format(self):
        """Get string length from file header."""
        length = self.parser(self._file, "big")
        return {"length": length}

    def _read_string(self, length: int, methods: List | None = None) -> str:
        """Read and decode string of specified length."""
        # Reading files
        list_characters = [
            dec.read_char(self._file, self.endianness) for _ in range(length)
        ]
        string_byte_characters = b"".join(list_characters)
        string = " - "
        # Decoding byte-strings
        if not methods:
            methods = ["utf8", "latin-1"]
        # Loop through the possible decoding methods
        for decoding_method in methods:
            try:
                string = string_byte_characters.decode(decoding_method)
            except UnicodeError as e:
                msg = f"Failed reading with an encoding {decoding_method}"
                _logger.warning(msg)
            else:
                break
        return string

    def _skip_string(self, length: int, data=False):
        """Skip string reading and return position info."""
        offset = self._file.tell()
        self._file.seek(length, 1)  # Skip string data
        string_info = {
            "size": length,
            "bytes_size": length,
            "offset": offset,
            "endian": self.endianness,
        }
        return string_info

    # =============================================================================
    # STRUCTURE METHODS
    # =============================================================================

    def _catch_structure_format(self):
        """Read structure format descriptor from file."""
        self.parser(self._file, "big")  # Skip struct length (not needed)
        n_fields = self.parser(self._file, "big")
        # Read field types
        s_format = []
        for _ in range(n_fields):
            self.parser(self._file, "big")  # Skip field length (not needed)
            s_format.append(self.parser(self._file, "big"))
        return {"struct_format": tuple(s_format)}

    def _read_structure(self, struct_format):
        """Read structure data according to format specification."""
        # Validate format first
        self._check_multipleElementObjects_DataTypes(struct_format)

        # Read struct values
        values = []
        for num_type in struct_format:
            data = self._simple_parsers_dictionary[num_type][0](self._file, self.endianness)
            values.append(data)

        return tuple(values)

    def _skip_structure(self, struct_format):
        """Skip structure reading and return position info."""
        # Validate format first
        self._check_multipleElementObjects_DataTypes(struct_format)

        # Calculate size and skip
        offset = self._file.tell()
        struct_Bsize = 0
        for num_type in struct_format:
            struct_Bsize += self._simple_parsers_dictionary[num_type][-1]

        self._file.seek(struct_Bsize, 1)  # Skip struct data

        # Create the info dictionary
        dictionary_struct_info = {
            "size": len(struct_format),
            "bytes_size": struct_Bsize,
            "offset": offset,
            "endian": self.endianness,
        }

        return dictionary_struct_info

    # =============================================================================
    # SIMPLE ARRAY METHODS
    # =============================================================================

    def _catch_simpleTypesArray_format(self):
        """Read array format (element type and length) from file header."""
        # Read array header
        element_encryption = self.parser(self._file, "big")
        size = self.parser(self._file, "big")
        return {"element_encryption_type": element_encryption, "length": size}

    def _read_simpleTypesArray(self, element_encryption_type, length):
        """Read array of simple types (or convert to string if appropriate)."""
        # Validate element type
        self._check_multipleElementObjects_DataTypes([element_encryption_type])

        reader = self._simple_parsers_dictionary[element_encryption_type][0]
        data = [reader(self._file, self.endianness) for _ in range(length)]
        
        # Convert to string if appropriate (type 4 = ushort, often used for strings)
        if element_encryption_type == 4 and data:
            try:
                data = "".join([chr(i) for i in data])
            except Exception as e:
                _logger.warning(f"Skipped array-to-string conversion. Exception: {e}")
                data = self._skip_string(length=length * 2)
        return data

    def _skip_simpleTypesArray(self, element_encryption_type, length):
        """Skip simple array reading and return position info."""
        # The info about size per element is in the dictionary
        self._check_multipleElementObjects_DataTypes(
            [
                element_encryption_type,
            ]
        )

        size_bytes = (
            self._simple_parsers_dictionary[element_encryption_type][-1] * length
        )
        data = {
            "size": length,  # Size of the array (number of elements)
            "endian": self.endianness,  # endianess of the elements
            "bytes_size": size_bytes,  # Size of the array in bytes
            "offset": self._file.tell(),
        }  # offset position of the array in the memory
        self._file.seek(size_bytes, 1)  # Skipping data -> Not read
        return data

    # =============================================================================
    # COMPLEX ARRAY METHODS
    # =============================================================================

    def _catch_complexTypesArray_format(self):
        """Read format header for complex arrays (strings, structures, arrays)."""
        element_encryption_type = self.parser(self._file, "big")
        keyword = self._get_callable_word(element_encryption_type)
        parsers_dict = self._get_callable_parsers_dictionary()
        format_definition = parsers_dict[keyword][0]()  # Definition of the elements
        array_size = self.parser(self._file, "big")
        return {
            "keyword": keyword,
            "array_size": array_size,
            "format_definition": format_definition,
        }

    def _read_complexTypesArray(self, keyword, array_size, format_definition):
        """Read array of complex types using appropriate reader."""
        # Let us read the arrays of length == array_size
        reader = self._get_callable_parsers_dictionary()[keyword][1]
        # And we read all the data inside, according to the type of reader we got ...
        data = [reader(**format_definition) for el in range(array_size)]
        return data

    def _skip_complexTypesArray(self, keyword, array_size, format_definition):
        """Skip complex array reading and return position info."""
        skipper = self._get_callable_parsers_dictionary()[keyword][-1]
        # This will advance an element_size length the pointer position in memory,
        # appart from retrieving the offset, size, size in bytes and endiannes in a
        # data dictionary
        element_data = skipper(**format_definition)
        # We advance the pointer the (array_size -1)*element_bytesSize positions
        # still to be moved
        self._file.seek(element_data["bytes_size"] * (array_size - 1), 1)
        # We substitute the size by the actual array size read from header
        element_data["size"] = array_size
        # and the size in bytes by the actual size for the whole array
        element_data["bytes_size"] *= array_size
        return element_data
