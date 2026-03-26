
import time
_whe_start_time = time.perf_counter()
import panel as pn
import holoviews as hv
from pathlib import Path
from whateels.helpers import KillProcess, ASSETS_ROOT

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

        # Cache imported class references so __import__ only hits the module
        # loader on the first visit; subsequent sessions reuse the cached class.
        _cls_cache: dict = {}

        def _lazy(module: str, cls: str):
            def _loader():
                if cls not in _cls_cache:
                    _cls_cache[cls] = getattr(__import__(module, fromlist=[cls]), cls)
                return _cls_cache[cls]()
            return _loader

        # Define the pages for the application
        pages = {
            # "": _lazy('whateels.pages.demo', 'DemoPage'),
            "/": _lazy('whateels.pages.home', 'HomePage'),
            "/metadata-details": _lazy('whateels.pages.metadata', 'Metadata'),
            "/clustering": _lazy('whateels.pages.clustering', 'Clustering'),
            "/clustering-2": _lazy('whateels.pages.clustering_2', 'Clustering2Page'),
            "/multifit-details": _lazy('whateels.pages.multifitting', 'MultiFitting'),
            "/quantification": _lazy('whateels.pages.quantification', 'Quantification'),
            "/fitting": _lazy('whateels.pages.fitting', 'Fitting'),
        }

        return pn.serve(
            pages, # type: ignore
            title=self._title, 
            port=port,
            show=show,
            allow_websocket_origin=["*"],
            static_dirs={"assets": str(ASSETS_ROOT)},
        )