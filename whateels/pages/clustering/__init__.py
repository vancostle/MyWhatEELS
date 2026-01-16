from whateels.templates import GeneralPageTemplate
from .MVC import ClusteringModel, ClusteringController, ClusteringView

class Clustering(GeneralPageTemplate):
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
            sidebar=[view.left_sidebar] if model.app_state.metadata is not None else [],
            right_sidebar=[] if model.app_state.metadata is None else [view.right_sidebar],
            collapsed_sidebar=True,
        )