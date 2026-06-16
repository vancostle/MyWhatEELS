"""
Spectrum image (datacube) visualization composer.

Extends BaseSpectrumImagePlot (HoloViews + Panel) with quantification-specific
overlays: power-law background fit, background-subtracted signal, and cross-section
curves. Inactivity timer logic temporarily shows hover spectra then reverts to the
ROI sum after a short pause.
"""

import panel as pn
import numpy as np
import time
import holoviews as hv
from holoviews import streams as hv_streams
import bokeh.palettes as palettes

from whateels.base.plots import BaseSpectrumImagePlot
from whateels.helpers import SpectrumFitting
from whateels.state import CacheManager
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import QuantificationModel
    from xarray import Dataset

colors = palettes.Category10[10]
NORMALIZATION_ANCHOR_WINDOW_EV = 10.0

WHITE_LINE_SHELL_PAIRS = (
    ("L2", "L3"),
    ("M2", "M3"),
    ("M4", "M5"),
    ("N2", "N3"),
)

WHITE_LINE_SHELL_GROUPS = tuple(frozenset(shells) for shells in WHITE_LINE_SHELL_PAIRS)

WHITE_LINE_SHELL_ALIASES = {
    "L23": ("L2", "L3"),
    "L32": ("L2", "L3"),
    "M23": ("M2", "M3"),
    "M32": ("M2", "M3"),
    "M45": ("M4", "M5"),
    "M54": ("M4", "M5"),
    "N23": ("N2", "N3"),
    "N32": ("N2", "N3"),
}


def _normalize_shell_label(shell):
    return str(shell).upper().replace(" ", "")


def _is_white_line_shell_group(shells) -> bool:
    if not shells:
        return False
    shell_labels = [_normalize_shell_label(shell) for shell in shells]
    if len(shell_labels) == 1 and shell_labels[0] in WHITE_LINE_SHELL_ALIASES:
        return True
    return frozenset(shell_labels) in WHITE_LINE_SHELL_GROUPS


def _expanded_white_line_shells(shells):
    shell_labels = [_normalize_shell_label(shell) for shell in shells]
    if len(shell_labels) == 1 and shell_labels[0] in WHITE_LINE_SHELL_ALIASES:
        return WHITE_LINE_SHELL_ALIASES[shell_labels[0]]
    for shell_pair in WHITE_LINE_SHELL_PAIRS:
        if frozenset(shell_labels) == frozenset(shell_pair):
            return shell_pair
    return tuple(shell_labels)


def _as_real_float_array(values):
    return np.asarray(values).real.astype(float, copy=False)


def _net_spectrum(selected_slice, y_extrapolated):
    selected = _as_real_float_array(selected_slice)
    if y_extrapolated is None:
        background = np.zeros_like(selected)
    else:
        background = _as_real_float_array(y_extrapolated)
    if selected.shape != background.shape:
        raise ValueError("selected_slice and y_extrapolated must have the same length.")
    return selected - background


def _normalization_anchor(eaxis, selected_slice, y_extrapolated, quant_range_values):
    axis = np.asarray(eaxis, dtype=float)
    net = _net_spectrum(selected_slice, y_extrapolated)
    if axis.shape[0] != net.shape[0]:
        raise ValueError("eaxis and selected_slice must have the same length.")

    finite_mask = np.isfinite(axis) & np.isfinite(net)
    if quant_range_values is not None and len(quant_range_values) >= 2:
        lo, hi = sorted((float(quant_range_values[0]), float(quant_range_values[1])))
        range_mask = finite_mask & (axis >= lo) & (axis <= hi)
        indices = np.flatnonzero(range_mask)
        if indices.size == 0:
            indices = np.flatnonzero(finite_mask)
            if indices.size == 0:
                raise ValueError("No finite experimental points available for normalization.")
            idx = indices[np.argmin(np.abs(axis[indices] - hi))]
            anchor_energy = float(axis[idx])
            anchor_window = (anchor_energy - NORMALIZATION_ANCHOR_WINDOW_EV, anchor_energy)
            target_value = _constant_fit_to_window(axis, net, anchor_window)
            if not np.isfinite(target_value):
                target_value = float(net[idx])
            return anchor_energy, target_value, anchor_window
        idx = indices[-1]
        anchor_energy = float(axis[idx])
        anchor_window = (max(lo, anchor_energy - NORMALIZATION_ANCHOR_WINDOW_EV), anchor_energy)
        target_value = _constant_fit_to_window(axis, net, anchor_window)
        if not np.isfinite(target_value):
            target_value = float(net[idx])
        return anchor_energy, target_value, anchor_window

    indices = np.flatnonzero(finite_mask)
    if indices.size == 0:
        raise ValueError("No finite experimental points available for normalization.")
    idx = indices[-1]
    anchor_energy = float(axis[idx])
    anchor_window = (anchor_energy - NORMALIZATION_ANCHOR_WINDOW_EV, anchor_energy)
    target_value = _constant_fit_to_window(axis, net, anchor_window)
    if not np.isfinite(target_value):
        target_value = float(net[idx])
    return anchor_energy, target_value, anchor_window


