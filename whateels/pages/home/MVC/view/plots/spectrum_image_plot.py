"""
Spectrum image (datacube) visualization composer.
Se reemplaza HoloViews por Panel + Plotly usando la lógica de si_view.py,
pero manteniendo la lógica de acceso a datos y widgets de SpectrumImageVisualizer.
"""

import panel as pn
import numpy as np
import time
import holoviews as hv

hv.extension('bokeh')  # type: ignore

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
    HoloViews / Panel visualizer for Spectrum Image.
    Uses hv.Image + hv.Points overlay with streams for hover, click and lasso/box selection.
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

        # None = unknown / leave HoloViews default; tuple = explicit (x0, x1) / (y0, y1)
        self._current_x_range = None
        self._current_y_range = None

        # Selection / hover / fitting state
        self._region_pairs = []         # list of (i,j) selected by lasso/box
        self._last_hover_point = None   # last hover {x,y}
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._fitting_active = False

        # Widgets / panes placeholders
        self.range_slider = None
        self.fitting_button = None
        self.paneA = None  # HoloViews heatmap pane
        self.paneB = None  # HoloViews spectrum pane
        self._pc = None    # periodic callback handle
        self._js_executor = None  # invisible HTML pane to run JS

        # HoloViews streams
        self._pointer_stream = None
        self._tap_stream = None
        self._selection_stream = None
        self._point_x_values = None  # meshgrid x coords (flattened) for Selection1D mapping
        self._point_y_values = None  # meshgrid y coords (flattened) for Selection1D mapping

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
            margin=0
        )
        
        right_column = pn.Column(
            self.paneB,
            # fila de botones (fitting + multifit)
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # slider/range debajo
            self.range_slider_row,
            sizing_mode='stretch_both',
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
        # Apply our CSS class to style the widget
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

        self._update_paneB(self._figB_message("Fitting", "Modo fitting: " + ("activado" if self._fitting_active else "desactivado")))
        
    def _update_paneB(self, fig):
        paneB = getattr(self, 'paneB', None)
        if paneB is not None:
            paneB.object = fig

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
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")

        ny, nx = m_image.shape
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # HoloViews Image (background heatmap)
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
            responsive=True,
            tools=['hover'],
            shared_axes=False,
        )

        # Invisible Points layer for lasso/box selection
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        points_data = np.column_stack([XX.ravel().astype(float), YY.ravel().astype(float)])
        self._point_x_values = points_data[:, 0]
        self._point_y_values = points_data[:, 1]

        points = hv.Points(points_data, kdims=['x', 'y']).opts(
            size=0,
            alpha=0,
            nonselection_alpha=0,
            tools=['lasso_select', 'box_select'],
            shared_axes=False,
        )

        # Streams
        self._pointer_stream = hv.streams.PointerXY(source=img, x=0.0, y=0.0)
        self._tap_stream = hv.streams.Tap(source=img, x=None, y=None)
        self._selection_stream = hv.streams.Selection1D(source=points, index=[])

        # Overlay: image + invisible selection points
        overlay = (img * points).opts(
            hv.opts.Overlay(responsive=True, shared_axes=False)
        )

        self.paneA = pn.pane.HoloViews(overlay, sizing_mode='stretch_both', margin=0)

        # Initial paneB message
        self.paneB = pn.pane.HoloViews(
            self._figB_message(" ", "Move the cursor over the image"),
            sizing_mode='stretch_both',
            margin=0,
        )

    # --- Callbacks setup (connect HoloViews streams & periodic callback) ---
    def _setup_callbacks(self):
        # Connect HoloViews streams to event handlers
        if self._pointer_stream is not None:
            self._pointer_stream.param.watch(self._on_pointer_moved, ['x', 'y'])
        if self._tap_stream is not None:
            self._tap_stream.param.watch(self._on_tap, ['x', 'y'])
        if self._selection_stream is not None:
            self._selection_stream.param.watch(self._on_selection, ['index'])

        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # --- Helpers / utilities ---

    def _figB_message(self, title, subtitle) -> "hv.Element":
        label = f"{title} — {subtitle}" if title.strip() else subtitle
        return hv.Curve(
            [], kdims=[self._X_AXIS_SPECTRUM_TITLE], vdims=[self._Y_AXIS_SPECTRUM_TITLE]
        ).opts(
            title=label,
            responsive=True,
            shared_axes=False,
            xaxis=None,
            yaxis=None,
        )

    def _figB_hover(self, point) -> "hv.Element":
        if not point:
            return self._figB_message("Hover", "Move the cursor over the image")
        i, j = int(round(point["y"])), int(round(point["x"]))
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        xlim = self._current_x_range if self._current_x_range else (None, None)
        ylim = self._current_y_range if self._current_y_range else (None, None)
        return hv.Curve(
            (self._energy, spec),
            kdims=[self._X_AXIS_SPECTRUM_TITLE],
            vdims=[self._Y_AXIS_SPECTRUM_TITLE],
        ).opts(
            title=f"Hover (i={i}, j={j})",
            color='black',
            line_width=1.5,
            responsive=True,
            shared_axes=False,
            xlim=xlim,
            ylim=ylim,
        )

    def _figB_region(self, pairs) -> "hv.Element":
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_message("ROI", "Select with lasso/box...")
        spec, n_points = res
        xlim = self._current_x_range if self._current_x_range else (None, None)
        ylim = self._current_y_range if self._current_y_range else (None, None)
        return hv.Curve(
            (self._energy, spec),
            kdims=[self._X_AXIS_SPECTRUM_TITLE],
            vdims=[self._Y_AXIS_SPECTRUM_TITLE],
        ).opts(
            title=f"ROI — sum (points={n_points})",
            color='steelblue',
            line_width=1.5,
            responsive=True,
            shared_axes=False,
            xlim=xlim,
            ylim=ylim,
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

    # --- Pane A event handlers (pointer / tap / selection via HoloViews streams) ---
    def _on_pointer_moved(self, event):
        """Called when pointer moves over paneA (PointerXY stream)."""
        x = self._pointer_stream.x
        y = self._pointer_stream.y
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point)
            self._last_hover_ts = self._now_ms()
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_tap(self, event):
        """Called when user taps/clicks on paneA (Tap stream)."""
        x = self._tap_stream.x
        y = self._tap_stream.y
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point)
            self._last_hover_ts = self._now_ms()
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_selection(self, event):
        """Called when user draws lasso/box selection on paneA (Selection1D stream)."""
        indices = self._selection_stream.index
        if not indices:
            pairs = []
        else:
            pairs = [
                (int(round(self._point_y_values[i])), int(round(self._point_x_values[i])))
                for i in indices
                if i < len(self._point_x_values)
            ]
        self._region_pairs = pairs
        self._show_spectrum(region_pairs=pairs)
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