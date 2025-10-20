from whateels.components import CustomPage
from .MVC import QuantificationModel, QuantificationController, QuantificationView

class Quantification(CustomPage):
    """
    Quantification class for the WhatEELS application.
    This class extends CustomPage to create a specific quantification page layout.
    """

    def __init__(self):
        model = QuantificationModel()
        view = QuantificationView(model)
        QuantificationController(model, view)

        super().__init__(
            title="Quantification",
            main=[view.main],
            sidebar=[view.sidebar],
            right_sidebar=[view.right_sidebar],
            collapsed_sidebar=True,
        )