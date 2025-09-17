import panel as pn

# Configure Panel with theme support (only called once here)
pn.extension('filedropper', 'floatpanel', 'plotly', theme='default')

from whateels.helpers import LoadCSS, CSS_ROOT
from whateels.pages import Home, Metadata, Clustering

class App:
    """
    Main application class for WhatEELS.
    
    This class initializes the Panel application with the necessary pages and configurations.
    """

    _DEFAULT_TITLE = "App"
    _DEFAULT_PORT = 5006
    
    def __init__(self, title : str = _DEFAULT_TITLE):
        self.title = title

    def run(self, port : int = _DEFAULT_PORT):
        # Load CSS files only once
        LoadCSS([
            str(CSS_ROOT / "home.css"),
            str(CSS_ROOT / "login.css"),
            str(CSS_ROOT / "custom_page.css"),
        ])
        
        # Define the pages for the application
        pages = {
            "/": Home(),
            "/metadata-details": Metadata(),
            "/clustering": Clustering(),
        }

        return pn.serve(
            pages,
            title=self.title,
            port=port,
        )