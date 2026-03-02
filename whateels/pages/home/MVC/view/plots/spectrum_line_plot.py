"""
Spectrum line visualization composer (HoloViews version).
"""
import panel as pn
import numpy as np
import holoviews as hv
from holoviews import streams as hv_streams
import xarray as xr

from whateels.components import InfoPanel
from whateels.interfaces import IPlot
from typing import override, TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

class SpectrumLinePlot(IPlot):
    """Composes spectrum line visualizations from EELS data (HoloViews)."""

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
        # Ranges for spectrum (it keeps zoom)
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None
        self._heatmap_stream = None
        self._spectrum_range_stream = None
        self._heatmap_overlay = None
        self._spectrum_curve = None

    @override
    def create_plots(self):
        # --- Base data ---
        img_da = self._dataset.ElectronCount.squeeze().fillna(0.0)
        img_da = img_da.where(np.isfinite(img_da), 0.0)

        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS

        x_coords = self._dataset.coords[x_name].where(np.isfinite(self._dataset.coords[x_name]), 0.0)
        e_coords = self._dataset.coords[e_name].where(np.isfinite(self._dataset.coords[e_name]), 0.0)

        data2d = img_da.values  # shape (x, E) or (E, x); assume dims in order (x, E)
        # Ensure expected order: y (energy) first for HoloViews Image
        if img_da.dims[0] == x_name and img_da.dims[1] == e_name:
            z = data2d.T  # transpose to (E, x)
        elif img_da.dims[0] == e_name and img_da.dims[1] == x_name:
            z = data2d  # already (E, x)
        else:
            z = data2d.T

        # --- Rango focal de energía (como antes) ---
        e_min = float(e_coords.min())
        e_max = float(e_coords.max())
        e_range = e_max - e_min if e_max > e_min else 1.0
        focused = e_range * self._FOCUS_RATIO
        e_center = 0.5 * (e_min + e_max)
        focus_low = e_center - focused / 2
        focus_high = e_center + focused / 2

        # --- HoloViews Image (heatmap) ---
        img = hv.Image(
            (x_coords.values, e_coords.values, z),
            kdims=[x_name, e_name],
            vdims=[self._model.constants.ELECTRON_COUNT]
        ).opts(
            cmap='Greys_r',
            colorbar=True,
            title=self._IMAGE_TITLE,
            xlabel=self._IMAGE_X_LABEL,
            ylabel=self._IMAGE_Y_LABEL,
            invert_yaxis=True,
            responsive=True,
            framewise=True,
            aspect='auto',
            tools=['hover'],
        )

        # --- Selection line (vertical) ---
        self._selected_x_value = x_coords.values[0] if len(x_coords) > 0 else None
        selection_line = self._make_selection_line(self._selected_x_value, e_coords)
        self._heatmap_overlay = img * selection_line # type: ignore

        # --- Spectrum curve ---
        self._spectrum_curve = self._make_spectrum_curve(self._selected_x_value)

        # --- Streams ---
        self._heatmap_stream = hv_streams.Tap(source=img, x=self._selected_x_value, y=None)
        self._heatmap_stream.add_subscriber(self._on_heatmap_tap)

        self._spectrum_range_stream = hv_streams.RangeXY(source=self._spectrum_curve)
        self._spectrum_range_stream.add_subscriber(self._on_spectrum_range_changed)

        # --- Panes ---
        self._heatmap_pane = pn.pane.HoloViews(
            self._heatmap_overlay,
            sizing_mode=self._STRETCH_BOTH,
            margin=0
        )
        self._spectrum_pane = pn.pane.HoloViews(
            self._spectrum_curve,
            sizing_mode=self._STRETCH_BOTH,
            margin=0
        )

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

    # --- HoloViews event handlers ---
    def _on_heatmap_tap(self, x=None, y=None):
        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS
        if x is None:
            return
        # Select nearest x slice and extract spectrum
        try:
            spectrum = self._dataset.ElectronCount.sel({x_name: x}, method="nearest")
        except Exception:
            return
        if 'y' in spectrum.dims:
            spectrum = spectrum.mean('y')

        energy = self._dataset.coords[e_name].values
        values = spectrum.fillna(0.0).where(np.isfinite(spectrum), 0.0).values
        self._selected_x_value = float(spectrum.coords[x_name]) if x_name in spectrum.coords else float(x)

        # Update spectrum curve
        self._spectrum_curve = self._make_spectrum_curve(self._selected_x_value)
        self._spectrum_pane.object = self._spectrum_curve # type: ignore

        # Update selection line on heatmap
        selection_line = self._make_selection_line(self._selected_x_value, self._dataset.coords[e_name])
        self._heatmap_overlay = self._heatmap_overlay[0] * selection_line # type: ignore
        self._heatmap_pane.object = self._heatmap_overlay # type: ignore

    def _on_spectrum_range_changed(self, x_range=None, y_range=None):
        # Store zoom/pan ranges for spectrum plot
        if x_range is not None:
            self._current_x_range = x_range
            self._current_x_autorange = False
        if y_range is not None:
            self._current_y_range = y_range
            self._current_y_autorange = False

    # --- Helpers ---
    def _make_spectrum_curve(self, x_value):
        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS
        if x_value is None:
            # Empty spectrum
            return hv.Curve([], kdims=[e_name], vdims=[self._Y_AXIS_SPECTRUM_TITLE]).opts(
                title="Click on heatmap to extract spectrum",
                xlabel=self._X_AXIS_SPECTRUM_TITLE,
                ylabel=self._Y_AXIS_SPECTRUM_TITLE,
                responsive=True,
                framewise=True,
            )
        try:
            spectrum = self._dataset.ElectronCount.sel({x_name: x_value}, method="nearest")
        except Exception:
            return hv.Curve([], kdims=[e_name], vdims=[self._Y_AXIS_SPECTRUM_TITLE]).opts(
                title="Click on heatmap to extract spectrum",
                xlabel=self._X_AXIS_SPECTRUM_TITLE,
                ylabel=self._Y_AXIS_SPECTRUM_TITLE,
                responsive=True,
                framewise=True,
            )
        if 'y' in spectrum.dims:
            spectrum = spectrum.mean('y')
        energy = self._dataset.coords[e_name].values
        values = spectrum.fillna(0.0).where(np.isfinite(spectrum), 0.0).values
        curve = hv.Curve(
            (energy, values),
            kdims=[self._X_AXIS_SPECTRUM_TITLE],
            vdims=[self._Y_AXIS_SPECTRUM_TITLE]
        ).opts(
            color='crimson',
            line_width=2,
            title=self._SPECTRUM_TITLE,
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            framewise=True,
        )
        # Apply stored zoom/pan ranges
        opts = {}
        if self._current_x_range is not None:
            opts['xlim'] = self._current_x_range
        if self._current_y_range is not None:
            opts['ylim'] = self._current_y_range
        if opts:
            curve = curve.opts(**opts) # type: ignore
        return curve

    def _make_selection_line(self, x_value, e_coords):
        if x_value is None or e_coords is None or len(e_coords) == 0:
            return hv.Curve([])
        y_min = float(np.min(e_coords.values))
        y_max = float(np.max(e_coords.values))
        line = hv.Curve(
            ([x_value, x_value], [y_min, y_max]),
            kdims=[self._IMAGE_X_LABEL],
            vdims=[self._IMAGE_Y_LABEL]
        ).opts(
            color='red',
            line_dash='dashed',
            line_width=2,
            alpha=1.0,
            responsive=True,
        )
        return line
