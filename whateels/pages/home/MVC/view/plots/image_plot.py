"""
Image visualization composer.
"""
from whateels.base.plots import BaseImagePlot
from .dataset_info import create_home_dataset_info
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel
    from xarray import Dataset

class ImagePlot(BaseImagePlot):
    """Composes image visualizations from EELS data"""
    
    def __init__(self, model: "HomePageModel", dataset: "Dataset"):
        super().__init__(dataset)
        self._model = model

    def create_dataset_info(self):
        return create_home_dataset_info(
            self._model,
            self._dataset,
            sizing_mode="stretch_width",
            margin=0,
        )
