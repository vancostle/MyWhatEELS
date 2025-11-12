"""
Shared visualizer components for EELS data visualization.

These are base/common visualizers that can be reused across different pages.
Page-specific features should extend these base components.
"""

from .image_plot import ImagePlot
from .spectrum_image_plot import SpectrumImagePlot

__all__ = [
    'ImagePlot',
    'SpectrumImagePlot',
]
