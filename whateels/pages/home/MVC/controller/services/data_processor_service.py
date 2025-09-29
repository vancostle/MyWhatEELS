"""
Processes EELS and non-EELS data to xarray datasets. No file I/O.
"""

import numpy as np
import xarray as xr

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model

class DataProcessorService:
    """
    Processes EELS/non-EELS data to xarray datasets.
    """
    
    # Constants for dataset types
    _AXIS_X = 'x'
    _AXIS_Y = 'y'
    _ELOSS = 'Eloss'

    def __init__(self, model: "Model"):
        """Init with model config."""
        self._model = model

    # --- Public Methods ---

    def clean_dataset(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Replace NaN/Inf with zeros in data and coordinates.
        """
        
        ELECTRON_COUNT = 'ElectronCount'
        COULD_NOT_CLEAN_DATASET_MESSAGE = "Could not clean dataset: {}"

        try:
            # Clean the main electron count data array
            electron_count = dataset.ElectronCount.values
            electron_count = np.nan_to_num(electron_count, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Clean coordinate arrays
            x_coords = dataset.coords[self._AXIS_X].values
            y_coords = dataset.coords[self._AXIS_Y].values
            x_coords = np.nan_to_num(x_coords, nan=0.0, posinf=0.0, neginf=0.0)
            y_coords = np.nan_to_num(y_coords, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Check if dataset has energy dimension (EELS data)
            if self._ELOSS in dataset.coords:
                eloss_coords = dataset.coords[self._ELOSS].values
                eloss_coords = np.nan_to_num(eloss_coords, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Reconstruct 3D dataset with energy dimension
                cleaned_dataset = xr.Dataset(
                    {ELECTRON_COUNT: (dataset.ElectronCount.dims, electron_count)},
                    coords={
                        self._AXIS_X: x_coords, 
                        self._AXIS_Y: y_coords, 
                        self._ELOSS: eloss_coords
                    }
                )
                # Preserve original metadata attributes
                cleaned_dataset.attrs = dataset.attrs.copy()
                return cleaned_dataset

            # Reconstruct 2D dataset without energy dimension
            cleaned_dataset = xr.Dataset(
                {ELECTRON_COUNT: (dataset.ElectronCount.dims, electron_count)},
                coords={
                    self._AXIS_X: x_coords, 
                    self._AXIS_Y: y_coords
                }
            )

            # Preserve original metadata attributes
            cleaned_dataset.attrs = dataset.attrs.copy()
            return cleaned_dataset

        except Exception as e:
            print(COULD_NOT_CLEAN_DATASET_MESSAGE.format(e))
            return dataset

    def determine_dataset_type(self, dataset: xr.Dataset, is_eels: bool) -> str:
        """
        Classify dataset type (EELS or non-EELS).
        """

        x_size = len(dataset.coords[self._AXIS_X])
        y_size = len(dataset.coords[self._AXIS_Y])
        
        # First check if this is EELS data
        if not is_eels:
            return self._model.constants.IMAGE  # Non-EELS data is just an image

        # For EELS data, classify based on dimensions
        if x_size == 1 and y_size == 1:
            return self._model.constants.SINGLE_SPECTRUM
        elif y_size == 1:
            return self._model.constants.SPECTRUM_LINE
        else:
            return self._model.constants.SPECTRUM_IMAGE

    def process_data_for_xarray(self, electron_count_data: np.ndarray, energy_axis: np.ndarray | None, is_eels: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """
        Process data for xarray (EELS or non-EELS).
        """
        # Route to appropriate processing method based on data type and dimensionality
        
        UNSUPPORTED_DIMENSION_MESSAGE = f"ERROR: Unsupported data dimensionality: {electron_count_data.shape}"

        # First branch: Check if this is EELS or non-EELS data
        if not is_eels:
            # Non-EELS data (conventional imaging) - always 2D spatial
            return self._process_2d_image_data(electron_count_data)

        # Second branch: EELS data processing based on dimensionality
        len_shape = len(electron_count_data.shape)

        if len_shape == 1:
            # Single spectrum: energy only
            return self._process_1d_data(electron_count_data)
        elif len_shape == 2:
            # Spectrum line: position × energy
            return self._process_2d_data(electron_count_data, energy_axis)
        elif len_shape == 3:
            # Spectrum image: energy × y × x (will be transposed to y × x × energy)
            return self._process_3d_data(electron_count_data)
        else:
            print(UNSUPPORTED_DIMENSION_MESSAGE)
            return None

    # --- Private Methods ---

    def _process_1d_data(self, electron_count_data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Process 1D spectrum: add spatial dims.
        """
        # Create artificial spatial coordinates (single point at origin)
        x_coordinates = np.array([0], dtype=np.int32)  # Single point in x
        y_coordinates = np.array([0], dtype=np.int32)  # Single point in y
        
        # Reshape from (energy,) to (y=1, x=1, energy) format
        shape_dimensions = [1, 1]
        shape_dimensions.extend(list(electron_count_data.shape))
        electron_count_data = electron_count_data.reshape(shape_dimensions)
        
        return electron_count_data, x_coordinates, y_coordinates

    def _process_2d_data(self, electron_count_data: np.ndarray, energy_axis: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Process 2D spectrum line: reshape and orient.
        """
        # Determine data orientation by comparing dimensions with energy axis
        if electron_count_data.shape[0] == len(energy_axis):
            # Data is (energy, position) - transpose to (position, energy)
            electron_count_data = electron_count_data.transpose()
            
        # Create coordinates: single row (y=0), multiple columns (x=positions)
        y_coordinates = np.array([0], dtype=np.int32)  # Only one spatial row
        x_coordinates = np.arange(0, electron_count_data.shape[0], dtype=np.int32)  # Position along line
        
        # Reshape to standard xarray format: (y, x, energy)
        shape_dimensions = [1, electron_count_data.shape[0], electron_count_data.shape[1]]
        electron_count_data = electron_count_data.reshape(shape_dimensions)
        
        return electron_count_data, x_coordinates, y_coordinates
    
    def _process_2d_image_data(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Process 2D image data: keep (y, x) format.
        """
        # For 2D non-EELS images, preserve the natural 2D spatial structure
        # No need to add artificial energy dimensions

        # Generate spatial coordinate arrays for pixel positions
        y_coordinates = np.arange(0, data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, data.shape[1], dtype=np.int32)  # Pixel columns
        
        return data, x_coordinates, y_coordinates

    def _process_3d_data(self, electron_count_data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Process 3D spectrum image: transpose to (y, x, energy).
        """
        # Transpose from (energy, y, x) to (y, x, energy) for xarray compatibility
        electron_count_data = electron_count_data.transpose((1, 2, 0))
        
        # Generate spatial coordinates for the spectrum image
        y_coordinates = np.arange(0, electron_count_data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, electron_count_data.shape[1], dtype=np.int32)  # Pixel columns
        
        return electron_count_data, x_coordinates, y_coordinates
