"""Exceptions for NumPy (.npy) file operations."""

from .base import NpyFileError


class NpyFileLoadingError(NpyFileError):
    """Raised when a .npy file cannot be loaded."""
    def __init__(self, filename=None):
        super().__init__("Invalid or unreadable NumPy file", filename)


class NpyFileUploadError(NpyFileError):
    """Raised when .npy file upload processing fails."""
    def __init__(self, original_exception=None):
        super().__init__(
            "File upload processing failed",
            str(original_exception) if original_exception else None,
        )


class NpyShapeMismatchError(NpyFileError):
    """Raised when a .npy array shape is not supported."""
    def __init__(self, shape=None):
        super().__init__("Unsupported array shape for .npy file", str(shape))
