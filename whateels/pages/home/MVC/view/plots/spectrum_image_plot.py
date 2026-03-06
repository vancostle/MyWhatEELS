import panel as pn
import time
import holoviews as hv

from whateels.helpers import SpectrumExtractor
from whateels.components import SplitJs
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
        self.range_slider = None
        self._range_slider_watcher = None
        self.fitting_button = None
        self._js_executor = None
        self.multifit_button = None
        self.buttons_row = None
        self.range_slider_row = None

        # super().__init__ calls _setup_plots() and _setup_callbacks() (base versions)
        super().__init__(dataset, eloss_name=self._model.constants.ELOSS)

        # Widgets depend on _e_axis set by super().__init__
        self._setup_widgets()

    # --- Public Layout Builders ---

    @override
    def create_plots(self):
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both',
            align='center',
            margin=0,
        )
        right_column = pn.Column(
            self.paneB,
            self.buttons_row if self.buttons_row is not None else self.fitting_button,
            self.range_slider_row,
            sizing_mode='stretch_both',
            align='center',
            margin=0
        )
        return SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )

    # create_dataset_info inherited from base class
    
    # --- Widget Setup (kept from original, but range_slider reused) ---
    def _setup_widgets(self):
        self.range_slider = pn.widgets.EditableRangeSlider(
            name="",
            start=float(self._e_axis[0]) if len(self._e_axis) > 0 else 0.0,
            end=float(self._e_axis[-1]) if len(self._e_axis) > 0 else 1.0,
            value=(float(self._e_axis[0]), float(self._e_axis[-1])),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["my-range"]
        )
        self._range_slider_watcher = self.range_slider.param.watch(self._on_range_changed, 'value')
        self.fitting_button = pn.widgets.Button(name="Fitting: OFF", button_type="primary")
        self.fitting_button.on_click(self._on_fitting_clicked)
        self.multifit_button = pn.widgets.Button(name="Multifit", button_type="warning")
        self.multifit_button.on_click(self._on_multifit_clicked)
        self.multifit_button.visible = False
        self._js_executor = pn.pane.HTML("", width=0, height=0)
        self.buttons_row = pn.Row(
            self.fitting_button,
            self.multifit_button,
            self._js_executor,
            sizing_mode=self._STRETCH_WIDTH
        )
        self.range_slider_row = pn.Row(
            pn.pane.HTML("<p class=\"range-label\">Range:</p>"),
            self.range_slider,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["range-label-wrapper"],
        )
        self.range_slider_row.visible = False

    def _show_spectrum(self, *, point=None, region_pairs=None):
        """
        Unified helper to extract spectrum (from point or region), apply fitting if needed, and update paneB.
        """

        fig = None
        spec = None
        if region_pairs is not None:
            if not region_pairs:
                # No region selected, show message or hover
                if self._last_hover_point is not None:
                    self._show_spectrum(point=self._last_hover_point)
                return
            fig = self._figB_region(region_pairs)
            res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, region_pairs)
            if res is not None:
                spec, _ = res
        elif point is not None:
            fig = self._figB_hover(point)
            spec = get_pixel_spectrum(self._electron_count_data, point)

        if self._fitting_active and spec is not None:
            fig = apply_fitting(fig, self._energy, spec, self.range_slider)
        self._update_paneB(fig)

    # --- Helper methods now imported from utils/plot_helpers.py ---
    def _refresh_paneB(self):
        """
        Unified logic to update paneB with the current region or hover point, applying fitting if active.
        """
        if self._region_pairs:
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
                if res is not None:
                    spec, _ = res
                    fig = apply_fitting(fig, self._energy, spec, self.range_slider)
            self._update_paneB(fig)
            return

        if self._last_hover_point is not None:
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                spec = get_pixel_spectrum(self._electron_count_data, self._last_hover_point)
                if spec is not None:
                    fig = apply_fitting(fig, self._energy, spec, self.range_slider)
            self._update_paneB(fig)
            return

        self._update_paneB(self._figB_hover(self._last_hover_point or {"x": 0, "y": 0}))
        
    def _update_paneB(self, fig):
        if self._paneB_pipe is not None:
            # Always send an hv.Overlay so the DynamicMap type stays consistent
            # (mixing plain Curve and Overlay causes an AssertionError in the cache).
            if fig is not None and not isinstance(fig, hv.Overlay):
                fig = hv.Overlay([fig])
            # Push the new element through the pipe — Bokeh updates data in-place
            # without rebuilding the whole model tree, avoiding the stale-reference warning.
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))

    def _on_multifit_clicked(self, event):
        """Callback para el botón de multifit"""
        # Publish the dataset now that multifit is requested.
        
        try:
            CacheManager.get_cached_app_state().plot_dataset = self._dataset
        except Exception:
            print("Error publishing dataset to AppState for multifit.")
        
        minmax = get_range_slider_value(self.range_slider)
        min_val, max_val = minmax if len(minmax) == 2 else (0, 1)

        location = getattr(pn.state, 'location', None)
        current_port = getattr(location, 'port', 5006)
        hostname = getattr(location, 'hostname', 'localhost')
        url_base = f"http://{hostname}:{current_port}"

        values = f"{min_val},{max_val}"
        url_with_params = f"{url_base}/multifit-details?values={values}"
        
        if self._js_executor is not None:
            self._js_executor.object = f"""
                <script>
                    const timeout = setTimeout(() => {{
                        window.open('{url_with_params}', '_blank');
                        
                        clearTimeout(timeout);
                    }}, 0);
                </script>
            """

    def _on_range_changed(self, event):
        """Refresh paneB when the fit range slider changes (only when fitting is active)."""
        if not self._fitting_active:
            return
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
            if self._fitting_active:
                self._refresh_paneB()
            return

        if self._last_hover_ts is not None and self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            self._refresh_paneB()
            stop_pc(self._pc)

    # --- Pane A event handlers (hover / click / selected) ---
    def _on_paneA_hover(self, x=None, y=None):
        # HoloViews PointerXY delivers x, y directly as kwargs
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
        # HoloViews Selection1D delivers a list of point indices into self._selectors
        # selectors were built from meshgrid(arange(nx), arange(ny)).ravel()
        # so index k → col = k % nx, row = k // nx → pair = (row, col)
        if not index:
            pairs = []
        else:
            pairs = list(dict.fromkeys(
                (idx // self._nx, idx % self._nx) for idx in index
            ))
        self._region_pairs = pairs
        self._show_spectrum(region_pairs=pairs)
        # prepare inactivity behaviour: stop periodic callback until next hover
        stop_pc(self._pc)
        self._last_hover_ts = None

    # --- Fitting and range behaviour ---
    def _on_fitting_clicked(self, event):
        self._fitting_active = not self._fitting_active
        fitting_button = getattr(self, 'fitting_button', None)

        if fitting_button is not None:
            fitting_button.name = f"Fitting: {'ON' if self._fitting_active else 'OFF'}"
            fitting_button.button_type = "danger" if self._fitting_active else "primary"

        range_slider_row = getattr(self, 'range_slider_row', None)
        range_slider = getattr(self, 'range_slider', None)

        if range_slider_row is not None:
            range_slider_row.visible = self._fitting_active
        elif range_slider is not None:
            range_slider.visible = self._fitting_active

        # Mostrar/ocultar botón de multifit (coincide con fitting)
        multifit_button = getattr(self, 'multifit_button', None)
        if multifit_button is not None:
            multifit_button.visible = self._fitting_active

        # Refresh current view
        self._refresh_paneB()

    @override
    def cleanup(self):
        """Stop periodic callback, unwatch widgets, and release all references."""
        stop_pc(self._pc)
        self._pc = None

        # Unwatch range slider to sever the reference from the watcher to self
        if self._range_slider_watcher is not None and self.range_slider is not None:
            try:
                self.range_slider.param.unwatch(self._range_slider_watcher)
            except Exception:
                pass
        self._range_slider_watcher = None

        # Null out all widget references
        self.range_slider = None
        self.fitting_button = None
        self.multifit_button = None
        self._js_executor = None
        self.buttons_row = None
        self.range_slider_row = None

        super().cleanup()