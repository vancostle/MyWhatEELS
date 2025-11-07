"""
Clustering page visualizers.

All visualizers for the clustering page:
- ImageVisualizer: Simple 2D image heatmap (wraps shared component)
- SpectrumImageVisualizer: Interactive 3D datacube with clustering features
"""

from .image_visualizer import ImageVisualizer
from .spectrum_image_visualizer import SpectrumImageVisualizer

__all__ = [
    'SpectrumImageVisualizer',  # Clustering-enhanced visualizer
    'ImageVisualizer'             # Base component from shared
]
