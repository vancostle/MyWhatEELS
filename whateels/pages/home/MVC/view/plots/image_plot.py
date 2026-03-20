"""
Image visualization composer.
"""
import xarray as xr

from whateels.base.plots import BaseImagePlot
from whateels.components import InfoPanel
from typing import TYPE_CHECKING, override
if TYPE_CHECKING:
    from ...model import HomePageModel

class ImagePlot(BaseImagePlot):
    """Composes image visualizations from EELS data"""
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):
        super().__init__(dataset)
        self._model = model

    @override
    def create_dataset_info(self) -> "InfoPanel":
        NOT_AVAILABLE = 'N/A'
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        ANGLE_UNIT = "mrad"
        ENERGY_UNIT = "keV"

        dataset = self._dataset
        
        attrs = dataset.attrs if dataset is not None else {}

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)
        
        beam_energy = f"{beam_energy} {ENERGY_UNIT}" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle = f"{convergence_angle} {ANGLE_UNIT}" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle = f"{collection_angle} {ANGLE_UNIT}" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE
        
        dataset_information = InfoPanel(
            title="Dataset Information", 
            information={
                "Shape": shape,
                "Beam Energy": beam_energy,
                "Convergence Angle": convergence_angle,
                "Collection Angle": collection_angle,
            },
            sizing_mode=self._STRETCH_WIDTH
        )
        
        return dataset_information


