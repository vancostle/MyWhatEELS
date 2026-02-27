"""
Plotting utilities for clustering visualization.

OOP-based visualization for creating HoloViews figures to display clustering results,
including cluster label heatmaps and cluster center spectra.
"""

import numpy as np
import holoviews as hv
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap
from typing import TYPE_CHECKING
from whateels.helpers.colormaps import get_nclusters_cmap

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
        self.cluster_colors, self._listed_cmap = self._build_colors()
    
    def _build_colors(self) -> tuple[list[str], ListedColormap]:
        """
        Build cluster hex colors and a matplotlib ListedColormap.
        
        Returns:
            Tuple of (cluster_colors, listed_cmap)
        """
        # Use default ordering for tab20-like palettes if not specified
        index_order = self.index_order
        if index_order is None and 'tab20' in self.colormap:
            index_order = list(self.DEFAULT_ORDER)
        
        listed = get_nclusters_cmap(self.colormap, self.n_clusters, index_order=index_order)
        cluster_colors = [mcolors.to_hex(c) for c in listed]
        listed_cmap = ListedColormap(cluster_colors, name='cluster_cmap', N=self.n_clusters)
        
        return cluster_colors, listed_cmap
    
    def plot_labels(
        self,
        labels: "ndarray",
        title: str = "Clustering Labels",
    ):
        """
        Plot clustering labels as an interactive heatmap.
        
        Args:
            labels: 2D array (y, x) with cluster labels for each pixel
            title: Plot title
        
        Returns:
            HoloViews Image with discrete cluster colormap
        """
        try:
            ny, nx = labels.shape[-2], labels.shape[-1]
        except Exception:
            ny, nx = 1, 1
        
        img = hv.Image(
            (np.arange(nx), np.arange(ny), labels.astype(float)),
            kdims=['x', 'y'],
            vdims=['Cluster'],
        ).opts(
            cmap=self._listed_cmap,
            clim=(-0.5, self.n_clusters - 0.5),
            colorbar=True,
            invert_yaxis=True,
            xaxis=None,
            yaxis=None,
            title=title,
            responsive=True,
            shared_axes=False,
            aspect='equal',
            framewise=True,
        )
        return img
    
    def plot_centers(
        self,
        centres: "ndarray",
        energy: "ndarray",
        title: str = "Cluster Centers"
    ):
        """
        Plot cluster center spectra.
        
        Args:
            centres: 2D array (n_clusters, n_energy) with cluster center spectra
            energy: 1D array (n_energy,) with energy axis values
            title: Plot title
        
        Returns:
            HoloViews Overlay of Curves, one per cluster center
        """
        curves = []
        for i, center in enumerate(centres):
            color = self.cluster_colors[i % len(self.cluster_colors)]
            curves.append(
                hv.Curve(
                    (energy, center),
                    kdims=['x'],
                    vdims=['y'],
                    label=f'Cluster {i}',
                ).opts(
                    color=color,
                    line_width=2,
                )
            )
        
        return hv.Overlay(curves).opts(
            hv.opts.Overlay(
                title=title,
                xlabel="Energy Loss (eV)",
                ylabel="Intensity (AU)",
                legend_position='top_right',
                responsive=True,
                shared_axes=False,
                framewise=True,
            )
        )