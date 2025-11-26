"""
Visualization factories for different EELS data types.
"""

from .spectrum_image_plot import SpectrumImagePlot
from .spectrum_line_plot import SpectrumLinePlot
from .single_spectrum_plot import SingleSpectrumPlot
from .image_plot import ImagePlot

__all__ = [
    'SpectrumLinePlot', 
    'SpectrumImagePlot',
    'SingleSpectrumPlot',
    'ImagePlot'
]
