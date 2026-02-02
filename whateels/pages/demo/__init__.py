from whateels.templates import GeneralPageTemplate
from .MVC import DemoPageView, DemoPageController, DemoPageModel

class DemoPage(GeneralPageTemplate):
    """
    DemoPage class for the WhatEELS application.
    This class extends CustomPage to create a specific demo page layout.
    """

    def __init__(self):        
        model = DemoPageModel()
        view = DemoPageView(model, custom_page=self)
        DemoPageController(model, view)
        
        super().__init__(
            title="Demo Page",
            main=[view.main],
            sidebar=[view.left_sidebar],
            right_sidebar=[view.right_sidebar],
            modal=view.modals,
            sidebar_width=200
        )