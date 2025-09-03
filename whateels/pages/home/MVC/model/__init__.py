from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from xarray import Dataset

from .constants import Constants, Colors, FileDropper, Placeholders

class Model:
    """
    Main application model for the WhatEELS home page.
    Stores the loaded EELS dataset, metadata, and shared configuration/state.
    """
    def __init__(self):
        # State attributes
        self._all_datasets: list["Dataset"] = []  # List of all loaded EELS datasets

        # Shared configuration and constants
        self._constants = Constants()
        self._colors = Colors()
        self._file_dropper = FileDropper()
        self._placeholders = Placeholders()
    
    @property
    def dataset(self) -> Optional["Dataset"]:
        return self._dataset
    @property
    def all_datasets(self) -> list["Dataset"]:
        return self._all_datasets
    @property
    def constants(self) -> Constants:
        return self._constants
    @property
    def colors(self) -> Colors:
        return self._colors
    @property
    def file_dropper(self) -> FileDropper:
        return self._file_dropper
    @property
    def placeholders(self) -> Placeholders:
        return self._placeholders

    @all_datasets.setter
    def all_datasets(self, datasets: list["Dataset"]):
        """Set the list of all EELS datasets."""
        self._all_datasets = datasets
