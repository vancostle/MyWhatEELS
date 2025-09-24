from whateels.components import CustomPage
from .MVC import Model, Controller, View

class Metadata(CustomPage):
    """
    HomePage class for the WhatEELS application.
    This class extends CustomPage to create a specific home page layout.
    """

    def __init__(self):
        model = Model()
        view = View(model)
        Controller(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            header=[], # No header for metadata page, pass [] to avoid default header
            header_background=model.constants.HEADER_BACKGROUND
        )