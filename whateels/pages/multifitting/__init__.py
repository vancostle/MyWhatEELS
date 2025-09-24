from whateels.components import CustomPage
from .MVC import Model, Controller, View

class MultiFitting(CustomPage):
    """
    MultiFitting page for the WhatEELS application.
    """

    def __init__(self):
        model = Model()
        view = View(model)
        Controller(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            header=[],  # No header for this page, pass [] to avoid default header
            header_background=model.constants.HEADER_BACKGROUND
        )