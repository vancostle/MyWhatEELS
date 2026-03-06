"""Spectrum-image (datacube) visualizer built with Panel and Plotly.

This implementation replaces HoloViews rendering while preserving the original
data access flow and interaction behavior (hover, click, ROI selection, fitting).
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

colors = palettes.Category10[10]  # Shared qualitative palette for multi-trace overlays.


class SpectrumImageVisualizer(AbstractEELSVisualizer):
    """
    Plotly/Panel implementation of the Spectrum Image visualizer.

    Keeps the original data flow and replaces HoloViews with Plotly panes and
    callback-based interactions for hover, click, ROI selection, and fitting.
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
        """Initialize visual state, interactive panes, and callback wiring."""
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset

        # Cached energy axis used to draw spectra in pane B.
        self._e_axis = self._dataset.coords[self._model.constants.ELOSS].values

        # ElectronCount data cube
        self._electron_count_data: "Dataset" = self._dataset.ElectronCount
        
        # Last selected pixel (x,y)
        self._last_selected = {"x": 0, "y": 0}

        # Range state for paneB (to preserve zoom/pan)
        self._current_x_range = None
        self._current_y_range = None
        # None leaves Plotly defaults; bool values explicitly control autorange.
        self._current_x_autorange = None
        self._current_y_autorange = None

        # Selection/hover/fitting state.
        self._region_pairs = []         # List of (i, j) pixels selected by lasso/box.
        self._last_hover_point = None   # Last hovered point payload: {x, y, curve}.
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
        """Return the 1D energy axis associated with the current datacube."""
        return self._e_axis
        
    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):
        """Build the two-pane split layout with image on the left and spectra on the right."""
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both'
        )
        
        right_column = pn.Column(
            self.paneB,
            # Button row (fitting + multifit), if available.
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # Energy-range slider row, if available.
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
        """Reuse the shared dataset-info card from the abstract base class."""
        return super().create_dataset_info()
    
    def plot_fitting(self, x, y_fit):
        """
        Overlay the fitted spectrum curve on top of the current pane-B figure.

        Parameters:
            x (array-like): Independent variable data.
            y_fit (array-like): Fitted curve values for all x samples.

        Returns:
            plotly.graph_objs.Figure: Updated figure including the fit overlay.
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
        AppState().fitting_results = y_fit  # Store the fitted curve in shared state for potential future use.
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
        """Refresh pane-B based on ROI state and clear fit overlays when needed."""
        if self._region_pairs:
            self.paneB.object = self._set_ranges_and_convert(self._figB_region(self._region_pairs))
        else:
            self.paneB.object = self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image"))

    def plot_image(self):
        """Render the integrated intensity image and reset fit/spectra shared state."""
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        # Validate and cache energy axis for spectrum traces.
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build heatmap plus an almost-transparent scatter trace for lasso/box selections.
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

        # Lock aspect ratio to preserve pixel geometry while resizing.
        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title=" ",
            height=400,
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect.
        figA.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                           showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Pane A (heatmap) is responsive; geometry stays correct via figure axis constraints.
        self.paneA.object = self._to_plotly(figA)

        self.paneB.object = self._set_ranges_and_convert(self._figB_message(" ", "Select a region for ROI"))

        AppState().fitting_results = None  # Clear fitting results when re-plotting original image
        AppState().spectra = None  # Clear spectra when re-plotting original image


    def plot_energy_map(self, energy_map):
        """Render a model-computed 2D energy map on pane A."""
        # `energy_map` must be a 2D matrix aligned with image pixel coordinates.
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
            colorscale=[
                [0.0, "#00eb6c"],
                [1.0, "#ff1493"],
            ],
            showscale=True,
            colorbar=dict(
                x=1.0,
                y=1.12,
                xanchor="right",
                yanchor="top",
                orientation="h",
                len=0.25,
                thickness=10,
                title=dict(text=""),
            ),
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
            

    def _setup_plots(self):
        """Create initial pane A/B Plotly objects before the layout is requested."""
        # Build image from datacube; expected ElectronCount dims: (y, x, E).
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        # Validate and cache energy axis for pane B traces.
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build heatmap plus transparent selectors for box/lasso ROI tools.
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

        # Lock aspect ratio to avoid geometric deformation.
        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title=" ",
            height=400,
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect.
        figA.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                           showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Pane A (heatmap) is responsive; geometry stays correct via figure axis constraints.
        self.paneA = pn.pane.Plotly(self._to_plotly(figA), config={"responsive": True}, sizing_mode='stretch_both')

        # Pane B starts with an instructional message while preserving stored axis state.
        self.paneB = pn.pane.Plotly(
            self._set_ranges_and_convert(self._figB_message(" ", "Select a region for ROI")),
            sizing_mode='stretch_both', config={"responsive": True}
        )

    def _setup_callbacks(self):
        """Bind Panel/Plotly events for hover, click, selection, and relayout."""
        # Attach watchers to pane A (image interactions) and pane B (zoom/pan relayout).
        self.paneA.param.watch(self._on_paneA_hover, "hover_data")
        self.paneA.param.watch(self._on_paneA_click, "click_data")
        self.paneA.param.watch(self._on_paneA_selected, "selected_data")

        # relayout_data is emitted by pn.pane.Plotly when axis ranges change.
        self.paneB.param.watch(self._on_paneB_relayout, "relayout_data")

        # Periodic callback used only while temporary hover override is active.
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

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
        """Return a placeholder pane-B figure with a centered instructional message."""
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
        """Create a single-pixel spectrum figure from a hovered image coordinate."""
        if not point:
            return self._figB_message("Hover", "Move the cursor over the image")
        i, j = point["y"], point["x"]
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"(i={i}, j={j})"))
        fig.update_layout(title="Hover", margin=dict(l=16, r=16, t=48, b=16),
                          xaxis_title=self._X_AXIS_SPECTRUM_TITLE, yaxis_title=self._Y_AXIS_SPECTRUM_TITLE)
        return fig

    def _figB_region(self, pairs):
        """Create an ROI-summed spectrum figure from selected pixel coordinates."""
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

    def _now_ms(self):
        """Return the current timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _check_inactivity(self):
        """Restore ROI view after temporary hover previews become inactive."""
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

    def _on_paneA_hover(self, event: "Event"):
        """Handle hover events to preview pixel spectra when ROI selection exists."""
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            # Show hover preview while preserving ROI state for later restoration.
            fig = self._figB_hover(self._last_hover_point)
            self.paneB.object = self._set_ranges_and_convert(fig)
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()

    def _on_paneA_click(self, event):
        """Handle click events as an explicit hover-spectrum request."""
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
        """Handle lasso/box selections and update pane-B with ROI spectrum."""
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
        # Keep ROI as canonical view and stop inactivity checks until next hover.
        if self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None

    def _on_paneB_relayout(self, event):
        """Track user zoom/pan state from Plotly relayout payloads."""
        # Extract ranges/autorange robustly from different Plotly payload formats.
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

            # Plotly versions may vary in payload shape; parser remains permissive.
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
        """Apply stored ranges to a figure and convert it to Panel-safe Plotly JSON."""
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
    Sum values in a rectangular matrix region defined by index bounds.

    Parameters:
        matrix: The 2D matrix to sum over.
        vertexs: Tuple `(x_start, x_end, y_start, y_end)` defining the region.

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
    Compute the upper envelope of two curves over their union x-domain.

    Parameters:
        x1, y1: The x and y values of the first curve.
        x2, y2: The x and y values of the second curve.

    Returns:
        tuple[np.ndarray, np.ndarray]: `(x_common, y_envelope)`.
    """
    # Find the common x range
    x_common = np.union1d(x1, x2)

    # Interpolate y values for the common x points
    y1_interp = np.interp(x_common, x1, y1)
    y2_interp = np.interp(x_common, x2, y2)

    # Calculate the envelope by taking the maximum at each point
    y_envelope = np.maximum(y1_interp, y2_interp)
    return x_common, y_envelope
