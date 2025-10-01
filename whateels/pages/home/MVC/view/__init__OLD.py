import panel as pn, holoviews as hv

from whateels.components import FileDropper
from typing import TYPE_CHECKING
from whateels.helpers import LoadCSS, CSS_ROOT

if TYPE_CHECKING:
    from ..model import Model

# Initialize HoloViews with Bokeh backend
hv.extension("bokeh", logo=False)

class HomePageView:
    """
    View class for the home page of the WhatEELS application.

    Responsibilities:
    - Render and manage the UI layout and state transitions (placeholders, loading, error, plots)
    - Instantiate and expose UI components (sidebar, file dropper, main area)
    - Coordinate with EELS plot factories for visualization
    - Expose properties for Controller to interact with UI elements

    The HomePageView does not make business logic decisions; it only renders what the Controller instructs.
    """

    # --- Class-level constants ---
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'

    # --- Initialization ---
    def __init__(self, model: "Model"):
        self._model = model
        self._main_container_layout = None
        self._sidebar_container_layout = None
        self._dataset_info_layout = None
        self._loading_placeholder = None
        self._no_file_placeholder = None
        self._error_placeholder = None
        self._file_dropper = None
        
        HOMEPAGE_CSS = str(CSS_ROOT / "home.css")
        DATASET_INFO_CSS = str(CSS_ROOT / "dataset_info.css")

        LoadCSS([HOMEPAGE_CSS, DATASET_INFO_CSS]) # CSS for the whole homepage and dataset info panels

         # Initialize visualization components and layouts
        self._init_visualization_components()

    # --- Properties ---

    @property
    def sidebar(self) -> pn.viewable.Viewable:
        """Sidebar layout containing the file dropper and additional controls."""
        return self._sidebar_container_layout
    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main_container_layout
    @property
    def loading_placeholder(self) -> pn.pane.HTML:
        """HTML placeholder shown while a file is being processed."""
        return self._loading_placeholder
    @property
    def no_file_placeholder(self) -> pn.pane.HTML:
        """HTML placeholder shown when no file is loaded."""
        return self._no_file_placeholder
    @property
    def error_placeholder(self) -> pn.pane.HTML:
        """HTML placeholder shown when an error occurs."""
        return self._error_placeholder
    @property
    def file_dropper(self) -> FileDropper:
        """FileDropper widget for file upload interactions."""
        return self._file_dropper
    @property
    def dataset_info(self) -> pn.viewable.Viewable:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout

    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable or None)."""
        if component is not None and not isinstance(component, pn.viewable.Viewable):
            raise ValueError("Component must be a Panel Viewable")
        self._dataset_info_layout = component

    # --- Private/Internal Setup Methods ---

    def _init_visualization_components(self):
        """
        Initialize main visualization container and placeholders.

        Sets up:
        - no_file_placeholder: shown when no file is loaded
        - loading_placeholder: shown during file processing
        - error_placeholder: shown when an error occurs
        - sidebar and main layout containers
        """
        self._no_file_placeholder = pn.pane.HTML(
            self._model.placeholders.NO_FILE_LOADED,
            sizing_mode=self._STRETCH_BOTH
        )
        self._loading_placeholder = pn.Column(
            pn.pane.HTML(
                self._model.placeholders.LOADING_FILE,
                sizing_mode=self._STRETCH_BOTH
            ),
            sizing_mode=self._STRETCH_BOTH,
        )
        self._error_placeholder = pn.pane.HTML(
            self._model.placeholders.ERROR_FILE,
            sizing_mode=self._STRETCH_BOTH
        )
        self._sidebar_container_layout = self._sidebar_layout()
        self._main_container_layout = self._main_layout()

    def _sidebar_layout(self):
        file_dropper = FileDropper(
            valid_extensions=self._model.file_dropper.VALID_EXTENSIONS,
            reject_message=self._model.file_dropper.REJECT_MESSAGE,
            success_message=self._model.file_dropper.SUCCESS_MESSAGE,
            feedback_message=self._model.file_dropper.FEEDBACK_MESSAGE,
        )        
        self._file_dropper = file_dropper
        self._sidebar_container_layout = pn.Column(
            self._file_dropper,
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return self._sidebar_container_layout

    def _main_layout(self):
        self._main_container_layout = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
        return self._main_container_layout