"""
Spectrum line visualization composer.
"""
import panel as pn
import numpy as np
import holoviews as hv
import xarray as xr

hv.extension('bokeh')  # type: ignore

from whateels.components import InfoPanel
from whateels.interfaces import IPlot
from typing import override, TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

class SpectrumLinePlot(IPlot):
    """Composes spectrum line visualizations from EELS data."""

    _IMAGE_X_LABEL = 'Position'
    _IMAGE_Y_LABEL = 'Energy Loss (eV)'
    _IMAGE_TITLE = 'EELS Spectrum Line'
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'
    _SPECTRUM_TITLE = 'Selected Spectrum'
    _ERR_EMPTY_ELOSS = 'Energy loss coordinates are empty'
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    _FOCUS_RATIO = 0.5
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):
        self._model = model
        self._dataset = dataset
        self._heatmap_pane = None
        self._spectrum_pane = None
        self._selected_x_value = None
        self._current_x_range = None
        self._current_y_range = None
        self._tap_stream = None
        self._heatmap_element = None  # base image, stored to rebuild overlay with VLine

    @override
    def create_plots(self):
        img_da = self._dataset.ElectronCount.squeeze().fillna(0.0)
        img_da = img_da.where(np.isfinite(img_da), 0.0)

        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS

        x_coords = self._dataset.coords[x_name].where(np.isfinite(self._dataset.coords[x_name]), 0.0)
        e_coords = self._dataset.coords[e_name].where(np.isfinite(self._dataset.coords[e_name]), 0.0)

        data2d = img_da.values
        # Ensure (E, x) order for hv.Image (rows=E, cols=x)
        if img_da.dims[0] == x_name and img_da.dims[1] == e_name:
            z = data2d.T
        elif img_da.dims[0] == e_name and img_da.dims[1] == x_name:
            z = data2d
        else:
            z = data2d.T

        x_vals = x_coords.values
        e_vals = e_coords.values

        # HoloViews Image (heatmap)
        img = hv.Image(
            (x_vals, e_vals, z),
            kdims=[x_name, e_name],
            vdims=['Intensity']
        ).opts(
            cmap='Greys',
            colorbar=True,
            clabel=self._model.constants.ELECTRON_COUNT,
            title=self._IMAGE_TITLE,
            xlabel=self._IMAGE_X_LABEL,
            ylabel=self._IMAGE_Y_LABEL,
            responsive=True,
            tools=['hover'],
            shared_axes=False,
        )
        self._heatmap_element = img

        # Tap stream for click-to-extract-spectrum
        self._tap_stream = hv.streams.Tap(source=img, x=None, y=None)
        self._tap_stream.param.watch(self._on_tap, ['x', 'y'])

        self._heatmap_pane = pn.pane.HoloViews(img, sizing_mode=self._STRETCH_BOTH)

        # Empty spectrum pane
        empty_curve = hv.Curve(
            [],
            kdims=[self._X_AXIS_SPECTRUM_TITLE],
            vdims=[self._Y_AXIS_SPECTRUM_TITLE]
        ).opts(
            title='Click on heatmap to extract spectrum',
            responsive=True,
            shared_axes=False,
        )
        self._spectrum_pane = pn.pane.HoloViews(empty_curve, sizing_mode=self._STRETCH_BOTH)

        return pn.Column(self._heatmap_pane, self._spectrum_pane, sizing_mode=self._STRETCH_BOTH)

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

    # --- Callbacks ---
    def _on_tap(self, event):
        x_clicked = self._tap_stream.x
        if x_clicked is None:
            return

        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS

        try:
            spectrum = self._dataset.ElectronCount.sel({x_name: x_clicked}, method='nearest')
        except Exception:
            return
        if 'y' in spectrum.dims:
            spectrum = spectrum.mean('y')

        energy = self._dataset.coords[e_name].values
        values = spectrum.fillna(0.0).where(np.isfinite(spectrum), 0.0).values
        self._selected_x_value = float(spectrum.coords[x_name]) if x_name in spectrum.coords else float(x_clicked)

        # Update spectrum pane
        curve = hv.Curve(
            (energy, values),
            self._X_AXIS_SPECTRUM_TITLE,
            self._Y_AXIS_SPECTRUM_TITLE
        ).opts(
            color='crimson',
            line_width=2,
            title=f'{self._SPECTRUM_TITLE} x={self._selected_x_value:.2f}',
            responsive=True,
            tools=['hover'],
            shared_axes=False,
        )
        if self._current_x_range is not None:
            curve = curve.opts(xlim=self._current_x_range)
        if self._current_y_range is not None:
            curve = curve.opts(ylim=self._current_y_range)

        if self._spectrum_pane is not None:
            self._spectrum_pane.object = curve

        self._update_heatmap_selection_line()

    # --- Helpers ---
    def _update_heatmap_selection_line(self):
        if self._selected_x_value is None or self._heatmap_pane is None or self._heatmap_element is None:
            return
        vline = hv.VLine(self._selected_x_value).opts(
            color='red',
            line_dash='dashed',
            line_width=2,
        )
        overlay = (self._heatmap_element * vline).opts(
            hv.opts.Overlay(shared_axes=False)
        )
        self._heatmap_pane.object = overlay

    def _apply_current_ranges(self, curve):
        """Apply stored x/y ranges to a HoloViews Curve via opts."""
        opts = {}
        if self._current_x_range is not None:
            opts['xlim'] = self._current_x_range
        if self._current_y_range is not None:
            opts['ylim'] = self._current_y_range
        if opts:
            return curve.opts(**opts)
        return curve
