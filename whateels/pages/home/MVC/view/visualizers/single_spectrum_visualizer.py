"""
Single spectrum visualization composer (Plotly version).
"""
import panel as pn
import numpy as np
import plotly.graph_objs as go

from typing import override, TYPE_CHECKING
from .abstract_eels_visualizer import AbstractEELSVisualizer

if TYPE_CHECKING:
    from ...model import Model
    from xarray import Dataset

class SingleSpectrumVisualizer(AbstractEELSVisualizer):
    """Composes single spectrum visualizations from EELS data (Plotly)."""
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "Model", dataset: "Dataset"):
        super().__init__(model, dataset)
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
        
        energy = self._dataset.coords[self._model.constants.ELOSS].values
        spectrum = spectrum_data.values

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=energy,
            y=spectrum,
            mode="lines",
            line=dict(color="black", width=2),
            name="Spectrum"
        ))
        fig.update_layout(
            title="EELS Spectrum",
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE,
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        # Convert to Panel
        spectrum_pane = pn.pane.Plotly(fig.to_plotly_json(), sizing_mode=self._STRETCH_BOTH, config={"responsive": True})
        
        return pn.Column(
            spectrum_pane,
            sizing_mode=self._STRETCH_BOTH
        )
        
    @override
    def create_dataset_info(self):
        return super().create_dataset_info()
    @override
    def create_dataset_info(self):
        super().create_dataset_info()
