from typing import TYPE_CHECKING
from whateels.helpers.in_memory_file import InMemoryFile
from .constants import Constants, Placeholders
from whateels.state import CacheManager

if TYPE_CHECKING:
    from whateels.state import AppState

class HomePageModel:
    """
    Main application model for the WhatEELS home page.
    Created fresh on every navigation — Panel's session lifecycle handles cleanup.
    AppState (user data) is retrieved from pn.state.cache via CacheManager.
    """
    def __init__(self):
        self._in_memory_file: InMemoryFile | None = None
        self._constants = Constants()
        self._placeholders = Placeholders()
        self._app_state = CacheManager.get_cached_app_state()

    @property
    def constants(self) -> Constants:
        return self._constants
    @property
    def in_memory_file(self) -> InMemoryFile | None:
        return self._in_memory_file
    @property
    def placeholders(self) -> Placeholders:
        return self._placeholders
    @property
    def app_state(self) -> "AppState":
        return self._app_state

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