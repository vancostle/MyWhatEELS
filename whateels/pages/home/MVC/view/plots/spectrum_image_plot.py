import panel as pn
import time
import threading
import numpy as np
import holoviews as hv
import lmfit

from whateels.helpers import SpectrumExtractor
from whateels.helpers.fitting.multifitting import MultiFit
from whateels.components import SplitJs, SimpleDetails, ToggleButton, ProgressDisplay
from whateels.pages.home.utils.plot_helpers import (
    get_range_slider_value, apply_fitting, get_pixel_spectrum, start_pc, stop_pc
)
from whateels.state import CacheManager
from whateels.base.plots.base_spectrum_image_plot import BaseSpectrumImagePlot

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
        self._fitting_active = False
        self._last_hover_ts = None
        self._pc = None

        # Widget placeholders (filled by _setup_widgets, called after super)
        self._range_slider = pn.widgets.EditableRangeSlider()
        self._range_slider_watcher = None
        self._fitting_switch = pn.widgets.Switch()
        self._fitting_switch_watcher = None

        self._remove_spikes_switch = pn.widgets.Switch()
        self._remove_spikes_watcher = None

        self._spike_threshold_slider = pn.widgets.FloatSlider()
        self._spike_threshold_slider_watcher = None
        self._spike_threshold = 5.0
        
        self._multifitting_switch = pn.widgets.Switch()
        self._multifitting_switch_watcher = None

        self._preprocessors_applied = False
        self._apply_preprocessors_button = None
        self._multifit_electron_count_data = None
        self._progress_display: ProgressDisplay = ProgressDisplay(name="Preprocessing")
        self._main_ref = None
        self._plots_tab_ref = None

        # super().__init__ calls _setup_plots() and _setup_callbacks() (base versions)
        super().__init__(dataset, eloss_name=self._model.constants.ELOSS)

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
        self._remove_spikes_switch = pn.widgets.Switch(
            name="Remove Spikes",
            value=False,
            css_classes=["background-switch"],
            styles={'height': '30px', 'max-height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center', 'margin': '0px'}
        )
        self._remove_spikes_watcher = self._remove_spikes_switch.param.watch(
            self._on_remove_spikes_changed, 'value'
        )
        self._spike_threshold_slider = pn.widgets.FloatSlider(
            name="Spike Threshold",
            start=1.0,
            end=20.0,
            step=0.1,
            value=self._spike_threshold,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )
        self._spike_threshold_slider_watcher = self._spike_threshold_slider.param.watch(self._on_spike_threshold_changed, 'value')
        self._spike_threshold = 5.0
        
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

        self._apply_preprocessors_button = ToggleButton(
            initial_state=False,
            states={
                "on": {"label": 'Display Raw Data', "on_click": self._on_display_raw_data, "button_type": 'warning'},
                "off": {"label": 'Apply Active Preprocessors', "on_click": self._on_apply_preprocessors, "button_type": 'success'},
            },
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )

    # --- Fitting Details SimpleDetails builder ---
    def create_fitting_details(self) -> SimpleDetails:
        """Build and return the fitting SimpleDetails block for the sidebar."""
        fitting_label = pn.pane.Markdown(
            "## Fitting",
            margin=0,
            styles={'padding': '0px', 'height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center'}
        )
        fitting_switch_container = pn.Row(
            fitting_label,
            self._fitting_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-container"],
            margin=(0, 0, 8, 0),
            styles={'display': 'flex', 'align-items': 'center',
                    'justify-content': 'center', 'padding': '0px'}
        )
        return SimpleDetails(
            title="Fitting Settings",
            content=pn.Column(
                fitting_switch_container,
                self._range_slider_container,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            sizing_mode=self._STRETCH_WIDTH,
        )
        
    def create_remove_spikes_details(self) -> SimpleDetails:
        """Build and return the Remove Spikes SimpleDetails block for the sidebar."""
        remove_spikes_label = pn.pane.Markdown(
            "## Remove Spikes",
            margin=0,
            styles={'padding': '0px', 'height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center'}
        )
        remove_spikes_container = pn.Row(
            remove_spikes_label,
            self._remove_spikes_switch,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            styles={'display': 'flex', 'align-items': 'center',
                    'justify-content': 'center', 'padding': '0px'}
        )
        threshold_slider_container = pn.Column(
            self._spike_threshold_slider,
            sizing_mode=self._STRETCH_WIDTH,
        )
        return SimpleDetails(
            title="Remove Spikes Settings",
            content=pn.Column(
                remove_spikes_container,
                threshold_slider_container,
            ),
            sizing_mode=self._STRETCH_WIDTH,
        )
        
    def create_preprocessors_button(self) -> ToggleButton:
        """Return the Apply Active Preprocessors toggle button for the sidebar."""
        return self._apply_preprocessors_button

    def set_view_refs(self, main, plots_tab) -> None:
        """Inject main layout and plots tab references so the plot can show progress and restore content."""
        self._main_ref = main
        self._plots_tab_ref = plots_tab

    def create_multifitting_details(self) -> SimpleDetails:
        """Build and return the Multifitting SimpleDetails block for the sidebar."""
        
        multiffitting_label = pn.pane.Markdown(
            "## Multifitting",
            margin=0,
            styles={'padding': '0px', 'height': '30px', 'display': 'flex',
                    'align-items': 'center', 'justify-content': 'center'}
        )
        
        multifitting_switch_container = pn.Row(
            multiffitting_label,
            self._multifitting_switch,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            styles={'display': 'flex', 'align-items': 'center',
                    'justify-content': 'center', 'padding': '0px'}
        )
        
        return SimpleDetails(
            title="Multifitting",
            content=pn.Column(
                multifitting_switch_container,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            sizing_mode=self._STRETCH_WIDTH,
        )

    def _remove_spikes(self, spectrum, threshold=None, window=5):
        """
        Spike removal using a rolling median with edge padding.
        Replaces points that deviate from the local median by more than
        'threshold' times the local MAD.
        Args:
            spectrum:  1D numpy array
            threshold: spike detection sensitivity (higher = less aggressive)
            window:    number of points in the rolling window (must be odd)
        Returns:
            1D numpy array with spikes replaced by the local median
        """
        if threshold is None:
            threshold = self._spike_threshold
        if spectrum is None or len(spectrum) < window:
            return spectrum
        half = window // 2
        filtered = spectrum.copy()
        padded = np.pad(spectrum, half, mode='edge')
        for i in range(len(spectrum)):
            local = padded[i:i + window]
            median = np.median(local)
            mad = np.median(np.abs(local - median))
            if mad < 1e-12:
                continue  # flat region — no spike possible
            if abs(spectrum[i] - median) > threshold * mad:
                filtered[i] = median
        return filtered

    def _build_spike_removed_curve(self, spec, title):
        """Rebuild an hv.Curve with spike-filtered spectrum, preserving the title."""
        filtered = self._remove_spikes(spec)
        return hv.Curve((self._energy, filtered), kdims=['x'], vdims=['y']).opts(
            color='black', line_width=1.5,
            title=title,
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True, shared_axes=False, framewise=True,
        )

    def _get_display_data(self):
        """Return the electron count data cube to use for spectrum display.
        Uses the multifit background-subtracted cube when multifitting is active and computed."""
        if (self._preprocessors_applied and self._multifitting_switch.value
                and self._multifit_electron_count_data is not None):
            return self._multifit_electron_count_data
        return self._electron_count_data

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
            fig = self._figB_region(region_pairs)
        elif point is not None:
            i, j = round(point['y']), round(point['x'])
            title = f"Hover (x={j}, y={i})"
            spec = get_pixel_spectrum(self._get_display_data(), point)
            fig = self._figB_hover(point)
            
        if self._preprocessors_applied and spec is not None:
            if self._remove_spikes_switch.value:
                spec = self._remove_spikes(spec)
                fig = self._build_spike_removed_curve(spec, title)
            if self._fitting_active:
                try:
                    fig = apply_fitting(fig, self._energy, spec, self._range_slider)
                except Exception:
                    pass
        self._update_paneB(fig)

    # --- Helper methods now imported from utils/plot_helpers.py ---
    def _refresh_paneB(self):
        """
        Unified logic to update paneB with the current region or hover point, applying fitting if active.
        """

        apply_preprocessors = self._preprocessors_applied

        if self._region_pairs:
            res = SpectrumExtractor.get_spectrum_from_indices(self._get_display_data(), self._region_pairs)
            spec = None
            n_points = 0
            if res is not None:
                spec, n_points = res
            fig = self._figB_region(self._region_pairs)
            if apply_preprocessors and spec is not None:
                if self._remove_spikes_switch.value:
                    spec = self._remove_spikes(spec)
                    fig = self._build_spike_removed_curve(spec, f"ROI \u2014 sum (points={n_points})")
                if self._fitting_active:
                    try:
                        fig = apply_fitting(fig, self._energy, spec, self._range_slider)
                    except Exception:
                        pass
            self._update_paneB(fig)
            return

        if self._last_hover_point is not None:
            point = self._last_hover_point
            i, j = round(point['y']), round(point['x'])
            spec = get_pixel_spectrum(self._get_display_data(), point)
            fig = self._figB_hover(point)
            if apply_preprocessors and spec is not None:
                if self._remove_spikes_switch.value:
                    spec = self._remove_spikes(spec)
                    fig = self._build_spike_removed_curve(spec, f"Hover (x={j}, y={i})")
                if self._fitting_active:
                    try:
                        fig = apply_fitting(fig, self._energy, spec, self._range_slider)
                    except Exception:
                        pass
            self._update_paneB(fig)
            return

        # No hover yet — use default pixel (0, 0)
        default_point = {"x": 0, "y": 0}
        spec = get_pixel_spectrum(self._get_display_data(), default_point)
        fig = self._figB_hover(default_point)
        if apply_preprocessors and spec is not None:
            if self._remove_spikes_switch.value:
                spec = self._remove_spikes(spec)
                fig = self._build_spike_removed_curve(spec, "Hover (x=0, y=0)")
            if self._fitting_active:
                try:
                    fig = apply_fitting(fig, self._energy, spec, self._range_slider)
                except Exception:
                    pass
        self._update_paneB(fig)
        
    def _update_paneB(self, fig):
        if self._paneB_pipe is not None:
            # Always send an hv.Overlay so the DynamicMap type stays consistent
            # (mixing plain Curve and Overlay causes an AssertionError in the cache).
            if fig is not None and not isinstance(fig, hv.Overlay):
                fig = hv.Overlay([fig])
            # Push the new element through the pipe — Bokeh updates data in-place
            # without rebuilding the whole model tree, avoiding the stale-reference warning.
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))

    def _on_fitting_switch_changed(self, event) -> None:
        """Handle fitting switch toggle: update state and slider only — refresh is triggered by the button."""
        self._fitting_active = event.new
        if self._range_slider is not None:
            self._range_slider.disabled = not event.new
        try:
            CacheManager.get_cached_app_state().plot_dataset = self._dataset
        except Exception:
            pass

    def _on_range_changed(self, event):
        """Refresh paneB when the fit range slider changes (only when preprocessors are applied and fitting is active)."""
        if not self._preprocessors_applied or not self._fitting_active:
            return
        self._refresh_paneB()

    def _on_remove_spikes_changed(self, event):
        """Update threshold slider state — refresh is triggered by the button."""
        self._spike_threshold_slider.disabled = not event.new

    def _on_spike_threshold_changed(self, event):
        self._spike_threshold = event.new
        if self._preprocessors_applied and self._remove_spikes_switch.value:
            self._refresh_paneB()
            
    def _on_multifitting_switch_changed(self, event):
        """Multifitting switch toggled — batch computation is triggered by the Apply button."""
        pass

    def _disable_sidebar_widgets(self):
        """Disable all right-sidebar interactive widgets during preprocessing."""
        self._fitting_switch.disabled = True
        self._range_slider.disabled = True
        self._remove_spikes_switch.disabled = True
        self._spike_threshold_slider.disabled = True
        self._multifitting_switch.disabled = True
        if self._apply_preprocessors_button is not None:
            self._apply_preprocessors_button.disabled = True

    def _enable_sidebar_widgets(self):
        """Re-enable right-sidebar widgets after preprocessing completes."""
        self._fitting_switch.disabled = False
        self._range_slider.disabled = not self._fitting_active
        self._remove_spikes_switch.disabled = False
        self._spike_threshold_slider.disabled = not bool(self._remove_spikes_switch.value)
        self._multifitting_switch.disabled = False
        if self._apply_preprocessors_button is not None:
            self._apply_preprocessors_button.disabled = False

    def _on_apply_preprocessors(self):
        """Disable sidebar, show progress in main, run all active preprocessors in a background thread."""
        self._disable_sidebar_widgets()
        threading.Thread(target=self._run_preprocessors_thread, daemon=True).start()

    def _run_preprocessors_thread(self):
        """Background thread: show per-step progress, compute preprocessors, then restore the plots view."""
        try:
            if self._main_ref is not None and self._plots_tab_ref is not None:
                tab = pn.Tabs(("Applying Preprocessors...", self._progress_display))
                self._main_ref.update(tab)

            self._progress_display.reset()
            self._progress_display.visible = True

            remove_spikes = bool(self._remove_spikes_switch.value)
            fitting = self._fitting_active
            multifitting = bool(self._multifitting_switch.value)

            self._progress_display.update(5, "Initializing preprocessors...", level='info')
            time.sleep(1)

            if remove_spikes:
                self._progress_display.update(20, "Removing spikes from spectra...", level='info')
                time.sleep(1)

            if fitting:
                self._progress_display.update(35, "Applying spectral fitting...", level='info')
                time.sleep(1)

            if multifitting:
                self._progress_display.update(50, "Running multifitting — fitting power-law background to all pixels...", level='info')
                time.sleep(1)
                try:
                    fit_range = tuple(self._range_slider.value) if fitting and self._range_slider is not None else None
                    mf = MultiFit(
                        self._dataset,
                        model=lmfit.models.PowerLawModel,
                        Eloss_x=self._e_axis,
                        fit_range=fit_range,
                    ).run(mode='subtracted')
                    fitted_ds = mf.to_dataset()
                    self._multifit_electron_count_data = fitted_ds['ElectronCount']
                except Exception:
                    self._multifit_electron_count_data = None
            else:
                self._multifit_electron_count_data = None

            self._progress_display.update(90, "Finalizing...", level='info')
            self._preprocessors_applied = True
            self._current_y_range = None
            self._current_y_autorange = True
            time.sleep(1)

            self._progress_display.completion("Preprocessors applied successfully!")
            time.sleep(2)

        except Exception as e:
            self._progress_display.error(f"Processing failed: {str(e)}")
            self._preprocessors_applied = False
            self._multifit_electron_count_data = None
            if self._apply_preprocessors_button is not None:
                self._apply_preprocessors_button.toggle()
            time.sleep(2)
        finally:
            if self._main_ref is not None and self._plots_tab_ref is not None:
                self._main_ref.update(self._plots_tab_ref)
            self._enable_sidebar_widgets()
            pn.state.execute(self._refresh_paneB)

    def _on_display_raw_data(self):
        """Stop applying preprocessors and revert paneB to raw spectrum."""
        self._preprocessors_applied = False
        self._multifit_electron_count_data = None
        self._current_y_range = None
        self._current_y_autorange = True
        self._refresh_paneB()

    # --- Callbacks setup (adds inactivity periodic callback on top of base) ---
    @override
    def _setup_callbacks(self):
        # All stream wiring (hover, tap, selection, rangexy) is handled by the base class.
        super()._setup_callbacks()
        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

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
        if self._hover_blocked:
            return
        if x is None or y is None:
            return
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

    def _on_paneA_click(self, x=None, y=None):
        # HoloViews Tap delivers x, y directly as kwargs
        if self._hover_blocked:
            return
        if x is None or y is None:
            return
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
        """Commit selection: run base logic then reset inactivity state."""
        super()._process_selection(index)
        stop_pc(self._pc)
        self._last_hover_ts = None

    def _update_selection_overlay(self, pairs):
        """Inherited from base — red-dot overlay recomposition."""
        super()._update_selection_overlay(pairs)

    @override
    def _on_paneA_double_tap(self, x=None, y=None):
        """Reset selection (base), stop inactivity timer, optionally show hover spectrum."""
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

        # Null out widget references
        self._range_slider = pn.widgets.EditableRangeSlider()
        self._fitting_switch = pn.widgets.Switch()
        self._remove_spikes_switch = pn.widgets.Switch()
        self._spike_threshold_slider = pn.widgets.FloatSlider()
        self._multifitting_switch = pn.widgets.Switch()
        self._multifitting_switch_watcher = None
        self._apply_preprocessors_button = None
        self._preprocessors_applied = False
        self._multifit_electron_count_data = None
        self._main_ref = None
        self._plots_tab_ref = None

        super().cleanup()