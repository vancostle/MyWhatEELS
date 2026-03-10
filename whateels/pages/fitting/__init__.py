from whateels.templates import GeneralPageTemplate
from .MVC import FittingModel, FittingController, FittingView
from whateels.state import CacheManager

class Fitting(GeneralPageTemplate):
    """
    Quantification class for the WhatEELS application.
    This class extends CustomPage to create a specific quantification page layout.
    """

    def __init__(self):
        model = FittingModel()
        view = FittingView(model)   
        FittingController(model, view)
        
        app_state = CacheManager.get_cached_app_state()
        
        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar] if app_state.metadata is not None else [],
            right_sidebar=[] if app_state.metadata is None else [view.right_sidebar],
            collapsed_sidebar=True,
        )