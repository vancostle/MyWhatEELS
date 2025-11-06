"""
Plotting utilities for clustering visualization.

OOP-based visualization for creating Plotly figures to display clustering results,
including cluster label heatmaps and cluster center spectra.
"""

import numpy as np
import plotly.graph_objs as go
from typing import TYPE_CHECKING
from whateels.helpers.colormaps import (
    get_nclusters_cmap,
    build_discrete_colorscale,
    to_plotly_color,
)

if TYPE_CHECKING:
    from numpy import ndarray


class ClusterVisualizer:
    """
    Handles visualization of clustering results.
    
    Provides methods for:
    - Building color schemes for clusters
    - Creating cluster label heatmaps
    - Plotting cluster center spectra
    """
    
    # Default cluster colormap and ordering
    DEFAULT_COLORMAP = 'tab20b'
    DEFAULT_ORDER = [3, 7, 15, 11, 19, 
                     2, 6, 14, 10, 18, 
                     1, 5, 13, 9, 17, 
                     0, 4, 12, 8, 16]
    
    def __init__(
        self,
        n_clusters: int,
        colormap: str | None = None,
        index_order: list[int] | None = None
    ):
        """
        Initialize the cluster visualizer.
        
        Args:
            n_clusters: Number of clusters
            colormap: Name of matplotlib colormap (default: 'tab20b')
            index_order: Custom ordering for sampling the colormap
        """
        self.n_clusters = n_clusters
        self.colormap = colormap or self.DEFAULT_COLORMAP
        self.index_order = index_order
        
        # Build colors on initialization
        self.cluster_colors, self.discrete_colorscale = self._build_colors()
    
    def _build_colors(self) -> tuple[list[str], list[list]]:
        """
        Build cluster colors and discrete Plotly colorscale.
        
        Returns:
            Tuple of (cluster_colors, discrete_colorscale)
        """
        # Use default ordering for tab20-like palettes if not specified
        index_order = self.index_order
        if index_order is None and 'tab20' in self.colormap:
            index_order = list(self.DEFAULT_ORDER)
        
        listed = get_nclusters_cmap(self.colormap, self.n_clusters, index_order=index_order)
        cluster_colors = [to_plotly_color(c) for c in listed]
        discrete_colorscale = build_discrete_colorscale(cluster_colors)
        
        return cluster_colors, discrete_colorscale
    
    def _build_colorbar(self, ny: int, nx: int) -> tuple[dict, dict]:
        """
        Construct colorbar dict and corresponding margin based on aspect ratio.
        
        Args:
            ny: Number of pixels in y direction
            nx: Number of pixels in x direction
        
        Returns:
            Tuple of (colorbar_config, margin_config)
        """
        tickvals = list(np.arange(self.n_clusters))
        ticktext = [str(i) for i in range(self.n_clusters)]
        
        # Vertical colorbar for tall images, horizontal for wide images
        if ny > nx:
            colorbar = dict(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext,
                orientation='v',
                x=1.02,
                y=0.5,
                xanchor='left',
                yanchor='middle',
                len=1.0,
                thickness=24,
            )
            margin = dict(l=16, r=80, t=50, b=20)
        else:
            colorbar = dict(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext,
                orientation='h',
                x=0.5,
                y=-0.18,
                xanchor='center',
                yanchor='top',
                len=1.0,
                thickness=20,
            )
            margin = dict(l=16, r=16, t=50, b=80)
        
        return colorbar, margin
    
    def plot_labels(
        self,
        labels: "ndarray",
        title: str = "Clustering Labels",
        height: int | None = None
    ) -> go.Figure:
        """
        Plot clustering labels as an interactive heatmap.
        
        Args:
            labels: 2D array (y, x) with cluster labels for each pixel
            title: Plot title
            height: Figure height in pixels (default: 400)
        
        Returns:
            Plotly figure with cluster label heatmap
        """
        # Get dimensions
        try:
            ny, nx = labels.shape[-2], labels.shape[-1]
        except Exception:
            ny, nx = 1, 1
        
        # Build colorbar and margin
        colorbar, margin = self._build_colorbar(ny, nx)
        
        # Create figure
        fig = go.Figure(go.Heatmap(
            z=labels,
            colorscale=self.discrete_colorscale,
            colorbar=colorbar,
            hovertemplate='x: %{x}<br>y: %{y}<br>Cluster: %{z}<extra></extra>',
            zmin=-0.5,
            zmax=self.n_clusters - 0.5
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            height=height if height is not None else 400,
            margin=margin,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(
            autorange='reversed',
            scaleanchor='x',
            scaleratio=1,
            constrain='domain',
            showgrid=False,
            zeroline=False,
            showticklabels=False
        )
        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            constrain='domain'
        )
        
        return fig
    
    def plot_centers(
        self,
        centres: "ndarray",
        energy: "ndarray",
        title: str = "Cluster Centers"
    ) -> go.Figure:
        """
        Plot cluster center spectra.
        
        Args:
            centres: 2D array (n_clusters, n_energy) with cluster center spectra
            energy: 1D array (n_energy,) with energy axis values
            title: Plot title
        
        Returns:
            Plotly figure with cluster center spectra
        """
        traces = []
        
        for i, center in enumerate(centres):
            color = self.cluster_colors[i % len(self.cluster_colors)]
            traces.append(go.Scatter(
                x=energy,
                y=center,
                mode='lines',
                name=f'Cluster {i}',
                line=dict(color=color, width=2)
            ))
        
        fig = go.Figure(data=traces)
        fig.update_layout(
            title=title,
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            showlegend=True,
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.6)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
            )
        )
        
        return fig