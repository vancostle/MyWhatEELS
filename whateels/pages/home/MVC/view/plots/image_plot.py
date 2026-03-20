"""
Image visualization composer.
"""
import xarray as xr

from whateels.base.plots import BaseImagePlot
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

class ImagePlot(BaseImagePlot):
    """Composes image visualizations from EELS data"""
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):
        super().__init__(dataset)
        self._model = model