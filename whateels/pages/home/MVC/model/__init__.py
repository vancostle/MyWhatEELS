
# from typing import Optional, TYPE_CHECKING
from whateels.helpers.in_memory_file import InMemoryFile
from .constants import Constants, Placeholders
from whateels.shared_state import AppState

# if TYPE_CHECKING:
#     from whateels.pages.home.MVC.controller import HomePageController

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
        self._app_state = AppState()
        
        # Reference to the active controller — used to clean up the previous
        # instance when a new HomePage is created within the same session.
        # self._active_controller: Optional["HomePageController"] = None
    
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
    def app_state(self) -> AppState:
        return self._app_state

    # @property
    # def active_controller(self) -> Optional["HomePageController"]:
    #     """Reference to the currently active HomePageController instance."""
    #     return self._active_controller

    # @active_controller.setter
    # def active_controller(self, controller: Optional["HomePageController"]):
    #     self._active_controller = controller

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