"""
Shared visualizer components for EELS data visualization.

These are base/common visualizers that can be reused across different pages.
Page-specific features should extend these base components.
"""

from .base_image_plot import BaseImagePlot
from .base_spectrum_image_plot import BaseSpectrumImagePlot

__all__ = [
    'BaseImagePlot',
    'BaseSpectrumImagePlot',
]
