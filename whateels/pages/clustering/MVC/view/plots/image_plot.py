"""
Image visualizer for clustering page.

This is a local wrapper that imports the shared ImageVisualizer component.
Keeping it here makes the architecture more explicit and easier to understand
for developers who are new to the codebase.

If clustering-specific image features are needed in the future, they can be
added to this file by extending the shared component.
"""

from whateels.components.visualizers import ImageVisualizer as SharedImageVisualizer


class ImageVisualizer(SharedImageVisualizer):
    """
    Clustering page's image visualizer.
    
    Currently just uses the shared ImageVisualizer component.
    Can be extended with clustering-specific features if needed.
    """
    pass
