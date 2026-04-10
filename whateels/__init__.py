
import time
_whe_start_time = time.perf_counter()
import panel as pn
import holoviews as hv
from pathlib import Path
from whateels.helpers import KillProcess, ASSETS_ROOT
from whateels.pages.home import HomePage
from whateels.pages.metadata import Metadata
from whateels.pages.clustering import Clustering
from whateels.pages.clustering_2 import Clustering2Page
from whateels.pages.quantification import Quantification
from whateels.pages.fitting import Fitting

# Configure Panel and HoloViews once globally — calling these inside page
# views or methods wastes time on every invocation.
pn.extension(
    'filedropper', 'floatpanel',
    notifications=True,
    theme='default',
)

# Register static CSS and JS so they are injected into every page <head>
pn.config.css_files.append('/assets/css/splash.css') # type: ignore
pn.config.css_files.append('/assets/css/custom_page.css') # type: ignore
pn.config.js_files['whatEELS_splash'] = '/assets/js/splash.js' # type: ignore

# Initialize Holoviews with Bokeh backend
hv.extension('bokeh') # type: ignore

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

        def _lazy(page_cls):
            def _loader():
                return page_cls()
            return _loader

        # Define the pages for the application
        pages = {
            "/": _lazy(HomePage),
            "/metadata-details": _lazy(Metadata),
            "/clustering": _lazy(Clustering),
            "/clustering-2": _lazy(Clustering2Page),
            "/quantification": _lazy(Quantification),
            "/fitting": _lazy(Fitting),
        }

        return pn.serve(
            pages, # type: ignore
            title=self._title, 
            port=port,
            show=show,
            allow_websocket_origin=["*"],
            static_dirs={"assets": str(ASSETS_ROOT)},
        )