def _prepare_curve_for_interpolation(xaxis, yaxis):
    x = np.asarray(xaxis, dtype=float)
    y = _as_real_float_array(yaxis)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size == 0:
        return x, y
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    unique_x, unique_idx = np.unique(x, return_index=True)
    return unique_x, y[unique_idx]


def _interp_at_energy(xaxis, yaxis, energy):
    x, y = _prepare_curve_for_interpolation(xaxis, yaxis)
    if x.size == 0:
        return np.nan
    if energy < x[0] or energy > x[-1]:
        return np.nan
    return float(np.interp(energy, x, y))


def _constant_fit_to_window(xaxis, yaxis, energy_window):
    if energy_window is None or len(energy_window) < 2:
        return np.nan

    x, y = _prepare_curve_for_interpolation(xaxis, yaxis)
    if x.size == 0:
        return np.nan

    lo, hi = sorted((float(energy_window[0]), float(energy_window[1])))
    lo = max(lo, float(x[0]))
    hi = min(hi, float(x[-1]))
    if hi < lo:
        return np.nan

    window_mask = (x >= lo) & (x <= hi)
    if np.any(window_mask):
        return float(np.mean(y[window_mask]))

    if hi == lo:
        return _interp_at_energy(x, y, hi)

    sample_x = np.linspace(lo, hi, 32)
    sample_y = np.interp(sample_x, x, y)
    return float(np.mean(sample_y))


def _scale_to_anchor(xaxis, yaxis, anchor_energy, target_value, anchor_window=None):
    simulated_value = _constant_fit_to_window(xaxis, yaxis, anchor_window)
    if not np.isfinite(simulated_value):
        simulated_value = _interp_at_energy(xaxis, yaxis, anchor_energy)
    if not np.isfinite(target_value) or not np.isfinite(simulated_value):
        return 1.0, simulated_value
    if abs(simulated_value) <= np.finfo(float).tiny:
        return 1.0, simulated_value
    return float(target_value / simulated_value), simulated_value


def _integrate_xy(yaxis, xaxis):
    try:
        return float(np.trapezoid(yaxis, xaxis))
    except Exception:
        return float(np.trapz(yaxis, xaxis))


def _curve_segment_for_range(xaxis, yaxis, delta):
    x, y = _prepare_curve_for_interpolation(xaxis, yaxis)
    if x.size == 0 or delta is None or len(delta) < 2:
        return np.array([], dtype=float), np.array([], dtype=float)

    lo, hi = sorted((float(delta[0]), float(delta[1])))
    lo = max(lo, float(x[0]))
    hi = min(hi, float(x[-1]))
    if hi <= lo:
        return np.array([], dtype=float), np.array([], dtype=float)

    inside = (x > lo) & (x < hi)
    segment_x = np.concatenate(([lo], x[inside], [hi]))
    segment_y = np.interp(segment_x, x, y)
    return segment_x, segment_y


def _integrate_curve_range(xaxis, yaxis, delta):
    segment_x, segment_y = _curve_segment_for_range(xaxis, yaxis, delta)
    if segment_x.size < 2:
        return 0.0
    return _integrate_xy(segment_y, segment_x)


def _sum_cross_sections_on_common_axis(shell_curves, chemical_shift=0.0):
    prepared_curves = []
    for eaxis_cs, cross_section in shell_curves:
        x = np.asarray(eaxis_cs, dtype=float) - float(chemical_shift)
        y = _as_real_float_array(cross_section)
        x, y = _prepare_curve_for_interpolation(x, y)
        if x.size:
            prepared_curves.append((x, y))

    if not prepared_curves:
        return np.array([], dtype=float), np.array([], dtype=float)

    x_common = np.unique(np.concatenate([x for x, _ in prepared_curves]))
    y_total = np.zeros_like(x_common, dtype=float)
    for x, y in prepared_curves:
        y_total += np.interp(x_common, x, y, left=0.0, right=0.0)
    return x_common, y_total


