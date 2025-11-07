
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

from .plots import SpectrumImageVisualizer, ImageVisualizer
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
        self._all_visualizers = {
            model.constants.SPECTRUM_IMAGE: SpectrumImageVisualizer,
            model.constants.IMAGE: ImageVisualizer
        }

    def choose_visualizer(
        self, 
        dataset_type: str, 
        dataset: "Dataset"
    ) -> SpectrumImageVisualizer | ImageVisualizer | None:
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
            chosen_spectrum_visualizer = self._all_visualizers.get(dataset_type)
            if chosen_spectrum_visualizer:
                # Pass controller only to SpectrumImageVisualizer, others get model and dataset only
                if chosen_spectrum_visualizer == SpectrumImageVisualizer:
                    chosen_spectrum_visualizer = chosen_spectrum_visualizer(self._model, self._view, dataset)
                else:
                    chosen_spectrum_visualizer = chosen_spectrum_visualizer(self._model, dataset)
                return chosen_spectrum_visualizer
            else:
                chosen_spectrum_visualizer = None
                error_msg = UNKNOWN_TYPE_ERROR.format(dataset_type, list(self._all_visualizers.keys()))
                raise ValueError(error_msg)
        except Exception as e:
            chosen_spectrum_visualizer = None
            error_msg = EXCEPTION_ERROR.format(dataset_type, e)
            traceback.print_exc()
            raise RuntimeError(error_msg) from e