from whateels.components import CustomPage
from .MVC import FittingModel, FittingController, FittingView
from whateels.shared_state import AppState

class Fitting(CustomPage):
    """
    Quantification class for the WhatEELS application.
    This class extends CustomPage to create a specific quantification page layout.
    """

    def __init__(self):
        model = FittingModel()
        print("NLLS initialized.")
        view = FittingView(model)
        print("NLLS View initialized.")
        FittingController(model, view)
        
        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar] if AppState().metadata is not None else [],
            right_sidebar=[] if AppState().metadata is None else [view.right_sidebar],
            collapsed_sidebar=True,
        )