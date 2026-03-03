"""
Base image visualizer component for 2D EELS image data.

This is a shared component that can be used across different pages.
It provides basic 2D image rendering with Plotly heatmaps.

No model dependency - only requires dataset and optional axis names.
"""
import panel as pn
import plotly.graph_objects as go
import numpy as np
import xarray as xr

from typing import Optional

class BaseImagePlot:
    """
    Base component for composing 2D image visualizations from EELS data.
    
    This visualizer renders a simple 2D heatmap using Plotly, with:
    - Automatic data cleaning (NaN/inf handling)
    - Locked aspect ratio (1:1 pixel)
    - Responsive layout
    - Interactive hover with pixel coordinates and intensity
    
    Can be extended by page-specific visualizers for additional features.
    No model dependency - works with any page.
    """

    # Constants for sizing modes and plot configuration
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    # Default axis names
    _DEFAULT_AXIS_X = 'x'
    _DEFAULT_AXIS_Y = 'y'
    
    def __init__(
        self, 
        dataset: "xr.Dataset",
        axis_x: Optional[str] = None,
        axis_y: Optional[str] = None
    ):
        """
        Initialize the image visualizer.
        
        Args:
            dataset: xarray Dataset containing ElectronCount data
            axis_x: Name of x-axis coordinate (default: 'x')
            axis_y: Name of y-axis coordinate (default: 'y')
        """
        self._dataset = dataset
        self._axis_x = axis_x or self._DEFAULT_AXIS_X
        self._axis_y = axis_y or self._DEFAULT_AXIS_Y
        
        # For tap/click throttling (if subclasses need it)
        self._last_click_x = None
        self._click_tolerance = 0.5  # Minimum distance to trigger update

    # -- Public Methods --
    
    def create_dataset_info(self, dataset_attrs: Optional[dict] = None):
        """
        Create dataset info panel.
        
        Args:
            dataset_attrs: Optional dictionary of dataset attributes.
                          If None, uses self._dataset.attrs
        
        Returns:
            pn.Column: Dataset information panel
        """
        from whateels.helpers import HTML_ROOT
        
        # Constants
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        HTML_FILE = 'metadata_info.html'
        READ_MODE = 'r'
        UTF_8 = 'utf-8'
        NOT_AVAILABLE = 'N/A'
        STRETCH_WIDTH = "stretch_width"
        DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
        DATASET_INFO_CLASS = ["dataset-info", "animated"]
        DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
        LABEL_SHAPE = "<strong>Shape:</strong>"
        LABEL_BEAM_ENERGY = "<strong>Beam Energy:</strong>"
        LABEL_CONVERGENCE_ANGLE = "<strong>Convergence Angle:</strong>"
        LABEL_COLLECTION_ANGLE = "<strong>Collection Angle:</strong>"
        ENERGY_UNIT = " keV"
        ANGLE_UNIT = " mrad"
        SPACER_HEIGHT_SMALL = 5
        SPACER_HEIGHT_MEDIUM = 10
        MARGIN_ZERO = 0
        
        attrs = dataset_attrs if dataset_attrs is not None else (self._dataset.attrs if self._dataset is not None else {})

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)

        # Load metadata button HTML
        metadata_html_path = HTML_ROOT / HTML_FILE
        with open(metadata_html_path, READ_MODE, encoding=UTF_8) as f:
            metadata_button_html = f.read()

        metadata_button = pn.pane.HTML(metadata_button_html, margin=MARGIN_ZERO)

        # Main info panel
        header = pn.Row(
            pn.pane.HTML(DATASET_INFO_TITLE, sizing_mode=STRETCH_WIDTH, margin=MARGIN_ZERO),
            metadata_button,
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_HEADER_CLASS,
            margin=MARGIN_ZERO
        )

        dataset_info = pn.Column(
            header,
            pn.Spacer(height=SPACER_HEIGHT_SMALL),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_SHAPE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(shape),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_BEAM_ENERGY),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{beam_energy}{ENERGY_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_CONVERGENCE_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{convergence_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_COLLECTION_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{collection_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Spacer(height=SPACER_HEIGHT_MEDIUM),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )
        return dataset_info

    def create_plots(self):
        """
        Create layout for 2D image visualization with Plotly.
        
        Returns:
            pn.Column: Panel column containing the image plot
        """
        # Use the axis names provided in constructor
        axis_x = self._axis_x
        axis_y = self._axis_y

        # Prepare cleaned image data and coordinates
        image_data = self._dataset.ElectronCount.squeeze()
        image_data = image_data.fillna(0.0)
        image_data = image_data.where(np.isfinite(image_data), 0.0)

        x_coords = self._dataset.coords[axis_x]
        x_coords = x_coords.where(np.isfinite(x_coords), 0.0)

        y_coords = self._dataset.coords[axis_y]
        y_coords = y_coords.where(np.isfinite(y_coords), 0.0)

        clean_image_data = image_data.assign_coords({
            axis_x: x_coords,
            axis_y: y_coords
        })

        ny, nx = clean_image_data.shape

        # Build Plotly heatmap with locked aspect ratio
        m_image = np.asarray(clean_image_data)
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny-1, -1, -1),
            colorscale='Greys_r',
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
        fig_base.update_yaxes(
            autorange="reversed", 
            scaleanchor="x", 
            scaleratio=1, 
            constrain="domain",
            showgrid=False, 
            zeroline=False, 
            showticklabels=False
        )
        fig_base.update_xaxes(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False, 
            constrain="domain"
        )

        # Use a responsive Plotly pane that fills the parent container
        image_panel = pn.pane.Plotly(
            self._to_plotly(fig_base), 
            sizing_mode='stretch_both', 
            config={'responsive': True}
        )
        plots = pn.Column(image_panel, sizing_mode=self._STRETCH_BOTH)
        return plots

    # -- Protected Helper Methods --

    def _to_plotly(self, obj):
        """
        Convert go.Figure to dict to avoid Panel<->Plotly relayout issues.
        
        Args:
            obj: Plotly Figure or dict
            
        Returns:
            dict: Plotly JSON representation
        """
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

    def _create_2d_image(self, clean_image_data, max_plot_size: int = 600) -> 'go.Figure':
        """
        Create a 2D image plot for image data using Plotly.
        
        This is a helper method that can be used by subclasses to create
        fixed-size image plots (as opposed to the responsive plot in create_plots).

        Args:
            clean_image_data: 2D numpy array or xarray DataArray with image data
            max_plot_size: Maximum width/height for the plot in pixels
            
        Returns:
            go.Figure: Plotly figure with preserved aspect ratio
        """
        # Calculate dimensions from the data itself
        data_height, data_width = clean_image_data.shape
        scale_factor = min(max_plot_size / data_width, max_plot_size / data_height)
        plot_width = int(data_width * scale_factor)
        plot_height = int(data_height * scale_factor)

        # Build Plotly heatmap; invert Y so origin is top-left
        m_image = np.asarray(clean_image_data)
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(data_width),
            y=np.arange(data_height-1, -1, -1),
            colorscale='Greys_r',
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
        fig.update_xaxes(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False, 
            constrain="domain", 
            fixedrange=True
        )
        fig.update_yaxes(
            scaleanchor="x", 
            scaleratio=1, 
            showgrid=False, 
            zeroline=False, 
            showticklabels=False, 
            constrain="domain", 
            fixedrange=True
        )

        return fig
