import panel as pn
import time
import threading
import os
import numpy as np
import holoviews as hv
import lmfit
import xarray as xr
from scipy.ndimage import median_filter
from bokeh.events import Reset
from bokeh.models import Range1d

from whateels.helpers import SpectrumExtractor
from whateels.helpers.fitting.multifitting import MultiFit
from whateels.components import SplitJs, SimpleDetails, ToggleButton, ProgressDisplay
from whateels.pages.home.utils.plot_helpers import (
    get_range_slider_value, apply_fitting, get_pixel_spectrum, start_pc, stop_pc
)
from whateels.state import CacheManager
from whateels.base.plots.base_spectrum_image_plot import BaseSpectrumImagePlot
from holoviews import streams as hv_streams

from typing import TYPE_CHECKING, override
if TYPE_CHECKING:
    from ...model import HomePageModel
    from xarray import Dataset

class SpectrumImagePlot(BaseSpectrumImagePlot):
    """
    Visualizador de Spectrum Image usando HoloViews + Panel (backend Bokeh).
    Extiende BaseSpectrumImagePlot para lógica compartida.
    """

    # Panel sizing modes
    _STRETCH_WIDTH = "stretch_width"

    # Axis titles for spectrum plot
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "HomePageModel", dataset: "Dataset"):
        self._model = model

        # Homepage-specific state — must be set before super().__init__ triggers _setup_callbacks
        self._INACTIVITY_MS = 700
        self._HOVER_DEBOUNCE_MS = 20  # 20 ms prevents event-queue pileup in the frozen exe while remaining imperceptible
        self._fitting_active = False
        self._last_hover_ts = None
        self._last_hover_render_ts = None  # tracks last time hover actually triggered a render
        self._last_rendered_pixel: tuple[int, int] | None = None  # pixel-level dedup: skip if same (i,j)
        self._pc = None
        self._paneB_reset_stream = None
        self._paneB_range_pc = None
        self._paneB_attached_model_id = None
        self._paneB_reset_baseline_dirty = True  # sync reset baseline on first render and after axis changes
        self._paneB_reset_baseline_pending = False  # True while a next_tick_callback is already queued
        self._paneB_range_cb_pending = False  # True while ensure_paneB_range_callbacks is already queued

        # Widget placeholders (filled by _setup_widgets, called after super)
        self._range_slider = pn.widgets.EditableRangeSlider()
        self._range_slider_watcher = None
        self._fitting_switch = pn.widgets.Switch()
        self._fitting_switch_watcher = None

        self._spike_threshold_slider = pn.widgets.FloatSlider()
        self._spike_threshold_slider_watcher = None
        self._spike_threshold = 5.0
        self._spike_window_slider = pn.widgets.IntSlider()
        self._spike_window_slider_watcher = None
        self._spike_window = 11
        
        self._multifitting_switch = pn.widgets.Switch()
        self._multifitting_switch_watcher = None

        self._cut_range_min_input = pn.widgets.FloatInput()
        self._cut_range_max_input = pn.widgets.FloatInput()
        self._cut_range_reset_button = pn.widgets.Button()
        self._apply_cut_range_button = ToggleButton()
        self._cut_range_active = False
        self._cut_range_preprocessed_electron_count = None
        self._applied_cut_range: tuple[float, float] | None = None

        self._preprocessors_applied = False
        self._applied_spike_threshold: float | None = None
        self._applied_spike_window: int | None = None
        self._preprocessed_source: str | None = None
        self._apply_remove_spikes_button = ToggleButton()
        self._apply_multifitting_button = ToggleButton()
        self._preprocessed_electron_count = None
        self._multifit_previous_electron_count = None
        self._multifit_previous_source: str | None = None
        self._multifit_input_had_spikes = False
        self._despiked_cube = None
        self._despike_cache_signature = None
        self._multifit_cube = None
        self._multifit_cache_signature = None
        self._raw_paneA_base_overlay = None
        self._progress_display: ProgressDisplay = ProgressDisplay(name="Preprocessing")
        self._main_ref = None
        self._plots_tab_ref = None
        self._debug_paneB_ranges = False
        self._debug_paneB_reset = True
        self._paneB_range_mode = "autorange"
        self._reset_in_progress = False  # Flag to prevent callback freeze during reset
        self._reset_finalize_attempts = 0

        # Numpy cache for the fast hover path — avoids xarray _as_row_col_energy conversion
        # on every mouse move. Invalidated automatically when _get_display_data() changes identity.
        self._display_numpy_cache: np.ndarray | None = None
        self._display_numpy_cache_source = None

        # super().__init__ calls _setup_plots() and _setup_callbacks() (base versions)
        super().__init__(dataset, eloss_name=self._model.constants.ELOSS)

        # Cache the initial (raw) paneA overlay to quickly restore raw view.
        self._raw_paneA_base_overlay = self._paneA_base_overlay

        # Widgets depend on _e_axis set by super().__init__()
        self._setup_widgets()
        
    @property
    def range_slider(self) -> pn.widgets.EditableRangeSlider:
        """Get the fit range slider widget."""
        return self._range_slider

    # --- Public Layout Builders ---

    @override
    def create_plots(self):
        left_column = pn.Column(
            self.paneA,
            self._hover_gate_widget,
            align='center',
            margin=0,
        )
        right_column = pn.Column(
            self.paneB,
            align='center',
            margin=0
        )
        return SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )

    # --- Widget Setup ---
    def _setup_widgets(self):
        self._range_slider = pn.widgets.EditableRangeSlider(
            name="",
            start=float(self._e_axis[0]) if len(self._e_axis) > 0 else 0.0,
            end=float(self._e_axis[-1]) if len(self._e_axis) > 0 else 1.0,
            value=(float(self._e_axis[0]), float(self._e_axis[-1])),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["my-range"],
            disabled=True,
        )
        
        self._range_slider_container = pn.Column(
            self._range_slider,
            margin=0,
            styles={'padding': '0px'},
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._range_slider_watcher = self._range_slider.param.watch(self._on_range_changed, 'value')
        self._fitting_switch = pn.widgets.Switch(
            name="Fitting",
            value=False,
            css_classes=["background-switch"],
            styles={'height': '30px', 'max-height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center', 'margin': '0px'}
        )
        self._fitting_switch_watcher = self._fitting_switch.param.watch(
            self._on_fitting_switch_changed, 'value'
        )
        self._spike_threshold_slider = pn.widgets.FloatSlider(
            name="Spike Threshold",
            start=0.1,
            end=20.0,
            step=0.1,
            value=self._spike_threshold,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._spike_threshold_slider_watcher = self._spike_threshold_slider.param.watch(self._on_spike_threshold_changed, 'value')
        self._spike_threshold = 5.0

        self._spike_window_slider = pn.widgets.IntSlider(
            name="Spike Window",
            start=3,
            end=51,
            step=2,
            value=self._spike_window,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._spike_window_slider_watcher = self._spike_window_slider.param.watch(self._on_spike_window_changed, 'value')
        
        self._multifitting_switch = pn.widgets.Switch(
            name="Multifitting",
            value=False,
            css_classes=["background-switch"],
            styles={'height': '30px', 'max-height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center', 'margin': '0px'}
        )
        
        self._multifitting_switch_watcher = self._multifitting_switch.param.watch(
            self._on_multifitting_switch_changed, 'value'
        )

        default_min_eloss = float(np.min(self._e_axis)) if len(self._e_axis) > 0 else 0.0
        default_max_eloss = float(np.max(self._e_axis)) if len(self._e_axis) > 0 else 1.0

        self._cut_range_min_input = pn.widgets.FloatInput(
            name="Min Eloss",
            value=default_min_eloss,
            step=0.1,
            start=default_min_eloss,
            end=default_max_eloss,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._cut_range_max_input = pn.widgets.FloatInput(
            name="Max Eloss",
            value=default_max_eloss,
            step=0.1,
            start=default_min_eloss,
            end=default_max_eloss,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._cut_range_reset_button = pn.widgets.Button(
            name="Reset Eloss Range",
            button_type="warning",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )
        self._cut_range_reset_button.on_click(self._on_reset_cut_range)

        self._apply_cut_range_button = ToggleButton(
            initial_state=False,
            states={
                "on": {"label": 'Revert Cut Range', "on_click": self._on_revert_cut_range, "button_type": 'warning'},
                "off": {"label": 'Apply Cut Range', "on_click": self._on_apply_cut_range, "button_type": 'success'},
            },
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )

        self._apply_remove_spikes_button = ToggleButton(
            initial_state=False,
            states={
                "on": {"label": 'Revert Remove Spikes', "on_click": self._on_revert_remove_spikes, "button_type": 'warning'},
                "off": {"label": 'Apply Remove Spikes', "on_click": self._on_apply_remove_spikes, "button_type": 'success'},
            },
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )

        self._apply_multifitting_button = ToggleButton(
            initial_state=False,
            states={
                "on": {"label": 'Revert Multifitting', "on_click": self._on_revert_multifitting, "button_type": 'warning'},
                "off": {"label": 'Apply Multifitting', "on_click": self._on_apply_multifitting, "button_type": 'success'},
            },
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )

    # --- Fitting Details SimpleDetails builder ---
    def create_fitting_details(self) -> SimpleDetails:
        """Build and return the multifitting SimpleDetails block for the sidebar."""
        fitting_label = pn.pane.Markdown(
            "## Fitting",
            margin=0,
            styles={
                'padding': '0px', 'height': '30px', 'display': 'flex',
                'align-items': 'center', 'justify-content': 'center'
            }
        )
        fitting_switch_container = pn.Row(
            fitting_label,
            self._fitting_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-container"],
            margin=(0, 0, 0, 0),
            styles={
                'display': 'flex', 'align-items': 'center',
                'justify-content': 'center', 'padding': '0px'
            }
        )
        return SimpleDetails(
            title="Fitting Settings",
            content=pn.Column(
                fitting_switch_container,
                self._range_slider_container,
                self._apply_multifitting_button,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 0, 0),
        )

    def create_cut_range_details(self) -> SimpleDetails:
        """Build and return the Cut Signal Range SimpleDetails block for the sidebar."""
        return SimpleDetails(
            title="Cut Signal Range Settings",
            content=pn.Column(
                self._cut_range_min_input,
                self._cut_range_max_input,
                self._cut_range_reset_button,
                self._apply_cut_range_button,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        
    def create_remove_spikes_details(self) -> SimpleDetails:
        """Build and return the Remove Spikes SimpleDetails block for the sidebar, including the Apply/Raw button as last widget."""
        threshold_slider_container = pn.Column(
            self._spike_threshold_slider,
            sizing_mode=self._STRETCH_WIDTH,
        )
        window_slider_container = pn.Column(
            self._spike_window_slider,
            sizing_mode=self._STRETCH_WIDTH,
        )
        return SimpleDetails(
            title="Remove Spikes Settings",
            content=pn.Column(
                threshold_slider_container,
                window_slider_container,
                self._apply_remove_spikes_button,
            ),
            margin=(0, 0, 8, 0),
            sizing_mode=self._STRETCH_WIDTH,
        )

    def set_view_refs(self, main, plots_tab) -> None:
        """Inject main layout and plots tab references so the plot can show progress and restore content."""
        self._main_ref = main
        self._plots_tab_ref = plots_tab

    def _get_full_eloss_bounds(self) -> tuple[float, float]:
        """Return the full available Eloss range from the current dataset."""
        if len(self._e_axis) == 0:
            return 0.0, 1.0
        return float(np.min(self._e_axis)), float(np.max(self._e_axis))

    def _normalize_cut_range_values(self) -> tuple[float, float]:
        """Return a validated and clamped (min, max) cut range."""
        full_min, full_max = self._get_full_eloss_bounds()
        try:
            min_eloss = float(self._cut_range_min_input.value)
        except Exception:
            min_eloss = full_min
        try:
            max_eloss = float(self._cut_range_max_input.value)
        except Exception:
            max_eloss = full_max

        if min_eloss > max_eloss:
            min_eloss, max_eloss = max_eloss, min_eloss

        min_eloss = max(full_min, min(full_max, min_eloss))
        max_eloss = max(full_min, min(full_max, max_eloss))

        if min_eloss > max_eloss:
            min_eloss, max_eloss = full_min, full_max

        return min_eloss, max_eloss

    def _build_cut_range_preprocessed_data(self):
        """Slice ElectronCount by the selected Eloss range and return (data, range)."""
        min_eloss, max_eloss = self._normalize_cut_range_values()
        eloss_values = np.asarray(self._electron_count_data.coords[self._eloss_name].values)
        if eloss_values.size == 0:
            raise ValueError("Eloss axis is empty.")

        ascending_eloss = bool(eloss_values[0] <= eloss_values[-1])
        eloss_slice = slice(min_eloss, max_eloss) if ascending_eloss else slice(max_eloss, min_eloss)
        cut_data = self._electron_count_data.sel({self._eloss_name: eloss_slice})

        if cut_data.shape[-1] == 0:
            raise ValueError("Selected cut range produced no Eloss samples.")

        return cut_data, (min_eloss, max_eloss)

    def _on_reset_cut_range(self, _=None):
        """Reset cut range widgets to the full available Eloss bounds."""
        full_min, full_max = self._get_full_eloss_bounds()
        self._cut_range_min_input.value = full_min
        self._cut_range_max_input.value = full_max

    def _sync_range_slider_to_energy_axis(self, energy_axis, reset_value: bool = False):
        """Clamp fitting slider bounds/value to the provided energy axis."""
        axis = np.asarray(energy_axis, dtype=float)
        axis = axis[np.isfinite(axis)]
        if axis.size == 0:
            return

        axis_min = float(np.min(axis))
        axis_max = float(np.max(axis))

        current_range = get_range_slider_value(self._range_slider)
        current_min = float(min(current_range[0], current_range[1]))
        current_max = float(max(current_range[0], current_range[1]))

        if reset_value:
            new_min, new_max = axis_min, axis_max
        else:
            new_min = max(axis_min, min(axis_max, current_min))
            new_max = max(axis_min, min(axis_max, current_max))
            if new_min > new_max:
                new_min, new_max = axis_min, axis_max

        self._range_slider.start = axis_min
        self._range_slider.end = axis_max
        self._range_slider.value = (new_min, new_max)
        # Energy axis changed — reset baseline must be resynced on next render.
        self._paneB_reset_baseline_dirty = True

    def _get_clipped_fit_range(self, energy_axis, update_slider: bool = False) -> tuple[float, float]:
        """Return fit range clipped to the provided energy axis bounds."""
        axis = np.asarray(energy_axis, dtype=float)
        axis = axis[np.isfinite(axis)]
        if axis.size == 0:
            return (0.0, 1.0)

        axis_min = float(np.min(axis))
        axis_max = float(np.max(axis))

        fit_range = get_range_slider_value(self._range_slider)
        fit_min = float(min(fit_range[0], fit_range[1]))
        fit_max = float(max(fit_range[0], fit_range[1]))

        clipped_min = max(axis_min, min(axis_max, fit_min))
        clipped_max = max(axis_min, min(axis_max, fit_max))
        if clipped_min > clipped_max:
            clipped_min, clipped_max = axis_min, axis_max

        if update_slider:
            self._range_slider.value = (clipped_min, clipped_max)

        return (clipped_min, clipped_max)

    def _clear_cut_range_state(self, clear_preprocessed_payload: bool = False):
        """Clear in-memory Cut Range state and optionally clear active preprocessed payload."""
        self._cut_range_active = False
        self._cut_range_preprocessed_electron_count = None
        self._applied_cut_range = None
        if clear_preprocessed_payload and self._preprocessed_source == 'cut_range':
            self._preprocessed_electron_count = None
            self._preprocessed_source = None
            self._preprocessors_applied = False

    def _on_apply_cut_range(self):
        """Apply cut range and refresh Home plots with the selected Eloss window."""
        # Cut Range supersedes any currently applied preprocessor output.
        if self._apply_multifitting_button.is_on():
            self._apply_multifitting_button.toggle()
        self._multifitting_switch.value = False
        self._multifit_input_had_spikes = False
        self._multifit_previous_electron_count = None
        self._multifit_previous_source = None

        if self._apply_remove_spikes_button.is_on():
            self._apply_remove_spikes_button.toggle()

        try:
            cut_data, normalized_range = self._build_cut_range_preprocessed_data()
        except Exception as e:
            pn.state.notifications.error(f"Failed to apply Cut Range: {e}", duration=5000) # type: ignore
            # Keep button in OFF state after ToggleButton internal toggle executes.
            self._apply_cut_range_button.toggle()
            return

        self._cut_range_preprocessed_electron_count = cut_data
        self._applied_cut_range = normalized_range
        self._cut_range_active = True
        self._preprocessed_electron_count = cut_data
        self._preprocessed_source = 'cut_range'
        self._preprocessors_applied = True
        CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": cut_data})
        self._sync_range_slider_to_energy_axis(np.asarray(cut_data.coords[self._eloss_name].values), reset_value=False)
        self._current_y_range = None
        self._current_y_autorange = True
        self._apply_sidebar_apply_locks()
        self._refresh_paneA()
        self._refresh_paneB()
        pn.state.notifications.success(
            f"Cut Range applied: Eloss [{normalized_range[0]:.3f}, {normalized_range[1]:.3f}]",
            duration=4000,
        ) # type: ignore

    def _on_revert_cut_range(self):
        """Revert cut range and restore Home plots to raw data."""
        app_state = CacheManager.get_cached_app_state()
        if (
            app_state.preprocessed_plot_dataset is not None
            and app_state.preprocessed_plot_dataset["ElectronCount"] is self._cut_range_preprocessed_electron_count
        ):
            app_state.clear_preprocessed_plot_dataset()

        self._clear_cut_range_state(clear_preprocessed_payload=True)
        self._sync_range_slider_to_energy_axis(np.asarray(self._e_axis), reset_value=False)
        self._current_y_range = None
        self._current_y_autorange = True
        self._enable_sidebar_widgets()
        self._refresh_paneA()
        self._refresh_paneB()
        pn.state.notifications.info(
            "Cut Range reverted. Raw data is now active for downstream pages.",
            duration=3500,
        ) # type: ignore

    def _normalize_spike_window(self, window: int, n_points: int) -> int:
        """Return a valid odd window in [3, n_points] for MAD-based despiking."""
        if n_points < 3:
            return 0
        w = int(window)
        if w < 3:
            w = 3
        if w % 2 == 0:
            w += 1
        if w > n_points:
            w = n_points if n_points % 2 == 1 else n_points - 1
        return max(0, w)

    def _remove_spikes_interpolated(self, spectrum, threshold=2.0, window=11, return_mask=False):
        """
        MAD-based spike detection with linear interpolation over non-spike points.
        Only spike-marked samples are modified.
        """
        if spectrum is None:
            if return_mask:
                return spectrum, np.array([], dtype=bool)
            return spectrum

        spec = np.asarray(spectrum, dtype=float)
        n = spec.size
        if n == 0:
            if return_mask:
                return spec, np.array([], dtype=bool)
            return spec

        w = self._normalize_spike_window(window, n)
        if w < 3:
            if return_mask:
                return spec.copy(), np.zeros(n, dtype=bool)
            return spec.copy()

        rolling_median = median_filter(spec, size=w, mode='nearest')
        abs_dev = np.abs(spec - rolling_median)
        mad = median_filter(abs_dev, size=w, mode='nearest')
        spike_mask = np.isfinite(spec) & (mad > 1e-12) & (abs_dev > threshold * mad)

        filtered = spec.copy()
        if np.any(spike_mask):
            good_mask = (~spike_mask) & np.isfinite(spec)
            good_points = np.where(good_mask)[0]
            if good_points.size > 1:
                spike_points = np.where(spike_mask)[0]
                filtered[spike_mask] = np.interp(spike_points, good_points, spec[good_mask])
            elif good_points.size == 1:
                filtered[spike_mask] = spec[good_points[0]]

        if return_mask:
            return filtered, spike_mask
        return filtered

    def _remove_spikes(self, spectrum, threshold=None, window=None):
        """Backward-compatible wrapper for interpolated despiking."""
        if threshold is None:
            threshold = self._spike_threshold
        if window is None:
            window = self._spike_window
        return self._remove_spikes_interpolated(
            spectrum,
            threshold=threshold,
            window=window,
            return_mask=False,
        )

    # Home keeps its own curve builder because the displayed Eloss axis can change
    # after preprocessors like Cut Range. BaseSpectrumImagePlot builds curves with
    # self._energy from the original dataset, which can mismatch the active spectrum
    # length and break paneB rendering when fitting toggles/reseeds.
    def _build_spectrum_curve(self, spec, title):
        """Build an hv.Curve from a pre-processed 1D spectrum array (no further transformation)."""
        spec_arr = np.asarray(spec)
        energy_axis = self._get_display_energy_axis()
        if energy_axis.shape[0] != spec_arr.shape[0]:
            energy_axis = np.arange(spec_arr.shape[0], dtype=float)
        return hv.Curve((energy_axis, spec_arr), kdims=['x'], vdims=['y']).opts(
            color='black', line_width=1.5, alpha = 0.7,
            title=title,
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True, shared_axes=False, framewise=True,
            axiswise=False,
        )

    def _build_spike_removed_curve(self, spec, title):
        """Rebuild an hv.Curve with spike-filtered spectrum, preserving the title."""
        filtered = self._remove_spikes(spec)
        return self._build_spectrum_curve(filtered, title)

    @override
    def _figB_hover(self, point):
        """Build hover spectrum using the cached numpy array."""
        if not point:
            point = {"x": 0, "y": 0}
        i, j = round(point["y"]), round(point["x"])
        try:
            spec = self._get_display_numpy()[i, j, :].astype(float)
        except Exception:
            spec = SpectrumExtractor.get_spectrum_from_pixel(self._get_display_data(), i, j)
        return self._build_spectrum_curve(spec, f"Pixel (x={j}, y={i})")

    @override
    def _figB_region(self, pairs):
        """Build region spectrum using the active display energy axis."""
        res = self._get_spectrum_from_indices_fast(pairs)
        if res is None:
            return self._figB_hover({"x": 0, "y": 0})
        spec, n_points = res
        return self._build_spectrum_curve(spec, f"ROI — sum (points={n_points})")

    def _get_display_data(self):
        """Return the electron count data cube to use for spectrum display.
        Returns the precomputed preprocessed cube when preprocessors have been applied."""
        if self._preprocessors_applied and self._preprocessed_electron_count is not None:
            return self._preprocessed_electron_count
        return self._electron_count_data

    def _get_display_numpy(self) -> np.ndarray:
        """Return a cached (row, col, energy) numpy array for the current display data.

        Avoids calling SpectrumExtractor._as_row_col_energy (which does xarray .values
        + dim-order inspection) on every hover event. The cache is invalidated automatically
        when the underlying data source changes (preprocessors applied/reverted).
        """
        display_data = self._get_display_data()
        if self._display_numpy_cache is None or self._display_numpy_cache_source is not display_data:
            self._display_numpy_cache = SpectrumExtractor._as_row_col_energy(display_data)
            self._display_numpy_cache_source = display_data
        return self._display_numpy_cache

    def _get_display_energy_axis(self) -> np.ndarray:
        """Return the Eloss axis associated with the currently displayed data cube."""
        try:
            display_data = self._get_display_data()
            energy_axis = np.asarray(display_data.coords[self._eloss_name].values)
            if energy_axis.size > 0:
                return energy_axis
        except Exception:
            pass
        return np.asarray(self._energy)

    def _set_paneB_autorange_state(self):
        """Put paneB into its clean autorange state."""
        self._paneB_range_mode = "autorange"
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = True
        self._current_y_autorange = True

    def _set_paneB_frozen_state(self, x_range=None, y_range=None):
        """Freeze paneB to the latest valid Bokeh ranges."""
        self._paneB_range_mode = "frozen"
        if self._is_valid_range(x_range):
            self._current_x_range = x_range
            self._current_x_autorange = False
        if self._is_valid_range(y_range):
            self._current_y_range = y_range
            self._current_y_autorange = False

    def _get_live_paneB_bokeh_plot(self):
        """Return the live bokeh figure for paneB, if it exists."""
        try:
            models = getattr(self.paneB, '_models', {}) if self.paneB is not None else {}
            model_tuple = next(iter(models.values()), None) if models else None
            if model_tuple:
                return model_tuple[0]
        except Exception:
            pass
        return None

    def _apply_paneB_reset_to_live_model(self):
        """Force the live paneB bokeh model back to full X bounds and Y autorange."""
        bokeh_plot = self._get_live_paneB_bokeh_plot()
        if bokeh_plot is None:
            return False

        axis = np.asarray(self._get_display_energy_axis(), dtype=float)
        axis = axis[np.isfinite(axis)]
        if axis.size == 0:
            return False

        full_x_min = float(np.min(axis))
        full_x_max = float(np.max(axis))

        try:
            if isinstance(bokeh_plot.x_range, Range1d):
                bokeh_plot.x_range.start = full_x_min
                bokeh_plot.x_range.end = full_x_max
                bokeh_plot.x_range.reset_start = full_x_min
                bokeh_plot.x_range.reset_end = full_x_max
            else:
                bokeh_plot.x_range = Range1d(
                    start=full_x_min,
                    end=full_x_max,
                    reset_start=full_x_min,
                    reset_end=full_x_max,
                )
            y_start = getattr(bokeh_plot.y_range, 'start', None)
            y_end = getattr(bokeh_plot.y_range, 'end', None)
            y_ready = (
                y_start is not None and y_end is not None and np.isfinite(y_start) and np.isfinite(y_end)
            )
            self._debug_paneB_reset_event(
                "live_model_reset_applied",
                x_min=full_x_min,
                x_max=full_x_max,
                y_ready=y_ready,
                y_start=y_start,
                y_end=y_end,
            )
            return bool(y_ready)
        except Exception as exc:
            self._debug_paneB_reset_event("live_model_reset_failed", error=repr(exc))
            return False

    def _sync_paneB_reset_baseline(self):
        """Pin the live paneB reset baseline to the full spectrum without changing the current view."""
        if self._reset_in_progress:
            return False

        bokeh_plot = self._get_live_paneB_bokeh_plot()
        if bokeh_plot is None:
            return False

        axis = np.asarray(self._get_display_energy_axis(), dtype=float)
        axis = axis[np.isfinite(axis)]
        if axis.size == 0:
            return False

        full_x_min = float(np.min(axis))
        full_x_max = float(np.max(axis))

        try:
            if isinstance(bokeh_plot.x_range, Range1d):
                bokeh_plot.x_range.reset_start = full_x_min
                bokeh_plot.x_range.reset_end = full_x_max
            self._debug_paneB_reset_event(
                "reset_baseline_synced",
                x_min=full_x_min,
                x_max=full_x_max,
            )
            return True
        except Exception as exc:
            self._debug_paneB_reset_event("reset_baseline_sync_failed", error=repr(exc))
            return False

    def _should_apply_visual_fitting(self) -> bool:
        """Return True only when paneB should draw interactive fitting overlays."""
        if not self._fitting_active:
            return False
        # When multifitting output is being displayed, avoid adding a second fitting overlay.
        if self._preprocessors_applied and self._preprocessed_source == 'multifit':
            return False
        return True

    def _show_spectrum(self, *, point=None, region_pairs=None):
        """
        Unified helper to extract spectrum (from point or region), apply fitting if needed, and update paneB.
        """

        fig = None
        spec = None
        title = ''
        if region_pairs is not None:
            if not region_pairs:
                # No region selected, show message or hover
                if self._last_hover_point is not None:
                    self._show_spectrum(point=self._last_hover_point)
                return
            res = SpectrumExtractor.get_spectrum_from_indices(self._get_display_data(), region_pairs)
            if res is not None:
                spec, n_points = res
                title = f"ROI — sum (points={n_points})"
            if (self._preprocessors_applied or self._fitting_active) and spec is not None:
                fig = self._build_spectrum_curve(spec, title)
                if self._should_apply_visual_fitting():
                    energy_axis = self._get_display_energy_axis()
                    try:
                        fig = apply_fitting(fig, energy_axis, spec, self._range_slider)
                    except Exception:
                        pass
            else:
                fig = self._figB_region(region_pairs)
        elif point is not None:
            i, j = round(point['y']), round(point['x'])
            title = f"Pixel (x={j}, y={i})"
            # Use cached numpy array — avoids xarray conversion and eliminates the
            # previous double-extraction (spec was computed then discarded for _figB_hover).
            try:
                spec = self._get_display_numpy()[i, j, :].astype(float)
            except Exception:
                spec = get_pixel_spectrum(self._get_display_data(), point)
            fig = self._build_spectrum_curve(spec, title)
            if (self._preprocessors_applied or self._fitting_active) and self._should_apply_visual_fitting():
                energy_axis = self._get_display_energy_axis()
                try:
                    fig = apply_fitting(fig, energy_axis, spec, self._range_slider)
                except Exception:
                    pass
        self._update_paneB(fig)

    # --- Helper methods now imported from utils/plot_helpers.py ---
    def _refresh_paneB(self):
        """
        Unified logic to update paneB with the current region or hover point, applying fitting if active.
        """

        apply_preprocessors = self._preprocessors_applied or self._fitting_active

        if self._region_pairs:
            spec = None
            n_points = 0
            if apply_preprocessors:
                res = SpectrumExtractor.get_spectrum_from_indices(self._get_display_data(), self._region_pairs)
                if res is not None:
                    spec, n_points = res
                if spec is not None:
                    fig = self._build_spectrum_curve(spec, f"ROI — sum (points={n_points})")
                    if self._should_apply_visual_fitting():
                        energy_axis = self._get_display_energy_axis()
                        try:
                            fig = apply_fitting(fig, energy_axis, spec, self._range_slider)
                        except Exception:
                            pass
                else:
                    fig = self._figB_region(self._region_pairs)
            else:
                fig = self._figB_region(self._region_pairs)
            self._update_paneB(fig)
            return

        if self._last_hover_point is not None:
            point = self._last_hover_point
            i, j = round(point['y']), round(point['x'])
            if apply_preprocessors:
                spec = get_pixel_spectrum(self._get_display_data(), point)
                if spec is not None:
                    fig = self._build_spectrum_curve(spec, f"Pixel (x={j}, y={i})")
                    if self._should_apply_visual_fitting():
                        energy_axis = self._get_display_energy_axis()
                        try:
                            fig = apply_fitting(fig, energy_axis, spec, self._range_slider)
                        except Exception:
                            pass
                else:
                    fig = self._figB_hover(point)
            else:
                fig = self._figB_hover(point)
            self._update_paneB(fig)
            return

        # No hover yet — use default pixel (0, 0)
        default_point = {"x": 0, "y": 0}
        if apply_preprocessors:
            spec = get_pixel_spectrum(self._get_display_data(), default_point)
            if spec is not None:
                fig = self._build_spectrum_curve(spec, "Pixel (x=0, y=0)")
                if self._should_apply_visual_fitting():
                    energy_axis = self._get_display_energy_axis()
                    try:
                        fig = apply_fitting(fig, energy_axis, spec, self._range_slider)
                    except Exception:
                        pass
            else:
                fig = self._figB_hover(default_point)
        else:
            fig = self._figB_hover(default_point)
        self._update_paneB(fig)
        
    def _update_paneB(self, fig):
        if self._paneB_pipe is not None:
            # Always send an hv.Overlay so the DynamicMap type stays consistent
            # (mixing plain Curve and Overlay causes an AssertionError in the cache).
            if fig is not None and not isinstance(fig, hv.Overlay):
                fig = hv.Overlay([fig])
            self._debug_paneB_state("update_paneB_before_send")
            # Push the new element through the pipe — Bokeh updates data in-place
            # without rebuilding the whole model tree, avoiding the stale-reference warning.
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))
            # Keep the live Bokeh reset baseline pinned to the full spectrum, but only
            # schedule once — not on every hover frame.
            if getattr(self, '_paneB_reset_baseline_dirty', True) and not getattr(self, '_paneB_reset_baseline_pending', False):
                try:
                    doc = pn.state.curdoc
                    if doc is not None:
                        self._paneB_reset_baseline_pending = True
                        def _sync_and_clear():
                            self._sync_paneB_reset_baseline()
                            self._paneB_reset_baseline_dirty = False
                            self._paneB_reset_baseline_pending = False
                        doc.add_next_tick_callback(_sync_and_clear)
                except Exception:
                    pass
            # Only attach range callbacks when the model is new or was reset,
            # and only schedule the callback once, not on every hover frame.
            if self._paneB_attached_model_id is None and not getattr(self, '_paneB_range_cb_pending', False):
                try:
                    doc = pn.state.curdoc
                    if doc is not None:
                        self._paneB_range_cb_pending = True
                        def _ensure_and_clear():
                            self._ensure_paneB_range_callbacks()
                            self._paneB_range_cb_pending = False
                        doc.add_next_tick_callback(_ensure_and_clear)
                except Exception:
                    pass

    @override
    def _set_ranges_and_convert(self, fig):
        """Apply stored paneB ranges using base conversion behavior."""
        if getattr(self, "_paneB_range_mode", "autorange") != "frozen":
            return fig
        return super()._set_ranges_and_convert(fig)

    def _rewire_paneB_reset_stream(self):
        """Wire PlotReset stream to clear persisted paneB ranges on toolbar reset."""
        if self._paneB_reset_stream is not None:
            try:
                self._paneB_reset_stream.remove_subscriber(self._on_paneB_plot_reset)
            except Exception:
                pass
            try:
                self._paneB_reset_stream.clear()
            except Exception:
                pass
            self._paneB_reset_stream = None

        plot_reset_stream_cls = getattr(hv_streams, 'PlotReset', None)
        if plot_reset_stream_cls is None:
            return

        try:
            self._paneB_reset_stream = plot_reset_stream_cls(source=self._paneB_dmap)
            self._paneB_reset_stream.add_subscriber(self._on_paneB_plot_reset)
        except Exception:
            self._paneB_reset_stream = None

    def _ensure_paneB_range_callbacks(self):
        """Attach Bokeh range callbacks to the live paneB figure once it exists."""
        self._debug_paneB_state(
            "ensure_attempt",
            has_paneB=self.paneB is not None,
            models_count=len(getattr(self.paneB, '_models', {}) or {}) if self.paneB is not None else 0,
        )
        if self.paneB is None:
            return

        models = getattr(self.paneB, '_models', None)
        self._debug_paneB_state("ensure_models", models_type=type(models).__name__ if models is not None else None)
        if not models:
            return

        model_tuple = next(iter(models.values()), None)
        self._debug_paneB_state(
            "ensure_model_tuple",
            model_tuple_type=type(model_tuple).__name__ if model_tuple is not None else None,
            model_tuple_len=len(model_tuple) if hasattr(model_tuple, '__len__') else None,
        )
        if not model_tuple:
            return

        try:
            bokeh_plot = model_tuple[0]
        except Exception:
            self._debug_paneB_state("ensure_model_tuple_failed")
            return

        model_id = getattr(bokeh_plot, 'id', None)
        self._debug_paneB_state(
            "ensure_bokeh_plot",
            bokeh_plot_type=type(bokeh_plot).__name__,
            model_id=model_id,
            already_attached=self._paneB_attached_model_id,
        )
        if model_id is None:
            return

        if self._paneB_attached_model_id == model_id:
            return

        try:
            self._debug_paneB_state("ensure_before_callbacks")

            # Force toolbar Reset in paneB to always return to full X domain.
            full_axis = np.asarray(self._get_display_energy_axis(), dtype=float)
            full_axis = full_axis[np.isfinite(full_axis)]
            if full_axis.size > 0:
                full_x_min = float(np.min(full_axis))
                full_x_max = float(np.max(full_axis))
                if isinstance(bokeh_plot.x_range, Range1d):
                    bokeh_plot.x_range.reset_start = full_x_min
                    bokeh_plot.x_range.reset_end = full_x_max
                    if bokeh_plot.x_range.start is None or bokeh_plot.x_range.end is None:
                        bokeh_plot.x_range.start = full_x_min
                        bokeh_plot.x_range.end = full_x_max
                else:
                    bokeh_plot.x_range = Range1d(
                        start=full_x_min,
                        end=full_x_max,
                        reset_start=full_x_min,
                        reset_end=full_x_max,
                    )

            def _sync_from_bokeh_ranges(attr, old, new):
                # If reset is in progress, don't freeze ranges during the transition
                if getattr(self, '_reset_in_progress', False):
                    self._debug_paneB_reset_event("sync_callback_skipped_during_reset")
                    return
                
                try:
                    x_range = (float(bokeh_plot.x_range.start), float(bokeh_plot.x_range.end))
                except Exception:
                    x_range = None
                try:
                    y_range = (float(bokeh_plot.y_range.start), float(bokeh_plot.y_range.end))
                except Exception:
                    y_range = None

                # When x reaches the full spectrum bounds and we were frozen,
                # treat that as a reset back to autorange mode.
                try:
                    axis = np.asarray(self._get_display_energy_axis(), dtype=float)
                    axis = axis[np.isfinite(axis)]
                    if axis.size > 0 and self._is_valid_range(x_range) and self._paneB_range_mode == "frozen":
                        x0 = float(np.min(axis))
                        x1 = float(np.max(axis))
                        rx0, rx1 = float(x_range[0]), float(x_range[1])
                        tol = max(1e-9, 1e-6 * max(1.0, abs(x1 - x0)))
                        if abs(rx0 - x0) <= tol and abs(rx1 - x1) <= tol:
                            self._set_paneB_autorange_state()
                            self._debug_paneB_reset_event(
                                "reset_like_range_detected",
                                x_range=x_range,
                                y_range=y_range,
                            )
                            # Some Panel/Bokeh combinations don't emit Reset events;
                            # when full-domain reset-like ranges are detected, force
                            # the full reset flow explicitly.
                            try:
                                self._on_paneB_plot_reset(source="range_detected")
                            except Exception as exc:
                                self._debug_paneB_reset_event("forced_reset_from_range_failed", error=repr(exc))
                            return
                except Exception:
                    pass

                if self._is_valid_range(x_range) or self._is_valid_range(y_range):
                    self._set_paneB_frozen_state(x_range=x_range, y_range=y_range)

                self._debug_paneB_state("bokeh_range_sync", x_range=x_range, y_range=y_range)

            bokeh_plot.x_range.on_change('start', _sync_from_bokeh_ranges)
            bokeh_plot.x_range.on_change('end', _sync_from_bokeh_ranges)
            bokeh_plot.y_range.on_change('start', _sync_from_bokeh_ranges)
            bokeh_plot.y_range.on_change('end', _sync_from_bokeh_ranges)

            def _on_bokeh_reset_event(event):
                self._debug_paneB_reset_event("bokeh_reset_event", event=type(event).__name__)
                try:
                    pn.state.notifications.info("paneB Reset capturado", duration=1200) # type: ignore
                except Exception:
                    pass
                self._on_paneB_plot_reset()

            bokeh_plot.on_event(Reset, _on_bokeh_reset_event)
            self._paneB_attached_model_id = model_id
            self._debug_paneB_state("attach_bokeh_range_callbacks", model_id=model_id)
            if self._paneB_range_pc is not None:
                try:
                    if self._paneB_range_pc.running:
                        self._paneB_range_pc.stop()
                except Exception:
                    pass
        except Exception as exc:
            self._debug_paneB_state("ensure_attach_failed", error=repr(exc))
            pass

    def _on_paneB_plot_reset(self, **_kwargs):
        """Handle paneB toolbar reset by restoring autorange state for both axes."""
        t0 = time.perf_counter()
        self._reset_in_progress = True
        self._reset_finalize_attempts = 0
        self._debug_paneB_reset_event("reset_clicked")
        self._set_paneB_autorange_state()
        self._debug_paneB_reset_event("reset_state_cleared")
        self._debug_paneB_state("plot_reset")
        # Rebuild paneB so it comes back with a clean autorange model and no stale zoom state.
        try:
            self._reset_paneB_pipe()
            self._debug_paneB_reset_event("paneB_pipe_rebuilt")
        except Exception as exc:
            self._debug_paneB_reset_event("paneB_pipe_rebuild_failed", error=repr(exc))
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        self._debug_paneB_reset_event("reset_refresh_dispatched", elapsed_ms=elapsed_ms)
        try:
            doc = pn.state.curdoc
            if doc is not None:
                def _finalize_reset():
                    self._reset_finalize_attempts += 1
                    if self._apply_paneB_reset_to_live_model():
                        self._reset_in_progress = False
                        self._log_paneB_post_reset_state()
                        self._debug_paneB_reset_event("reset_complete")
                    else:
                        # Try again on the next tick until the live y-range is ready.
                        if self._reset_finalize_attempts < 20:
                            try:
                                doc.add_next_tick_callback(_finalize_reset)
                                return
                            except Exception:
                                pass
                        # Give up rather than keep the plot locked forever.
                        self._reset_in_progress = False
                
                doc.add_next_tick_callback(_finalize_reset)
        except Exception:
            self._reset_in_progress = False

    def _log_paneB_post_reset_state(self):
        """Temporary: log live bokeh ranges right after reset render tick."""
        if not getattr(self, '_debug_paneB_reset', False):
            return
        try:
            models = getattr(self.paneB, '_models', {}) if self.paneB is not None else {}
            model_tuple = next(iter(models.values()), None) if models else None
            if not model_tuple:
                self._debug_paneB_reset_event("post_reset_no_model")
                return
            bokeh_plot = model_tuple[0]
            x_live = (float(bokeh_plot.x_range.start), float(bokeh_plot.x_range.end))
            y_live = (float(bokeh_plot.y_range.start), float(bokeh_plot.y_range.end))
            self._debug_paneB_reset_event(
                "post_reset_live_ranges",
                x_live=x_live,
                y_live=y_live,
                x_state=self._current_x_range,
                y_state=self._current_y_range,
                x_auto=self._current_x_autorange,
                y_auto=self._current_y_autorange,
                range_mode=self._paneB_range_mode,
            )
        except Exception as exc:
            self._debug_paneB_reset_event("post_reset_log_failed", error=repr(exc))

    def _debug_paneB_reset_event(self, label: str, **extra):
        """Temporary debug trace for paneB reset latency and state transitions."""
        if not getattr(self, '_debug_paneB_reset', False):
            return
        try:
            parts = [
                f"paneB_reset[{label}]",
                f"ts={round(time.perf_counter(), 6)}",
            ]
            for key, value in extra.items():
                parts.append(f"{key}={value}")
        except Exception:
            pass

    def _debug_paneB_state(self, label: str, **extra):
        """Temporary debug trace for paneB autorange/range persistence."""
        if not getattr(self, '_debug_paneB_ranges', False):
            return
        try:
            parts = [
                f"paneB[{label}]",
                f"x_range={self._current_x_range}",
                f"y_range={self._current_y_range}",
                f"x_auto={self._current_x_autorange}",
                f"y_auto={self._current_y_autorange}",
            ]
            for key, value in extra.items():
                parts.append(f"{key}={value}")
        except Exception:
            pass
            
    def _refresh_paneA(self):
        """Rebuild paneA (heatmap) using the current display data (raw or preprocessed)."""
        display_data = self._get_display_data()
        # Sum over the energy axis. np.sum() on the values directly produces
        # a small 2D result without creating a large intermediate copy.
        # Then clean NaNs on the small result (not the full 3D array).
        m_image = np.sum(display_data.values, axis=2)
        m_image = np.nan_to_num(m_image, nan=0.0, posinf=0.0, neginf=0.0)
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")
        ny, nx = m_image.shape
        self._nx = nx
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'],
            vdims=['Intensity'],
        ).opts(
            cmap='Greys_r',
            colorbar=False,
            xaxis=None,
            yaxis=None,
            invert_yaxis=True,
            aspect='equal',
            responsive=True,
            shared_axes=False,
        )
        # Overlay: heatmap + selection layer
        overlay = (img * self._selectors).opts(
            hv.opts.Overlay(responsive=True, aspect='equal', shared_axes=False)
        )
        self._paneA_base_overlay = overlay
        self._update_selection_overlay(self._region_pairs)

    def _reset_paneB_pipe(self):
        """Tear down and rebuild the Pipe + DynamicMap backing paneB.

        Required when the HoloViews element structure changes (e.g. single Curve
        Overlay → 3-element fitting Overlay and back).  Bokeh builds one renderer
        per element in the first Overlay it sees; sending a structurally different
        Overlay later leaves stale renderers and makes paneB go blank.
        Replacing the DynamicMap forces Bokeh to build a fresh model tree.
        """
        if self._rangexy_stream is not None:
            try:
                self._rangexy_stream.remove_subscriber(self._on_paneB_range_changed)
            except Exception:
                pass
            try:
                self._rangexy_stream.clear()
            except Exception:
                pass
            self._rangexy_stream = None

        self._paneB_pipe = hv_streams.Pipe(data=None)
        self._paneB_dmap = hv.DynamicMap(lambda data: data, streams=[self._paneB_pipe])
        self._paneB_attached_model_id = None
        # Reset pending-guard flags so the new model gets its callbacks attached.
        self._paneB_range_cb_pending = False
        self._paneB_reset_baseline_pending = False
        self._paneB_reset_baseline_dirty = True

        # Seed the pipe with a valid figure before assigning to paneB.object.
        # Panel calls initialize_dynamic() immediately on assignment, which calls
        # dmap[_initial_key()] — if the pipe still holds None, DynamicMap raises
        # TypeError. Seeding first avoids that.
        if self._region_pairs:
            _seed = self._figB_region(self._region_pairs)
        elif self._last_hover_point is not None:
            _seed = self._figB_hover(self._last_hover_point)
        else:
            _seed = self._figB_hover({"x": 0, "y": 0})
        if not isinstance(_seed, hv.Overlay):
            _seed = hv.Overlay([_seed])
        self._paneB_pipe.send(self._set_ranges_and_convert(_seed))

        # Rewire RangeXY to the new DynamicMap
        self._rangexy_stream = hv_streams.RangeXY(source=self._paneB_dmap)
        self._rangexy_stream.add_subscriber(self._on_paneB_range_changed)
        self._rewire_paneB_reset_stream()

        if self.paneB is not None:
            self.paneB.object = self._paneB_dmap
            try:
                doc = pn.state.curdoc
                if doc is not None:
                    self._paneB_range_cb_pending = True
                    def _ensure_and_clear_reset():
                        self._ensure_paneB_range_callbacks()
                        self._paneB_range_cb_pending = False
                    doc.add_next_tick_callback(_ensure_and_clear_reset)
            except Exception:
                pass
        if self._paneB_range_pc is not None:
            try:
                if not self._paneB_range_pc.running:
                    self._paneB_range_pc.start()
            except Exception:
                pass

    def _on_fitting_switch_changed(self, event) -> None:
        """Handle fitting switch toggle: update state, slider, and immediately refresh paneB."""
        self._fitting_active = event.new
        self._range_slider.disabled = not event.new
        self._apply_sidebar_apply_locks()
        # Reset y-range so paneB auto-scales to the new content.
        self._current_y_range = None
        self._current_y_autorange = True
        # Toggling fitting changes the Overlay structure (1 vs 3 elements).
        # Bokeh builds one renderer per element on first render and cannot handle
        # the structural change cleanly — rebuild the pipe to get a fresh model.
        self._reset_paneB_pipe()
        CacheManager.get_cached_app_state().plot_dataset = self._dataset
        self._refresh_paneB()

    def _on_range_changed(self, event):
        """Refresh paneB when the fit range slider changes (only when fitting is active)."""
        if not self._fitting_active:
            return
        self._refresh_paneB()

    def _on_spike_threshold_changed(self, event):
        self._spike_threshold = event.new
        self._despiked_cube = None
        self._despike_cache_signature = None
        self._multifit_cube = None
        self._multifit_cache_signature = None
        if self._applied_spike_threshold is None:
            return
        if self._preprocessed_source not in (None, 'spikes'):
            return
        values_match = (
            round(float(self._spike_threshold), 6) == self._applied_spike_threshold
            and self._spike_window == self._applied_spike_window
        )
        if values_match and not self._preprocessors_applied:
            self._preprocessors_applied = True
            if self._preprocessed_electron_count is not None:
                CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
            self._apply_remove_spikes_button.toggle()
        elif not values_match and self._preprocessors_applied:
            self._preprocessors_applied = False
            CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()
            self._apply_remove_spikes_button.toggle()

    def _on_spike_window_changed(self, event):
        self._spike_window = int(event.new)
        self._despiked_cube = None
        self._despike_cache_signature = None
        self._multifit_cube = None
        self._multifit_cache_signature = None
        if self._applied_spike_threshold is None:
            return
        if self._preprocessed_source not in (None, 'spikes'):
            return
        values_match = (
            round(float(self._spike_threshold), 6) == self._applied_spike_threshold
            and self._spike_window == self._applied_spike_window
        )
        if values_match and not self._preprocessors_applied:
            self._preprocessors_applied = True
            if self._preprocessed_electron_count is not None:
                CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
            self._apply_remove_spikes_button.toggle()
        elif not values_match and self._preprocessors_applied:
            self._preprocessors_applied = False
            CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()
            self._apply_remove_spikes_button.toggle()
            
    def _on_multifitting_switch_changed(self, event):
        """Multifitting switch toggled — batch computation is triggered by the Apply button."""
        pass

    def _disable_sidebar_widgets(self):
        """Disable all right-sidebar interactive widgets during preprocessing."""
        self._fitting_switch.disabled = True
        self._range_slider.disabled = True
        self._spike_threshold_slider.disabled = True
        self._spike_window_slider.disabled = True
        self._multifitting_switch.disabled = True
        self._cut_range_min_input.disabled = True
        self._cut_range_max_input.disabled = True
        self._cut_range_reset_button.disabled = True
        self._apply_cut_range_button.disabled = True
        self._apply_remove_spikes_button.disabled = True
        self._apply_multifitting_button.disabled = True

    def _apply_sidebar_apply_locks(self):
        """Lock only the controls of the currently applied preprocessor section."""
        spikes_applied = self._preprocessors_applied and self._preprocessed_source == 'spikes'
        multifit_applied = self._preprocessors_applied and self._preprocessed_source == 'multifit'
        cut_range_applied = self._cut_range_active
        multifit_based_on_spikes = multifit_applied and self._multifit_input_had_spikes

        # If Remove Spikes is currently applied, freeze only its own sliders.
        self._spike_threshold_slider.disabled = spikes_applied or multifit_based_on_spikes
        self._spike_window_slider.disabled = spikes_applied or multifit_based_on_spikes

        # If Multifitting is currently applied, freeze only fitting controls.
        self._fitting_switch.disabled = multifit_applied
        self._multifitting_switch.disabled = multifit_applied
        self._range_slider.disabled = multifit_applied or (not self._fitting_active)

        # Freeze only the Cut Range section when Cut Range is currently applied.
        self._cut_range_min_input.disabled = cut_range_applied
        self._cut_range_max_input.disabled = cut_range_applied
        self._cut_range_reset_button.disabled = cut_range_applied

    def _enable_sidebar_widgets(self):
        """Enable/disable sidebar widgets based on current preprocessing state."""
        self._fitting_switch.disabled = False
        self._range_slider.disabled = not self._fitting_active
        self._spike_threshold_slider.disabled = False
        self._spike_window_slider.disabled = False
        self._multifitting_switch.disabled = False
        self._cut_range_min_input.disabled = False
        self._cut_range_max_input.disabled = False
        self._cut_range_reset_button.disabled = False
        self._apply_cut_range_button.disabled = False
        self._apply_remove_spikes_button.disabled = False
        self._apply_multifitting_button.disabled = False
        self._apply_sidebar_apply_locks()

    def _on_apply_remove_spikes(self):
        """Disable sidebar, show progress in main, run all active preprocessors in a background thread."""
        # A new despike application supersedes a previously displayed multifit output.
        if self._apply_multifitting_button.is_on():
            self._apply_multifitting_button.toggle()
        self._multifitting_switch.value = False
        self._multifit_input_had_spikes = False
        self._multifit_previous_electron_count = None
        self._multifit_previous_source = None

        # Reuse cached result if slider values haven't changed since last Apply.
        current_threshold = round(float(self._spike_threshold), 6)
        current_window = self._spike_window
        if (
            self._preprocessed_electron_count is not None
            and self._preprocessed_source == 'spikes'
            and self._applied_spike_threshold == current_threshold
            and self._applied_spike_window == current_window
        ):
            self._preprocessors_applied = True
            CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
            self._current_y_range = None
            self._current_y_autorange = True
            self._finalize_remove_spikes_ui()
            return

        self._disable_sidebar_widgets()

        if self._main_ref is not None and self._plots_tab_ref is not None:
            tab = pn.Tabs(("Applying Remove Spikes...", self._progress_display))
            self._main_ref.update(tab)

        threading.Thread(target=self._run_remove_spikes_thread, daemon=True).start()

    def _on_apply_multifitting(self):
        """Disable sidebar, show progress in main, then run multifitting in a background thread."""
        self._disable_sidebar_widgets()

        if self._main_ref is not None and self._plots_tab_ref is not None:
            tab = pn.Tabs(("Applying Multifitting...", self._progress_display))
            self._main_ref.update(tab)

        self._multifit_previous_electron_count = (
            self._preprocessed_electron_count if self._preprocessors_applied else None
        )
        self._multifit_previous_source = (
            self._preprocessed_source if self._preprocessors_applied else None
        )
        self._multifit_input_had_spikes = (
            self._preprocessors_applied and self._preprocessed_source == 'spikes'
        )

        threading.Thread(target=self._run_multifitting_thread, daemon=True).start()

    def _build_multifit_signature(self, input_da, input_arr: np.ndarray, fit_range: tuple[float, float]):
        """Build a stable cache signature for multifitting based on source, range, and shape."""
        fit_range_signature = tuple(round(float(v), 6) for v in fit_range)
        try:
            input_eloss = np.asarray(input_da.coords[self._eloss_name].values)
            eloss_signature = (
                round(float(input_eloss[0]), 6),
                round(float(input_eloss[-1]), 6),
                int(input_eloss.size),
            ) if input_eloss.size > 0 else (0.0, 0.0, 0)
        except Exception:
            eloss_signature = (0.0, 0.0, int(input_arr.shape[-1]))

        if self._apply_remove_spikes_button.is_on():
            source_signature = (
                'despiked',
                round(float(self._spike_threshold), 6),
                int(self._spike_window),
            )
        else:
            source_signature = ('raw',)
        if self._cut_range_active and self._applied_cut_range is not None:
            source_signature = (
                *source_signature,
                'cut_range',
                round(float(self._applied_cut_range[0]), 6),
                round(float(self._applied_cut_range[1]), 6),
            )
        return (source_signature, fit_range_signature, eloss_signature, tuple(input_arr.shape))

    def _run_multifitting_thread(self):
        """Background thread: run multifitting for every pixel and cache the resulting cube."""
        try:
            self._progress_display.reset()
            self._progress_display.visible = True
            self._progress_display.update(5, "Initializing multifitting...", level='info')

            input_da = self._get_display_data()
            input_arr = np.asarray(input_da)
            if input_arr.ndim != 3:
                raise ValueError(f"Expected 3D spectrum image, got shape={input_arr.shape}")

            input_eloss = np.asarray(input_da.coords[self._eloss_name].values)
            if input_eloss.shape[0] != input_arr.shape[-1]:
                input_eloss = np.arange(input_arr.shape[-1], dtype=float)
            fit_range = self._get_clipped_fit_range(input_eloss, update_slider=False)

            dimx, dimy, _ = input_arr.shape
            total_pixels = max(1, dimx * dimy)
            multifit_signature = self._build_multifit_signature(input_da, input_arr, fit_range)

            if (
                self._multifit_cube is not None
                and self._multifit_cache_signature == multifit_signature
                and self._multifit_cube.shape == input_arr.shape
            ):
                self._progress_display.update(55, "Using cached multifitting result...", level='info')
                working_arr = self._multifit_cube.copy()
            else:
                self._progress_display.update(20, "Running multifitting...", level='info')

                def multifit_progress_callback(progress, total):
                    denom = max(1, int(total))
                    percent = 20 + int(65 * min(progress, denom) / denom)
                    self._progress_display.update(
                        percent,
                        f"Multifitting: {progress}/{denom} pixels",
                        level='info',
                    )

                cpu_count = os.cpu_count() or 1
                workers = max(1, min(8, cpu_count - 1)) if cpu_count > 1 else 1
                use_parallel = (total_pixels >= 512) and (workers > 1)

                mf = MultiFit(
                    np.ascontiguousarray(input_arr),
                    model=lmfit.models.PowerLawModel,
                    Eloss_x=input_eloss,
                    fit_range=fit_range,
                ).run(
                    mode='subtracted',
                    use_parallel=use_parallel,
                    workers=workers if use_parallel else None,
                    progress_callback=multifit_progress_callback,
                )

                working_arr = np.asarray(mf.get_fitted_data())
                self._multifit_cube = working_arr.copy()
                self._multifit_cache_signature = multifit_signature

            self._progress_display.update(90, "Finalizing...", level='info')
            time.sleep(0.5)

            preprocessed_da = xr.DataArray(
                working_arr,
                dims=input_da.dims,
                coords=input_da.coords,
            )
            self._preprocessed_electron_count = preprocessed_da
            CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": preprocessed_da})
            self._preprocessors_applied = True
            self._preprocessed_source = 'multifit'
            self._multifitting_switch.value = True
            self._current_y_range = None
            self._current_y_autorange = True
            self._progress_display.completion("Multifitting applied successfully!")
            time.sleep(2)

        except Exception as e:
            self._progress_display.error(f"Multifitting failed: {str(e)}")

            # Restore previous display state if multifitting fails.
            self._preprocessed_electron_count = self._multifit_previous_electron_count
            self._preprocessed_source = self._multifit_previous_source
            if self._multifit_previous_electron_count is not None:
                self._preprocessors_applied = True
                CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._multifit_previous_electron_count})
            else:
                self._preprocessors_applied = False
                CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()

            self._multifitting_switch.value = False
            self._apply_multifitting_button.toggle()
            time.sleep(2)
        finally:
            try:
                pn.state.execute(self._restore_after_remove_spikes)
            except Exception:
                self._restore_after_remove_spikes()

    def _on_revert_multifitting(self):
        """Revert multifitting and restore the previous display cube (raw or despiked)."""
        if self._multifit_previous_electron_count is not None:
            self._preprocessed_electron_count = self._multifit_previous_electron_count
            self._preprocessed_source = self._multifit_previous_source
            self._preprocessors_applied = True
            CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
        else:
            self._preprocessed_electron_count = None
            self._preprocessed_source = None
            self._preprocessors_applied = False
            CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()

        self._multifitting_switch.value = False
        self._multifit_input_had_spikes = False
        self._multifit_previous_electron_count = None
        self._multifit_previous_source = None
        self._current_y_range = None
        self._current_y_autorange = True
        self._refresh_paneA()
        self._refresh_paneB()
        self._enable_sidebar_widgets()

    def _finalize_remove_spikes_ui(self):
        """Final pane refresh once plots tab is mounted in the document."""
        self._enable_sidebar_widgets()
        self._refresh_paneA()
        self._refresh_paneB()

    def _restore_after_remove_spikes(self):
        """Restore plots tab and refresh paneA/paneB on the main UI thread."""
        if self._main_ref is not None and self._plots_tab_ref is not None:
            self._main_ref.update(self._plots_tab_ref)
        try:
            doc = pn.state.curdoc
            if doc is not None:
                doc.add_next_tick_callback(self._finalize_remove_spikes_ui)
                return
        except Exception:
            pass
        self._finalize_remove_spikes_ui()

    def _run_remove_spikes_thread(self):
        """Background thread: precompute all active preprocessors across every pixel, cache result, then restore the plots view."""
        try:
            self._progress_display.reset()
            self._progress_display.visible = True

            remove_spikes = True
            fitting = self._fitting_active
            multifitting = bool(self._multifitting_switch.value)

            self._progress_display.update(5, "Initializing preprocessors...", level='info')

            input_da = self._get_display_data()
            input_arr = np.asarray(input_da)
            dimx, dimy, n_energy = input_arr.shape
            total_pixels = dimx * dimy

            despike_window = self._normalize_spike_window(self._spike_window, n_energy)
            despike_signature = (round(float(self._spike_threshold), 6), int(despike_window))
            use_cached_despiked = (
                multifitting
                and not remove_spikes
                and self._despiked_cube is not None
                and self._despike_cache_signature == despike_signature
                and self._despiked_cube.shape == input_arr.shape
            )

            # Work on a plain numpy copy so we can mutate freely
            if use_cached_despiked:
                working_arr = self._despiked_cube.copy()
                input_signature = ('despiked', despike_signature)
                self._progress_display.update(8, "Using cached despiked spectra for multifitting...", level='info')
            else:
                working_arr = input_arr.copy()

            if remove_spikes:
                self._progress_display.update(10, f"Removing spikes from {total_pixels} pixels...", level='info')
                threshold = self._spike_threshold
                window = despike_window

                if window < 3:
                    self._despiked_cube = None
                    self._despike_cache_signature = None
                    self._progress_display.update(
                        44,
                        "Spike removal skipped: energy axis too short.",
                        level='warning',
                    )
                else:
                    rolling_median = median_filter(working_arr, size=(1, 1, window), mode='nearest')
                    abs_dev = np.abs(working_arr - rolling_median)
                    mad = median_filter(abs_dev, size=(1, 1, window), mode='nearest')
                    spike_mask = np.isfinite(working_arr) & (mad > 1e-12) & (abs_dev > threshold * mad)

                    flat = working_arr.reshape(-1, n_energy)
                    flat_mask = spike_mask.reshape(-1, n_energy)
                    affected = np.flatnonzero(np.any(flat_mask, axis=1))

                    corrected_points = 0
                    total_affected = int(affected.size)
                    update_every = max(1, total_affected // 20) if total_affected > 0 else 1

                    for k, pix in enumerate(affected):
                        mask_1d = flat_mask[pix]
                        spec_1d = flat[pix]
                        good_mask = (~mask_1d) & np.isfinite(spec_1d)
                        good_points = np.where(good_mask)[0]

                        if good_points.size > 1:
                            spike_points = np.where(mask_1d)[0]
                            spec_1d[mask_1d] = np.interp(spike_points, good_points, spec_1d[good_mask])
                            corrected_points += int(mask_1d.sum())
                        elif good_points.size == 1:
                            spec_1d[mask_1d] = spec_1d[good_points[0]]
                            corrected_points += int(mask_1d.sum())

                        if (k + 1) % update_every == 0 or (k + 1) == total_affected:
                            pct = 10 + int(34 * (k + 1) / max(total_affected, 1))
                            self._progress_display.update(
                                pct,
                                f"Despiking: {k + 1}/{max(total_affected, 1)} spectra with spikes",
                                level='info',
                            )

                    self._progress_display.update(
                        44,
                        f"Spike removal complete ({corrected_points} points corrected in {total_affected} spectra).",
                        level='info',
                    )

                    # Cache despiked spectra so multifitting can reuse them later.
                    self._despiked_cube = working_arr.copy()
                    self._despike_cache_signature = despike_signature
                    input_signature = ('despiked', despike_signature)

            # if fitting:
            #     self._progress_display.update(45, "Spectral fitting will be applied on display.", level='info')
            #     time.sleep(0.3)

            # if multifitting:
            #     multifit_signature = (input_signature, fit_range, tuple(raw_arr.shape))

            #     if (
            #         self._multifit_cube is not None
            #         and self._multifit_cache_signature == multifit_signature
            #         and self._multifit_cube.shape == working_arr.shape
            #     ):
            #         self._progress_display.update(50, "Using cached multifitting result...", level='info')
            #         working_arr = self._multifit_cube.copy()
            #     else:
            #         self._progress_display.update(50, "Running multifitting...", level='info')

            #         def multifit_progress_callback(progress, total):
            #             percent = 50 + int(40 * progress / total)
            #             self._progress_display.update(
            #                 percent, f"Multifitting: {progress}/{total} pixels", level='info'
            #             )

            #         try:
            #             cpu_count = os.cpu_count() or 1
            #             workers = max(1, min(8, cpu_count - 1)) if cpu_count > 1 else 1
            #             use_parallel = (total_pixels >= 512) and (workers > 1)

            #             mf = MultiFit(
            #                 np.ascontiguousarray(working_arr),
            #                 model=lmfit.models.PowerLawModel,
            #                 Eloss_x=self._e_axis,
            #                 fit_range=fit_range,
            #             ).run(
            #                 mode='subtracted',
            #                 use_parallel=use_parallel,
            #                 workers=workers if use_parallel else None,
            #                 progress_callback=multifit_progress_callback,
            #             )
            #             working_arr = mf.get_fitted_data()
            #             self._multifit_cube = np.asarray(working_arr).copy()
            #             self._multifit_cache_signature = multifit_signature
            #         except Exception:
            #             pass

            self._progress_display.update(90, "Finalizing...", level='info')
            time.sleep(0.5)

            preprocessed_da = xr.DataArray(
                working_arr,
                dims=input_da.dims,
                coords=input_da.coords,
            )
            self._preprocessed_electron_count = preprocessed_da
            CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": preprocessed_da})
            self._preprocessors_applied = True
            self._preprocessed_source = 'spikes'
            self._applied_spike_threshold = round(float(self._spike_threshold), 6)
            self._applied_spike_window = self._spike_window
            self._current_y_range = None
            self._current_y_autorange = True
            time.sleep(0.5)
            self._progress_display.completion("Despike applied successfully!")
            time.sleep(2)

        except Exception as e:
            self._progress_display.error(f"Processing failed: {str(e)}")
            if self._cut_range_active and self._cut_range_preprocessed_electron_count is not None:
                self._preprocessed_electron_count = self._cut_range_preprocessed_electron_count
                self._preprocessed_source = 'cut_range'
                self._preprocessors_applied = True
                CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
            else:
                self._preprocessors_applied = False
                self._preprocessed_electron_count = None
                self._preprocessed_source = None
                CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()
            self._apply_remove_spikes_button.toggle()
            time.sleep(2)
        finally:
            try:
                pn.state.execute(self._restore_after_remove_spikes)
            except Exception:
                # Fallback path for non-server contexts.
                self._restore_after_remove_spikes()

    def _on_revert_remove_spikes(self):
        """Stop applying preprocessors and revert paneB and paneA to raw spectrum and image. Restore selection overlay if region is selected."""
        had_preprocessed = self._preprocessors_applied or self._preprocessed_electron_count is not None

        if self._apply_multifitting_button.is_on():
            self._apply_multifitting_button.toggle()
        self._multifitting_switch.value = False
        self._multifit_input_had_spikes = False
        self._multifit_previous_electron_count = None
        self._multifit_previous_source = None

        restoring_cut_range = self._cut_range_active and self._cut_range_preprocessed_electron_count is not None
        if restoring_cut_range:
            self._preprocessed_electron_count = self._cut_range_preprocessed_electron_count
            self._preprocessed_source = 'cut_range'
            self._preprocessors_applied = True
            CacheManager.get_cached_app_state().preprocessed_plot_dataset = self._dataset.assign({"ElectronCount": self._preprocessed_electron_count})
            self._sync_range_slider_to_energy_axis(
                np.asarray(self._preprocessed_electron_count.coords[self._eloss_name].values),
                reset_value=False,
            )
        else:
            self._preprocessors_applied = False
            self._preprocessed_source = None
            # Keep _preprocessed_electron_count and _applied_spike_threshold/_applied_spike_window in memory
            # so re-clicking Apply with the same values skips recomputation.
            CacheManager.get_cached_app_state().clear_preprocessed_plot_dataset()
            self._sync_range_slider_to_energy_axis(np.asarray(self._e_axis), reset_value=False)
        self._current_y_range = None
        self._current_y_autorange = True

        if restoring_cut_range:
            self._refresh_paneA()
        elif had_preprocessed and self._raw_paneA_base_overlay is not None and self.paneA is not None:
            self._paneA_base_overlay = self._raw_paneA_base_overlay
            self._update_selection_overlay(self._region_pairs)
        else:
            self._refresh_paneA()

        self._refresh_paneB()
        self._enable_sidebar_widgets()

    # --- Callbacks setup (adds inactivity periodic callback on top of base) ---
    @override
    def _setup_callbacks(self):
        # All stream wiring (hover, tap, selection, rangexy) is handled by the base class.
        super()._setup_callbacks()
        self._rewire_paneB_reset_stream()
        try:
            pn.state.onload(lambda: self._ensure_paneB_range_callbacks())
        except Exception:
            pass
        self._paneB_range_pc = pn.state.add_periodic_callback(self._ensure_paneB_range_callbacks, period=200, start=True)
        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    @override
    def _on_paneB_range_changed(self, x_range=None, y_range=None):
        """Persist paneB zoom/pan ranges if RangeXY still emits values in this environment."""

        if self._is_valid_range(x_range) or self._is_valid_range(y_range):
            self._set_paneB_frozen_state(x_range=x_range, y_range=y_range)

        self._debug_paneB_state("range_changed", x_range=x_range, y_range=y_range)

    # --- Inactivity logic ---
    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        # No selection -> nothing to do
        if not self._region_pairs:
            stop_pc(self._pc)
            return

        # If there is no hover timestamp, ensure selection is shown and timer stopped
        if self._last_hover_ts is None:
            stop_pc(self._pc)
            if self._preprocessors_applied:
                self._refresh_paneB()
            return

        if self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            self._refresh_paneB()
            stop_pc(self._pc)

    # --- Pane A event handlers (hover / click / selected) ---
    def _on_paneA_hover(self, x=None, y=None):
        # HoloViews PointerXY delivers x, y directly as kwargs
        if x is None or y is None:
            return
        self._queue_hover(x, y)

    def _handle_hover_render(self, point):
        if self._hover_blocked:
            return
        if (
            not self._region_pairs
            and not self._preprocessors_applied
            and not self._fitting_active
            and self._try_fast_hover_update(point)
        ):
            stop_pc(self._pc)
            self._last_hover_ts = None
            return
        current_pixel = (round(point["y"]), round(point["x"]))
        now = self._now_ms()
        self._last_hover_render_ts = now
        self._last_rendered_pixel = current_pixel

        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = now
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_paneA_click(self, x=None, y=None):
        # HoloViews Tap delivers x, y directly as kwargs
        if self._hover_blocked:
            return
        if x is None or y is None:
            return
        # Force re-render on click even if same pixel (user intent is explicit).
        self._last_rendered_pixel = None
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = self._now_ms()
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_paneA_selected(self, index=None):
        # Delegate to base debounce logic.
        super()._on_paneA_selected(index)

    @override
    def _process_selection(self, index=None):
        """Commit selection: reset y-range so paneB auto-scales to the new spectrum, then run base logic."""
        self._current_y_range = None
        self._current_y_autorange = True
        self._last_rendered_pixel = None  # force re-render on next hover even at same pixel
        self._debug_paneB_state("process_selection_before_base")
        super()._process_selection(index)
        stop_pc(self._pc)
        self._last_hover_ts = None
        self._debug_paneB_state("process_selection_after_base")

    def _update_selection_overlay(self, pairs):
        """Inherited from base — red-dot overlay recomposition."""
        super()._update_selection_overlay(pairs)

    @override
    def _on_paneA_double_tap(self, x=None, y=None):
        """Reset selection (base), stop inactivity timer, optionally show hover spectrum."""
        self._last_rendered_pixel = None  # force re-render on next hover even at same pixel
        super()._on_paneA_double_tap(x, y)
        stop_pc(self._pc)
        self._last_hover_ts = None
        if x is not None and y is not None:
            self._last_hover_point = {"x": x, "y": y}
            self._show_spectrum(point=self._last_hover_point)

    @override
    def cleanup(self):
        """Stop periodic callback, unwatch widgets, and release all references."""
        stop_pc(self._pc)
        self._pc = None

        # Unwatch range slider to sever the reference from the watcher to self
        if self._range_slider_watcher is not None and self._range_slider is not None:
            try:
                self._range_slider.param.unwatch(self._range_slider_watcher)
            except Exception:
                pass
        self._range_slider_watcher = None

        if self._fitting_switch_watcher is not None and self._fitting_switch is not None:
            try:
                self._fitting_switch.param.unwatch(self._fitting_switch_watcher)
            except Exception:
                pass
        self._fitting_switch_watcher = None

        if self._spike_threshold_slider_watcher is not None and self._spike_threshold_slider is not None:
            try:
                self._spike_threshold_slider.param.unwatch(self._spike_threshold_slider_watcher)
            except Exception:
                pass
        self._spike_threshold_slider_watcher = None

        if self._spike_window_slider_watcher is not None and self._spike_window_slider is not None:
            try:
                self._spike_window_slider.param.unwatch(self._spike_window_slider_watcher)
            except Exception:
                pass
        self._spike_window_slider_watcher = None

        if self._multifitting_switch_watcher is not None and self._multifitting_switch is not None:
            try:
                self._multifitting_switch.param.unwatch(self._multifitting_switch_watcher)
            except Exception:
                pass
        self._multifitting_switch_watcher = None

        # Null out widget references
        self._range_slider = pn.widgets.EditableRangeSlider()
        self._fitting_switch = pn.widgets.Switch()
        self._spike_threshold_slider = pn.widgets.FloatSlider()
        self._spike_window_slider = pn.widgets.IntSlider()
        self._multifitting_switch = pn.widgets.Switch()
        self._cut_range_min_input = pn.widgets.FloatInput()
        self._cut_range_max_input = pn.widgets.FloatInput()
        self._cut_range_reset_button = pn.widgets.Button()
        self._apply_cut_range_button = ToggleButton()
        self._cut_range_active = False
        self._cut_range_preprocessed_electron_count = None
        self._applied_cut_range = None
        self._apply_remove_spikes_button = ToggleButton()
        self._apply_multifitting_button = ToggleButton()
        self._preprocessors_applied = False
        self._preprocessed_source = None
        self._preprocessed_electron_count = None
        self._multifit_previous_electron_count = None
        self._multifit_previous_source = None
        self._multifit_input_had_spikes = False
        self._despiked_cube = None
        self._despike_cache_signature = None
        self._multifit_cube = None
        self._multifit_cache_signature = None
        self._raw_paneA_base_overlay = None
        self._main_ref = None
        self._plots_tab_ref = None

        if self._paneB_reset_stream is not None:
            try:
                self._paneB_reset_stream.remove_subscriber(self._on_paneB_plot_reset)
            except Exception:
                pass
            try:
                self._paneB_reset_stream.clear()
            except Exception:
                pass
        self._paneB_reset_stream = None

        if self._paneB_range_pc is not None:
            try:
                if self._paneB_range_pc.running:
                    self._paneB_range_pc.stop()
            except Exception:
                pass
        self._paneB_range_pc = None
        self._paneB_attached_model_id = None

        super().cleanup()