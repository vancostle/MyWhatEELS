from whateels.components import CustomPage
from .MVC import LoginPageView, LoginPageController, LoginPageModel

class Login(CustomPage):
    """
    Login page class for the WhatEELS application.
    This class extends CustomPage to create a specific login page layout.
    """
    
    _DEFAULT_TITLE = "Login"
    
    def __init__(self, title: str = _DEFAULT_TITLE):

        model = LoginPageModel()
        view = LoginPageView(model)
        LoginPageController(model, view)
        
        super().__init__(
            title=title,
            main=[view.main],
        )