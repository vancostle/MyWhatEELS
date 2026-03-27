from whateels.templates import GeneralPageTemplate
from .MVC import HomePageController, HomePageView, HomePageModel

class HomePage(GeneralPageTemplate):
    """
    HomePage class for the WhatEELS application.
    This class extends CustomPage to create a specific home page layout.
    """

    def __init__(self):
        # Model is created fresh each navigation — Panel's session lifecycle
        # handles cleanup of the old session's resources automatically.
        # AppState (user data) is preserved separately in pn.state.cache.
        model = HomePageModel()
        view = HomePageView(model)
        HomePageController(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar, view.left_sidebar.welcome_message],
            right_sidebar=[view.right_sidebar],
            sidebar_width=260
        )