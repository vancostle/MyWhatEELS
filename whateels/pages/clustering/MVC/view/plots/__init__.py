"""
Clustering page visualizers.

All visualizers for the clustering page:
- ImageVisualizer: Simple 2D image heatmap (wraps shared component)
- SpectrumImageVisualizer: Interactive 3D datacube with clustering features
"""

from .image_plot import ImagePlot
from .spectrum_image_plot import SpectrumImagePlot

__all__ = [
    'SpectrumImagePlot',  # Clustering-enhanced visualizer
    'ImagePlot'             # Base component from shared
]
