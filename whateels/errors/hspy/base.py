"""
Base HyperSpy File Exception Classes

Foundation exception classes for HyperSpy (.hspy / .zspy) file operations.
"""


class HSpyFileError(Exception):
    """Base exception for all HyperSpy file operations."""

    def __init__(self, message: str, value=None):
        self.message = message
        self.value = value
        super().__init__(self.message)

    def __str__(self):
        if self.value is not None:
            return f"{self.message}: {self.value}"
        return self.message
