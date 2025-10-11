from whateels.components import CustomPage
from .MVC import Model, Controller, View

class Quantification(CustomPage):
    """
    Quantification class for the WhatEELS application.
    This class extends CustomPage to create a specific quantification page layout.
    """

    def __init__(self):
        model = Model()
        view = View(model)
        Controller(model, view)

        super().__init__(
            title="Quantification",
            main=[view.main],
            sidebar=[view.sidebar],
        )