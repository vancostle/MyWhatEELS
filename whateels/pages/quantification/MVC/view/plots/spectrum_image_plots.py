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
    - Quantification bar chart (replaces Plotly pie).
    """

    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

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

        # Quantification state
        self.selected_slice = None
        self.element_quant_data = []

        # Base __init__ sets up HoloViews heatmap + spectrum panes and wires streams
        super().__init__(dataset, eloss_name=model.constants.ELOSS)

        # Periodic callback for inactivity logic (stopped initially)
        self._pc = pn.state.add_periodic_callback(
            self._check_inactivity, period=250, start=False
        )

    def get_e_axis(self):
        return self._e_axis

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
        # Selection1D fires on every point while drawing the lasso.
        # Store the latest index and timestamp; _check_inactivity will process
        # it once it has been stable for _SELECTION_DEBOUNCE_MS.
        self._pending_selection_index = index
        self._pending_selection_ts = self._now_ms()
        if self._pc and not self._pc.running:
            self._pc.start()

    def _process_selection(self, index=None):
        app_state = CacheManager.get_cached_app_state()
        if not index:
            pairs = []
        else:
            pairs = list(dict.fromkeys(
                (idx // self._nx, idx % self._nx) for idx in index
            ))
        self._region_pairs = pairs
        if not pairs:
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                self._update_paneB(self._figB_hover(self._last_hover_point))
            return
        if app_state.quantification_elements:
            self.plot_quantification_elements(app_state.quantification_elements)
        else:
            self._show_spectrum(region_pairs=pairs)
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None

    # --- Quantification overlays ---

    def plot_quantification_elements(self, element_items: list):
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
        if res is None:
            return
        spec, n_points = res
        self.selected_slice = spec

        base_curve = hv.Curve(
            (self._energy, spec), kdims=['x'], vdims=['y'], label='Spectrum',
        ).opts(
            color='black', line_width=1.5,
            title=f"ROI — sum (points={n_points})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True, shared_axes=False, framewise=True,
        )
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
            y_fit = SpectrumFitting.fit_powerlaw_curve(
                self._energy, self.selected_slice, range_values=element_item.fit_range
            )
            if y_fit is not None:
                curves.append(hv.Curve(
                    (self._energy, y_fit), kdims=['x'], vdims=['y'],
                    label=f'{element_item.element} PowerLaw Fit',
                ).opts(color=color, line_width=1.5))
                bg_sub = self.selected_slice - y_fit
                curves.append(hv.Area(
                    (self._energy, bg_sub), kdims=['x'], vdims=['y'],
                    label=f'{element_item.element} BG Subtraction',
                ).opts(color=color, alpha=0.3, line_color=color, line_alpha=0.6))
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
                    eaxis=self._energy, eaxis_cs=eaxis_cs,
                    counts=counts, onset=onset, cross_section=cross_section,
                )
                xaxis, yaxis = cs_instance.get_data()
                curves.append(hv.Curve(
                    (xaxis, yaxis), kdims=['x'], vdims=['y'],
                    label=f'{element_item.element} {ishell} OOS',
                ).opts(line_width=1.5))
        except Exception:
            pass
        return curves

    def calculate_shell_data(self, selected_slice, element_item, y_extrapolated, ishell):
        eaxis = element_item.cross_sections[ishell][0]
        counts = element_item.cross_sections[ishell][1]
        onset = element_item.cross_sections[ishell][2]
        cross_section = element_item.cross_sections[ishell][3]
        cs_instance = add_cs(
            element=element_item.element, ishell=ishell,
            selected_slice=selected_slice, y_extrapolated=y_extrapolated,
            chemical_shift=element_item.chemical_shift,
            quant_range_values=element_item.quant_range,
            eaxis=self._energy, eaxis_cs=eaxis,
            counts=counts, onset=onset, cross_section=cross_section,
        )
        return cs_instance.get_data()

    def plot_quantification_pie(self, element_items):
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
                if q_aux < 0:
                    return (
                        f" | Quantification result: Negative value for "
                        f"{element_item0.element} / {element_item1.element}, check ranges."
                    )
                q_list.append((element_item0.element, element_item1.element, q_aux))
                i += 1
            print(f" | Quantification result: {q_list}")
            self._update_paneB(self._build_quant_bars(q_list))
        except Exception as e:
            print(f"Error in quantification calculation: {e}")

    def _build_quant_bars(self, q_list):
        """Build an hv.Bars chart from quantification ratios (replaces Plotly pie)."""
        abc_list = [1.0]
        for i in range(len(q_list)):
            abc_list.append(abc_list[i] / q_list[i][2])
        total = sum(abc_list)
        labels = [q_list[i][0] for i in range(len(abc_list) - 1)] + [q_list[-1][1]]
        proportions = [v / total for v in abc_list]
        return hv.Bars(
            list(zip(labels, proportions)), kdims=['Element'], vdims=['Proportion'],
        ).opts(
            title='Quantification',
            xlabel='Element', ylabel='Proportion',
            responsive=True, shared_axes=False, framewise=True,
        )

    # --- Cleanup ---

    @override
    def cleanup(self):
        self._pending_selection_index = None
        self._pending_selection_ts = None
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
