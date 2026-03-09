import panel as pn
import holoviews as hv

# Configure Panel and HoloViews once globally — calling these inside page
# views or methods wastes time on every invocation.
pn.extension(
    'filedropper', 'floatpanel',
    notifications=True,
    theme='default',
)

# Initialize Holoviews with Bokeh backend
hv.extension('bokeh') # type: ignore

from whateels.helpers import LoadCSS, CSS_ROOT, KillProcess

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
            "/": _lazy('whateels.pages.home', 'HomePage'),
            "/metadata-details": _lazy('whateels.pages.metadata', 'Metadata'),
            "/clustering": _lazy('whateels.pages.clustering', 'Clustering'),
            "/clustering-2": _lazy('whateels.pages.clustering_2', 'Clustering2Page'),
            "/multifit-details": _lazy('whateels.pages.multifitting', 'MultiFitting'),
            "/quantification": _lazy('whateels.pages.quantification', 'Quantification'),
            # "/nlls": _lazy('whateels.pages.nlls', 'NLLS'),
        }

        return pn.serve(
            pages, # type: ignore
            title=self._title,
            port=port,
            show=show,
            allow_websocket_origin=["*"],
        )