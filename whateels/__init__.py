import panel as pn
import holoviews as hv

# Configure Panel and HoloViews once globally — calling these inside page
# views or methods wastes time on every invocation.
pn.extension('filedropper', 'floatpanel', 'plotly', notifications=True, theme='default')

# Initialize Holoviews with Bokeh backend
hv.extension('bokeh') # type: ignore

from whateels.helpers import LoadCSS, CSS_ROOT, KillProcess
from whateels.pages import HomePage, Metadata, Clustering, MultiFitting, Quantification, DemoPage, Login, Clustering2Page, Fitting

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
        # Kill any process using the port
        KillProcess.by_port(port) # Ensure the port is free
        
        # Load custom CSS for the entire app
        LoadCSS([str(CSS_ROOT / "custom_page.css")])

        # Define the pages for the application
        # Use lambdas to avoid immediate instantiation
        pages = {
            "/": lambda: HomePage(),
            "/metadata-details": lambda: Metadata(),
            "/clustering": lambda: Clustering(),
            "/clustering-2": lambda: Clustering2Page(),
            "/multifit-details": lambda: MultiFitting(),
            "/quantification": lambda: Quantification(),
            "/fitting": lambda: Fitting(),
        }

        return pn.serve(
            pages,
            title=self._title,
            port=port,
            show=show,
            allow_websocket_origin=["*"],
        )