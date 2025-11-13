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
    # Reactive parameter to hold the dataset currently plotted in the visualizer
    plot_dataset = param.Parameter(default=None, doc="""
        The xarray Dataset (or view) currently used to build figA/figB in the
        SpectrumImageVisualizer. Stored here so other pages (e.g. multifitting)
        can access the same dataset instance.
    """)

    # Reactive parameter for all loaded datasets
    all_datasets = param.List(default=list(), doc="""
        List of all loaded EELS datasets (xarray.Dataset).
    """)

    filename = param.String(default="No file uploaded", doc="""
        Name of the currently loaded file.
    """)
    
    selected_tab_index_dataset = param.Integer(default=0, doc="""
        Index of the currently selected dataset tab.
    """)

    quantification_elements = param.List(default=list(), doc="""
        List of quantification elements selected for quantification.
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

    @param.depends('plot_dataset', watch=True)
    def _on_plot_dataset_change(self):
        """Called when the shared plot dataset changes."""
        if self.plot_dataset is not None:
            _logger.info("plot_dataset published to AppState")
        else:
            _logger.info("plot_dataset cleared in AppState")
    @param.depends('all_datasets', watch=True)
    def _on_datasets_change(self):
        """Called automatically when all_datasets parameter changes."""
        count = len(self.all_datasets) if isinstance(self.all_datasets, list) else 0
        _logger.info(f"All datasets updated via param, count: {count}")
        
    @param.depends('filename', watch=True)
    def _on_filename_change(self):
        """Called automatically when filename parameter changes."""
        if self.filename is not None and self.filename != "":
            _logger.info(f"Filename updated via param: {self.filename}")
        else:
            _logger.info("Filename cleared via param")
            
    @param.depends('selected_tab_index_dataset', watch=True)
    def _on_selected_tab_index_change(self):
        """Called automatically when selected_tab_index_dataset changes."""
        _logger.info(f"Selected dataset tab index changed to: {self.selected_tab_index_dataset}")

    def clear_metadata(self):
        self.metadata = None
        
    def clear_datasets(self):
        self.all_datasets = []
        
    def clear_filename(self):
        self.filename = ""
    
    def clear_elements_selected(self):
        self.quantification_elements = []
        
    def clear_selected_tab_index(self):
        self.selected_tab_index_dataset = 0

    def clear_all(self):
        """Clear all shared state parameters."""
        self.clear_metadata()
        self.clear_datasets()
        self.clear_filename()
        self.clear_elements_selected()
        self.clear_selected_tab_index()
