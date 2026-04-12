
import sys
import panel as pn
import holoviews as hv
# Import only what is strictly needed for startup — avoids triggering
# scipy/numpy imports that live in the full helpers package.
from whateels.helpers.kill_process import KillProcess
from whateels.helpers.constants import ASSETS_ROOT

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

        # Each page is imported and instantiated only when the user first
        # visits that route — heavy dependencies (numpy, scipy, etc.) inside
        # each page module are deferred until they are actually needed.
        def _lazy(module_path: str, class_name: str):
            def _loader():
                import importlib
                mod = importlib.import_module(module_path)
                return getattr(mod, class_name)()
            return _loader

        # Define the pages for the application
        pages = {
            "/": _lazy("whateels.pages.home", "HomePage"),
            "/metadata-details": _lazy("whateels.pages.metadata", "Metadata"),
            "/clustering": _lazy("whateels.pages.clustering", "Clustering"),
            "/clustering-2": _lazy("whateels.pages.clustering_2", "Clustering2Page"),
            "/quantification": _lazy("whateels.pages.quantification", "Quantification"),
            "/fitting": _lazy("whateels.pages.fitting", "Fitting"),
        }

        return pn.serve(
            pages, # type: ignore
            title=self._title, 
            port=port,
            show=show,
            allow_websocket_origin=["*"],
            static_dirs={"assets": str(ASSETS_ROOT)},
            on_session_destroyed=lambda _ : sys.exit(0) # Ensure full process termination on session close,
        )