"""
Data Parsers for Home Page Controller

This module contains parsing logic specific to the home page functionality,
particularly for processing DM3/DM4 files and extracting EELS data.
"""

from .dm_eels_data import DM_EELS_data
from .dm_info_parser import DM_InfoParser

__all__ = [
    'DM_EELS_data',
    'DM_InfoParser'
]
