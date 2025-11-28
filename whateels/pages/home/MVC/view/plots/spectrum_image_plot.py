"""
Spectrum image (datacube) visualization composer.
Se reemplaza HoloViews por Panel + Plotly usando la lógica de si_view.py,
pero manteniendo la lógica de acceso a datos y widgets de SpectrumImageVisualizer.
"""

import panel as pn
import numpy as np
import time
import plotly.graph_objs as go

from whateels.helpers import SpectrumExtractor
from whateels.pages.home.utils.plot_helpers import (
    get_range_slider_value, apply_fitting, get_pixel_spectrum, start_pc, stop_pc
)
from whateels.components import ResizableColumns, DatasetInformation
from whateels.shared_state import AppState
from whateels.interfaces import IPlot

from typing import TYPE_CHECKING, override
if TYPE_CHECKING:
    from ...model import HomePageModel
    from xarray import Dataset
    from param.parameterized import Event

class SpectrumImagePlot(IPlot):
    """
    Version Plotly / Panel del visualizador de Spectrum Image.
    Mantiene la lógica de datos del visualizador original y reemplaza
    HoloViews por Plotly panes y callbacks (hover / click / select).
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
        # None = unknown / leave Plotly default; True/False = explicitly requested autorange
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
        self.paneA = None  # Plotly heatmap pane
        self.paneB = None  # Plotly spectrum pane
        self._pc = None    # periodic callback handle
        self._js_executor = None  # invisible HTML pane to run JS

        # Setup widgets, plots and callbacks
        self._setup_widgets()
        self._setup_plots()
        self._setup_callbacks()

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):        
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both'
        )
        
        right_column = pn.Column(
            self.paneB,
            # fila de botones (fitting + multifit)
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # slider/range debajo
            self.range_slider_row,
            sizing_mode='stretch_both'
        )
        
        resizable_columns = ResizableColumns(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
 
        return resizable_columns

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
        
        dataset = all_datasets[0]
        
        attrs = dataset.attrs if dataset is not None else {}

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)
        
        beam_energy = f"{beam_energy} {ENERGY_UNIT}" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle = f"{convergence_angle} {ANGLE_UNIT}" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle = f"{collection_angle} {ANGLE_UNIT}" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE
        
        dataset_information = DatasetInformation(
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
            paneB.object = self._set_ranges_and_convert(fig)

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


    # --- Plot / Pane Setup (Plotly) ---
    def _setup_plots(self):
        # Build image (m_image) from data cube in the canonical way used in this class
        # ElectronCount dims assumed (y, x, E)
        # Use self._electron_count_data from constructor
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        # energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build Plotly heatmap (figA) and selectors scatter for box/lasso selections
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny),
            colorscale="Greys_r",
            showscale=False,
            name="m_image",
            hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>",
        )

        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        selectors = go.Scattergl(
            x=XX.ravel(),
            y=YY.ravel(),
            mode="markers",
            name="selectors",
            marker=dict(size=6, opacity=0.01),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=0.3, size=8)),
            unselected=dict(marker=dict(opacity=0.01)),
        )

        # Create figure with default size but lock aspect ratio so it doesn't deform
        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title=" ",
            height=400,  # default initial height as in the original copy
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect to avoid deformation
        figA.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                           showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Pane A (heatmap) — responsive and will scale to parent; aspect locked by figure axes
        self.paneA = pn.pane.Plotly(self._to_plotly(figA), config={"responsive": True}, sizing_mode='stretch_both')

        # Pane B initial message (apply stored ranges if any)
        self.paneB = pn.pane.Plotly(
            self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image")),
            sizing_mode='stretch_both', config={"responsive": True}
        )

    # --- Callbacks setup (connect pane watchers & periodic callback) ---
    def _setup_callbacks(self):
        # Attach panel watchers to figA and paneB
        if self.paneA is not None:
            self.paneA.param.watch(self._on_paneA_hover, "hover_data")
            self.paneA.param.watch(self._on_paneA_click, "click_data")
            self.paneA.param.watch(self._on_paneA_selected, "selected_data")

        # relayout_data is emitted by pn.pane.Plotly on axis changes
        if self.paneB is not None:
            self.paneB.param.watch(self._on_paneB_relayout, "relayout_data")

        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # --- Helpers / utilities (from si_view.py adapted) ---
    def _to_plotly(self, obj):
        """Convert go.Figure to dict to avoid Panel<->Plotly relayout issues."""
        try:
            if isinstance(obj, go.Figure):
                return obj.to_plotly_json()
        except Exception:
            pass
        try:
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        return obj

    def _figB_message(self, title, subtitle):
        fig = go.Figure()
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(title=title, margin=dict(l=16, r=16, t=48, b=16))
        fig.add_annotation(
            x=0.5, y=0.6, xref="paper", yref="paper",
            text=subtitle, showarrow=False,
            font=dict(size=22), align="center",
        )
        return fig

    def _figB_hover(self, point):
        if not point:
            return self._figB_message("Hover", "Move the cursor over the image")
        i, j = int(point["y"]), int(point["x"])
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"(i={i}, j={j})"))
        fig.update_layout(title="Hover", margin=dict(l=16, r=16, t=48, b=16),
                          xaxis_title=self._X_AXIS_SPECTRUM_TITLE, yaxis_title=self._Y_AXIS_SPECTRUM_TITLE)
        return fig

    def _figB_region(self, pairs):
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_message("ROI", "Select with lasso/box...")
        spec, n_points = res
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"sum (points={n_points})"))
        fig.update_layout(
            title=f"ROI — sum (points={n_points})",
            margin=dict(l=16, r=16, t=48, b=16), 
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE, 
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE
        )
        return fig

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
    def _on_paneA_hover(self, event: "Event"):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = self._now_ms()
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_paneA_click(self, event):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = self._now_ms()
            start_pc(self._pc)
        else:
            self._show_spectrum(point=point)
            stop_pc(self._pc)
            self._last_hover_ts = None

    def _on_paneA_selected(self, event: "Event"):
        pairs = SpectrumExtractor.extract_region(event)
        self._region_pairs = pairs
        self._show_spectrum(region_pairs=pairs)
        # prepare inactivity behaviour: stop periodic callback until next hover
        stop_pc(self._pc)
        self._last_hover_ts = None

    # --- Pane B relayout (preserve zoom/pan ranges) ---
    def _on_paneB_relayout(self, event):
        # Robustly extract ranges/autorange from relayout payloads emitted by Plotly
        try:
            data = event.new or {}

            # X axis: support 'xaxis.range', 'xaxis.range[0/1]', 'xaxis.autorange'
            if 'xaxis.range[0]' in data and 'xaxis.range[1]' in data:
                self._current_x_range = (float(data['xaxis.range[0]']), float(data['xaxis.range[1]']))
                self._current_x_autorange = False
            elif 'xaxis.range' in data:
                rng = data.get('xaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_x_range = (float(rng[0]), float(rng[1]))
                    self._current_x_autorange = False
            elif 'xaxis.autorange' in data:
                # autorange True means clear explicit range
                self._current_x_autorange = bool(data.get('xaxis.autorange'))
                if self._current_x_autorange:
                    self._current_x_range = None

            # Y axis: same logic
            if 'yaxis.range[0]' in data and 'yaxis.range[1]' in data:
                self._current_y_range = (float(data['yaxis.range[0]']), float(data['yaxis.range[1]']))
                self._current_y_autorange = False
            elif 'yaxis.range' in data:
                rng = data.get('yaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_y_range = (float(rng[0]), float(rng[1]))
                    self._current_y_autorange = False
            elif 'yaxis.autorange' in data:
                self._current_y_autorange = bool(data.get('yaxis.autorange'))
                if self._current_y_autorange:
                    self._current_y_range = None

            # Some Plotly versions emit nested keys or different payload shapes; handled permissively above.
        except Exception:
            # Ignore noisy relayout payloads
            pass

    def _apply_current_ranges(self, fig):
        """Apply stored ranges to fig if present."""
        try:
            # Only set explicit ranges when available. Only set autorange when explicitly known.
            if self._current_x_range is not None:
                fig.update_xaxes(range=self._current_x_range)
            elif self._current_x_autorange is not None:
                fig.update_xaxes(autorange=bool(self._current_x_autorange))
            if self._current_y_range is not None:
                fig.update_yaxes(range=self._current_y_range)
            elif self._current_y_autorange is not None:
                fig.update_yaxes(autorange=bool(self._current_y_autorange))
        except Exception:
            pass
        return fig

    def _set_ranges_and_convert(self, fig):
        # Ensure we operate on a go.Figure to apply ranges reliably
        try:
            fig_obj = fig if isinstance(fig, go.Figure) else go.Figure(fig)
        except Exception:
            # fallback: empty figure
            fig_obj = go.Figure()
        self._apply_current_ranges(fig_obj)
        return self._to_plotly(fig_obj)

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