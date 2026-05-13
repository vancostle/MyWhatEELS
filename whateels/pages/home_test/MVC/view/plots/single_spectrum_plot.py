"""
Single spectrum visualization composer.
"""
import panel as pn
import numpy as np
import holoviews as hv

from typing import override, TYPE_CHECKING
from whateels.interfaces import IPlot
from whateels.components import InfoPanel

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
        NOT_AVAILABLE = 'N/A'
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        ANGLE_UNIT = "mrad"
        ENERGY_UNIT = "keV"
        
        app_state = self._model.app_state
        all_datasets = app_state.all_datasets
        if not isinstance(all_datasets, list):
            raise ValueError("all_datasets should be a list of Dataset objects.")
        
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
