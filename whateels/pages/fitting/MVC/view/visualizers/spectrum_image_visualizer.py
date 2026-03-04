"""
Spectrum image (datacube) visualization composer.
Se reemplaza HoloViews por Panel + Plotly usando la lógica de si_view.py,
pero manteniendo la lógica de acceso a datos y widgets de SpectrumImageVisualizer.
"""

import panel as pn
import numpy as np
import time
import plotly.graph_objs as go
import xarray as xr

from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING
from whateels.helpers import SpectrumExtractor, SpectrumFitting
from whateels.components import SplitJs
from whateels.shared_state import AppState
from ...controller.services.oos_loader_service import Loader_OOS

if TYPE_CHECKING:
    from ...model import Model
    from xarray import Dataset
    from param.parameterized import Event
    
import bokeh.palettes as palettes

colors = palettes.Category10[10]  # o Category20, viridis, etc.


class SpectrumImageVisualizer(AbstractEELSVisualizer):
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

    def __init__(self, model: "Model", dataset: "Dataset"):
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset

        # Energy axis (eje de energía)
        self._e_axis = self._dataset.coords[self._model.constants.ELOSS].values

        # ElectronCount data cube
        self._electron_count_data: "Dataset" = self._dataset.ElectronCount
        
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

        self.element_quant_data = []  # to store quantification data per element
        self.selected_slice = None

        # Setup widgets, plots and callbacks
        self._setup_plots()
        self._setup_callbacks()

    def get_e_axis(self):
        return self._e_axis
        
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
            self.range_slider_row if hasattr(self, 'range_slider_row') else self.range_slider,
            sizing_mode='stretch_both'
        )
        
        resizable_columns = SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
            margin = 0
        )
 
        return resizable_columns

    @override
    def create_dataset_info(self):
        return super().create_dataset_info()
    
    def plot_fitting(self, x, y_fit):
        """
        Add fit and background subtraction traces to a Plotly figure.

        Parameters:
            fig (plotly.graph_objs.Figure): The Plotly figure to add traces to.
            x (array-like): Independent variable data.
            y (array-like): Dependent variable data.
            y_fit (array-like): Fitted curve values for all x.

        Returns:
            plotly.graph_objs.Figure: The figure with added fit and subtraction traces.
        """
        
        # Local constants for Plotly and fitting
        FIT_NAME = f'Fit'
        BG_LINE_COLOR = 'rgba(255,0,255,0.6)'
        BG_FILL_COLOR = 'rgba(255,0,255,0.6)'
        LEGEND_X = 0.98
        LEGEND_Y = 0.98
        LEGEND_XANCHOR = 'right'
        LEGEND_YANCHOR = 'top'
        LEGEND_BGCOLOR = 'rgba(255,255,255,0.6)'
        LEGEND_BORDER_COLOR = 'rgba(0,0,0,0.1)'
        LEGEND_BORDER_WIDTH = 1
        FILL_TO_ZEROY = 'tozeroy'
        fig = self.paneB.object
        newfig = go.Figure(fig)
        newfig.add_trace(go.Scatter(
            x=x,
            y=y_fit,
            fill=FILL_TO_ZEROY,
            line=dict(color=BG_LINE_COLOR),
            fillcolor=BG_FILL_COLOR,
            name=FIT_NAME
        ))
        newfig.update_layout(
            legend=dict(
                x=LEGEND_X,
                y=LEGEND_Y,
                xanchor=LEGEND_XANCHOR,
                yanchor=LEGEND_YANCHOR,
                bgcolor=LEGEND_BGCOLOR,
                bordercolor=LEGEND_BORDER_COLOR,
                borderwidth=LEGEND_BORDER_WIDTH,
            )
        )
        self.paneB.object = self._set_ranges_and_convert(newfig)
        return newfig
    
    def update_plot(self):
        if self._region_pairs:
            self.paneB.object = self._set_ranges_and_convert(self._figB_region(self._region_pairs))
        else:
            self.paneB.object = self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image"))

    def toggle_energy_map(self, energy_map):
        # energy_map is a 2D array with the same shape as the image (value per pixel)
        energy_map_arr = np.asarray(energy_map)
        if energy_map_arr.ndim != 2:
            raise ValueError(f"Expected a 2D energy map, got shape={energy_map_arr.shape}")

        energy_map_arr = np.where(np.isfinite(energy_map_arr), energy_map_arr, 0.0)
        ny, nx = energy_map_arr.shape

        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        heat = go.Heatmap(
            z=energy_map_arr,
            x=np.arange(nx),
            y=np.arange(ny),
            colorscale="Viridis",
            showscale=True,
            name="energy_map",
            hovertemplate="i=%{y}, j=%{x}<br>E=%{z}<extra></extra>",
        )

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

        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title="Energy Map",
            height=400,
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        figA.update_yaxes(
            autorange="reversed",
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        )
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        self.paneA.object = self._to_plotly(figA)
            

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
            self._set_ranges_and_convert(self._figB_message(" ", "Select a region for ROI")),
            sizing_mode='stretch_both', config={"responsive": True}
        )

    # --- Callbacks setup (connect pane watchers & periodic callback) ---
    def _setup_callbacks(self):
        # Attach panel watchers to figA and paneB
        self.paneA.param.watch(self._on_paneA_hover, "hover_data")
        self.paneA.param.watch(self._on_paneA_click, "click_data")
        self.paneA.param.watch(self._on_paneA_selected, "selected_data")

        # relayout_data is emitted by pn.pane.Plotly on axis changes
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
        if AppState().is_multifit:
            multifit_electron_count_data = xr.DataArray(AppState().multifit)
            res = SpectrumExtractor.get_spectrum_from_indices(multifit_electron_count_data, pairs)
        else:
            res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_message("ROI", "Select with lasso/box...")
       
        spec, n_points = res
        AppState().spectra = spec
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"sum (points={n_points})"))
        fig.update_layout(
            title=f"ROI — sum (points={n_points})",
            margin=dict(l=16, r=16, t=48, b=16), 
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE, 
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE
        )
        region_selected = True
        return fig

    # --- Inactivity logic (restaurar selección tras inactivity) ---
    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        # No selection -> nothing to do
        if not self._region_pairs:
            if self._pc.running:
                self._pc.stop()
            return

        # If there is no hover timestamp, ensure selection is shown and timer stopped
        if self._last_hover_ts is None:
            if self._pc.running:
                self._pc.stop()
            fig = self._figB_region(self._region_pairs)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if AppState().fitting_results is not None:
                self.plot_fitting(self._energy, AppState().fitting_results)
            return

        if self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            fig = self._figB_region(self._region_pairs)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if self._pc.running:
                self._pc.stop()
            if AppState().fitting_results is not None:
                self.plot_fitting(self._energy, AppState().fitting_results)

    # --- Pane A event handlers (hover / click / selected) ---
    def _on_paneA_hover(self, event: "Event"):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            # Temporary hover while a selection exists: show hover spectrum and start/renew timer
            fig = self._figB_hover(self._last_hover_point)
            self.paneB.object = self._set_ranges_and_convert(fig)
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()

    def _on_paneA_click(self, event):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        fig = self._figB_hover(self._last_hover_point)
        if self._region_pairs:
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()
        else:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None

    def _on_paneA_selected(self, event: "Event"):
        pairs = SpectrumExtractor.extract_region(event)
        self._region_pairs = pairs
        if not pairs:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                fig = self._figB_hover(self._last_hover_point)
                self.paneB.object = self._set_ranges_and_convert(fig)
            else:
                self.paneB.object = self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image"))
            return
        else:
            self.paneB.object = self._set_ranges_and_convert(self._figB_region(self._region_pairs))
        # prepare inactivity behaviour: stop periodic callback until next hover
        if self._pc.running:
            self._pc.stop()
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
