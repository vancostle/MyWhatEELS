"""
DM Data Processing Exceptions

Exceptions related to EELS data validation, type checking,
and scientific data processing operations.
"""

from .base import DMFileError

class DMNonEelsError(DMFileError):
    """Raised when the DM file doesn't contain EELS spectral data."""
    
    def __init__(self, file_info=None):
        super().__init__("DM file does not contain EELS spectral data", file_info)


class DMNonSupportedDataType(DMFileError):
    """Raised when data type is not supported by NumPy."""
    
    def __init__(self, data_type=None):
        super().__init__("Data type not supported for NumPy operations", data_type)


class DMConflictingDataTypeRead(DMFileError):
    """Raised when data type doesn't match expected size or item count."""
    
    def __init__(self, conflict_info=None):
        super().__init__("Data type conflicts with expected size/count", conflict_info)


class DMEmptyInfoDictionary(DMFileError):
    """Raised when the info dictionary is empty or not provided."""
    
    def __init__(self, dict_info=None):
        super().__init__("Empty or missing info dictionary from DM file", dict_info)


class DMShapeMismatchError(DMFileError):
    """Raised when data shape doesn't match expected dimensions."""
    
    def __init__(self, image_name=None, expected_shape=None, actual_shape=None):
        self.image_name = image_name
        self.expected_shape = expected_shape
        self.actual_shape = actual_shape
        
        message = f"Shape mismatch for {image_name}: expected {expected_shape}, got {actual_shape}"
        super().__init__(message, {
            'image_name': image_name,
            'expected_shape': expected_shape,
            'actual_shape': actual_shape
        })


class DMFileLoadingError(DMFileError):
    """Raised when DM file cannot be loaded or is corrupted."""
    
    def __init__(self, filename=None):
        super().__init__("Invalid or corrupted DM3/DM4 file", filename)


class DMFileUploadError(DMFileError):
    """Raised when file upload processing fails."""
    
    def __init__(self, original_exception=None):
        super().__init__("File upload processing failed", str(original_exception) if original_exception else None)


class DMFileRemovalError(DMFileError):
    """Raised when file removal operations fail."""
    
    def __init__(self, original_exception=None):
        super().__init__("File removal operation failed", str(original_exception) if original_exception else None)


class DMPlotCreationError(DMFileError):
    """Raised when plot creation fails."""
    
    def __init__(self, original_exception=None):
        super().__init__("Plot creation failed", str(original_exception) if original_exception else None)
