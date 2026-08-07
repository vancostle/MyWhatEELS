class Constants:
    TITLE = "Fitting"
    
    # Visualization constants
    AXIS_X = 'x'
    AXIS_Y = 'y'
    ELOSS = 'Eloss'
    ELECTRON_COUNT = 'ElectronCount'

    # Dataset types
    SPECTRUM_LINE = 'SLi'
    SPECTRUM_IMAGE = 'SIm'
    SINGLE_SPECTRUM = 'SSp'
    IMAGE = 'Img'
    
    DEFAULT_BACKGROUND_SUBTRACTION = False

    # Right sidebar tabs
    TAB_MANUAL = "Manual"
    TAB_ELEMENTAL = "Elemental"
    TAB_RESULTS = "Results"

    # TODO (NLLS_TODO 5.5:663): migrate the elemental defaults below - and the
    # CHEMICAL_SHIFT_TOOLTIP text - to whateels/nlls/defaults.py once that module
    # exists, and share them with the quantification view (NLLS_TODO 5.4.2:478)
    # so the domain phase does not create a third copy of these values.
    # Elemental NLLS defaults
    AVAILABLE_ELEMENTAL_MODELS = ["GaussianModel", "LorentzianModel", "PseudoVoigtModel", "SplitLorentzianModel"]
    DEFAULT_ELEMENTAL_MODEL = "GaussianModel"
    DEFAULT_ELEMENTAL_FLEXIBILITY = "Medium"
    AVAILABLE_ELEMENTAL_FLEXIBILITIES = ["Low", "Medium", "High", "Maximum"]
    AVAILABLE_ELEMENTAL_AREAS = ["default"]
    DEFAULT_ELEMENTAL_AREA = "default"

    # Elemental NLLS - OOS controls (NLLS_TODO 5.1)
    # Model composition
    AVAILABLE_ELEMENTAL_MODEL_COMPOSITIONS = {
        "Continuum + ELNES": "continuum_plus_elnes",
        "Continuum only": "continuum_only",
    }
    DEFAULT_ELEMENTAL_MODEL_COMPOSITION = "continuum_plus_elnes"

    # Edge definition
    ELEMENTAL_MIN_ATOMIC_NUMBER = 1
    ELEMENTAL_MAX_ATOMIC_NUMBER = 99
    DEFAULT_ELEMENTAL_ATOMIC_NUMBER = 1

    # Experimental geometry: E0, beta and alpha are no longer typed in the Elemental tab.
    # They are read and edited in the shared "Dataset Information" card
    # (whateels/components/dataset_info_card.py), which writes into dataset.attrs, so the
    # DEFAULT_ELEMENTAL_* geometry defaults no longer exist. Only the geometry STATUS pane
    # stays in the tab (see ELEMENTAL_GEOMETRY_STATUS_UNKNOWN, NLLS_TODO 5.1:276).

    # Chemical shift: the only manual correction of the edge position
    DEFAULT_ELEMENTAL_CHEMICAL_SHIFT = 0.0
    ELEMENTAL_CHEMICAL_SHIFT_STEP = 0.1
    CHEMICAL_SHIFT_TOOLTIP = (
        "Positive chemical shift evaluates table(x + shift) and moves the modeled edge "
        "to lower energy; ELNES center uses the opposite direction."
    )

    # Edge softening
    DEFAULT_ELEMENTAL_SOFTEN_EDGE = True
    DEFAULT_ELEMENTAL_SOFTEN_STRENGTH = 1.5
    ELEMENTAL_SOFTEN_STRENGTH_STEP = 0.1

    # OOS status (read-only, informative)
    DEFAULT_ELEMENTAL_OOS_METHOD_VERSION = "OOS / F. Salvat Hartree cross-sections (version not resolved)"
    ELEMENTAL_BACKGROUND_STATUS_UNKNOWN = (
        "**Background status:** unknown - no validated power-law pre-edge subtraction "
        "provenance for the active source."
    )
    ELEMENTAL_OOS_STATUS_PLACEHOLDER = (
        "**OOS status:** no edge selected yet. Table, version/checksum and covered energy "
        "range will be reported here."
    )
    ELEMENTAL_GEOMETRY_STATUS_UNKNOWN = (
        "**Geometry status:** not validated yet - E0, beta and alpha will be read from the "
        "dataset metadata. E0 <= 0 or beta <= 0 is reported here and corrected locally, "
        "without touching the dataset attributes."
    )
    ELEMENTAL_ONSET_READOUT_PLACEHOLDER = "Onset (eV): -"

    # Elemental tab section titles
    SECTION_ELEMENTAL_EDGE = "Edge Definition"
    SECTION_ELEMENTAL_MODEL = "Model Setup"
    SECTION_ELEMENTAL_OOS_STATUS = "OOS Status"
    SECTION_ELEMENTAL_AREAS = "Areas"
    SECTION_ELEMENTAL_RUN_SETUP = "Run Setup"
    # SECTION_ELEMENTAL_MODEL_IO removed: Save/Load Model (NLLS_TODO 5.1:287 and 12.1)
    # returns in the serialization phase.

    # Elemental tab tooltips
    TOOLTIP_ELEMENTAL_SUBSHELLS = (
        "Subshell options come from the OOS catalogue and are filled in once an element is selected."
    )
    TOOLTIP_ELEMENTAL_FIT_AREAS = "Areas become selectable once their reference fit has converged."
    TOOLTIP_ELEMENTAL_FIT_RANGE = "The fit range is initialised from the dataset energy-loss axis."
    TOOLTIP_ELEMENTAL_SOFTEN = (
        "Soften strength is expressed in eV, never in samples: it is converted to channels with "
        "the real dataset dispersion. If a FWHM is entered, convert once with "
        "sigma_eV = fwhm_eV / 2.354820045. The 1.5 default is kept only for compatibility with "
        "the legacy code."
    )
    TOOLTIP_ELEMENTAL_OOS_METHOD = (
        "Informative field: OOS / F. Salvat is the only continuum backend. It is persisted with "
        "the model and is not a GOS selector."
    )

    # K-Means defaults
    DEFAULT_SELECTED_NORM = 'none'
    AVAILABLE_NORMS = [DEFAULT_SELECTED_NORM, 'l1', 'l2', 'max']
    DEFAULT_NUMBER_OF_CLUSTERS = 3
    DEFAULT_NUMBER_OF_INIT = 10
    DEFAULT_MAX_ITER = 100
    DEFAULT_INIT_METHOD = 'k-means++'
    AVAILABLE_INIT_METHODS = [DEFAULT_INIT_METHOD, 'random']

    # Tabs clustering names
    TAB_KMEANS = "K-Means"
    TAB_AGGLOMERATIVE = "Agglomerative"
    TAB_SPECTRAL = "Spectral"
    
    # Input keys
    INPUT_N_CLUSTERS = "n_clusters"
    INPUT_AVAILABLE_NORMS = "available_norms"
    INPUT_N_INIT = "n_init"
    INPUT_MAX_ITER = "max_iter"
    INPUT_INIT_METHOD = "init_method"
    INPUT_LINKAGE = "linkage"
    INPUT_AFFINITY = "affinity"
    INPUT_SPECTRAL_AFFINITY = "spectral_affinity"
    INPUT_SPECTRAL_N_NEIGHBORS = "spectral_n_neighbors"
    INPUT_SPECTRAL_GAMMA = "spectral_gamma"
    INPUT_LABELS_ASSIGN_METHOD = "labels_assign_method"
    
    # K-Means defaults
    DEFAULT_SELECTED_NORM = 'none'
    AVAILABLE_NORMS = [DEFAULT_SELECTED_NORM, 'l1', 'l2', 'max']
    DEFAULT_NUMBER_OF_CLUSTERS = 3
    DEFAULT_NUMBER_OF_INIT = 10
    DEFAULT_MAX_ITER = 100
    DEFAULT_INIT_METHOD = 'k-means++'
    AVAILABLE_INIT_METHODS = [DEFAULT_INIT_METHOD, 'random']
    
    # Agglomerative defaults
    DEFAULT_LINKAGE = 'ward'
    AVAILABLE_LINKAGE_METHODS = [DEFAULT_LINKAGE, 'complete', 'average', 'single']
    DEFAULT_AFFINITY = 'euclidean'
    AVAILABLE_AFFINITIES = [DEFAULT_AFFINITY, 'manhattan', 'cosine']
    
    # Spectral defaults
    DEFAULT_SPECTRAL_AFFINITY = 'rbf'
    AVAILABLE_SPECTRAL_AFFINITIES = [DEFAULT_SPECTRAL_AFFINITY, 'nearest_neighbors']
    DEFAULT_SPECTRAL_N_NEIGHBORS = 20
    DEFAULT_SPECTRAL_GAMMA = 1.0
    DEFAULT_SPECTRAL_ASSIGN_LABELS = 'kmeans'
    AVAILABLE_SPECTRAL_ASSIGN_LABELS = [DEFAULT_SPECTRAL_ASSIGN_LABELS, 'discretize', 'cluster_qr']