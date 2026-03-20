"""
Visualization factories for different EELS data types.
"""

from .spectrum_image_plot import SpectrumImageVisualizer
from .image_plot import ImagePlot

__all__ = [
    'SpectrumImageVisualizer',
    'ImagePlot'
]
