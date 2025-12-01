class Constants:
    TEMP_PREFIX = "whateels_"
    TITLE = "WhatEELS"
    
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
    
    # FileDropper constants
    FILE_DROPPER_TITLE = "Upload EELS data file"
    FILE_DROPPER_VALID_EXTENSIONS = ('.dm3', '.dm4')
    FILE_DROPPER_REJECT_MESSAGE = "Invalid file type."
    FILE_DROPPER_SUCCESS_MESSAGE = "File uploaded successfully!"
    FILE_DROPPER_FEEDBACK_MESSAGE = "No file uploaded yet... :(" # TODO: REMOVE IT