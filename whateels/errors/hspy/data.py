"""
HyperSpy Data Processing Exceptions

Exceptions related to loading, processing, and removing HyperSpy files.
"""

from .base import HSpyFileError


class HSpyFileLoadingError(HSpyFileError):
    """Raised when a .hspy/.zspy file cannot be loaded or is corrupted."""

    def __init__(self, filename=None):
        super().__init__("Invalid or corrupted HyperSpy file", filename)


class HSpyFileUploadError(HSpyFileError):
    """Raised when HyperSpy file upload processing fails."""

    def __init__(self, original_exception=None):
        super().__init__(
            "File upload processing failed",
            str(original_exception) if original_exception else None,
        )


class HSpyFileRemovalError(HSpyFileError):
    """Raised when HyperSpy file removal operations fail."""

    def __init__(self, original_exception=None):
        super().__init__(
            "File removal operation failed",
            str(original_exception) if original_exception else None,
        )


class HSpyShapeMismatchError(HSpyFileError):
    """Raised when HyperSpy signal shape doesn't match expected dimensions."""

    def __init__(self, signal_name=None, expected_shape=None, actual_shape=None):
        self.signal_name = signal_name
        self.expected_shape = expected_shape
        self.actual_shape = actual_shape
        message = f"Shape mismatch for {signal_name}: expected {expected_shape}, got {actual_shape}"
        super().__init__(message, {
            'signal_name': signal_name,
            'expected_shape': expected_shape,
            'actual_shape': actual_shape,
        })


class HSpyPlotCreationError(HSpyFileError):
    """Raised when plot creation fails for a HyperSpy dataset."""

    def __init__(self, original_exception=None):
        super().__init__(
            "Plot creation failed",
            str(original_exception) if original_exception else None,
        )