class SpectrumImagePlot(BaseSpectrumImagePlot):
    """
    HoloViews-based spectrum image visualizer for the quantification page.

    Extends BaseSpectrumImagePlot with:
    - Inactivity timer: hover temporarily shows pixel spectrum, then reverts to ROI.
    - Quantification overlays: power-law fit, background subtraction, cross-sections.
    - Quantification pie chart built with pure HoloViews.
    """

    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'
    _QUANT_PIE_SIZE = 420

    def __init__(self, model: "QuantificationModel", dataset: "Dataset"):
        self._model = model

        # Inactivity timer state — must be set before super().__init__ triggers callbacks
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._pc = None

        # Pending selection — overwritten on every Selection1D event while drawing;
        # processed by _check_inactivity on the next periodic callback tick.
        self._pending_selection_index = None
        self._pending_selection_ts = None
        self._SELECTION_DEBOUNCE_MS = 200

        # Hover is blocked while a lasso selection is active; reset only by double-click.
        self._hover_blocked = False
        self._double_tap_stream = None

        # Quantification state
        self.selected_slice = None
        self.element_quant_data = []

        # Base __init__ sets up HoloViews heatmap + spectrum panes and wires streams
        super().__init__(dataset, eloss_name=model.constants.ELOSS)

        # Wire DoubleTap to reset hover block (source available after super().__init__)
        self._double_tap_stream = hv_streams.DoubleTap(source=self._selectors)
        self._double_tap_stream.add_subscriber(self._on_paneA_double_tap)

        # Periodic callback for inactivity logic (stopped initially)
        self._pc = pn.state.add_periodic_callback(
            self._check_inactivity, period=250, start=False
        )

    def get_e_axis(self):
        return self._e_axis

    # --- paneB override: static charts (bars/pie polygons) use direct rendering ---

    def _is_quant_pie_polygons(self, obj) -> bool:
        """Return True only for quantification pie polygon elements."""
        if not isinstance(obj, hv.Polygons):
            return False
        try:
            vdim_names = {vd.name for vd in obj.vdims}
            return 'ProportionPct' in vdim_names
        except Exception:
            return False

    def _requires_static_paneB_render(self, fig) -> bool:
        """Return True when paneB should bypass the curve DynamicMap pipe."""
        if isinstance(fig, hv.Bars) or self._is_quant_pie_polygons(fig):
            return True
        if isinstance(fig, hv.Overlay):
            try:
                return any(self._is_quant_pie_polygons(el) for el in fig.values())
            except Exception:
                return False
        return False

    @override
    def _update_paneB(self, fig):
        if self._requires_static_paneB_render(fig):
            # Static charts use a different renderer than the curve DynamicMap.
            # Rendering directly avoids Bokeh model type mismatches.
            # Lock pane size so SplitJs resizing cannot stretch the pie chart.
            self.paneB.sizing_mode = 'fixed'
            self.paneB.width = self._QUANT_PIE_SIZE
            self.paneB.height = self._QUANT_PIE_SIZE
            self.paneB.align = ('center', 'center')
            self.paneB.styles = {'margin': 'auto'}
            self.paneB.object = fig
            self._paneB_static_mode = True
        else:
            if getattr(self, '_paneB_static_mode', False):
                # Restore the DynamicMap so the Pipe-based spectrum updates work again.
                self.paneB.sizing_mode = 'stretch_both'
                self.paneB.width = None
                self.paneB.height = None
                self.paneB.align = 'start'
                self.paneB.styles = {}
                self.paneB.object = self._paneB_dmap
                self._paneB_static_mode = False
            super()._update_paneB(fig)

    @override
    def _setup_plots(self):
        super()._setup_plots()
        # Make lasso the default active drag tool, matching the previous Plotly dragmode="lasso"
        self.paneA.object = self.paneA.object.opts(
            hv.opts.Overlay(active_tools=['lasso_select'])
        )

    # --- Inactivity timer ---

    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        # --- Flush pending selection after debounce ---
        if self._pending_selection_ts is not None:
            if self._now_ms() - self._pending_selection_ts >= self._SELECTION_DEBOUNCE_MS:
                index = self._pending_selection_index
                self._pending_selection_index = None
                self._pending_selection_ts = None
                self._process_selection(index)
            # Always return while a selection is pending — don't let the
            # region_pairs / hover checks below stop the pc prematurely.
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
            if app_state.quantification_elements:
                self.plot_quantification_elements(app_state.quantification_elements)
            else:
                self._show_spectrum(region_pairs=self._region_pairs)
            if self._pc and self._pc.running:
                self._pc.stop()

    # --- Overridden event handlers ---

    @override
    def _on_paneA_hover(self, x=None, y=None):
        if x is None or y is None:
            return
        self._queue_hover(x, y)

    def _handle_hover_render(self, point):
        # Hover is blocked after a lasso selection — double-click on paneA to reset.
        if self._hover_blocked:
            return
        if not self._region_pairs and self._try_fast_hover_update(point):
            return
        if self._region_pairs:
            # Temporarily show pixel spectrum; inactivity timer will revert to ROI
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
        self._last_hover_pixel = (round(y), round(x))
        # Ignore while a selection is being drawn or processed — Tap fires at mouse-up
        # which is the same moment Selection1D finishes, causing interference.
        if self._pending_selection_ts is not None or self._hover_blocked:
            return
        app_state = CacheManager.get_cached_app_state()
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if app_state.quantification_elements and self._region_pairs:
            self.plot_quantification_elements(app_state.quantification_elements)
            return
        if self._region_pairs:
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
        # Block hover immediately so paneB isn't overwritten while lasso is being drawn.
        self._hover_blocked = True
        # Always refresh the debounce timestamp.
        self._pending_selection_ts = self._now_ms()
        # Only store non-empty indices: Bokeh fires a final Selection1D(index=[]) after
        # mouse release to clear the visual highlight — that would overwrite the real indices.
        if index:
            self._pending_selection_index = index
        if self._pc and not self._pc.running:
            self._pc.start()

    def _process_selection(self, index=None):
        app_state = CacheManager.get_cached_app_state()
        pairs = self._index_to_pairs(index)
        self._region_pairs = pairs
        self._update_selection_overlay(pairs)
        if not pairs:
            self._hover_blocked = False
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                self._update_paneB(self._figB_hover(self._last_hover_point))
            if self.on_selection_change:
                self.on_selection_change(False)
            return
        if app_state.quantification_elements:
            self.plot_quantification_elements(app_state.quantification_elements)
        else:
            self._show_spectrum(region_pairs=pairs)
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None
        self._hover_blocked = True
        if self.on_selection_change:
            self.on_selection_change(True)

    @override
    def _on_paneA_double_tap(self, x=None, y=None):
        """Double-click resets the lasso selection and unblocks hover."""
        super()._on_paneA_double_tap(x, y)
        self._last_hover_ts = None
        if self._pc and self._pc.running:
            self._pc.stop()
        if x is not None and y is not None:
            point = {"x": x, "y": y}
            self._last_hover_point = point
            self._show_spectrum(point=point)

    # --- Quantification overlays ---

    def plot_quantification_elements(self, element_items: list):
        # Keep ROI spectrum styling fully aligned with BaseSpectrumImagePlot
        # (including alpha and default title/axes options).
        res = self._get_spectrum_from_indices_fast(self._region_pairs)
        if res is None:
            return
        spec, _n_points = res
        self.selected_slice = spec

        base_curve = self._figB_region(self._region_pairs).relabel('Spectrum')
        curves = [base_curve]
        for i, element_item in enumerate(element_items):
            color = colors[i % len(colors)]
            curves.extend(self._build_quant_curves(element_item, color))

        overlay = hv.Overlay(curves).opts(
            hv.opts.Overlay(
                responsive=True, shared_axes=False, framewise=True, show_legend=True,
            )
        )
        self._update_paneB(overlay)

    def _build_quant_curves(self, element_item, color):
        """Build HoloViews fit + cross-section curves for one element."""
        curves = []
        try:
            plot_min, plot_max = self._get_quantification_plot_window(element_item)
            y_fit = SpectrumFitting.fit_powerlaw_curve(
                self._energy, self.selected_slice, range_values=element_item.fit_range
            )
            quant_eaxis = self._get_quantification_eaxis(self.selected_slice)
            if y_fit is not None:
                x_fit = np.asarray(self._energy, dtype=float)
                y_fit_arr = np.asarray(y_fit, dtype=float)
                fit_mask = (
                    np.isfinite(x_fit)
                    & np.isfinite(y_fit_arr)
                    & (x_fit >= plot_min)
                    & (x_fit <= plot_max)
                )
                if np.count_nonzero(fit_mask) >= 2:
                    curves.append(hv.Curve(
                        (x_fit[fit_mask], y_fit_arr[fit_mask]), kdims=['x'], vdims=['y'],
                        label=f'{element_item.element} PowerLaw Fit',
                    ).opts(color=color, line_width=1.5))

                # Use Curve instead of Area to avoid HoloViews AreaMixin range issues
                # on dynamic updates with multiple elements and slider changes.
                bg_sub = np.asarray(self.selected_slice, dtype=float) - y_fit_arr
                bg_mask = (
                    np.isfinite(x_fit)
                    & np.isfinite(bg_sub)
                    & (x_fit >= plot_min)
                    & (x_fit <= plot_max)
                )
                if np.count_nonzero(bg_mask) >= 2:
                    bg_x = x_fit[bg_mask]
                    bg_y = bg_sub[bg_mask]
                    bg_area = self._integrate_area(bg_x, bg_y)
                    bg_label = (
                        f"{element_item.element} BG Subtraction "
                    )
                    # Build a filled polygon between BG subtraction and baseline y=0
                    # to preserve the original "area" aesthetics without hv.Area.
                    poly_x = np.concatenate([bg_x, bg_x[::-1]])
                    poly_y = np.concatenate([bg_y, np.zeros_like(bg_y)[::-1]])
                    curves.append(hv.Polygons(
                        [{'x': poly_x, 'y': poly_y}],
                        kdims=['x', 'y'],
                        label=bg_label,
                    ).opts(
                        color=color,
                        alpha=0.3,
                        line_color=color,
                        line_alpha=0.6,
                        show_legend=True,
                    ))
            if _is_white_line_shell_group(element_item.shells):
                xaxis, yaxis = self.calculate_white_line_shell_data(
                    self.selected_slice,
                    element_item,
                    y_fit if y_fit is not None else np.zeros_like(self.selected_slice),
                )
                xaxis = np.asarray(xaxis, dtype=float)
                yaxis = np.asarray(yaxis, dtype=float)
                cs_mask = (
                    np.isfinite(xaxis)
                    & np.isfinite(yaxis)
                    & (xaxis >= plot_min)
                    & (xaxis <= plot_max)
                )
                if np.count_nonzero(cs_mask) < 2:
                    return curves
                curves.append(hv.Curve(
                    (xaxis[cs_mask], yaxis[cs_mask]), kdims=['x'], vdims=['y'],
                    label=f'{element_item.element} {" + ".join(element_item.shells)} OOS',
                ).opts(line_width=1.5))
            else:
                for ishell in element_item.shells:
                    eaxis_cs = element_item.cross_sections[ishell][0]
                    counts = element_item.cross_sections[ishell][1]
                    onset = element_item.cross_sections[ishell][2]
                    cross_section = element_item.cross_sections[ishell][3]
                    cs_instance = add_cs(
                        element=element_item.element, ishell=ishell,
                        selected_slice=self.selected_slice,
                        y_extrapolated=y_fit if y_fit is not None else np.zeros_like(self.selected_slice),
                        chemical_shift=element_item.chemical_shift,
                        quant_range_values=element_item.quant_range,
                        eaxis=quant_eaxis, eaxis_cs=eaxis_cs,
                        counts=counts, onset=onset, cross_section=cross_section,
                    )
                    xaxis, yaxis = cs_instance.get_data()
                    xaxis = np.asarray(xaxis, dtype=float)
                    yaxis = np.asarray(yaxis, dtype=float)
                    cs_mask = (
                        np.isfinite(xaxis)
                        & np.isfinite(yaxis)
                        & (xaxis >= plot_min)
                        & (xaxis <= plot_max)
                    )
                    if np.count_nonzero(cs_mask) < 2:
                        continue
                    curves.append(hv.Curve(
                        (xaxis[cs_mask], yaxis[cs_mask]), kdims=['x'], vdims=['y'],
                        label=f'{element_item.element} {ishell} OOS',
                    ).opts(line_width=1.5))
        except Exception:
            pass
        return curves

    def _integrate_area(self, x, y) -> float:
        """Compute signed area under y(x) using trapezoidal integration."""
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        if x_arr.size < 2 or y_arr.size < 2:
            return 0.0
        try:
            return float(np.trapezoid(y_arr, x_arr))
        except Exception:
            return float(np.trapz(y_arr, x_arr))

    def _get_quantification_plot_window(self, element_item):
        """Return the x-axis window to display quantification overlays."""
        fit_range = getattr(element_item, 'fit_range', None)
        quant_range = getattr(element_item, 'quant_range', None)

        if fit_range is not None and len(fit_range) >= 2:
            plot_min = float(fit_range[0])
        elif quant_range is not None and len(quant_range) >= 2:
            plot_min = float(quant_range[0])
        else:
            plot_min = float(np.nanmin(self._energy))

        if quant_range is not None and len(quant_range) >= 2:
            plot_max = float(quant_range[1])
        elif fit_range is not None and len(fit_range) >= 2:
            plot_max = float(fit_range[1])
        else:
            plot_max = float(np.nanmax(self._energy))

        if not np.isfinite(plot_min):
            plot_min = float(np.nanmin(self._energy))
        if not np.isfinite(plot_max):
            plot_max = float(np.nanmax(self._energy))
        if plot_max < plot_min:
            plot_min, plot_max = plot_max, plot_min

        return plot_min, plot_max

    def _transparent_bokeh_hook(self, plot, element):
        """Force fully transparent Bokeh figure background for HoloViews objects."""
        fig = getattr(plot, 'state', None)
        if fig is None:
            return
        fig.background_fill_color = None
        fig.background_fill_alpha = 0
        fig.border_fill_color = None
        fig.border_fill_alpha = 0
        fig.outline_line_alpha = 0

    def _get_quantification_eaxis(self, selected_slice):
        """Prefer physical Eloss axis when shape matches; otherwise fallback to plotting axis."""
        try:
            e_axis = np.asarray(self._e_axis)
            if selected_slice is not None and e_axis.shape[0] == np.asarray(selected_slice).shape[0]:
                return e_axis
        except Exception:
            pass
        return np.asarray(self._energy)

    def calculate_shell_data(self, selected_slice, element_item, y_extrapolated, ishell):
        eaxis = element_item.cross_sections[ishell][0]
        counts = element_item.cross_sections[ishell][1]
        onset = element_item.cross_sections[ishell][2]
        cross_section = element_item.cross_sections[ishell][3]
        quant_eaxis = self._get_quantification_eaxis(selected_slice)
        cs_instance = add_cs(
            element=element_item.element, ishell=ishell,
            selected_slice=selected_slice, y_extrapolated=y_extrapolated,
            chemical_shift=element_item.chemical_shift,
            quant_range_values=element_item.quant_range,
            eaxis=quant_eaxis, eaxis_cs=eaxis,
            counts=counts, onset=onset, cross_section=cross_section,
        )
        return cs_instance.get_data()

    def calculate_white_line_shell_data(self, selected_slice, element_item, y_extrapolated):
        shell_curves = []
        white_line_shells = _expanded_white_line_shells(element_item.shells)
        missing_shells = [shell for shell in white_line_shells if shell not in element_item.cross_sections]
        if missing_shells:
            raise ValueError(
                f"Missing sub-shell cross-sections for White Line {element_item.shells}: "
                f"{missing_shells}."
            )
        for ishell in white_line_shells:
            eaxis = element_item.cross_sections[ishell][0]
            cross_section = element_item.cross_sections[ishell][3]
            shell_curves.append((eaxis, cross_section))

        quant_eaxis = self._get_quantification_eaxis(selected_slice)
        xaxis, total_cross_section = _sum_cross_sections_on_common_axis(
            shell_curves,
            chemical_shift=element_item.chemical_shift,
        )
        anchor_energy, target_value, anchor_window = _normalization_anchor(
            quant_eaxis,
            selected_slice,
            y_extrapolated,
            element_item.quant_range,
        )
        scale_factor, _simulated_value = _scale_to_anchor(
            xaxis,
            total_cross_section,
            anchor_energy,
            target_value,
            anchor_window,
        )
        yaxis = (total_cross_section * scale_factor).real

        max_eaxis = np.asarray(quant_eaxis, dtype=float)[-1]
        mask = xaxis <= max_eaxis
        return xaxis[mask], yaxis[mask]

    def calculate_shell_theoretical_data(self, selected_slice, element_item, ishell):
        eaxis = element_item.cross_sections[ishell][0]
        cross_section = element_item.cross_sections[ishell][3]
        quant_eaxis = self._get_quantification_eaxis(selected_slice)
        xaxis, yaxis = _prepare_curve_for_interpolation(
            np.asarray(eaxis, dtype=float) - element_item.chemical_shift,
            cross_section,
        )
        max_eaxis = np.asarray(quant_eaxis, dtype=float)[-1]
        mask = xaxis <= max_eaxis
        return xaxis[mask], yaxis[mask]

    def calculate_white_line_theoretical_data(self, selected_slice, element_item):
        shell_curves = []
        white_line_shells = _expanded_white_line_shells(element_item.shells)
        missing_shells = [shell for shell in white_line_shells if shell not in element_item.cross_sections]
        if missing_shells:
            raise ValueError(
                f"Missing sub-shell cross-sections for White Line {element_item.shells}: "
                f"{missing_shells}."
            )
        for ishell in white_line_shells:
            eaxis = element_item.cross_sections[ishell][0]
            cross_section = element_item.cross_sections[ishell][3]
            shell_curves.append((eaxis, cross_section))

        quant_eaxis = self._get_quantification_eaxis(selected_slice)
        xaxis, yaxis = _sum_cross_sections_on_common_axis(
            shell_curves,
            chemical_shift=element_item.chemical_shift,
        )
        max_eaxis = np.asarray(quant_eaxis, dtype=float)[-1]
        mask = xaxis <= max_eaxis
        return xaxis[mask], yaxis[mask]

    def calculate_element_theoretical_data(self, selected_slice, element_item):
        if _is_white_line_shell_group(element_item.shells):
            return self.calculate_white_line_theoretical_data(selected_slice, element_item)
        if len(element_item.shells) == 1:
            return self.calculate_shell_theoretical_data(
                selected_slice,
                element_item,
                element_item.shells[0],
            )
        raise ValueError(
            f"Unsupported shell combination for quantification: {element_item.shells}. "
            "Use one edge or a supported White Line pair."
        )

    def _ensure_selected_slice_for_quantification(self):
        """Try to recover selected_slice from pending/active ROI before quantification."""
        if self.selected_slice is not None:
            return

        pending_index = self._pending_selection_index
        has_pending_index = False
        if pending_index is not None:
            try:
                has_pending_index = len(pending_index) > 0
            except Exception:
                has_pending_index = bool(pending_index)

        # Flush debounced lasso selection if it exists.
        if self._pending_selection_ts is not None and has_pending_index:
            self._process_selection(pending_index)
            self._pending_selection_index = None
            self._pending_selection_ts = None
            if self.selected_slice is not None:
                return

        # Fallback: recover from already committed region.
        if self._region_pairs:
            res = self._get_spectrum_from_indices_fast(self._region_pairs)
            if res is not None:
                self.selected_slice, _ = res

    def plot_quantification_pie(self, element_items):
        self._ensure_selected_slice_for_quantification()
        if self.selected_slice is None:
            raise ValueError("No region selected. Use lasso/box on the image before running quantification.")
        element_data = []
        if element_items is None or len(element_items) == 0:
            raise ValueError("No elements provided for quantification.")
        quant_eaxis = self._get_quantification_eaxis(self.selected_slice)
        for element_item in element_items:
            try:
                y_fit = SpectrumFitting.fit_powerlaw_curve(
                    self._energy, self.selected_slice, range_values=element_item.fit_range
                )
                y_extrapolated = y_fit if y_fit is not None else np.zeros_like(self.selected_slice)
                net_signal = _net_spectrum(self.selected_slice, y_extrapolated)
                pure_cs_x, pure_cs_y = self.calculate_element_theoretical_data(
                    self.selected_slice,
                    element_item,
                )
                intensity = _integrate_curve_range(quant_eaxis, net_signal, element_item.quant_range)
                sigma = _integrate_curve_range(pure_cs_x, pure_cs_y, element_item.quant_range)
                if not np.isfinite(intensity) or intensity <= 0:
                    raise ValueError(
                        f"Invalid net intensity ({intensity}) for {element_item.element}. "
                        "Check background fit and quantification range."
                    )
                if not np.isfinite(sigma) or sigma <= 0:
                    raise ValueError(
                        f"Invalid theoretical cross-section integral ({sigma}) for "
                        f"{element_item.element}. Check beam metadata and selected shell."
                    )
                element_data.append({
                    'element': str(element_item.element),
                    'intensity': float(intensity),
                    'sigma': float(sigma),
                    'relative_amount': float(intensity / sigma),
                })
            except Exception as e:
                raise e
        try:
            element_color_map = {
                str(element_item.element): colors[i % len(colors)]
                for i, element_item in enumerate(element_items)
            }
            if len(element_data) < 2:
                raise ValueError("At least two valid elements are required for quantification.")
            self._update_paneB(self._build_quant_pie(element_data, element_color_map))
        except Exception as e:
            raise RuntimeError(f"Error in quantification calculation: {e}")

    def _build_quant_pie(self, element_data, element_color_map):
        """Build a pure HoloViews pie chart using polygon wedges."""
        _QUANT_COLORS = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
        _RADIUS = 1.0
        _LABEL_RADIUS = 0.67
        _N_POINTS_PER_SLICE = 90
        _PIE_SIZE = self._QUANT_PIE_SIZE

        total = float(sum(item['relative_amount'] for item in element_data))
        if total <= 0:
            raise ValueError("Quantification proportions must sum to a positive value.")

        polygons = []
        label_data = []
        start_angle = np.pi / 2.0

        for i, item in enumerate(element_data):
            label = item['element']
            prop = float(item['relative_amount']) / total
            end_angle = start_angle - (2.0 * np.pi * prop)
            theta = np.linspace(end_angle, start_angle, _N_POINTS_PER_SLICE)

            xs = np.concatenate(([0.0], _RADIUS * np.cos(theta), [0.0]))
            ys = np.concatenate(([0.0], _RADIUS * np.sin(theta), [0.0]))
            color = element_color_map.get(label, _QUANT_COLORS[i % len(_QUANT_COLORS)])
            pct = prop * 100.0

            polygons.append({
                'xs': xs,
                'ys': ys,
                'Element': label,
                'ProportionPct': pct,
                'NetIntensity': item['intensity'],
                'Sigma': item['sigma'],
                'RelativeAmount': item['relative_amount'],
                'Color': color,
            })

            mid_angle = 0.5 * (start_angle + end_angle)
            label_x = _LABEL_RADIUS * np.cos(mid_angle)
            label_y = _LABEL_RADIUS * np.sin(mid_angle)
            label_data.append((label_x, label_y, f"{label}\n{pct:.1f}%"))

            start_angle = end_angle

        pie = hv.Polygons(
            polygons,
            kdims=['xs', 'ys'],
            vdims=['Element', 'ProportionPct', 'NetIntensity', 'Sigma', 'RelativeAmount', 'Color'],
        ).opts(
            title='Quantification Proportions in ROI',
            color='Color',
            line_color='white',
            line_width=1,
            alpha=0.95,
            tools=['hover'],
            hover_tooltips=[
                ('Element', '@{Element}'),
                ('Proportion', '@{ProportionPct}{0.2f}%'),
                ('I(Delta)', '@{NetIntensity}{0.4g}'),
                ('sigma(Delta)', '@{Sigma}{0.4g}'),
                ('I/sigma', '@{RelativeAmount}{0.4g}'),
            ],
            xaxis=None,
            yaxis=None,
            show_grid=False,
            show_frame=False,
            xlim=(-1.15, 1.15),
            ylim=(-1.15, 1.15),
            aspect='square',
            data_aspect=1,
            responsive=False,
            width=_PIE_SIZE,
            height=_PIE_SIZE,
            bgcolor='rgba(0,0,0,0)',
            hooks=[self._transparent_bokeh_hook],
            shared_axes=False,
            framewise=True,
        )

        labels_overlay = hv.Labels(
            label_data,
            kdims=['x', 'y'],
            vdims=['text'],
        ).opts(
            text_align='center',
            text_baseline='middle',
            text_font_size='9pt',
            text_color='white',
            hooks=[self._transparent_bokeh_hook],
        )

        return (pie * labels_overlay).opts(
            hv.opts.Overlay(
                responsive=False,
                aspect='square',
                width=_PIE_SIZE,
                height=_PIE_SIZE,
                bgcolor='rgba(0,0,0,0)',
                hooks=[self._transparent_bokeh_hook],
                shared_axes=False,
                framewise=True,
            )
        )

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

