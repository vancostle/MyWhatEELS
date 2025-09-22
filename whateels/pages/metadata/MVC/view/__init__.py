import panel as pn
from typing import TYPE_CHECKING
from whateels.helpers import HTML_ROOT
import minify_html

if TYPE_CHECKING:
    from ..model import Model

class View:
    """
    View class for the metadata page of the WhatEELS application.
    Handles the UI components and layout for displaying metadata information.
    """
    
    # --- Class-level constants ---
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    
    def __init__(self, model: "Model") -> None:
        self._model = model
        self._main_container_layout = None
        
        self._init_components()
    
    # --- UI Component Creation Methods ---
    
    def create_json_component(self, data):
        """Creates interactive JSON pane."""
        return pn.pane.JSON(
            data,
            depth=1,
            hover_preview=True,
            sizing_mode=self._STRETCH_BOTH
        )
    
    def create_no_metadata_component(self):
        """Creates no metadata available component."""
        UTF8 = 'utf-8'
        READ_MODE = 'r'
        
        NO_METADATA_PATH = HTML_ROOT / "no_metadata_loaded.html"

        with open(NO_METADATA_PATH, READ_MODE, encoding=UTF8) as f:
            no_metadata_template = f.read()
        minified_html = minify_html.minify(no_metadata_template)
        return pn.pane.HTML(minified_html, sizing_mode=self._STRETCH_BOTH)

    def create_error_component(self):
        """Creates error display component."""
        UTF8 = 'utf-8'
        READ_MODE = 'r'
        
        JSON_ERROR_PATH = HTML_ROOT / "json_error.html"
        with open(JSON_ERROR_PATH, READ_MODE, encoding=UTF8) as f:
            error_template = f.read()
        minified_html = minify_html.minify(error_template.encode(UTF8)).decode(UTF8)
        return pn.pane.HTML(minified_html, sizing_mode=self._STRETCH_BOTH)

    # --- Properties ---
    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying metadata."""
        return self._main_container_layout
        
    # --- Private/Internal Setup Methods ---
    
    def _init_components(self):
        """Initialize main and sidebar layout containers."""
        self._main_container_layout = self._main_layout()

    def _main_layout(self):
        """Create and return the main layout."""
        # Create a placeholder that will be populated by the controller
        self._main_container_layout = pn.Column(
            pn.pane.HTML("<p>Loading...</p>"),
            sizing_mode=self._STRETCH_BOTH
        )
        return self._main_container_layout
    
    def get_main_container(self):
        """Provide access to the main container for controller to populate."""
        return self._main_container_layout