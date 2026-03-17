"""Spectrum-image (datacube) visualizer for the fitting page.

HoloViews + Panel implementation that replaces the previous Plotly-based version.
Extends BaseSpectrumImagePlot with fitting-specific features: inactivity timer,
fit-curve overlay, energy map display, and multifit ROI extraction.
"""

import panel as pn
import numpy as np
import time
import xarray as xr
import holoviews as hv
from holoviews import streams as hv_streams
from matplotlib.colors import LinearSegmentedColormap

from whateels.base.plots import BaseSpectrumImagePlot
from typing import override, TYPE_CHECKING
from whateels.helpers import SpectrumExtractor
from whateels.components import SplitJs
from whateels.state import CacheManager

if TYPE_CHECKING:
    from ...model import FittingModel
    from xarray import Dataset


class SpectrumImageVisualizer(BaseSpectrumImagePlot):
    """
    HoloViews/Panel implementation of the Spectrum Image visualizer for the fitting page.

    Extends BaseSpectrumImagePlot with:
    - Inactivity timer: hover temporarily shows pixel spectrum, then reverts to ROI.
    - Fit-curve overlay: magenta filled area drawn on top of the ROI spectrum.
    - Energy map display: replaces paneA image with a green-to-pink heatmap.
    - Multifit ROI extraction: reads from app_state.multifit when is_multifit is set.
    """

    # Axis titles for spectrum plot
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "FittingModel", dataset: "Dataset"):
        """Initialize visual state, interactive panes, and callback wiring."""
        self._model = model

        # Inactivity timer state — must be set before super().__init__ triggers _setup_plots
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._pc = None

        # Hover/selection debounce (same pattern as quantification page)
        self._pending_selection_index = None
        self._pending_selection_ts = None
        self._SELECTION_DEBOUNCE_MS = 200
        self._hover_blocked = False
        self._double_tap_stream = None

        # Fitting/UI state
        self.element_quant_data = []
        self.selected_slice = None
        self.range_slider = None
        self.fitting_button = None

        # BaseSpectrumImagePlot.__init__ expects (dataset, eloss_name) and calls
        # _setup_plots() + _setup_callbacks() internally.
        super().__init__(dataset, eloss_name=model.constants.ELOSS)

        # Wire DoubleTap to reset hover block (source available after super().__init__)
        self._double_tap_stream = hv_streams.DoubleTap(source=self._selectors)
        self._double_tap_stream.add_subscriber(self._on_paneA_double_tap)

        # Periodic callback for inactivity logic (stopped initially)
        self._pc = pn.state.add_periodic_callback(
            self._check_inactivity, period=250, start=False
        )

    def get_e_axis(self):
        """Return the 1D energy axis associated with the current datacube."""
        return self._e_axis

    # --- paneA setup override: activate lasso by default ---

    @override
    def _setup_plots(self):
        super()._setup_plots()
        self.paneA.object = self.paneA.object.opts(
            hv.opts.Overlay(active_tools=['lasso_select'])
        )

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):
        """Build the two-pane split layout with image on the left and spectra on the right."""
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both',
            margin=0,
        )
        right_column = pn.Column(
            self.paneB,
            # Button row (fitting + multifit), if available.
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # Energy-range slider row, if available.
            self.range_slider_row if hasattr(self, 'range_slider_row') else self.range_slider,
            sizing_mode='stretch_both',
            margin=0,
        )
        return SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
            margin=0,
        )

    # --- Multifit-aware _figB_region override ---

    @override
    def _figB_region(self, pairs):
        """Return an hv.Curve for a region, using multifit data when active."""
        app_state = CacheManager.get_cached_app_state()
        if app_state.is_multifit:
            multifit_data = xr.DataArray(app_state.multifit)
            res = SpectrumExtractor.get_spectrum_from_indices(multifit_data, pairs)
        else:
            res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_hover({"x": 0, "y": 0})
        spec, n_points = res
        app_state.spectra = spec
        return hv.Curve(
            (self._energy, spec),
            kdims=['x'], vdims=['y'],
        ).opts(
            color='black', line_width=1.5,
            title=f"ROI — sum (points={n_points})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True, shared_axes=False, framewise=True,
        )

    # --- Fitting overlay ---

    def plot_fitting(self, x, y_fit):
        """Overlay the fitted spectrum as a magenta filled area on paneB."""
        CacheManager.get_cached_app_state().fitting_results = y_fit
        roi_curve = self._figB_region(self._region_pairs) if self._region_pairs else self._figB_hover({"x": 0, "y": 0})
        fit_area = hv.Area(
            (x, y_fit), kdims=['x'], vdims=['y'], label='Fit',
        ).opts(
            color='#FF00FF', alpha=0.35,
            line_color='#FF00FF', line_alpha=0.6,
            responsive=True, shared_axes=False, framewise=True,
        )
        overlay = hv.Overlay([roi_curve, fit_area]).opts(
            hv.opts.Overlay(responsive=True, shared_axes=False, framewise=True, show_legend=True)
        )
        self._update_paneB(overlay)

    def update_plot(self):
        """Refresh paneB based on ROI state (clears fit overlay)."""
        if self._region_pairs:
            self._update_paneB(self._figB_region(self._region_pairs))
        else:
            self._update_paneB(self._figB_hover(self._last_hover_point or {"x": 0, "y": 0}))

    def plot_image(self):
        """Re-render the integrated intensity heatmap and reset fit/spectra shared state."""
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")

        ny, nx = m_image.shape
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'], vdims=['Intensity'],
        ).opts(
            cmap='Greys_r', colorbar=False,
            xaxis=None, yaxis=None,
            invert_yaxis=True, aspect='equal',
            responsive=True, shared_axes=False,
        )
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        points_data = np.column_stack([XX.ravel().astype(float), YY.ravel().astype(float)])
        selectors = hv.Points(points_data, kdims=['x', 'y']).opts(
            size=0, alpha=0, nonselection_alpha=0,
            tools=['lasso_select', 'box_select'],
            shared_axes=False,
        )
        self._selectors = selectors
        self._nx = nx
        overlay = (img * selectors).opts(
            hv.opts.Overlay(responsive=True, aspect='equal', shared_axes=False,
                            active_tools=['lasso_select'])
        )
        self.paneA.object = overlay

        # Rewire streams to new selectors
        if self._hover_stream is not None:
            try:
                self._hover_stream.remove_subscriber(self._on_paneA_hover)
            except Exception:
                pass
        if self._tap_stream is not None:
            try:
                self._tap_stream.remove_subscriber(self._on_paneA_click)
            except Exception:
                pass
        if self._selection_stream is not None:
            try:
                self._selection_stream.remove_subscriber(self._on_paneA_selected)
            except Exception:
                pass
        if self._double_tap_stream is not None:
            try:
                self._double_tap_stream.remove_subscriber(self._on_paneA_double_tap)
            except Exception:
                pass
        from holoviews import streams as hv_streams_local
        self._hover_stream = hv_streams_local.PointerXY(source=selectors)
        self._tap_stream = hv_streams_local.Tap(source=selectors)
        self._selection_stream = hv_streams_local.Selection1D(source=selectors)
        self._double_tap_stream = hv_streams_local.DoubleTap(source=selectors)
        self._hover_stream.add_subscriber(self._on_paneA_hover)
        self._tap_stream.add_subscriber(self._on_paneA_click)
        self._selection_stream.add_subscriber(self._on_paneA_selected)
        self._double_tap_stream.add_subscriber(self._on_paneA_double_tap)

        self._region_pairs = []
        self._hover_blocked = False
        self._last_hover_ts = None
        self._update_paneB(self._figB_hover({"x": 0, "y": 0}))

        CacheManager.get_cached_app_state().fitting_results = None
        CacheManager.get_cached_app_state().spectra = None

    def plot_energy_map(self, energy_map):
        """Render a model-computed 2D energy map on paneA."""
        energy_map_arr = np.asarray(energy_map)
        if energy_map_arr.ndim != 2:
            raise ValueError(f"Expected a 2D energy map, got shape={energy_map_arr.shape}")
        energy_map_arr = np.where(np.isfinite(energy_map_arr), energy_map_arr, 0.0)
        ny, nx = energy_map_arr.shape

        _energy_map_cmap = LinearSegmentedColormap.from_list('energy_map', ['#00eb6c', '#ff1493'])

        img = hv.Image(
            (np.arange(nx), np.arange(ny), energy_map_arr),
            kdims=['x', 'y'], vdims=['Energy'],
        ).opts(
            cmap=_energy_map_cmap,
            colorbar=True,
            xaxis=None, yaxis=None,
            invert_yaxis=True, aspect='equal',
            responsive=True, shared_axes=False,
            title='Energy Map',
        )
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        points_data = np.column_stack([XX.ravel().astype(float), YY.ravel().astype(float)])
        selectors = hv.Points(points_data, kdims=['x', 'y']).opts(
            size=0, alpha=0, nonselection_alpha=0,
            tools=['lasso_select', 'box_select'],
            shared_axes=False,
        )
        overlay = (img * selectors).opts(
            hv.opts.Overlay(responsive=True, aspect='equal', shared_axes=False,
                            active_tools=['lasso_select'])
        )
        self.paneA.object = overlay

    # --- Inactivity timer ---

    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        """Flush pending selection or restore ROI after hover preview times out."""
        # Flush debounced selection first
        if self._pending_selection_ts is not None:
            if self._now_ms() - self._pending_selection_ts >= self._SELECTION_DEBOUNCE_MS:
                index = self._pending_selection_index
                self._pending_selection_index = None
                self._pending_selection_ts = None
                self._process_selection(index)
            return

        if not self._region_pairs:
            if self._pc and self._pc.running:
                self._pc.stop()
            return
        if self._last_hover_ts is None:
            if self._pc and self._pc.running:
                self._pc.stop()
            return
        if self._now_ms() - self._last_hover_ts >= self._INACTIVITY_MS:
            app_state = CacheManager.get_cached_app_state()
            if app_state.fitting_results is not None:
                self.plot_fitting(self._energy, app_state.fitting_results)
            else:
                self._update_paneB(self._figB_region(self._region_pairs))
            if self._pc and self._pc.running:
                self._pc.stop()

    # --- Overridden event handlers ---

    @override
    def _on_paneA_hover(self, x=None, y=None):
        if self._hover_blocked:
            return
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._update_paneB(self._figB_hover(point))
            self._last_hover_ts = self._now_ms()
            if self._pc and not self._pc.running:
                self._pc.start()
        else:
            self._show_spectrum(point=point)

    @override
    def _on_paneA_click(self, x=None, y=None):
        if x is None or y is None:
            return
        if self._pending_selection_ts is not None or self._hover_blocked:
            return
        app_state = CacheManager.get_cached_app_state()
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            if app_state.fitting_results is not None:
                self.plot_fitting(self._energy, app_state.fitting_results)
            else:
                self._last_hover_ts = self._now_ms()
                if self._pc and not self._pc.running:
                    self._pc.start()
        else:
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            self._show_spectrum(point=point)

    @override
    def _on_paneA_selected(self, index=None):
        self._hover_blocked = True
        self._pending_selection_ts = self._now_ms()
        if index:
            self._pending_selection_index = index
        if self._pc and not self._pc.running:
            self._pc.start()

    def _process_selection(self, index=None):
        if not index:
            pairs = []
        else:
            pairs = list(dict.fromkeys(
                (idx // self._nx, idx % self._nx) for idx in index
            ))
        self._region_pairs = pairs
        if not pairs:
            self._hover_blocked = False
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                self._update_paneB(self._figB_hover(self._last_hover_point))
            return
        app_state = CacheManager.get_cached_app_state()
        if app_state.fitting_results is not None:
            self.plot_fitting(self._energy, app_state.fitting_results)
        else:
            self._show_spectrum(region_pairs=pairs)
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None
        self._hover_blocked = True

    def _on_paneA_double_tap(self, x=None, y=None):
        """Double-click resets the lasso selection and unblocks hover."""
        self._hover_blocked = False
        self._region_pairs = []
        self._pending_selection_index = None
        self._pending_selection_ts = None
        self._last_hover_ts = None
        if self._pc and self._pc.running:
            self._pc.stop()
        if x is not None and y is not None:
            point = {"x": x, "y": y}
            self._last_hover_point = point
            self._show_spectrum(point=point)

    # --- Cleanup ---

    @override
    def cleanup(self):
        self._pending_selection_index = None
        self._pending_selection_ts = None
        if self._double_tap_stream is not None:
            try:
                self._double_tap_stream.remove_subscriber(self._on_paneA_double_tap)
                self._double_tap_stream.clear()
            except Exception:
                pass
            self._double_tap_stream = None
        if self._pc is not None:
            try:
                if self._pc.running:
                    self._pc.stop()
            except Exception:
                pass
        super().cleanup()

def sum_slice(matrix, vertexs):
    """
    Sum values in a rectangular matrix region defined by index bounds.

    Parameters:
        matrix: The 2D matrix to sum over.
        vertexs: Tuple `(x_start, x_end, y_start, y_end)` defining the region.

    Returns:
        The sum of the values in the specified region.
    """
    suma = 0
    for i in range(vertexs[0], vertexs[1]):
        for j in range(vertexs[2], vertexs[3]):
            suma += matrix[j][i]
    return suma

def get_envelope(x1, y1, x2, y2):
    """
    Compute the upper envelope of two curves over their union x-domain.

    Parameters:
        x1, y1: The x and y values of the first curve.
        x2, y2: The x and y values of the second curve.

    Returns:
        tuple[np.ndarray, np.ndarray]: `(x_common, y_envelope)`.
    """
    # Find the common x range
    x_common = np.union1d(x1, x2)

    # Interpolate y values for the common x points
    y1_interp = np.interp(x_common, x1, y1)
    y2_interp = np.interp(x_common, x2, y2)

    # Calculate the envelope by taking the maximum at each point
    y_envelope = np.maximum(y1_interp, y2_interp)
    return x_common, y_envelope
