"""
EELSPlotFactory: Centralized factory for creating EELS visualizer components based on dataset type.

Features:
- Uses the Factory Pattern to decouple visualization creation from the View.
- Supports extensible mapping of dataset types to visualizer classes.
- Provides a consistent interface for visualization components.
- Handles errors robustly by raising exceptions with clear messages.
"""

from ..view.visualizers import SpectrumLineVisualizer, SpectrumImageVisualizer, SingleSpectrumVisualizer, ImageVisualizer

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from . import ClusteringController
    from xarray import Dataset

import traceback

class VisualizerFactory:
    """
    Centralized factory for creating EELS visualizer components.
    
    - Decouples visualization creation from the View.
    - Maps dataset types to visualizer classes.
    - Raises exceptions for unknown types or plot creation errors.
    """
    
    def __init__(self, model: "ClusteringModel", controller: "ClusteringController") -> None:
        self._model = model
        self._controller = controller
        
        # Mapping of dataset types to visualizer classes
        # This can be extended with more visualizers as needed
        self._all_visualizers = {
            model.constants.SPECTRUM_LINE: SpectrumLineVisualizer,
            model.constants.SPECTRUM_IMAGE: SpectrumImageVisualizer,
            model.constants.SINGLE_SPECTRUM: SingleSpectrumVisualizer,
            model.constants.IMAGE: ImageVisualizer
        }

    def choose_visualizer(
        self, 
        dataset_type: str, 
        dataset: "Dataset"
    ) -> SpectrumLineVisualizer | SpectrumImageVisualizer | SingleSpectrumVisualizer | ImageVisualizer | None:
        """
        Instantiates and returns the appropriate EELS visualizer for the specified dataset type.

        Args:
            dataset_type (str): The dataset type key (e.g., model.constants.SPECTRUM_LINE or SPECTRUM_IMAGE).

        Returns:
            SpectrumLineVisualizer | SpectrumImageVisualizer: An instance of the corresponding visualizer class.

        Raises:
            ValueError: If the dataset type is not recognized (not mapped in _all_spectrum_visualizer).
            RuntimeError: If an exception occurs during visualizer instantiation.
        """
        
        # Error message constants
        UNKNOWN_TYPE_ERROR = "[VisualizerFactory] Unknown dataset type: '{}'. Supported types: {}"
        EXCEPTION_ERROR = "[VisualizerFactory] Exception while creating plot for dataset type '{}': {}"

        try:
            chosen_spectrum_visualizer = self._all_visualizers.get(dataset_type)
            if chosen_spectrum_visualizer:
                # Pass controller only to SpectrumImageVisualizer, others get model and dataset only
                if chosen_spectrum_visualizer == SpectrumImageVisualizer:
                    chosen_spectrum_visualizer = chosen_spectrum_visualizer(self._model, self._controller, dataset)
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