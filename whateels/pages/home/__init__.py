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
            sidebar=[view.left_sidebar, view.left_sidebar.welcome_message],
            # modal=[
            #     pn.Column(
            #         pn.pane.Markdown("# Welcome to WhatEELS!"),
            #         pn.pane.Markdown("This is a simple modal example."),
            #         width=400,
            #         height=200
            #     )    
            # ],
            sidebar_width=260
        )