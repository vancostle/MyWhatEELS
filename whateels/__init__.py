import panel as pn
import psutil
import os
import signal

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

    def _kill_process_on_port(self, port: int) -> bool:
        """
        Kill any process using the specified port.
        Args:
            port: The port number to check and free up
        Returns:
            True if a process was killed, False otherwise
        """
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                connections = proc.net_connections(kind='inet')
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"Killing process {proc.pid} ({proc.name()}) using port {port}")
                        if os.name == 'nt':  # Windows
                            proc.kill()
                        else:  # Unix/Linux/Mac
                            os.kill(proc.pid, signal.SIGTERM)
                        killed = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return killed

    def run(self, port : int = _DEFAULT_PORT, show : bool = True):
        # Kill any process using the port
        self._kill_process_on_port(port)
        
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