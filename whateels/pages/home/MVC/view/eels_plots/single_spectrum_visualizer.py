"""
Single spectrum visualization composer.
"""

import panel as pn
import holoviews as hv
import numpy as np

from typing import override
from .abstract_eels_visualizer import AbstractEELSVisualizer

# Initialize HoloViews with Bokeh backend
hv.extension("bokeh", logo=False)

class SingleSpectrumVisualizer(AbstractEELSVisualizer):
    """Composes single spectrum visualizations from EELS data"""
    
    def __init__(self, model):
        self._model = model
        self._STRETCH_WIDTH = 'stretch_width'
        self._STRETCH_BOTH = 'stretch_both'
    
    def create_layout(self):
        """Create layout for single spectrum visualization"""
        # Create spectrum plot
        spectrum_data = self._model.dataset.ElectronCount.squeeze()
        
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
        attrs = self._model.dataset.attrs if self._model.dataset is not None else {}
        shape = attrs.get('shape', 'N/A')
        beam_energy = attrs.get('beam_energy', 'N/A')
        convergence_angle = attrs.get('convergence_angle', 'N/A')
        collection_angle = attrs.get('collection_angle', 'N/A')

        # Load metadata button HTML
        metadata_html_path = HTML_ROOT / "metadata_info.html"
        with open(metadata_html_path, 'r', encoding='utf-8') as f:
            metadata_button_html = f.read()
        
        metadata_button = pn.pane.HTML(metadata_button_html, margin=0)

        # Main info panel
        header = pn.Row(
            pn.pane.HTML(self._DATASET_INFO_TITLE, sizing_mode=self._STRETCH_WIDTH, margin=0),
            metadata_button,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=self._DATASET_INFO_HEADER_CLASS,
            margin=0
        )

        dataset_info = pn.Column(
            header,
            pn.Spacer(height=5),
            pn.Row(
                pn.Row(
                    pn.pane.HTML("<strong>Shape:</strong>"),
                    sizing_mode=self._STRETCH_WIDTH
                ),
                pn.pane.Str(shape),
                sizing_mode=self._STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML("<strong>Beam Energy:</strong>"),
                    sizing_mode=self._STRETCH_WIDTH
                ),
                pn.pane.Str(f"{beam_energy} keV"),
                sizing_mode=self._STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML("<strong>Convergence Angle:</strong>"),
                    sizing_mode=self._STRETCH_WIDTH
                ),
                pn.pane.Str(f"{convergence_angle} mrad"),
                sizing_mode=self._STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML("<strong>Collection Angle:</strong>"),
                    sizing_mode=self._STRETCH_WIDTH
                ),
                pn.pane.Str(f"{collection_angle} mrad"),
                sizing_mode=self._STRETCH_WIDTH
            ),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=self._DATASET_INFO_CLASS
        )
        return dataset_info
