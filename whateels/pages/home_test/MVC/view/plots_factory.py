"""
EELSPlotFactory: Centralized factory for creating EELS visualizer components based on dataset type.

Features:
- Uses the Factory Pattern to decouple visualization creation from the View.
- Supports extensible mapping of dataset types to visualizer classes.
- Provides a consistent interface for visualization components.
- Handles errors robustly by raising exceptions with clear messages.
"""

from .plots import SpectrumLinePlot, SpectrumImagePlot, SingleSpectrumPlot, ImagePlot

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import HomePageModel
    from xarray import Dataset

import traceback

class PlotsFactory:
    """
    Centralized factory for creating EELS visualizer components.
    
    - Decouples visualization creation from the View.
    - Maps dataset types to visualizer classes.
    - Raises exceptions for unknown types or plot creation errors.
    """
    
    def __init__(self, model: "HomePageModel") -> None:
        self._model = model
        
        # Mapping of dataset types to visualizer classes
        # This can be extended with more visualizers as needed
        self._all_plots = {
            model.constants.SPECTRUM_LINE: SpectrumLinePlot,
            model.constants.SPECTRUM_IMAGE: SpectrumImagePlot,
            model.constants.SINGLE_SPECTRUM: SingleSpectrumPlot,
            model.constants.IMAGE: ImagePlot
        }

    def choose_plots(
        self, 
        dataset_type: str, 
        dataset: "Dataset"
    ) -> SpectrumLinePlot | SpectrumImagePlot | SingleSpectrumPlot | ImagePlot | None:
        """
        Instantiates and returns the appropriate EELS visualizer for the specified dataset type.

        Args:
            dataset_type (str): The dataset type key (e.g., model.constants.SPECTRUM_LINE or SPECTRUM_IMAGE).

        Returns:
            SpectrumLinePlot | SpectrumImagePlot | SingleSpectrumPlot | ImagePlot: An instance of the corresponding visualizer class.

        Raises:
            ValueError: If the dataset type is not recognized (not mapped in _all_spectrum_visualizer).
            RuntimeError: If an exception occurs during visualizer instantiation.
        """
        
        # Error message constants
        UNKNOWN_TYPE_ERROR = "[PlotsFactory] Unknown dataset type: '{}'. Supported types: {}"
        EXCEPTION_ERROR = "[PlotsFactory] Exception while creating plot for dataset type '{}': {}"

        try:
            chosen_plot = self._all_plots.get(dataset_type)
            if chosen_plot is None:
                keys = list(self._all_plots.keys())
                raise ValueError(UNKNOWN_TYPE_ERROR.format(dataset_type, keys))

            return chosen_plot(self._model, dataset)

        except Exception as e:
            error_msg = EXCEPTION_ERROR.format(dataset_type, e)
            traceback.print_exc()
            raise RuntimeError(error_msg) from e