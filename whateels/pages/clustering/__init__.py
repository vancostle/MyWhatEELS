from whateels.components import CustomPage
from .MVC import ClusteringModel, ClusteringController, ClusteringView

class Clustering(CustomPage):
    """
    Clustering class for the WhatEELS application.
    This class extends CustomPage to create a specific clustering page layout.
    """

    def __init__(self):
        model = ClusteringModel()
        view = ClusteringView(model)
        ClusteringController(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.sidebar],
            right_sidebar=[view.right_sidebar],
            collapsed_sidebar=True,
        )