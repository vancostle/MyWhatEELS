"""
Image visualization composer.
"""
import panel as pn
import holoviews as hv
import numpy as np
import xarray as xr

from whateels.components import InfoPanel
from whateels.interfaces import IPlot
from typing import TYPE_CHECKING, override
if TYPE_CHECKING:
    from ...model import HomePageModel

class ImagePlot(IPlot):
    """Composes image visualizations from EELS data"""

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):

        self._model = model
        self._dataset = dataset        
        
        # For tap/click throttling
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --
    @override
    def create_plots(self):
        """Create layout for image visualization with HoloViews/Bokeh."""

        # Prepare cleaned image data and coordinates
        image_data = self._dataset.ElectronCount.squeeze()
        image_data = image_data.fillna(0.0)
        image_data = image_data.where(np.isfinite(image_data), 0.0)

        ny, nx = image_data.shape
        m_image = np.asarray(image_data)

        # hv.Image expects (x_coords, y_coords, 2D-array) with shape (ny, nx)
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'],
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

        image_panel = pn.pane.HoloViews(img, sizing_mode='stretch_height', margin=0, styles={'margin': 'auto'})
        plots = pn.Column(
            image_panel,
            sizing_mode=self._STRETCH_BOTH,
            align='center',
            styles={'width': '100%'}
        )
        return plots

    @override
    def create_dataset_info(self):
        NOT_AVAILABLE = 'N/A'
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        ANGLE_UNIT = "mrad"
        ENERGY_UNIT = "keV"

        dataset = self._dataset
        
        attrs = dataset.attrs if dataset is not None else {}

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)
        
        beam_energy = f"{beam_energy} {ENERGY_UNIT}" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle = f"{convergence_angle} {ANGLE_UNIT}" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle = f"{collection_angle} {ANGLE_UNIT}" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE
        
        dataset_information = InfoPanel(
            title="Dataset Information", 
            information={
                "Shape": shape,
                "Beam Energy": beam_energy,
                "Convergence Angle": convergence_angle,
                "Collection Angle": collection_angle,
            },
            sizing_mode=self._STRETCH_WIDTH
        )
        
        return dataset_information


