class Constants:
    TEMP_PREFIX = "whateels_"
    TITLE = "WhatEELS"
    
    # Visualization constants
    AXIS_X = 'x'
    AXIS_Y = 'y'
    ELOSS = 'Eloss'
    ELECTRON_COUNT = 'ElectronCount'

    # Eloss axis metadata (set by file loaders; read by plots)
    ELOSS_CALIBRATED_ATTR = 'eloss_calibrated'
    ELOSS_AXIS_LABEL_ATTR = 'eloss_axis_label'
    ELOSS_AXIS_LABEL_EV = 'Energy Loss (eV)'
    ELOSS_AXIS_LABEL_CHANNEL = 'Channel index'

    # Dataset types
    SPECTRUM_LINE = 'SLi'
    SPECTRUM_IMAGE = 'SIm'
    SINGLE_SPECTRUM = 'SSp'
    IMAGE = 'Img'
    
    # FileDropper constants
    FILE_DROPPER_TITLE = "Select DM3, DM4 or HyperSpy file"
    FILE_DROPPER_VALID_EXTENSIONS = ('.dm3', '.dm4', '.hspy', '.npy', '.npz', '.emd')
    FILE_DROPPER_REJECT_MESSAGE = "Unsupported file type!"
