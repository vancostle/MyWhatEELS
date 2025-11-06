"""
Clustering page utilities.

Page-specific utility modules for clustering algorithms, data preprocessing,
and visualization that can be used across the clustering MVC components.

Classes:
--------
- DataPreprocessor: Handles data preparation and normalization
- ClusteringAlgorithm: Base class for clustering algorithms
- KMeansClusteringAlgorithm: K-Means clustering implementation
- AgglomerativeClusteringAlgorithm: Hierarchical clustering implementation
- SpectralClusteringAlgorithm: Spectral clustering implementation
- ClusterVisualizer: Handles visualization of clustering results

Functions (backwards compatibility):
-------------------------------------
Legacy function wrappers are maintained for existing code.
"""

# Import classes (preferred OOP interface)
from .preprocessing import DataPreprocessor
from .clustering import (
    ClusteringAlgorithm,
    KMeansClusteringAlgorithm,
    AgglomerativeClusteringAlgorithm,
    SpectralClusteringAlgorithm,
)
from .visualization import ClusterVisualizer

# Import legacy functions (backwards compatibility)
from .clustering import kmeans_clustering, agglomerative_clustering, spectral_clustering
from .preprocessing import prepare_clustering_matrix, should_use_multifit_data, get_multifit_data
from .visualization import (
    plot_cluster_labels,
    build_cluster_colors_and_scale,
    build_colorbar,
    plot_cluster_centers
)

__all__ = [
    # Classes (OOP interface)
    'DataPreprocessor',
    'ClusteringAlgorithm',
    'KMeansClusteringAlgorithm',
    'AgglomerativeClusteringAlgorithm',
    'SpectralClusteringAlgorithm',
    'ClusterVisualizer',
    
    # Legacy functions (backwards compatibility)
    'kmeans_clustering',
    'agglomerative_clustering', 
    'spectral_clustering',
    'prepare_clustering_matrix',
    'should_use_multifit_data',
    'get_multifit_data',
    'plot_cluster_labels',
    'build_cluster_colors_and_scale',
    'build_colorbar',
    'plot_cluster_centers',
]
