
import time
from whateels.templates import GeneralPageTemplate
from .MVC import HomePageController, HomePageView, get_cached_homepage_model

class HomePage(GeneralPageTemplate):
    """
    HomePage class for the WhatEELS application.
    This class extends CustomPage to create a specific home page layout.
    """

    def __init__(self):
        start = time.perf_counter()
        model = get_cached_homepage_model()
        
        # Clean up the previous controller/view before creating new ones.
        # This prevents memory leaks from accumulated watchers and callbacks
        # when the user navigates away from and back to the HomePage multiple times
        # within the same session (model is cached, but view/controller are recreated).
        if model.active_controller is not None:
            model.active_controller.cleanup()
            model.active_controller = None

        view = HomePageView(model)
        HomePageController(model, view)

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar, view.left_sidebar.welcome_message],
            sidebar_width=260
        )
        elapsed = time.perf_counter() - start
        print(f"[DEBUG] Tiempo de carga HomePage: {elapsed:.3f} s")