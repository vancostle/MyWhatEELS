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
from whateels.helpers import SpectrumExtractor, SpectrumFitting
from whateels.state import CacheManager
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import QuantificationModel
    from xarray import Dataset

colors = palettes.Category10[10]


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
        # Hover is blocked after a lasso selection — double-click on paneA to reset.
        if self._hover_blocked:
            return
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
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
            res = SpectrumExtractor.get_spectrum_from_indices(
                self._electron_count_data, self._region_pairs
            )
            if res is not None:
                self.selected_slice, _ = res

    def plot_quantification_pie(self, element_items):
        self._ensure_selected_slice_for_quantification()
        if self.selected_slice is None:
            raise ValueError("No region selected. Use lasso/box on the image before running quantification.")
        element_data = []
        if element_items is None or len(element_items) == 0:
            raise ValueError("No elements provided for quantification.")
        for element_item in element_items:
            try:
                shells_data = []
                y_fit = SpectrumFitting.fit_powerlaw_curve(
                    self._energy, self.selected_slice, range_values=element_item.fit_range
                )
                for ishell in element_item.shells:
                    shell_data = self.calculate_shell_data(
                        self.selected_slice, element_item, y_fit, ishell
                    )
                    shells_data.append((ishell, shell_data))
                if len(shells_data) == 2:
                    element_data.append([
                        element_item, y_fit,
                        get_envelope(
                            shells_data[0][1][0], shells_data[0][1][1],
                            shells_data[1][1][0], shells_data[1][1][1],
                        )
                    ])
                else:
                    element_data.append([element_item, y_fit, shells_data[0][1]])
            except Exception as e:
                raise e
        try:
            element_color_map = {
                str(element_item.element): colors[i % len(colors)]
                for i, element_item in enumerate(element_items)
            }
            q_list = []
            i = 0
            while i < len(element_data) - 1:
                element_item0, y_extrapolated0, element_data0 = element_data[i]
                element_item1, y_extrapolated1, element_data1 = element_data[i + 1]
                q_aux = quanti(
                    element_item0.quant_range, element_item1.quant_range,
                    element_data0, element_data1,
                    y_extrapolated0, y_extrapolated1,
                    self._energy,
                ).get_quanti()
                if not np.isfinite(float(q_aux)) or q_aux < 0:
                    raise ValueError(
                        f"Invalid quantification result ({q_aux}) for "
                        f"{element_item0.element} / {element_item1.element}. "
                        f"Check fit and quantification ranges."
                    )
                q_list.append((element_item0.element, element_item1.element, q_aux))
                i += 1
            self._update_paneB(self._build_quant_pie(q_list, element_color_map))
        except Exception as e:
            raise RuntimeError(f"Error in quantification calculation: {e}")

    def _build_quant_pie(self, q_list, element_color_map):
        """Build a pure HoloViews pie chart using polygon wedges."""
        _QUANT_COLORS = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
        _RADIUS = 1.0
        _LABEL_RADIUS = 0.67
        _N_POINTS_PER_SLICE = 90
        _PIE_SIZE = self._QUANT_PIE_SIZE

        abc_list = [1.0]
        for i in range(len(q_list)):
            abc_list.append(abc_list[i] / q_list[i][2])

        total = float(sum(abc_list))
        if total <= 0:
            raise ValueError("Quantification proportions must sum to a positive value.")

        labels = [str(q_list[i][0]) for i in range(len(abc_list) - 1)] + [str(q_list[-1][1])]
        proportions = [float(v) / total for v in abc_list]

        polygons = []
        label_data = []
        start_angle = np.pi / 2.0

        for i, (label, prop) in enumerate(zip(labels, proportions)):
            end_angle = start_angle - (2.0 * np.pi * prop)
            theta = np.linspace(end_angle, start_angle, _N_POINTS_PER_SLICE)

            xs = np.concatenate(([0.0], _RADIUS * np.cos(theta), [0.0]))
            ys = np.concatenate(([0.0], _RADIUS * np.sin(theta), [0.0]))
            color = element_color_map.get(str(label), _QUANT_COLORS[i % len(_QUANT_COLORS)])
            pct = prop * 100.0

            polygons.append({
                'xs': xs,
                'ys': ys,
                'Element': label,
                'ProportionPct': pct,
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
            vdims=['Element', 'ProportionPct', 'Color'],
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

        # Normalize the experimental and simulated data within the quantification range
        if self.quant_range_values:
            mask = (self.eaxis >= self.quant_range_values[0]) & (self.eaxis <= self.quant_range_values[1])
            mask_ = (self.eaxis_cs >= self.quant_range_values[0]) & (self.eaxis_cs <= self.quant_range_values[1])
            x_filtered = self.eaxis[mask]
            y_filtered = selected_slice[mask] - y_extrapolated[mask]
            x_filtered_ = self.eaxis_cs[mask_]
            y_filtered_ = self.cross_section[mask_]
            self.norm_exp = np.trapz(y_filtered, x_filtered).real  # Experimental normalization
            self.norm_sim = np.trapz(y_filtered_, x_filtered_).real  # Simulated normalization
        else:
            self.norm_sim = np.trapz(self.cross_section, self.eaxis).real
            self.norm_exp = np.trapz(selected_slice - y_extrapolated, self.eaxis).real

        # Apply the chemical shift and calculate the normalized cross-section
        self.xaxis = self.eaxis_cs - self.chemical_shift
        self.yaxis = (self.cross_section / self.norm_sim * self.norm_exp).real

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

class quanti:
    """
    Class to calculate quantification between two regions.
    """
    def __init__(self, d_a, d_b, cs_a, cs_b, y1, y2, eaxis):
        """
        Initializes the quanti object.

        Parameters:
            d_a, d_b: Energy ranges for the two regions.
            cs_a, cs_b: Cross-section data for the two regions.
            y1, y2: Experimental data for the two regions.
            eaxis: The energy axis.
        """
        self.y1 = y1
        self.y2 = y2
        self.d_a = d_a
        self.d_b = d_b
        self.cs_b_x, self.cs_b_y = cs_b
        self.cs_a_x, self.cs_a_y = cs_a
        self.eaxis = eaxis

    def get_part_delta(self, y, axis, delta):
        """
        Calculates the integral of a portion of the data within a specified range.

        Parameters:
            y: The data to integrate.
            axis: The corresponding axis.
            delta: The range for integration.

        Returns:
            The integral value.
        """
        mask = (axis >= delta[0]) & (axis <= delta[1])
        return np.trapz(y[mask], axis[mask]).real

    def get_quanti(self):
        """
        Calculates the quantification ratio between two regions.

        Returns:
            The quantification ratio (q_ab).
        """
        i_a = self.get_part_delta(self.y1, self.eaxis, self.d_a)
        i_b = self.get_part_delta(self.y2, self.eaxis, self.d_b)
        cs_a = self.get_part_delta(self.cs_a_y, self.cs_a_x, self.d_a)
        cs_b = self.get_part_delta(self.cs_b_y, self.cs_b_x, self.d_b)
        self.q_ab = i_a / i_b * cs_b / cs_a
        return self.q_ab

def get_envelope(x1, y1, x2, y2):
    """
    Calculates the envelope of two curves.

    Parameters:
        x1, y1: The x and y values of the first curve.
        x2, y2: The x and y values of the second curve.

    Returns:
        x_common: The common x values.
        y_envelope: The envelope (maximum y values at each x).
    """
    # Find the common x range
    x_common = np.union1d(x1, x2)

    # Interpolate y values for the common x points
    y1_interp = np.interp(x_common, x1, y1)
    y2_interp = np.interp(x_common, x2, y2)

    # Calculate the envelope by taking the maximum at each point
    y_envelope = np.maximum(y1_interp, y2_interp)
    return x_common, y_envelope
