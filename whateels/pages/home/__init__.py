from whateels.components import CustomPage
from .MVC import HomePageModel, HomePageController, HomePageView

class HomePage(CustomPage):
    """
    HomePage class for the WhatEELS application.
    This class extends CustomPage to create a specific home page layout.
    """

    def __init__(self):        
        model = HomePageModel()
        view = HomePageView(model)
        HomePageController(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.sidebar],
        )