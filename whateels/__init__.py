import panel as pn

# Configure Panel with theme support (only called once here)
pn.extension('filedropper', 'floatpanel', 'plotly', theme='default')

from whateels.helpers import LoadCSS, CSS_ROOT
from whateels.pages import HomePage, Metadata, Clustering, MultiFitting, Quantification, NLLS, DemoPage

class App:
    """
    Main application class for WhatEELS.
    
    This class initializes the Panel application with the necessary pages and configurations.
    """

    _DEFAULT_TITLE = "App"
    _DEFAULT_PORT = 5006
    
    def __init__(self, title : str = _DEFAULT_TITLE):
        self._title = title

    def run(self, port : int = _DEFAULT_PORT, show : bool = True):
        # Load custom CSS for the entire app
        LoadCSS([str(CSS_ROOT / "custom_page.css")])

        # Define the pages for the application
        # Use lambdas to avoid immediate instantiation
        pages = {
            "/": lambda: HomePage(),
            "/metadata-details": lambda: Metadata(),
            "/clustering": lambda: Clustering(),
            "/multifit-details": lambda: MultiFitting(),
            "/quantification": lambda: Quantification(),
            # "/nlls": lambda: NLLS(),
        }

        return pn.serve(
            pages,
            title=self._title,
            port=port,
            show=show,
            allow_websocket_origin=["*"],
        )