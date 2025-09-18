"""
Single spectrum visualization composer.
"""

import panel as pn
import holoviews as hv
import numpy as np

from typing import override
from .abstract_eels_visualizer import AbstractEELSVisualizer
from whateels.helpers import HTML_ROOT
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import Model
    from xarray import Dataset

# Initialize HoloViews with Bokeh backend
hv.extension("bokeh", logo=False)

class SingleSpectrumVisualizer(AbstractEELSVisualizer):
    """Composes single spectrum visualizations from EELS data"""
    
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _NOT_AVAILABLE = 'N/A'

    def __init__(self, model: "Model", dataset: "Dataset"):
        self._model = model
        self._dataset = dataset
    
    @override
    def create_plots(self):
        """Create layout for single spectrum visualization"""
        # Create spectrum plot
        spectrum_data = self._dataset.ElectronCount.squeeze()

        # Clean spectrum data for any remaining NaN/inf values
        spectrum_data = spectrum_data.fillna(0.0)
        spectrum_data = spectrum_data.where(np.isfinite(spectrum_data), 0.0)
        
        spectrum = hv.Curve(
            spectrum_data,
            kdims=[self._model.Constants.ELOSS],
            vdims=[self._model.Constants.ELECTRON_COUNT]
        ).opts(
            width=800,
            height=400,
            color=self._model.Colors.BLACK,
            line_width=2,
            xlabel='Energy Loss (eV)',
            ylabel='Electron Count',
            title='EELS Spectrum'
        )
        
        # Convert to Panel
        spectrum_pane = pn.pane.HoloViews(spectrum, sizing_mode=self._STRETCH_WIDTH)
        
        return pn.Column(
            spectrum_pane,
            sizing_mode=self._STRETCH_BOTH
        )
        
    @override
    def create_dataset_info(self):
        super().create_dataset_info()
