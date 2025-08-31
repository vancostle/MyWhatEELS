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

class EELSDataProcessorService:
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
        try:
            # Clean the main electron count data array
            electron_count = dataset.ElectronCount.values
            electron_count = np.nan_to_num(electron_count, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Clean all coordinate arrays to prevent axis issues
            x_coords = dataset.coords[self._AXIS_X].values
            y_coords = dataset.coords[self._AXIS_Y].values
            eloss_coords = dataset.coords[self._ELOSS].values

            # Sanitize coordinate arrays
            x_coords = np.nan_to_num(x_coords, nan=0.0, posinf=0.0, neginf=0.0)
            y_coords = np.nan_to_num(y_coords, nan=0.0, posinf=0.0, neginf=0.0)
            eloss_coords = np.nan_to_num(eloss_coords, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Reconstruct dataset with cleaned data and coordinates
            cleaned_dataset = xr.Dataset(
                {
                    'ElectronCount': (dataset.ElectronCount.dims, electron_count)
                },
                coords={
                    self._AXIS_X: x_coords, 
                    self._AXIS_Y: y_coords, 
                    self._ELOSS: eloss_coords
                }
            )
            
            # Preserve original metadata attributes
            cleaned_dataset.attrs = dataset.attrs.copy()
            
            return cleaned_dataset
        except Exception as e:
            print(f"Warning: Could not clean dataset: {e}")
            return dataset

    def determine_dataset_type(self, dataset: xr.Dataset) -> str:
        """Classify dataset as Single Spectrum, Spectrum Line, or Spectrum Image based on spatial dimensions."""
        x_size = len(dataset.coords[self._AXIS_X])
        y_size = len(dataset.coords[self._AXIS_Y])
        if x_size == 1 and y_size == 1:
            return self._model.constants.SINGLE_SPECTRUM
        elif y_size == 1:
            return self._model.constants.SPECTRUM_LINE
        else:
            return self._model.constants.SPECTRUM_IMAGE

    def process_data_for_xarray(self, electron_count_data, energy_axis):
        """Process raw EELS data into xarray format (y, x, energy)."""
        # Route to appropriate processing method based on data dimensionality
        if len(electron_count_data.shape) == 3:
            return self._process_3d_data(electron_count_data)
        elif len(electron_count_data.shape) == 2:
            return self._process_2d_data(electron_count_data, energy_axis)
        elif len(electron_count_data.shape) == 1:
            return self._process_1d_data(electron_count_data)
        else:
            print(f"ERROR: Unsupported data dimensionality: {electron_count_data.shape}")
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

    def _process_3d_data(self, electron_count_data):
        """Process 3D spectrum image: transpose (energy, y, x) → (y, x, energy)."""
        # Transpose from (energy, y, x) to (y, x, energy) for xarray compatibility
        electron_count_data = electron_count_data.transpose((1, 2, 0))
        
        # Generate spatial coordinates for the spectrum image
        y_coordinates = np.arange(0, electron_count_data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, electron_count_data.shape[1], dtype=np.int32)  # Pixel columns
        
        return electron_count_data, x_coordinates, y_coordinates
