from whateels.templates import GeneralPageTemplate
from .MVC import QuantificationModel, QuantificationController, QuantificationView
from whateels.shared_state import get_cached_app_state

class Quantification(GeneralPageTemplate):
    """
    Quantification class for the WhatEELS application.
    This class extends CustomPage to create a specific quantification page layout.
    """

    def __init__(self):
        model = QuantificationModel()
        view = QuantificationView(model)
        QuantificationController(model, view)
        
        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar] if get_cached_app_state().metadata is not None else [],
            right_sidebar=[] if get_cached_app_state().metadata is None else [view.right_sidebar],
            collapsed_sidebar=True,
        )