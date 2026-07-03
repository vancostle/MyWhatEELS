"""Base exception for NumPy (.npy) file operations."""


class NpyFileError(Exception):
    def __init__(self, message: str, value=None):
        self.message = message
        self.value = value
        super().__init__(self.message)

    def __str__(self):
        if self.value is not None:
            return f"{self.message}: {self.value}"
        return self.message
