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

    # Elemental NLLS defaults
    AVAILABLE_ELEMENTAL_MODELS = ["GaussianModel", "LorentzianModel", "PseudoVoigtModel", "SplitLorentzianModel"]
    DEFAULT_ELEMENTAL_MODEL = "GaussianModel"
    DEFAULT_ELEMENTAL_ENERGY_CENTER = 500
    ELEMENTAL_ENERGY_RANGE_THRESHOLD = 50
    DEFAULT_ELEMENTAL_FLEXIBILITY = "Low"
    AVAILABLE_ELEMENTAL_FLEXIBILITIES = ["Low", "Medium", "High", "Maximum"]
    AVAILABLE_ELEMENTAL_AREAS = ["Area 1"]
    DEFAULT_ELEMENTAL_AREA = "Area 1"

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