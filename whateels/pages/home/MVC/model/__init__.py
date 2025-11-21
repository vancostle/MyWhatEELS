from whateels.helpers.in_memory_file import InMemoryFile
from .constants import Constants, Placeholders

class HomePageModel:
    """
    Main application model for the WhatEELS home page.
    Stores the loaded EELS dataset, metadata, and shared configuration/state.
    """
    def __init__(self):
        # State attributes
        self._in_memory_file: InMemoryFile | None = None  # Currently loaded file in memory (if any)

        # Shared configuration and constants
        self._constants = Constants()
        self._placeholders = Placeholders()

    @property
    def constants(self) -> Constants:
        return self._constants
    @property
    def in_memory_file(self) -> InMemoryFile | None:
        return self._in_memory_file
    @property
    def placeholders(self) -> Placeholders:
        return self._placeholders

    @in_memory_file.setter
    def in_memory_file(self, file: InMemoryFile | None):
        """Set the in-memory file (or None to clear)."""
        self._in_memory_file = file
        
    @in_memory_file.deleter
    def in_memory_file(self):
        """Delete the in-memory file to free resources."""
        if self._in_memory_file:
            self._in_memory_file.close()
            self._in_memory_file = None