"""
EELS Data Processor for scientific data processing operations.

This processor handles all scientific data manipulation and transformation operations
for EELS (Electron Energy Loss Spectroscopy) datasets. It focuses purely on data
processing logic without any file I/O dependencies, making it reusable and testable.

Key Responsibilities:
- Data reshaping and dimensional transformations (1D → 2D → 3D)
- Coordinate system generation for spatial and energy axes
- NaN/infinity value cleaning and data sanitization
- xarray Dataset format standardization
- Dataset type classification (Single Spectrum, Spectrum Line, Spectrum Image)
- Scientific data validation and quality control

Supported Data Types:
- 1D: Single spectrum (energy only)
- 2D: Spectrum line (position × energy)  
- 3D: Spectrum image (y × x × energy)

Data Flow:
Raw numpy arrays → Dimensional analysis → Coordinate generation → 
Data cleaning → xarray Dataset → Type classification
"""

import numpy as np
import xarray as xr

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model

class DataProcessorService:
    """
    Processes EELS data arrays into standardized xarray datasets.
    
    Handles 1D/2D/3D data reshaping, coordinate generation, and data cleaning.
    No file I/O dependencies - pure data transformation operations.
    """
    
    # Constants for dataset types
    _AXIS_X = 'x'
    _AXIS_Y = 'y'
    _ELOSS = 'Eloss'

    def __init__(self, model: "Model"):
        """Initialize the processor with a Model instance for constants/config."""
        self._model = model

    # --- Public Methods ---

    def clean_dataset(self, dataset):
        """Replace NaN/inf values with zeros in data and coordinates."""
        
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

    def determine_dataset_type(self, dataset: xr.Dataset, image_name: str) -> str:
        """Classify dataset as Single Spectrum, Spectrum Line, or Spectrum Image based on spatial dimensions."""

        EELS = "EELS"

        x_size = len(dataset.coords[self._AXIS_X])
        y_size = len(dataset.coords[self._AXIS_Y])
        
        # First check if this is EELS data
        if EELS not in image_name:
            return self._model.constants.IMAGE  # Non-EELS data is just an image

        # For EELS data, classify based on dimensions
        if x_size == 1 and y_size == 1:
            return self._model.constants.SINGLE_SPECTRUM
        elif y_size == 1:
            return self._model.constants.SPECTRUM_LINE
        else:
            return self._model.constants.SPECTRUM_IMAGE

    def process_data_for_xarray(self, electron_count_data, energy_axis, image_name: str) -> xr.Dataset | None:
        """Process raw EELS data into xarray format (y, x, energy)."""
        # Route to appropriate processing method based on data dimensionality
        
        EELS = "EELS"
        UNSUPPORTED_DIMENSION_MESSAGE = f"ERROR: Unsupported data dimensionality: {electron_count_data.shape}"

        # Check if this is EELS or non-EELS data
        if EELS not in image_name:
            return self._process_2d_image_data(electron_count_data)

        len_shape = len(electron_count_data.shape)

        print(f"Shape {electron_count_data.shape} Name {image_name}")

        if len_shape == 1:
            return self._process_1d_data(electron_count_data)
        elif len_shape == 2:
            return self._process_2d_data(electron_count_data, energy_axis)
        elif len_shape == 3:
            return self._process_3d_data(electron_count_data)
        else:
            print(UNSUPPORTED_DIMENSION_MESSAGE)
            return None

    # --- Private Methods ---

    def _process_1d_data(self, electron_count_data):
        """Process 1D single spectrum: add spatial dims to create (y=1, x=1, energy)."""
        # Create artificial spatial coordinates (single point at origin)
        x_coordinates = np.array([0], dtype=np.int32)  # Single point in x
        y_coordinates = np.array([0], dtype=np.int32)  # Single point in y
        
        # Reshape from (energy,) to (y=1, x=1, energy) format
        shape_dimensions = [1, 1]
        shape_dimensions.extend(list(electron_count_data.shape))
        electron_count_data = electron_count_data.reshape(shape_dimensions)
        
        return electron_count_data, x_coordinates, y_coordinates

    def _process_2d_data(self, electron_count_data, energy_axis):
        """Process 2D spectrum line: detect orientation and reshape to (y=1, x, energy)."""
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
    
    def _process_2d_image_data(self, data):
        """Process 2D non-EELS image data: keep natural (y, x) format."""
        # For 2D images (non-EELS), keep the natural 2D shape
        # No need to add artificial dimensions
        
        print(f"Processing 2D image data - Input shape: {data.shape}")
        
        # Generate spatial coordinates
        y_coordinates = np.arange(0, data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, data.shape[1], dtype=np.int32)  # Pixel columns

        print(f"Generated coordinates - Y: {len(y_coordinates)}, X: {len(x_coordinates)}")
        print(f"Output shape: {data.shape}")
        
        return data, x_coordinates, y_coordinates

    def _process_3d_data(self, electron_count_data):
        """Process 3D spectrum image: transpose (energy, y, x) → (y, x, energy)."""
        # Transpose from (energy, y, x) to (y, x, energy) for xarray compatibility
        electron_count_data = electron_count_data.transpose((1, 2, 0))
        
        # Generate spatial coordinates for the spectrum image
        y_coordinates = np.arange(0, electron_count_data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, electron_count_data.shape[1], dtype=np.int32)  # Pixel columns
        
        return electron_count_data, x_coordinates, y_coordinates
