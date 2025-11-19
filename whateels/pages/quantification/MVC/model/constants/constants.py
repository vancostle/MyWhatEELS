class Constants:
    TITLE = "Quantification"
    
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
    
    # K-Means defaults
    DEFAULT_SELECTED_NORM = 'none'
    AVAILABLE_NORMS = [DEFAULT_SELECTED_NORM, 'l1', 'l2', 'max']
    DEFAULT_NUMBER_OF_CLUSTERS = 3
    DEFAULT_NUMBER_OF_INIT = 10
    DEFAULT_MAX_ITER = 100
    DEFAULT_INIT_METHOD = 'k-means++'
    AVAILABLE_INIT_METHODS = [DEFAULT_INIT_METHOD, 'random']