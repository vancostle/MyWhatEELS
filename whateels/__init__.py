import panel as pn
import holoviews as hv

# Configure Panel and HoloViews once globally — calling these inside page
# views or methods wastes time on every invocation.
# TODO raw_css must be deleted once all plotly plots have been updated by holoviews
pn.extension(
    'filedropper', 'floatpanel',
    notifications=True,
    theme='default',
    raw_css=[
        ".plotly .modebar, .plotly .modebar-container, .plotly .modebar-group, .plotly .modebar-btn, .plotly .modebar-btn--hover { background: transparent !important; box-shadow: none !important; border: none !important; }",
        ".plotly .modebar-btn { background: transparent !important; }",
        ".plotly .modebar-btn svg, .plotly .modebar-btn path { fill: currentColor !important; stroke: currentColor !important; }",
    ]
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

        #
        # Each route uses a function (not a direct import or lambda) to enable lazy loading of page modules.
        # This avoids importing all heavy dependencies at startup, improving cold start time.
        # Using named functions (not lambdas) is more type-checker friendly and clearer in stack traces.
        # Panel will call each function only when the route is accessed.
        #
        def home_page():
            return __import__('whateels.pages.home', fromlist=['HomePage']).HomePage()

        def metadata_page():
            return __import__('whateels.pages.metadata', fromlist=['Metadata']).Metadata()

        def clustering_page():
            return __import__('whateels.pages.clustering', fromlist=['Clustering']).Clustering()

        def clustering2_page():
            return __import__('whateels.pages.clustering_2', fromlist=['Clustering2Page']).Clustering2Page()

        def multifit_page():
            return __import__('whateels.pages.multifitting', fromlist=['MultiFitting']).MultiFitting()

        def quantification_page():
            return __import__('whateels.pages.quantification', fromlist=['Quantification']).Quantification()

        pages = {
            "/": home_page,
            "/metadata-details": metadata_page,
            "/clustering": clustering_page,
            "/clustering-2": clustering2_page,
            "/multifit-details": multifit_page,
            "/quantification": quantification_page,
            # "/nlls": nlls_page,  # Add if needed
        }

        return pn.serve(
            pages, # type: ignore
            title=self._title,
            port=port,
            show=show,
            allow_websocket_origin=["*"],
        )