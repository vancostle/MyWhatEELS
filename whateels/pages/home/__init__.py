import panel as pn
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
        
        # Create a simple modal
        modal_content = pn.Column(
            pn.pane.Markdown("# Welcome to WhatEELS!"),
            pn.pane.Markdown("This is a simple modal example."),
            width=400,
            height=200
        )

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar],
            modal=[modal_content],
            sidebar_width=260
        )
        
        # Set up the modal trigger
        def open_modal(event):
            self.open_modal()
        
        view.left_sidebar.open_modal_btn.on_click(open_modal)