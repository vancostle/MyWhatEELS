"""
Single spectrum visualization composer.
"""
import panel as pn
import numpy as np
import holoviews as hv

from typing import override, TYPE_CHECKING
from whateels.interfaces import IPlot
from .dataset_info import create_home_dataset_info

if TYPE_CHECKING:
    from ...model import HomePageModel
    from xarray import Dataset

class SingleSpectrumPlot(IPlot):
    """Composes single spectrum visualizations from EELS data."""
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "HomePageModel", dataset: "Dataset"):
        self._model = model
        self._dataset = dataset

    @override
    def create_plots(self) -> pn.viewable.Viewable:
        """Create layout for single spectrum visualization"""
        # Create spectrum plot
        spectrum_data = self._dataset.ElectronCount.squeeze()

        # Clean spectrum data for any remaining NaN/inf values
        spectrum_data = spectrum_data.fillna(0.0)
        spectrum_data = spectrum_data.where(np.isfinite(spectrum_data), 0.0)
        
        energy = self._dataset.coords[self._model.constants.ELOSS].values
        spectrum = spectrum_data.values

        curve = hv.Curve(
            (energy, spectrum),
            kdims=['Energy Loss (eV)'],
            vdims=['Intensity (a.u.)'],
            label='Spectrum'
        ).opts(
            color='black',
            line_width=2,
            title='EELS Spectrum',
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            shared_axes=False,
        )

        spectrum_pane = pn.pane.HoloViews(curve, sizing_mode=self._STRETCH_BOTH, margin=0)
        
        return pn.Column(
            spectrum_pane,
            sizing_mode=self._STRETCH_BOTH
        )
        
    @override
    def create_dataset_info(self):
        return create_home_dataset_info(
            self._model,
            self._dataset,
            sizing_mode=self._STRETCH_WIDTH,
        )
