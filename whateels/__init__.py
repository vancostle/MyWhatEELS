
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

        # Imports are static so PyInstaller can trace them, but placed here
        # (inside run()) so they execute AFTER the splash screen is already
        # visible. Heavy deps (numpy, scipy) are only pulled in at this point.
        
        # from whateels.pages import HomePage, Metadata, Clustering, Clustering2Page, Quantification, Fitting, HomePageRosetta
        from whateels.pages import HomePageTest, HomePage

        def _lazy(page_cls):
            def _loader():
                return page_cls()
            return _loader

        # Define the pages for the application
        pages = {
            "/": _lazy(HomePageTest), # Use the Rosetta Stone version of the homepage
            # "/metadata-details": _lazy(Metadata),
            # "/clustering": _lazy(Clustering),
            # "/clustering-2": _lazy(Clustering2Page),
            # "/quantification": _lazy(Quantification),
            # "/fitting": _lazy(Fitting),
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