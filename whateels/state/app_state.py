"""
AppState model for shared application state management.

Uses param.Parameterized for reactive updates across Panel components.
State is cached per-user (or globally if no auth configured).
"""

import param
from whateels.helpers.logging import Logger

_logger = Logger.get_logger("shared_state.log", __name__)

class AppState(param.Parameterized):
    """
    Shared application state using param for reactive metadata management.
    
    This class provides a reactive way to share metadata across the application.
    Any Panel component can depend on the state parameters and will automatically
    update when they change.
    
    Instances are cached per-user (or globally), ensuring cross-tab sharing
    for the same user while maintaining isolation between users.
    """
    
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
        The xarray Dataset (or view) currently used to build paneA/paneB in the
        SpectrumImageVisualizer. Stored here so other pages (e.g. multifitting)
        can access the same dataset instance.
    """)
    
    # Reactive parameter for all loaded datasets
    all_datasets = param.List(default=list(), doc="""
        List of all loaded EELS datasets (xarray.Dataset).
    """)
    
    spectra = param.Parameter(default=None, doc="""
        Spectra of selected data
    """)

    is_multifit = param.Boolean(default=False, doc="""
        Flag indicating whether background subtraction (multifit) is enabled.
    """)

    fitting_results = param.Parameter(default=None, doc="""
        The results of the fitting procedure, stored here for access across pages. 
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

    last_clustering_result = param.Parameter(default=None, doc="""
        The last clustering result dictionary.
    """)

    preprocessed_electron_count = param.Parameter(default=None, doc="""
        The fully preprocessed ElectronCount DataArray, cached after the user
        clicks 'Apply Active Preprocessors' on the home page.
        Contains the result of all active data-transforming preprocessors
        (spike removal, background subtraction) applied to every pixel.
        None when no preprocessors have been applied or after reverting to raw.
    """)

    # Preprocessed counterparts of plot_dataset / all_datasets
    preprocessed_plot_dataset = param.Parameter(default=None, doc="""
        Preprocessed version of plot_dataset. Set when the user applies
        preprocessors on the home page. Used by pages (e.g. clustering) that
        offer a 'Use preprocessed data' switch.
        None if no preprocessing has been applied yet.
    """)

    preprocessed_all_datasets = param.List(default=list(), doc="""
        Preprocessed counterpart of all_datasets. Each entry corresponds to
        the same index in all_datasets but contains the preprocessed variant.
        Empty until the user applies preprocessors on the home page.
    """)

    def __init__(self):
        super().__init__()

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
        self.clear_elements_selected()
        
    @param.depends('filename', watch=True)
    def _on_filename_change(self):
        """Called automatically when filename parameter changes."""
        if self.filename is not None and self.filename != "":
            _logger.info(f"Filename updated via param: {self.filename}")
        else:
            _logger.info("Filename cleared via param")
        self.clear_elements_selected()
            
    @param.depends('selected_tab_index_dataset', watch=True)
    def _on_selected_tab_index_change(self):
        """Called automatically when selected_tab_index_dataset changes."""
        _logger.info(f"Selected dataset tab index changed to: {self.selected_tab_index_dataset}")
        
    @param.depends('last_clustering_result', watch=True)
    def _on_last_clustering_result_change(self):
        """Called automatically when last_clustering_result changes."""
        if self.last_clustering_result is not None:
            _logger.info("Last clustering result updated via param")
        else:
            _logger.info("Last clustering result cleared via param")

    def clear_metadata(self):
        self.metadata = None
        
    def clear_datasets(self):
        # Clear the list; CPython reference counting handles the actual deallocation.
        self.all_datasets = []
        
    def clear_filename(self):
        self.filename = ""
    
    def clear_elements_selected(self):
        self.quantification_elements = []
        
    def clear_selected_tab_index(self):
        self.selected_tab_index_dataset = 0
    
    def clear_last_clustering_result(self):
        self.last_clustering_result = None

    def clear_preprocessed_electron_count(self):
        self.preprocessed_electron_count = None

    def clear_preprocessed_plot_dataset(self):
        self.preprocessed_plot_dataset = None

    def clear_preprocessed_all_datasets(self):
        self.preprocessed_all_datasets = []

    def clear_all(self):
        """Clear all shared state parameters."""
        self.clear_metadata()
        self.clear_datasets()
        self.clear_filename()
        self.clear_elements_selected()
        self.clear_selected_tab_index()
        self.clear_last_clustering_result()
        self.clear_preprocessed_electron_count()
        self.clear_preprocessed_plot_dataset()
        self.clear_preprocessed_all_datasets()
