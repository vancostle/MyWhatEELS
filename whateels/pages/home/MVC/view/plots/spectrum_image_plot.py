"""
Spectrum image (datacube) visualization composer.
Usa HoloViews + Panel (Bokeh backend) para la visualización interactiva del datacubo,
manteniendo la lógica de acceso a datos y widgets de SpectrumImageVisualizer."""

import panel as pn
import numpy as np
import time
import holoviews as hv
from holoviews import streams as hv_streams

from whateels.helpers import SpectrumExtractor
from whateels.pages.home.utils.plot_helpers import (
    get_range_slider_value, apply_fitting, get_pixel_spectrum, start_pc, stop_pc
)
from whateels.components import InfoPanel, SplitJs
from whateels.shared_state import AppState
from whateels.interfaces import IPlot

from typing import TYPE_CHECKING, override
if TYPE_CHECKING:
    from ...model import HomePageModel
    from xarray import Dataset
    from param.parameterized import Event

class SpectrumImagePlot(IPlot):
    """
    Visualizador de Spectrum Image usando HoloViews + Panel (backend Bokeh).
    Mantiene la lógica de datos del visualizador original usando
    HoloViews panes y streams (hover / click / select / range).
    """
    
    # Panel sizing modes
    _STRETCH_WIDTH = "stretch_width"
    
    # CSS classes and constants for dataset info panel
    _DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
    _DATASET_INFO_CLASS = ["dataset-info", "animated"]
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    
    _NOT_AVAILABLE = 'N/A'
    
    # Axis titles for spectrum plot
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "HomePageModel", dataset: "Dataset"):
        self._model = model
        self._dataset = dataset

        # Energy axis (eje de energía)
        self._e_axis = self._dataset.coords[self._model.constants.ELOSS].values

        # ElectronCount data cube
        self._electron_count_data = self._dataset.ElectronCount
        
        # Last selected pixel (x,y)
        self._last_selected = {"x": 0, "y": 0}

        # Range state for paneB (to preserve zoom/pan)
        self._current_x_range = None
        self._current_y_range = None
        # True = let HoloViews auto-fit; False = explicit range stored above
        self._current_x_autorange = None
        self._current_y_autorange = None

        # Selection / hover / fitting state (inspired by si_view.py)
        self._region_pairs = []         # lista de (i,j) seleccionados por lasso/box
        self._last_hover_point = None   # último hover {x,y,curve}
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._fitting_active = False

        # Widgets / panes placeholders
        self.range_slider = None
        self.fitting_button = None
        self.paneA = None  # HoloViews image pane
        self.paneB = None  # HoloViews spectrum pane
        self._pc = None    # periodic callback handle
        self._js_executor = None  # invisible HTML pane to run JS
        self._selectors = None  # HoloViews Points element (selection layer)
        self._nx = 0            # image width, used for index→(row,col) mapping
        self._hover_stream = None
        self._tap_stream = None
        self._selection_stream = None
        self._rangexy_stream = None  # HoloViews RangeXY stream for paneB zoom/pan
        self._paneB_pipe = None      # Pipe stream to push elements into paneB without full rebuild
        self._paneB_dmap = None      # DynamicMap backed by _paneB_pipe

        # Setup widgets, plots and callbacks
        self._setup_widgets()
        self._setup_plots()
        self._setup_callbacks()

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):        
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both',
            align='center',
            margin=0,
            # styles={'width': '40%'}
        )
        
        right_column = pn.Column(
            self.paneB,
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button, # show fitting button if buttons_row not ready yet
            self.range_slider_row, # show range slider row if ready
            sizing_mode='stretch_both',
            align='center',
            margin=0
        )

        splitjs = SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
 
        return splitjs

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
            sizing_mode=self._STRETCH_WIDTH,
            margin=0
        )
        
        return dataset_information
    
    # --- Widget Setup (kept from original, but range_slider reused) ---
    def _setup_widgets(self):
        # Range slider ya usado por la implementación anterior  
        self.range_slider = pn.widgets.EditableRangeSlider(
            name="",  # label externo controlado manualmente
            start=float(self._e_axis[0]) if len(self._e_axis) > 0 else 0.0,
            end=float(self._e_axis[-1]) if len(self._e_axis) > 0 else 1.0,
            value=(float(self._e_axis[0]), float(self._e_axis[-1])),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["my-range"]
        )
        self.range_slider.param.watch(self._on_range_changed, 'value')

        # Fitting toggle button
        self.fitting_button = pn.widgets.Button(name="Fitting: OFF", button_type="primary")
        self.fitting_button.on_click(self._on_fitting_clicked)

        # Multifit button (orange)
        self.multifit_button = pn.widgets.Button(name="Multifit", button_type="warning")
        self.multifit_button.on_click(self._on_multifit_clicked)  # server-side fallback
        self.multifit_button.visible = False

        # Invisible HTML pane to run JavaScript (Open new window with params)
        self._js_executor = pn.pane.HTML("", width=0, height=0)

        # Fila de botones debajo de paneB
        self.buttons_row = pn.Row(
            self.fitting_button,
            self.multifit_button,
            self._js_executor,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        # Fila con label y slider para alineación limpia
        self.range_slider_row = pn.Row(
            pn.pane.HTML(
                "<p class=\"range-label\">Range:</p>",
            ),
            self.range_slider,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["range-label-wrapper"],
        )
        self.range_slider_row.visible = False

    def _show_spectrum(self, *, point=None, region_pairs=None, message=None):
        """
        Unified helper to extract spectrum (from point or region), apply fitting if needed, and update paneB.
        If message is provided, shows a message figure instead.
        """
        if message is not None:
            self._update_paneB(self._figB_message(*message))
            return

        fig = None
        spec = None
        if region_pairs is not None:
            if not region_pairs:
                # No region selected, show message or hover
                if self._last_hover_point is not None:
                    self._show_spectrum(point=self._last_hover_point)
                else:
                    self._update_paneB(self._figB_message(" ", "Move the cursor over the image"))
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
            # Push the new element through the pipe — Bokeh updates data in-place
            # without rebuilding the whole model tree, avoiding the stale-reference warning.
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))

    def _on_multifit_clicked(self, event):
        """Callback para el botón de multifit"""
        # Publish the dataset now that multifit is requested.
        
        try:
            AppState().plot_dataset = self._dataset
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


    # --- Plot / Pane Setup (HoloViews) ---
    def _setup_plots(self):
        # Build image (m_image) from data cube in the canonical way used in this class
        # ElectronCount dims assumed (y, x, E)
        # Use self._electron_count_data from constructor
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        self._nx = nx
        # energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build HoloViews image (background heatmap for paneA)
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'],
            vdims=['Intensity']
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

        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        points_data = np.column_stack([XX.ravel().astype(float), YY.ravel().astype(float)])
        self._selectors = hv.Points(points_data, kdims=['x', 'y']).opts(
            size=0,
            alpha=0,
            nonselection_alpha=0,
            tools=['lasso_select', 'box_select'],
            shared_axes=False,
        )

        # Overlay image + invisible selectors
        overlay = (img * self._selectors).opts(hv.opts.Overlay(responsive=True, aspect='equal', shared_axes=False)) # type: ignore

        # Pane A (heatmap) — width controlled by SplitJs
        self.paneA = pn.pane.HoloViews(
            overlay, 
            sizing_mode='stretch_height', 
            margin=0,
            styles={'margin': 'auto'}
        )

        # Pane B: use a Pipe + DynamicMap so hover updates only push new data
        # into the existing Bokeh renderer instead of replacing the whole model tree.
        self._paneB_pipe = hv_streams.Pipe(data=None)
        self._paneB_dmap = hv.DynamicMap(lambda data: data, streams=[self._paneB_pipe])
        self.paneB = pn.pane.HoloViews(
            self._paneB_dmap,
            sizing_mode='stretch_both',
            margin=0,
        )
        # Seed the pipe with the top-left pixel spectrum so the chart is visible immediately.
        self._paneB_pipe.send(self._figB_hover({"x": 0, "y": 0}))

    # --- Callbacks setup (connect pane watchers & periodic callback) ---
    def _setup_callbacks(self):
        # Wire HoloViews streams to paneA interaction handlers
        if self._selectors is not None:
            self._hover_stream = hv_streams.PointerXY(source=self._selectors)
            self._tap_stream = hv_streams.Tap(source=self._selectors)
            self._selection_stream = hv_streams.Selection1D(source=self._selectors)
            self._hover_stream.add_subscriber(self._on_paneA_hover)
            self._tap_stream.add_subscriber(self._on_paneA_click)
            self._selection_stream.add_subscriber(self._on_paneA_selected)

        # Wire RangeXY stream to capture paneB zoom/pan — source the DynamicMap once
        self._rangexy_stream = hv_streams.RangeXY(source=self._paneB_dmap)
        self._rangexy_stream.add_subscriber(self._on_paneB_range_changed)

        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # --- Helpers / utilities (from si_view.py adapted) ---

    def _figB_hover(self, point):
        """Extract spectrum from a single pixel hover and return an hv.Curve."""
        if not point:
            point = {"x": 0, "y": 0}

        i, j = round(point["y"]), round(point["x"])
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)

        return hv.Curve(
            (self._energy, spec), 
            kdims=['x'], 
            vdims=['y']
        ).opts(
            color='black',
            line_width=1.5,
            title=f"Hover (x={j}, y={i})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )

    def _figB_region(self, pairs):
        """Extract spectrum from a region selection and return an hv.Curve."""
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)

        if res is None:
            return self._figB_hover({"x": 0, "y": 0})

        spec, n_points = res

        return hv.Curve(
            (self._energy, spec), 
            kdims=['x'], 
            vdims=['y']
        ).opts(
            color='black',
            line_width=1.5,
            title=f"ROI — sum (points={n_points})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )

    # --- Inactivity logic (restaurar selección tras inactivity) ---
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

    # --- Pane B range change (preserve zoom/pan ranges) ---
    @staticmethod
    def _is_valid_range(r):
        """Return True only if r is a 2-tuple of finite, distinct values."""
        if r is None:
            return False
        try:
            lo, hi = r
            return (
                lo is not None and hi is not None
                and lo == lo and hi == hi  # NaN check
                and abs(hi - lo) > 1e-12
            )
        except Exception:
            return False

    def _on_paneB_range_changed(self, x_range=None, y_range=None):
        # HoloViews RangeXY delivers x_range and y_range as tuples (min, max) or None.
        # Ignore degenerate (zero-width / NaN) ranges that come from the empty seed curve.
        if self._is_valid_range(x_range):
            self._current_x_range = x_range
            self._current_x_autorange = False
        elif x_range is None:
            self._current_x_autorange = True
            self._current_x_range = None
        # else: degenerate range — keep whatever was stored before

        if self._is_valid_range(y_range):
            self._current_y_range = y_range
            self._current_y_autorange = False
        elif y_range is None:
            self._current_y_autorange = True
            self._current_y_range = None
        # else: degenerate range — keep whatever was stored before

    def _apply_current_ranges(self, fig):
        """Apply stored zoom/pan ranges to the HoloViews element as xlim/ylim opts."""
        if fig is None:
            # Fallback to empty placeholder — mirrors original go.Figure() fallback
            return self._figB_message(" ", " ")
        try:
            opts = {}
            # Only apply explicit ranges; when autorange is True, omit xlim/ylim so
            # HoloViews auto-fits the data (equivalent to Plotly autorange=True).
            if self._current_x_range is not None:
                opts['xlim'] = self._current_x_range
            if self._current_y_range is not None:
                opts['ylim'] = self._current_y_range
            if opts:
                return fig.opts(**opts)
        except Exception:
            pass
        return fig

    def _set_ranges_and_convert(self, fig):
        # Delegate range application to _apply_current_ranges
        return self._apply_current_ranges(fig)

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