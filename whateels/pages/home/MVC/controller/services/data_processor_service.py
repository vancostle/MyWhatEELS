"""
Scientific Data Processor for electron microscopy data processing operations.

This processor handles all scientific data manipulation and transformation operations
for both EELS (Electron Energy Loss Spectroscopy) and conventional imaging datasets. 
It focuses purely on data processing logic without any file I/O dependencies, 
making it reusable and testable.

Key Responsibilities:
- Data reshaping and dimensional transformations (1D → 2D → 3D)
- Coordinate system generation for spatial and energy axes
- NaN/infinity value cleaning and data sanitization
- xarray Dataset format standardization
- Dataset type classification (Single Spectrum, Spectrum Line, Spectrum Image, Image)
- Scientific data validation and quality control
- Dual processing paths for EELS and non-EELS data

Supported Data Types:
EELS Data:
- 1D: Single spectrum (energy only)
- 2D: Spectrum line (position × energy)  
- 3D: Spectrum image (y × x × energy)

Non-EELS Data:
- 2D: Conventional images (y × x spatial data)

Data Flow:
Raw numpy arrays → EELS/non-EELS detection → Dimensional analysis → 
Coordinate generation → Data cleaning → xarray Dataset → Type classification
"""

import numpy as np
import xarray as xr

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Model

class DataProcessorService:
    """
    Processes both EELS and non-EELS electron microscopy data into standardized xarray datasets.
    
    This service handles the complete data processing pipeline from raw numpy arrays
    to cleaned, coordinate-mapped xarray datasets. It automatically detects data type
    (EELS vs non-EELS) based on image names and routes to appropriate processing methods.
    
    Features:
    - Automatic EELS/non-EELS detection and routing
    - 1D/2D/3D data reshaping and coordinate generation
    - Data cleaning and validation
    - xarray Dataset standardization
    - No file I/O dependencies - pure data transformation operations
    """
    
    # Constants for dataset types
    _AXIS_X = 'x'
    _AXIS_Y = 'y'
    _ELOSS = 'Eloss'

    def __init__(self, model: "Model"):
        """Initialize the processor with a Model instance for constants/config."""
        self._model = model

    # --- Public Methods ---

    def clean_dataset(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Replace NaN/inf values with zeros in data and coordinates.
        
        Handles both EELS (3D with energy dimension) and non-EELS (2D spatial only) datasets.
        Preserves original dataset structure and metadata attributes.
        
        Args:
            dataset: xarray Dataset to clean
            
        Returns:
            xr.Dataset: Cleaned dataset with NaN/inf values replaced by zeros
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

    def determine_dataset_type(self, dataset: xr.Dataset, image_name: str) -> str:
        """
        Classify dataset type based on image name and spatial dimensions.
        
        First determines if data is EELS or non-EELS based on image name,
        then classifies EELS data by spatial dimensions.
        
        Args:
            dataset: xarray Dataset to classify
            image_name: Name of the image from metadata
            
        Returns:
            str: Dataset type constant (IMAGE, SINGLE_SPECTRUM, SPECTRUM_LINE, SPECTRUM_IMAGE)
            
        Classification Logic:
            Non-EELS: Always returns IMAGE
            EELS: 
                - (1,1) spatial → SINGLE_SPECTRUM
                - (1,x) spatial → SPECTRUM_LINE  
                - (y,x) spatial → SPECTRUM_IMAGE
        """

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

    def process_data_for_xarray(self, electron_count_data: np.ndarray, energy_axis: np.ndarray | None, image_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """
        Process raw electron microscopy data into xarray-compatible format.
        
        Main entry point for data processing that routes to appropriate methods
        based on data type (EELS vs non-EELS) and dimensionality.
        
        Args:
            electron_count_data: Raw numpy array of electron count data
            energy_axis: Energy values for EELS data (None for non-EELS)
            image_name: Image name from metadata for EELS detection
            
        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray] | None: 
                (processed_data, x_coordinates, y_coordinates) or None if failed
                
        Processing Routes:
            Non-EELS: → _process_2d_image_data() for 2D spatial data
            EELS: → _process_1d_data(), _process_2d_data(), or _process_3d_data()
                 based on input dimensionality
        """
        # Route to appropriate processing method based on data type and dimensionality
        
        EELS = "EELS"
        UNSUPPORTED_DIMENSION_MESSAGE = f"ERROR: Unsupported data dimensionality: {electron_count_data.shape}"

        # First branch: Check if this is EELS or non-EELS data
        if EELS not in image_name:
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
        Process 1D single spectrum: add spatial dims to create (y=1, x=1, energy).
        
        Converts single energy spectrum to standardized 3D format by adding
        artificial spatial dimensions.
        
        Args:
            electron_count_data: 1D array of energy spectrum data
            
        Returns:
            tuple: (reshaped_data, x_coordinates, y_coordinates)
                - reshaped_data: (1, 1, energy) format
                - x_coordinates: [0] (single point)
                - y_coordinates: [0] (single point)
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
        Process 2D spectrum line: detect orientation and reshape to (y=1, x, energy).
        
        Handles 2D EELS spectrum line data which can be oriented as either
        (energy, position) or (position, energy). Automatically detects orientation
        by comparing dimensions with energy axis length.
        
        Args:
            electron_count_data: 2D array of spectrum line data
            energy_axis: 1D array of energy values for orientation detection
            
        Returns:
            tuple: (reshaped_data, x_coordinates, y_coordinates)
                - reshaped_data: (1, x, energy) format
                - x_coordinates: position indices along the line
                - y_coordinates: [0] (single row)
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
        Process 2D non-EELS image data: keep natural (y, x) format.
        
        Handles conventional electron microscopy images (ADF, BF, etc.) that contain
        only spatial information without energy dimension. Preserves the natural
        2D structure without adding artificial dimensions.
        
        Args:
            data: 2D array of image intensity data
            
        Returns:
            tuple: (data, x_coordinates, y_coordinates)
                - data: unchanged 2D array
                - x_coordinates: pixel column indices
                - y_coordinates: pixel row indices
                
        Note: Debug prints are temporary for development tracking.
        """
        # For 2D non-EELS images, preserve the natural 2D spatial structure
        # No need to add artificial energy dimensions

        # Generate spatial coordinate arrays for pixel positions
        y_coordinates = np.arange(0, data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, data.shape[1], dtype=np.int32)  # Pixel columns
        
        return data, x_coordinates, y_coordinates

    def _process_3d_data(self, electron_count_data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Process 3D spectrum image: transpose (energy, y, x) → (y, x, energy).
        
        Handles 3D EELS spectrum image data by transposing from the typical
        DM file format (energy, y, x) to xarray-compatible format (y, x, energy).
        
        Args:
            electron_count_data: 3D array in (energy, y, x) format
            
        Returns:
            tuple: (transposed_data, x_coordinates, y_coordinates)
                - transposed_data: (y, x, energy) format
                - x_coordinates: pixel column indices
                - y_coordinates: pixel row indices
        """
        # Transpose from (energy, y, x) to (y, x, energy) for xarray compatibility
        electron_count_data = electron_count_data.transpose((1, 2, 0))
        
        # Generate spatial coordinates for the spectrum image
        y_coordinates = np.arange(0, electron_count_data.shape[0], dtype=np.int32)  # Pixel rows
        x_coordinates = np.arange(0, electron_count_data.shape[1], dtype=np.int32)  # Pixel columns
        
        return electron_count_data, x_coordinates, y_coordinates
