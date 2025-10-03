import panel as pn
from typing import TYPE_CHECKING
from whateels.helpers import HTML_ROOT

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
    
    def create_plot_component(self, data):
        """Creates interactive plot pane.

        If `data` looks like an xarray Dataset (duck-typed via `coords`),
        return a small HTML pane indicating a dataset is available so other
        pages (e.g. multifitting) can detect it.
        """
        # Duck-typing: xarray Datasets usually have a `coords` attribute.
        try:
            if hasattr(data, 'coords'):
                return self.create_dataset_component(data)
        except Exception:
            pass

        return pn.pane.Plot(
            data,
            depth=1,
            hover_preview=True,
            sizing_mode=self._STRETCH_BOTH
        )

    def create_dataset_component(self, dataset):
        """Return a small HTML pane announcing the presence of a dataset.

        This avoids attempting to render the entire xarray Dataset as a Plot
        and gives a clear indicator that a dataset is available for
        multifitting or other downstream pages.
        """
        try:
            name = type(dataset).__name__
            print(f"Dataset type detected: {name}")
        except Exception:
            name = 'Dataset'
        return pn.pane.HTML(f"<p>Dataset available: {name}</p>", sizing_mode=self._STRETCH_BOTH)

    # def create_no_multifit_component(self):
    #     """Fallback component when no multifit is available."""
    #     return pn.pane.HTML("<p>No multifit data available.</p>", sizing_mode=self._STRETCH_BOTH)

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