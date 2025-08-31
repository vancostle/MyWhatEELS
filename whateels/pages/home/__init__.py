from whateels.components import CustomPage
from .MVC import Model, Controller, View

class Home(CustomPage):
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
            sidebar=[view.sidebar],
        )