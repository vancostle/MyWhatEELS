"""
Image visualizer for clustering page.

This is a local wrapper that imports the shared ImageVisualizer component.
Keeping it here makes the architecture more explicit and easier to understand
for developers who are new to the codebase.

If clustering-specific image features are needed in the future, they can be
added to this file by extending the shared component.
"""

from whateels.base.plots import BaseImagePlot


class ImagePlot(BaseImagePlot):
    """
    Clustering page's image visualizer.

    Currently just uses the shared ImagePlot component.
    Can be extended with clustering-specific features if needed.
    """
    pass
