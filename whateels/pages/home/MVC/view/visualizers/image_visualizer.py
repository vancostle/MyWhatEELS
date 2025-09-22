"""
Spectrum line visualization composer.
"""
import panel as pn
import plotly.graph_objects as go
import numpy as np
import xarray as xr

<<<<<<< HEAD
=======
# Make Plotly modebar transparent
pn.extension(raw_css=[
    ".plotly .modebar, .plotly .modebar-container, .plotly .modebar-group, .plotly .modebar-btn, .plotly .modebar-btn--hover { background: transparent !important; box-shadow: none !important; border: none !important; }",
    ".plotly .modebar-btn { background: transparent !important; }",
    ".plotly .modebar-btn svg, .plotly .modebar-btn path { fill: currentColor !important; stroke: currentColor !important; }",
])

>>>>>>> andry
from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import Model

class ImageVisualizer(AbstractEELSVisualizer):
    """Composes image visualizations from EELS data"""

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "Model", dataset: "xr.Dataset"):
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset        
        
        # For tap/click throttling
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --

    @override
    def create_plots(self):
        """Create layout for spectrum line visualization with Plotly (no HoloViews/Bokeh)."""

        # Prepare cleaned image data and coordinates
        image_data = self._dataset.ElectronCount.squeeze()
        image_data = image_data.fillna(0.0)
        image_data = image_data.where(np.isfinite(image_data), 0.0)

        x_coords = self._dataset.coords[self._model.constants.AXIS_X]
        x_coords = x_coords.where(np.isfinite(x_coords), 0.0)

        y_coords = self._dataset.coords[self._model.constants.AXIS_Y]
        y_coords = y_coords.where(np.isfinite(y_coords), 0.0)

        clean_image_data = image_data.assign_coords({
            self._model.constants.AXIS_X: x_coords,
            self._model.constants.AXIS_Y: y_coords
        })

        ny, nx = clean_image_data.shape
        aspect = ny / nx if nx else 1.0

        # Build Plotly heatmap (base) and layout with locked aspect
        m_image = np.asarray(clean_image_data)
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny-1, -1, -1),
            colorscale=self._model.colors.GREYS_R if hasattr(self._model, 'colors') else 'Greys_r',
            showscale=False,
            hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>",
        )
        fig_base = go.Figure(data=[heat])
        fig_base.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
<<<<<<< HEAD
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, constrain="domain"),
            yaxis=dict(scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showticklabels=False, constrain="domain"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        # layout padding values used to compute available size
        # If viewport_size is available, prefer using full window (no extra margins)
        if hasattr(pn.state, 'viewport_size'):
            extra_vertical_px = 0
            extra_horizontal_px = 0
        else:
            extra_vertical_px = 140
            extra_horizontal_px = 24

        def make_plot(vw, vh):
            if not vw or not vh:
                return pn.pane.Markdown("Cargando dimensiones…")

            w_max = max(200, int(vw - extra_horizontal_px))
            h_max = max(200, int(vh - extra_vertical_px))

            # Encaje dentro de ambas cotas manteniendo aspect ratio
            w = min(w_max, int(h_max / aspect))
            h = int(max(1, w * aspect))

            # Ensure within bounds
            if h > h_max:
                h = h_max
                w = max(200, int(h / aspect))

            f = go.Figure(fig_base)
            f.update_layout(
                autosize=False,
                width=w,
                height=h,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            f.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain", fixedrange=True)
            f.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain", scaleanchor="x", scaleratio=1, fixedrange=True)
            return pn.pane.Plotly(f, config={"responsive": True})

        # Use the current container size (not global viewport) to size the image
        container = pn.Column(sizing_mode=self._STRETCH_BOTH)
        image_panel = pn.pane.Plotly(sizing_mode='stretch_both')

        def update_from_container(*args, **kwargs):
            vw = container.width or 1200
            vh = container.height or 800
            # apply same margin logic as before
            extra_vertical = 0 if hasattr(pn.state, 'viewport_size') else 140
            extra_horizontal = 0 if hasattr(pn.state, 'viewport_size') else 24
            w_max = max(200, int(vw - extra_horizontal))
            h_max = max(200, int(vh - extra_vertical))
            w = min(w_max, int(h_max / aspect))
            h = int(max(1, w * aspect))
            if h > h_max:
                h = h_max
                w = max(200, int(h / aspect))

            f = go.Figure(fig_base)
            f.update_layout(
                autosize=False,
                width=w,
                height=h,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            f.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain", fixedrange=True)
            f.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain", scaleanchor="x", scaleratio=1, fixedrange=True)
            image_panel.object = f

        # initial render and watch container size changes
        update_from_container()
        container.param.watch(update_from_container, ['width', 'height'])

        container.append(image_panel)
        plots = container

        return plots

=======
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect to avoid deformation
        fig_base.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                             showgrid=False, zeroline=False, showticklabels=False)
        fig_base.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Use a responsive Plotly pane that fills the parent container to avoid resize loops
        image_panel = pn.pane.Plotly(self._to_plotly(fig_base), sizing_mode='stretch_both', config={'responsive': True})
        plots = pn.Column(image_panel, sizing_mode=self._STRETCH_BOTH)
        return plots

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

>>>>>>> andry
    @override
    def create_dataset_info(self):
       return super().create_dataset_info()

    # -- Private Methods --

    def _create_2d_image(self, clean_image_data) -> 'go.Figure':
        """Create a 2D image plot for image data using Plotly (replaces HoloViews).

        Returns a plotly.graph_objects.Figure sized to data with preserved aspect ratio.
        """
        IMAGE_X_LABEL = 'X Position'
        IMAGE_Y_LABEL = 'Y Position'
        IMAGE_TITLE = 'Image Data'

        MAX_PLOT_SIZE = 600

        # Calculate dimensions from the data itself
        data_height, data_width = clean_image_data.shape
        scale_factor = min(MAX_PLOT_SIZE / data_width, MAX_PLOT_SIZE / data_height)
        plot_width = int(data_width * scale_factor)
        plot_height = int(data_height * scale_factor)

        # Build Plotly heatmap; invert Y so origin is top-left
        m_image = np.asarray(clean_image_data)
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(data_width),
            y=np.arange(data_height-1, -1, -1),
            colorscale=self._model.colors.GREYS_R if hasattr(self._model, 'colors') else 'Greys_r',
            showscale=False,
            hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>",
        )

        fig = go.Figure(data=[heat])
        fig.update_layout(
            width=plot_width,
            height=plot_height,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain", fixedrange=True)
        fig.update_yaxes(scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showticklabels=False, constrain="domain", fixedrange=True)

        return fig
