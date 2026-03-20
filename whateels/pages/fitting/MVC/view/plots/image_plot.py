from whateels.base.plots import BaseImagePlot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import FittingModel
    from xarray import Dataset

class ImagePlot(BaseImagePlot):
    """Fitting page wrapper around the shared HoloViews image visualizer."""
    
    def __init__(self, model: "FittingModel", dataset: "Dataset"):
        """Bind the fitting model constants to the shared base image plot."""
        self._model = model
        super().__init__(
            dataset,
            axis_x=model.constants.AXIS_X,
            axis_y=model.constants.AXIS_Y,
        )
