class Constants:
    TITLE = "Clustering"
    
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
    
    DEFAULT_PRE_NORMALIZATION = False
    
    DEFAULT_SELECTED_NORM = 'I1'
    AVAILABLE_NORMS = [DEFAULT_SELECTED_NORM, 'I2', 'MAX']
    
    # K-Means defaults
    DEFAULT_NUMBER_OF_CLUSTERS = 3
    DEFAULT_NUMBER_OF_INIT = 10
    DEFAULT_MAX_ITER = 300
    DEFAULT_INIT_METHOD = 'k-means++'
    INITIALIZATION_METHODS = [DEFAULT_INIT_METHOD, 'random']
    
    