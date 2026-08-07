"""
AppState model for shared application state management.

Uses param.Parameterized for reactive updates across Panel components.
State is cached per-user (or globally if no auth configured).
"""

import param

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

    preprocessed_plot_dataset = param.Parameter(default=None, doc="""
        Copy of plot_dataset with its ElectronCount replaced by the fully
        preprocessed DataArray (spike removal, Savitzky-Golay smoothing,
        PCA reconstruction, background subtraction, cut range).
        Set when the user applies preprocessors on the home page.
        None when no preprocessing has been applied or after reverting to raw.
        Consumers access the ElectronCount via preprocessed_plot_dataset["ElectronCount"].
    """)

    nlls_workspace = param.Parameter(default=None, doc="""
        Active Elemental NLLS workspace. It is separate from the manual fitting
        dictionary and always carries a DatasetIdentity.
    """)

    nlls_results = param.Parameter(default=None, doc="""
        Dense xarray result of an Elemental NLLS run. ModelResult objects are
        never stored here.
    """)

    nlls_run_state = param.ObjectSelector(
        default="idle",
        objects=[
            "idle",
            "building",
            "fitting_references",
            "running",
            "cancelling",
            "complete",
            "error",
        ],
        doc="Current Elemental NLLS controller/service state.",
    )

    nlls_revision = param.Integer(default=0, bounds=(0, None), doc="""
        Reactive revision incremented whenever mutable NLLS workspace content changes.
    """)

    def __init__(self):
        super().__init__()

    @param.depends('metadata', watch=True)
    def _on_metadata_change(self):
        """Called automatically when metadata parameter changes."""
        # print(f"Metadata updated via param: {self.metadata}")
        pass
            
    @param.depends('multifit', watch=True)
    def _on_multifit_change(self):
        """Called automatically when multifit parameter changes."""
        # print(f"Multifit updated via param: {self.multifit}")
        pass

    @param.depends('plot_dataset', watch=True)
    def _on_plot_dataset_change(self):
        """Called when the shared plot dataset changes."""
        # print("Plot dataset updated via param.")
        pass
    
    @param.depends('all_datasets', watch=True)
    def _on_datasets_change(self):
        """Called automatically when all_datasets parameter changes."""
        # count = len(self.all_datasets) if isinstance(self.all_datasets, list) else 0
        # self.clear_elements_selected()
        pass
        
    @param.depends('filename', watch=True)
    def _on_filename_change(self):
        """Called automatically when filename parameter changes."""
        # print(f"Filename updated via param: {self.filename}")
        self.clear_elements_selected()
            
    @param.depends('selected_tab_index_dataset', watch=True)
    def _on_selected_tab_index_change(self):
        """Called automatically when selected_tab_index_dataset changes."""
        # print(f"Selected dataset tab index updated via param: {self.selected_tab_index_dataset}")
        self.clear_elements_selected()        

    @param.depends('last_clustering_result', watch=True)
    def _on_last_clustering_result_change(self):
        """Called automatically when last_clustering_result changes."""
        # print("Last clustering result updated via param.")
        pass

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

    def clear_preprocessed_plot_dataset(self):
        self.preprocessed_plot_dataset = None

    def clear_nlls_state(self):
        """Clear only Elemental NLLS state, preserving manual fitting fields."""
        self.nlls_workspace = None
        self.nlls_results = None
        self.nlls_run_state = "idle"
        self.nlls_revision += 1

    def clear_all(self):
        """Clear all shared state parameters."""
        self.clear_metadata()
        self.clear_datasets()
        self.clear_filename()
        self.clear_elements_selected()
        self.clear_selected_tab_index()
        self.clear_last_clustering_result()
        self.clear_preprocessed_plot_dataset()
        self.clear_nlls_state()
