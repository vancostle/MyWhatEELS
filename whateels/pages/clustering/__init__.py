from whateels.components import CustomPage
from .MVC import Model, Controller, View

class Clustering(CustomPage):
    """
    Clustering class for the WhatEELS application.
    This class extends CustomPage to create a specific clustering page layout.
    """

    def __init__(self):
        model = Model()
        view = View(model)
        Controller(model, view)

        super().__init__(
            title="Clustering",
            main=[view.main],
            sidebar=[view.sidebar],
        )