"""
Spectrum line visualization composer.
"""
import panel as pn
import holoviews as hv
import numpy as np
import xarray as xr

from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import Model

# Initialize HoloViews with Bokeh backend
hv.extension("bokeh", logo=False)

class ImageVisualizer(AbstractEELSVisualizer):
    """Composes image visualizations from EELS data"""

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "Model", dataset: "xr.Dataset"):
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset        
        
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
        x_coords = x_coords.where(np.isfinite(x_coords), 0.0)
        
        y_coords = self._dataset.coords[self._model.constants.AXIS_Y]
        y_coords = y_coords.where(np.isfinite(y_coords), 0.0)

        # For 2D image data, assign coordinates for both axes
        clean_image_data = image_data.assign_coords({
            self._model.constants.AXIS_X: x_coords,
            self._model.constants.AXIS_Y: y_coords
        })
        
        # Create 2D image plot
        image: hv.Image = self._create_2d_image(clean_image_data)
        image_container = pn.pane.HoloViews(image, sizing_mode=self._STRETCH_BOTH)
        
        plots = pn.Column(
            image_container,
            sizing_mode=self._STRETCH_BOTH
        )

        return plots

    @override
    def create_dataset_info(self):
       return super().create_dataset_info()

    # -- Private Methods --

    def _create_2d_image(self, clean_image_data) -> hv.Image:
        """Create a 2D image plot for image data"""
        
        IMAGE_X_LABEL = 'X Position'
        IMAGE_Y_LABEL = 'Y Position'
        IMAGE_TITLE = 'Image Data'
        
        MAX_PLOT_SIZE = 600
        
        # Calculate dimensions from the data itself
        data_height, data_width = clean_image_data.shape
        scale_factor = min(MAX_PLOT_SIZE / data_width, MAX_PLOT_SIZE / data_height)
        plot_width = int(data_width * scale_factor)
        plot_height = int(data_height * scale_factor)

        return hv.Image(
            clean_image_data,
            kdims=[self._model.constants.AXIS_X, self._model.constants.AXIS_Y]
        ).opts(
            width=plot_width,
            height=plot_height,
            cmap=self._model.colors.GREYS_R,
            xlabel=IMAGE_X_LABEL,
            ylabel=IMAGE_Y_LABEL,
            title=IMAGE_TITLE,
            margin=0,
            padding=0,
        )
