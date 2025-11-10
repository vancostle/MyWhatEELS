"""
Clustering page visualizers.

All visualizers for the clustering page:
- ImageVisualizer: Simple 2D image heatmap (wraps shared component)
- SpectrumImageVisualizer: Interactive 3D datacube with clustering features
"""

from .image_plot import ImageVisualizer
from .spectrum_image_plot import SpectrumImageVisualizer

__all__ = [
    'SpectrumImageVisualizer',  # Clustering-enhanced visualizer
    'ImageVisualizer'             # Base component from shared
]
