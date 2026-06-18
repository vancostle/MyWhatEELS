import time
from whateels.templates import GeneralPageTemplate
from .MVC import HomePageController, HomePageView, HomePageModel

class HomePage(GeneralPageTemplate):
    """
    HomePage class for the WhatEELS application.
    This class extends CustomPage to create a specific home page layout.
    """

    def __init__(self):
        _t0 = time.perf_counter()

        # Model is created fresh each navigation — Panel's session lifecycle
        # handles cleanup of the old session's resources automatically.
        # AppState (user data) is preserved separately in pn.state.cache.
        model = HomePageModel()
        _t_model = time.perf_counter()

        view = HomePageView(model)
        _t_view = time.perf_counter()

        HomePageController(model, view)
        _t_controller = time.perf_counter()

        super().__init__(
            title=model.constants.TITLE,
            main=[view.main],
            sidebar=[view.left_sidebar, view.left_sidebar.welcome_message],
            right_sidebar=[view.right_sidebar],
            sidebar_width=260,
            right_sidebar_width=378,
            collapsed_right_sidebar=True,
        )
        _t_end = time.perf_counter()

        print(
            f"\n[HomePage] Load breakdown:"
            f"\n  Model:      {(_t_model      - _t0)          * 1000:.1f} ms"
            f"\n  View:       {(_t_view       - _t_model)     * 1000:.1f} ms"
            f"\n  Controller: {(_t_controller - _t_view)      * 1000:.1f} ms"
            f"\n  Template:   {(_t_end        - _t_controller)* 1000:.1f} ms"
            f"\n  TOTAL:      {(_t_end        - _t0)          * 1000:.1f} ms\n"
        )