"""
Spectrum line visualization composer.
"""
import panel as pn
import holoviews as hv
import numpy as np
import xarray as xr

from holoviews import streams
from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING
from whateels.helpers import HTML_ROOT

if TYPE_CHECKING:
    from ...model import Model

# Initialize HoloViews with Bokeh backend
hv.extension("bokeh", logo=False)

class SpectrumLineVisualizer(AbstractEELSVisualizer):
    """Composes spectrum line visualizations from EELS data"""
    
    # Text and label constants (specific to each plot)
    _IMAGE_X_LABEL = 'Position'
    _IMAGE_Y_LABEL = 'Energy Loss (eV)'
    _IMAGE_TITLE = 'EELS Spectrum Line'
    _SPECTRUM_X_LABEL = 'Energy Loss (eV)'
    _SPECTRUM_Y_LABEL = 'Electron Count'
    _SPECTRUM_TITLE = 'Selected Spectrum'
    _ERR_EMPTY_ELOSS = 'Energy loss coordinates are empty'
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    _DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
    _DATASET_INFO_CLASS = ["dataset-info", "animated"]
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    _DATASET_DETAILS_NAME = "Dataset Details"
    _DATASET_DETAILS_WIDTH = 350
    _DATASET_DETAILS_HEIGHT = 250
    _DATASET_DETAILS_POSITION = "center"
    _DATASET_DETAILS_HEADER = "### More Dataset Details"
    _DATASET_DETAILS_PLACEHOLDER = "(Add more details here as needed)"

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'

    # Visualization configuration constants
    _MAX_PLOT_SIZE = 600
    _FOCUS_RATIO = 0.5
    _SPECTRUM_WIDTH = 600
    _SPECTRUM_HEIGHT = 300
    
    def __init__(self, model: "Model", dataset: "xr.Dataset"):
        self._model = model
        self._dataset = dataset

        self._tap_stream = None
        self._spectrum_pane = None
        
        # For tap/click throttling
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --
    @override
    def create_plots(self):
        """Create layout for spectrum line visualization with tap/click interaction."""
        # Sum over y dimension to create image
        image_data = self._dataset.ElectronCount.squeeze()
        image_data = image_data.fillna(0.0)
        image_data = image_data.where(np.isfinite(image_data), 0.0)
        x_coords = self._dataset.coords[self._model.constants.AXIS_X]
        eloss_coords = self._dataset.coords[self._model.constants.ELOSS]
        x_coords = x_coords.where(np.isfinite(x_coords), 0.0)
        eloss_coords = eloss_coords.where(np.isfinite(eloss_coords), 0.0)
        clean_image_data = image_data.assign_coords({
            self._model.constants.AXIS_X: x_coords,
            self._model.constants.ELOSS: eloss_coords
        })
        image = self._create_image(clean_image_data, x_coords, eloss_coords)
        empty_spectrum = self._create_empty_spectrum(eloss_coords)
        # Setup tap interaction
        self._tap_stream = streams.Tap(x=0, y=0, source=image)
        self._tap_stream.add_subscriber(self._handle_tap_stream)
        image_pane = pn.pane.HoloViews(image, sizing_mode=self._STRETCH_BOTH)
        self._spectrum_pane = pn.pane.HoloViews(empty_spectrum, sizing_mode=self._STRETCH_BOTH)
        self._trigger_refresh(image_pane)
        
        plots = pn.Column(
            image_pane,
            self._spectrum_pane,
            sizing_mode=self._STRETCH_BOTH
        )

        return plots

    @override
    def create_dataset_info(self):
        return super().create_dataset_info()

    # -- Private Methods --

    def _handle_tap_stream(self, x=None, y=None, **kwargs):
        """Handle tap events from HoloViews streams for spectrum line."""
        # Only update if x is valid and changed significantly
        if x is None:
            return
        if self._last_click_x is not None and abs(x - self._last_click_x) < self._click_tolerance:
            return
        self._last_click_x = x
        self._update_spectrum_display(x)

    def _update_spectrum_display(self, x):
        """Update the spectrum pane with the spectrum at the tapped x position."""
        # Get spectrum at tapped x position
        try:
            spectrum = self._dataset.ElectronCount.sel(
                x=x, method='nearest'
            )
            # Ensure the spectrum is 1D by reducing over 'y' if present
            if 'y' in spectrum.dims:
                spectrum = spectrum.mean(dim='y')
        except Exception:
            return
        eloss_coords = self._dataset.coords[self._model.constants.ELOSS]
        spectrum_curve = hv.Curve(
            (eloss_coords, spectrum),
            kdims=[self._model.constants.ELOSS],
            vdims=[self._model.constants.ELECTRON_COUNT]
        ).opts(
            width=self._SPECTRUM_WIDTH,
            height=self._SPECTRUM_HEIGHT,
            color=self._model.colors.RED,
            line_width=2,
            xlabel=self._SPECTRUM_X_LABEL,
            ylabel=self._SPECTRUM_Y_LABEL,
            title=self._SPECTRUM_TITLE
        )
        if self._spectrum_pane is not None:
            self._spectrum_pane.object = spectrum_curve

    def _create_image(self, clean_image_data, x_coords, eloss_coords):
        """Create the spectrum line image"""
        # Calculate dimensions
        data_width = len(x_coords)
        data_height = len(eloss_coords)
        scale_factor = min(self._MAX_PLOT_SIZE / data_width, self._MAX_PLOT_SIZE / data_height)
        plot_width = int(data_width * scale_factor)
        plot_height = int(data_height * scale_factor)

        # Focus on energy range
        eloss_min, eloss_max = float(eloss_coords.min()), float(eloss_coords.max())
        eloss_range = eloss_max - eloss_min
        focused_range = eloss_range * self._FOCUS_RATIO
        eloss_center = (eloss_min + eloss_max) / 2
        focused_ylim = (eloss_center - focused_range/2, eloss_center + focused_range/2)

        return hv.Image(
            clean_image_data,
            kdims=[self._model.constants.AXIS_X, self._model.constants.ELOSS]
        ).opts(
            width=plot_width,
            height=plot_height,
            ylim=focused_ylim,
            cmap=self._model.colors.GREYS_R,
            xlabel=self._IMAGE_X_LABEL,
            ylabel=self._IMAGE_Y_LABEL,
            title=self._IMAGE_TITLE,
            invert_yaxis=True,
            tools=['hover', 'tap'],
            margin=0,
            padding=0,
        )
    
    def _create_empty_spectrum(self, eloss_coords):
        """Create empty spectrum for interaction"""
        empty_data = xr.zeros_like(eloss_coords)
        
        if len(eloss_coords) == 0:
            raise ValueError(self._ERR_EMPTY_ELOSS)
        
        return hv.Curve(
            (eloss_coords, empty_data),
            kdims=[self._model.constants.ELOSS],
            vdims=[self._model.constants.ELECTRON_COUNT]
        ).opts(
            width=self._SPECTRUM_WIDTH,
            height=self._SPECTRUM_HEIGHT,
            color=self._model.colors.BLACK,
            line_width=2,
            xlabel=self._SPECTRUM_X_LABEL,
            ylabel=self._SPECTRUM_Y_LABEL,
            title=self._SPECTRUM_TITLE
        )
    
    def _trigger_refresh(self, image_pane):
        """Programmatically trigger refresh for square display"""
        def trigger_refresh():
            image_pane.param.watchers.clear()
            image_pane._update_pane()
        
        pn.state.add_periodic_callback(trigger_refresh, period=0, count=1)
