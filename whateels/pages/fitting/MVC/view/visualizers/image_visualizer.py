"""
Spectrum line visualization composer.
"""
import panel as pn
import plotly.graph_objects as go
import numpy as np
import xarray as xr

# Make Plotly modebar transparent
pn.extension(raw_css=[
    ".plotly .modebar, .plotly .modebar-container, .plotly .modebar-group, .plotly .modebar-btn, .plotly .modebar-btn--hover { background: transparent !important; box-shadow: none !important; border: none !important; }",
    ".plotly .modebar-btn { background: transparent !important; }",
    ".plotly .modebar-btn svg, .plotly .modebar-btn path { fill: currentColor !important; stroke: currentColor !important; }",
])

from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import HomePageModel

class ImageVisualizer(AbstractEELSVisualizer):
    """Render 2D image datasets as Plotly heatmaps inside Panel layouts."""

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):
        """Store model/dataset references and initialize click-state fields."""
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset        
        
        # Click state placeholders kept for future interaction throttling.
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --

    @override
    def create_plots(self):
        """Create the responsive image panel layout for 2D datasets."""

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
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect to avoid deformation
        fig_base.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                             showgrid=False, zeroline=False, showticklabels=False)
        fig_base.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Use a responsive Plotly pane that fills the parent container.
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

    @override
    def create_dataset_info(self):
       return super().create_dataset_info()

    # -- Private Methods --

    def _create_2d_image(self, clean_image_data) -> 'go.Figure':
        """Create a 2D image plot for image data using Plotly (replaces HoloViews).

        Returns a plotly.graph_objects.Figure sized to data with preserved aspect ratio.
        """
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
