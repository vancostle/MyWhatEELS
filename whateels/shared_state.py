"""
Shared Application State for WhatEELS

This module provides a singleton AppState class to manage shared metadata
across different pages and components of the WhatEELS application.

The AppState uses param for reactive updates across the application.
"""

import param
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
    # Reactive parameter for multifit results/state
    multifit = param.Parameter(default=None, doc="""
        Multifit results or state object. None if not available yet.
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
            
    @param.depends('multifit', watch=True)
    def _on_multifit_change(self):
        """Called automatically when multifit parameter changes."""
        if self.multifit is not None:
            _logger.info(f"Multifit updated via param")
        else:
            _logger.info("Multifit cleared via param")