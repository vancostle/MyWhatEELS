"""
Shared Application State for WhatEELS

This module provides a singleton AppState class to manage shared metadata
across different pages and components of the WhatEELS application.

The AppState uses param for reactive updates across the application.
"""

import param
from xarray import Dataset
from .helpers.logging import Logger

_logger = Logger.get_logger("shared_state.log", __name__)


class AppState(param.Parameterized):
    """
    Singleton AppState class using param for reactive metadata management.
    
    This class provides a reactive way to share metadata across the application.
    Any Panel component can depend on the metadata parameter and will automatically
    update when the metadata changes.
    """
    
    _instance = None
    
    # Reactive parameter for metadata
    metadata = param.Parameter(default=None, doc="""
        Dictionary containing EELS metadata, None if no data loaded, 
        or {'error': str} if extraction failed.
    """)

    # Reactive parameter for all loaded datasets
    all_datasets = param.List(default=list(), doc="""
        List of all loaded EELS datasets (xarray.Dataset).
    """)
    
    filename = param.String(default="", doc="""
        Name of the currently loaded file.
    """)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True

    @param.depends('metadata', watch=True)
    def _on_metadata_change(self):
        """Called automatically when metadata parameter changes."""
        if self.metadata is not None:
            _logger.info(f"Metadata updated via param")
        else:
            _logger.info("Metadata cleared via param")
            
    @param.depends('all_datasets', watch=True)
    def _on_datasets_change(self):
        """Called automatically when all_datasets parameter changes."""
        _logger.info(f"All datasets updated via param, count: {len(self.all_datasets)}")
        
    @param.depends('filename', watch=True)
    def _on_filename_change(self):
        """Called automatically when filename parameter changes."""
        if self.filename:
            _logger.info(f"Filename updated via param: {self.filename}")
        else:
            _logger.info("Filename cleared via param")
        
    def clear_metadata(self):
        self.metadata = None
        
    def clear_datasets(self):
        self.all_datasets = []
        
    def clear_filename(self):
        self.filename = ""
        
    def clear_all(self):
        """Clear all shared state parameters."""
        self.clear_metadata()
        self.clear_datasets()
        self.clear_filename()
