from whateels.templates import GeneralPageTemplate
from .MVC import MultifittingModel, MultifittingController, MultifittingView

class MultiFitting(GeneralPageTemplate):
    """
    MultiFitting page for the WhatEELS application.
    """

    def __init__(self):
        model = MultifittingModel()
        view = MultifittingView(model)
        MultifittingController(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            header=[],  # No header for this page, pass [] to avoid default header
            header_background=model.constants.HEADER_BACKGROUND
        )