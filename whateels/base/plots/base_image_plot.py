"""
Base image visualizer component for 2D EELS image data.

This is a shared component that can be used across different pages.
It provides basic 2D image rendering with HoloViews.

No model dependency - only requires dataset and optional axis names.
"""
import panel as pn
import holoviews as hv
import numpy as np
import xarray as xr

from whateels.components import InfoPanel
from whateels.interfaces import IPlot
from typing import Optional, override

class BaseImagePlot(IPlot):
    """
    Base component for composing 2D image visualizations from EELS data.
    
    This visualizer renders a simple 2D heatmap using HoloViews, with:
    - Automatic data cleaning (NaN/inf handling)
    - Locked aspect ratio (1:1 pixel)
    - Responsive layout
    - Interactive hover with pixel coordinates and intensity
    
    Can be extended by page-specific visualizers for additional features.
    No model dependency - works with any page.
    """

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    # Default axis names
    _DEFAULT_AXIS_X = 'x'
    _DEFAULT_AXIS_Y = 'y'
    
    def __init__(
        self, 
        dataset: "xr.Dataset",
        axis_x: Optional[str] = None,
        axis_y: Optional[str] = None
    ):
        """
        Initialize the image visualizer.
        
        Args:
            dataset: xarray Dataset containing ElectronCount data
            axis_x: Name of x-axis coordinate (default: 'x')
            axis_y: Name of y-axis coordinate (default: 'y')
        """
        super().__init__()
        self._dataset = dataset
        self._axis_x = axis_x or self._DEFAULT_AXIS_X
        self._axis_y = axis_y or self._DEFAULT_AXIS_Y
        
        # For tap/click throttling (if subclasses need it)
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --
    
    @override
    def create_dataset_info(self) -> "InfoPanel":
        """
        Returns a panel with dataset information (shape, beam energy, angles).
        Shared implementation for all spectrum image plot subclasses.
        """
        NOT_AVAILABLE = 'N/A'
        attrs = self._dataset.attrs if self._dataset is not None else {}

        shape = attrs.get('shape', NOT_AVAILABLE)
        beam_energy = attrs.get('beam_energy', NOT_AVAILABLE)
        convergence_angle = attrs.get('convergence_angle', NOT_AVAILABLE)
        collection_angle = attrs.get('collection_angle', NOT_AVAILABLE)

        beam_energy_fmt = f"{beam_energy} keV" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle_fmt = f"{convergence_angle} mrad" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle_fmt = f"{collection_angle} mrad" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE

        return InfoPanel(
            title="Dataset Information",
            information={
                "Shape": shape,
                "Beam Energy": beam_energy_fmt,
                "Convergence Angle": convergence_angle_fmt,
                "Collection Angle": collection_angle_fmt,
            },
            sizing_mode='stretch_width',
            margin=0,
        )


    def create_plots(self):
        """
        Create layout for 2D image visualization with HoloViews.
        
        Returns:
            pn.Column: Panel column containing the image plot
        """
        image_data = self._dataset.ElectronCount.squeeze()
        image_data = image_data.fillna(0.0)
        image_data = image_data.where(np.isfinite(image_data), 0.0)

        image_plot = self._create_2d_image(image_data)
        image_panel = pn.pane.HoloViews(
            image_plot,
            sizing_mode='stretch_height',
            margin=0,
            styles={'margin': 'auto'}
        )
        plots = pn.Column(
            image_panel,
            sizing_mode=self._STRETCH_BOTH,
            align='center',
            styles={'width': '100%'}
        )
        return plots

    # -- Protected Helper Methods --

    def _create_2d_image(self, clean_image_data):
        """
        Create a 2D image plot for image data using HoloViews.

        Args:
            clean_image_data: 2D numpy array or xarray DataArray with image data
            
        Returns:
            A HoloViews image-like object with preserved aspect ratio
        """
        m_image = np.asarray(clean_image_data)
        ny, nx = m_image.shape

        return hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=[self._axis_x, self._axis_y],
            vdims=['Intensity']
        ).opts(
            cmap='Greys_r',
            colorbar=False,
            xaxis=None,
            yaxis=None,
            invert_yaxis=True,
            responsive=True,
            aspect='equal',
            shared_axes=False,
        )
