
"""
PlotsFactory: Centralized factory for creating clustering plot components based on dataset type.

Features:
- Uses the Factory Pattern to decouple plot creation from the View and Layouts.
- Supports extensible mapping of dataset types to plot classes (e.g., spectrum, image).
- Provides a consistent interface for plot components.
- Handles errors robustly by raising exceptions with clear messages.

This factory is located in the 'plots' folder, which contains all clustering-specific plot components and visualizers.
It should be used by views/layouts to instantiate the correct plot for a given dataset type.
"""
import traceback

from .plots import SpectrumImagePlot, ImagePlot
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from . import ClusteringView
    from xarray import Dataset

class PlotsFactory:
    """
    Centralized factory for creating clustering plot components.
    
    - Decouples plot creation from the View and Layouts.
    - Maps dataset types to plot classes (e.g., spectrum, image).
    - Raises exceptions for unknown types or plot creation errors.
    """

    def __init__(self, model: "ClusteringModel", view: "ClusteringView") -> None:
        self._model = model
        self._view = view

        # Mapping of dataset types to plot classes
        # Extend this dictionary to support more plot types as needed
        self._all_plots = {
            model.constants.SPECTRUM_IMAGE: SpectrumImagePlot,
            model.constants.IMAGE: ImagePlot
        }

    def choose_plot(
        self, 
        dataset_type: str, 
        dataset: "Dataset"
    ) -> SpectrumImagePlot | ImagePlot | None:
        """
        Instantiates and returns the appropriate plot component for the specified dataset type.

        Args:
            dataset_type (str): The dataset type key (e.g., model.constants.SPECTRUM_IMAGE or IMAGE).

        Returns:
            SpectrumImageVisualizer | ImageVisualizer: An instance of the corresponding plot class.

        Raises:
            ValueError: If the dataset type is not recognized (not mapped in _all_visualizers).
            RuntimeError: If an exception occurs during plot instantiation.
        """
        
        # Error message constants
        UNKNOWN_TYPE_ERROR = "[VisualizerFactory] Unknown dataset type: '{}'. Supported types: {}"
        EXCEPTION_ERROR = "[VisualizerFactory] Exception while creating plot for dataset type '{}': {}"

        try:
            chosen_plot = self._all_plots.get(dataset_type)

            if chosen_plot is None:
                error_msg = UNKNOWN_TYPE_ERROR.format(dataset_type, list(self._all_plots.keys()))
                raise ValueError(error_msg)

            return (
                chosen_plot(self._model, self._view, dataset)
                if chosen_plot == SpectrumImagePlot
                else chosen_plot(self._model, dataset)
            )

        except Exception as e:
            chosen_plot = None
            error_msg = EXCEPTION_ERROR.format(dataset_type, e)
            traceback.print_exc()
            raise RuntimeError(error_msg) from e