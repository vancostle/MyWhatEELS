
import sys
import time
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
        _t0 = time.perf_counter()
        KillProcess.by_port(port)
        _t_kill = time.perf_counter()

        # Imports are static so PyInstaller can trace them, but placed here
        # (inside run()) so they execute AFTER the splash screen is already
        # visible. Heavy deps (numpy, scipy) are only pulled in at this point.
        
        # Static imports inside each closure — PyInstaller traces them at build
        # time, but they only execute when a user first navigates to that route.
        def _home():
            from whateels.pages.home import HomePage
            return HomePage()
        
        def _home_test():
            from whateels.pages.home_test import HomePageTest
            return HomePageTest()

        def _metadata():
            from whateels.pages.metadata import Metadata
            return Metadata()

        def _clustering():
            from whateels.pages.clustering import Clustering
            return Clustering()

        def _clustering_2():
            from whateels.pages.clustering_2 import Clustering2Page
            return Clustering2Page()

        def _quantification():
            from whateels.pages.quantification import Quantification
            return Quantification()

        def _fitting():
            from whateels.pages.fitting import Fitting
            return Fitting()

        pages = {
            # "/":                 _home_test,
            "/":                 _home,
            "/metadata-details": _metadata,
            "/clustering":       _clustering,
            "/clustering-2":     _clustering_2,
            "/quantification":   _quantification,
            "/fitting":          _fitting,
        }

        _t_end = time.perf_counter()
        print(
            f"\n[App.run()] Server startup breakdown:"
            f"\n  Kill port:    {(_t_kill - _t0)   * 1000:.1f} ms"
            f"\n  Pages setup:  {(_t_end  - _t_kill)* 1000:.1f} ms"
            f"\n  TOTAL:        {(_t_end  - _t0)    * 1000:.1f} ms"
            f"\n  → pn.serve() starting on port {port}...\n"
        )

        return pn.serve(
            pages, # type: ignore
            title=self._title, 
            port=port,
            show=show,
            allow_websocket_origin=["*"],
            static_dirs={"assets": str(ASSETS_ROOT)},
            on_session_destroyed=lambda _ : sys.exit(0) # Ensure full process termination on session close,
        )