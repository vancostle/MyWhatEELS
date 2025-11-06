"""
Clustering page visualizers.

Imports:
- Base ImageVisualizer from shared components
- Clustering-specific SpectrumImageVisualizer (extends base component)
"""

# Import base ImageVisualizer from shared components
from whateels.components.visualizers import ImageVisualizer

# Import clustering-specific SpectrumImageVisualizer (local, extends base)
from .spectrum_image_visualizer import SpectrumImageVisualizer

__all__ = [
    'SpectrumImageVisualizer',  # Clustering-enhanced visualizer
    'ImageVisualizer'             # Base component from shared
]