class add_cs:
    """
    Class to calculate and normalize cross-sections for a given element and shell.
    """
    def __init__(self, element, ishell, selected_slice, y_extrapolated, chemical_shift=0, quant_range_values=None, eaxis=None, eaxis_cs=None, counts=None, onset=None, cross_section=None):
        """
        Initializes the add_cs object.

        Parameters:
            element: The element name (e.g., "Fe").
            ishell: The shell name (e.g., "K").
            selected_slice: The selected slice of data.
            y_extrapolated: The extrapolated background values.
            chemical_shift: The chemical shift to apply (default is 0).
            quant_range_values: The range of energy for quantification.
            eaxis: The energy axis for the experimental data.
            eaxis_cs: The energy axis for the cross-section data.
            counts: The counts data.
            onset: The onset energy.
            cross_section: The cross-section data.
        """
        self.eaxis, self.counts, self.onset = eaxis, counts, onset
        self.cross_section = cross_section
        self.element = element
        self.ishell = ishell
        self.chemical_shift = chemical_shift
        self.quant_range_values = quant_range_values
        self.eaxis_cs = eaxis_cs

        # Ensure that the lengths of the energy axes and data match
        if len(eaxis) != len(selected_slice) and len(eaxis_cs) != len(cross_section):
            raise ValueError("eaxis, selected_slice, and cross_section must have the same length.")

        # Match the simulated curve to a constant fit over the final energy window.
        self.xaxis = np.asarray(self.eaxis_cs, dtype=float) - self.chemical_shift
        self.anchor_energy, self.norm_exp, self.anchor_window = _normalization_anchor(
            self.eaxis,
            selected_slice,
            y_extrapolated,
            self.quant_range_values,
        )
        self.scale_factor, self.norm_sim = _scale_to_anchor(
            self.xaxis,
            self.cross_section,
            self.anchor_energy,
            self.norm_exp,
            self.anchor_window,
        )
        self.yaxis = _as_real_float_array(self.cross_section) * self.scale_factor

        max_eaxis = self.eaxis[-1]
        mask = self.xaxis <= max_eaxis
        self.xaxis = self.xaxis[mask]
        self.yaxis = self.yaxis[mask]

    def get_data(self):
        """
        Returns the calculated data for plotting.

        Returns:
            xaxis: The shifted energy axis.
            yaxis: The normalized cross-section.
        """
        return self.xaxis, self.yaxis

def sum_slice(matrix, vertexs):
    """
    Sums the values in a region defined by vertices in a matrix.

    Parameters:
        matrix: The 2D matrix to sum over.
        vertexs: A tuple (x_start, x_end, y_start, y_end) defining the region.

    Returns:
        The sum of the values in the specified region.
    """
    suma = 0
    for i in range(vertexs[0], vertexs[1]):
        for j in range(vertexs[2], vertexs[3]):
            suma += matrix[j][i]
    return suma
