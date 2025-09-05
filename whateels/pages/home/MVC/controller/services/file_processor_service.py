"""
Scientific Data File Processor for DM3/DM4 electron microscopy files.

This processor handles the complete file-to-dataset pipeline for electron microscopy
data files. It manages file I/O operations, validation, temporary file handling, and
orchestrates the conversion from raw DM file data to standardized xarray datasets
for both EELS and non-EELS data types.

Key Responsibilities:
- DM3/DM4 file format reading and validation
- Temporary file management with automatic cleanup
- File size and format validation
- Data quality assessment and logging
- Coordination with DataProcessorService for scientific data transformation
- Metadata extraction and storage in application state
- Error handling and recovery for file operations

Supported File Types:
- DM3 (Digital Micrograph version 3)
- DM4 (Digital Micrograph version 4)

Data Types Handled:
- EELS spectrum images (3D: y × x × energy)
- EELS spectrum lines (2D: position × energy)
- EELS single spectra (1D: energy only)
- Conventional electron microscopy images (2D: y × x spatial)

Processing Pipeline:
Raw DM file → File validation → Data extraction → Quality assessment →
Data cleaning → Dataset creation → Metadata attachment → xarray Dataset output
"""

import os, numpy as np, xarray as xr
from pathlib import Path
from whateels.errors.dm import (
    DMEmptyInfoDictionary, 
    DMNonEelsError, 
    DMShapeMismatchError, 
    DMFileLoadingError, 
    DMFileUploadError
)
from whateels.helpers import TempFile
from whateels.shared_state import AppState
from ..dm_file_processing import DM_EELS_Reader
from .data_processor_service import DataProcessorService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..dm_file_processing.readers.dm_eels_reader import DM_EELS_data
    from ...model import Model

class FileProcessorService:
    """
    Handles DM3/DM4 file I/O and orchestrates file-to-dataset processing pipeline.
    
    This service manages the complete workflow from uploaded file bytes to processed
    xarray datasets. It handles file validation, temporary file operations, data
    extraction, quality assessment, and coordinates with DataProcessorService for
    scientific data transformations.
    
    Features:
    - Automatic file format detection and validation
    - Temporary file management with cleanup
    - Data quality assessment and cleaning
    - Metadata extraction and storage
    - Error handling and recovery
    - Support for both EELS and non-EELS data processing
    """
    
    def __init__(self, model: "Model"):
        """
        Initialize the file processor with model configuration.
        
        Args:
            model: Application model containing constants and configuration
        """
        self._model = model

    # -- Public Methods --

    def process_upload(self, filename: str, file_content: bytes) -> list[xr.Dataset]:
        """
        Process uploaded DM3/DM4 file bytes into electron microscopy xarray datasets.
        
        Main entry point for file processing that handles the complete pipeline from
        uploaded file bytes to processed datasets. Creates temporary files, validates
        content, and orchestrates data extraction and processing.
        
        Args:
            filename: Name of the uploaded file (used for extension detection)
            file_content: Binary content of the uploaded DM3/DM4 file
            
        Returns:
            list[xr.Dataset]: List of processed xarray datasets, one per image/spectrum
            
        Raises:
            DMFileLoadingError: When DM file cannot be loaded or is corrupted
            DMFileUploadError: When file upload processing fails
            DMShapeMismatchError: When data dimensions don't match expectations
        """
        BINARY_WRITE_MODE = 'wb'
        
        # Get the correct file extension from the uploaded filename
        file_extension = Path(filename).suffix
        
        # Create temporary file that will be automatically cleaned up
        with TempFile(suffix=file_extension, prefix=self._model.constants.TEMP_PREFIX) as temp_path:
            try:
                # Write the uploaded binary content to temporary file
                with open(temp_path, BINARY_WRITE_MODE) as f:
                    f.write(file_content)
                
                all_datasets: list[xr.Dataset] = []

                # Load the DM3/DM4 file and convert to xarray dataset
                all_datasets = self._load_dm_file(temp_path)

                if not all_datasets:
                    raise DMFileLoadingError(filename)
                
                return all_datasets
            except DMFileLoadingError:
                raise  # Re-raise DM-specific errors as-is
            except Exception as e:
                raise DMFileUploadError(e)

    # -- Private Methods --

    def _load_dm_file(self, filepath: str) -> list[xr.Dataset]:
        """
        Load DM3/DM4 file and convert to xarray datasets with metadata.
        
        Handles the complete data extraction and processing pipeline including
        file validation, data reading, quality assessment, cleaning, and dataset creation.
        
        Args:
            filepath: Path to the DM3/DM4 file to process
            
        Returns:
            list[xr.Dataset]: List of processed datasets, empty list if loading fails
            
        Processing Steps:
            1. File size validation
            2. DM file reading and metadata extraction
            3. Data quality assessment and logging
            4. Data cleaning (NaN/inf handling)
            5. Dataset creation with metadata
        """
        try:
            # Validate file size before processing
            if not self._validate_file_size(filepath):
                return []

            # Read the DM file and extract data
            dm_eels_reader = DM_EELS_Reader(filepath)

            # Extract file metadata and processed spectral data
            all_metadata_file = dm_eels_reader.file_metadata
            eels_data: DM_EELS_data = dm_eels_reader.processed_all_eels_spectrums

            # Store metadata in application state for global access
            self._store_metadata(all_metadata_file)

            # Extract raw spectral data and energy axes
            all_spectrum_images = eels_data.all_data
            all_energy_axes = eels_data.all_energy_axes

            # Assess and log data quality issues (NaN/inf detection)
            self._log_all_data_quality(all_spectrum_images, all_energy_axes)

            # Clean data arrays by replacing NaN/inf values with zeros
            cleaned_all_energy_axes = self._clean_all_axes(all_energy_axes)
            cleaned_all_electron_count_data = self._clean_all_electron_count_data(all_spectrum_images)

            # Create standardized xarray datasets with metadata
            all_datasets: list[xr.Dataset] = self._create_all_datasets_from_data(
                cleaned_all_electron_count_data, 
                cleaned_all_energy_axes,
                eels_data, 
                filepath
            )

            return all_datasets

        except Exception as exception:
            self._handle_file_error(exception)
        
    def _clean_all_electron_count_data(self, all_electron_count_data: list[np.ndarray]) -> list[np.ndarray]:
        """
        Clean all electron count data arrays by replacing NaN and Inf values.
        
        Processes each electron count array in the list to replace invalid values
        (NaN, positive infinity, negative infinity) with zeros to ensure numerical
        stability in downstream processing.
        
        Args:
            all_electron_count_data: List of raw electron count numpy arrays
            
        Returns:
            list[np.ndarray]: List of cleaned electron count arrays with invalid values replaced
        """
        cleaned_electron_count_data = []
        for electron_count_data in all_electron_count_data:
            cleaned_electron_count_data.append(np.nan_to_num(electron_count_data, nan=0.0, posinf=0.0, neginf=0.0))
        return cleaned_electron_count_data

    def _clean_all_axes(self, all_energy_axes: list[np.ndarray]) -> list[np.ndarray]:
        """
        Clean all energy axis arrays by replacing NaN and Inf values.
        
        Processes each energy axis array to replace invalid values with zeros,
        ensuring that coordinate systems remain numerically stable for xarray operations.
        
        Args:
            all_energy_axes: List of raw energy axis numpy arrays
            
        Returns:
            list[np.ndarray]: List of cleaned energy axis arrays with invalid values replaced
        """
        cleaned_energy_axes = []
        for energy_axis in all_energy_axes:
            cleaned_energy_axis = np.nan_to_num(energy_axis, nan=0.0, posinf=0.0, neginf=0.0)
            cleaned_energy_axes.append(cleaned_energy_axis)
        return cleaned_energy_axes

    def _store_metadata(self, infoDict: dict | None = None) -> None:
        """
        Store file metadata from parsed info dictionary in application state.
        
        Extracts and stores metadata from the DM file parsing operation into the
        global application state for access by other components.
        
        Args:
            infoDict: Dictionary containing parsed file metadata from DM reader
            
        Raises:
            DMEmptyInfoDictionary: If infoDict is None or empty
            DMNonEelsError: If storing metadata in AppState fails
        """
        NOT_INFO_DICT_MESSAGE = "Expected an information dictionary from parser. None provided. {}"
        FAILED_TO_STORE_METADATA_MESSAGE = "Failed to store metadata in AppState. {}"

        if not infoDict:
            raise DMEmptyInfoDictionary(NOT_INFO_DICT_MESSAGE.format(infoDict))
        try:
            # Store metadata in AppState for application-wide access
            AppState().metadata = infoDict
        except Exception:
            raise DMNonEelsError(FAILED_TO_STORE_METADATA_MESSAGE.format(infoDict.keys() if infoDict else 'None'))

    def _validate_file_size(self, filepath: str) -> bool:
        """
        Validate file size for DM files to ensure minimum viable content.
        
        Checks if the file size meets minimum requirements for a valid DM3/DM4 file.
        Files that are too small are likely corrupted or incomplete.
        
        Args:
            filepath: Path to the file to validate
            
        Returns:
            bool: True if file size is valid (>= 1KB), False otherwise
        """
        FILE_SIZE_TOO_SMALL_MESSAGE = "File size is too small for a valid DM3/DM4 file. Expected at least 1KB."
        MIN_FILE_SIZE = 1000  # Minimum size in bytes for a valid DM3/DM4 file

        file_size = os.path.getsize(filepath)

        if file_size < MIN_FILE_SIZE:
            print(FILE_SIZE_TOO_SMALL_MESSAGE)
            return False
        return True

    # TODO - Check this functions. It seems incomplete
    def _log_all_data_quality(self, all_electron_count_data: list[np.ndarray], all_energy_axes: list[np.ndarray]) -> None:
        """
        Assess and log data quality information for all spectra.
        
        Analyzes each spectrum and energy axis for data quality issues including
        NaN and infinity values. This information is useful for understanding
        data integrity and potential processing issues.
        
        Args:
            all_electron_count_data: List of electron count arrays to analyze
            all_energy_axes: List of energy axis arrays to analyze
            
        Note:
            Only logs warnings when quality issues are detected to avoid spam.
        """
        
        RAW_DATA_QUALITY_ISSUES_MESSAGE = "Warning: Raw data has {} NaN values and {} Inf values"
        ENERGY_AXIS_QUALITY_ISSUES_MESSAGE = "Warning: Energy axis has {} NaN values and {} Inf values"

        for _, (electron_count_data, energy_axis) in enumerate(zip(all_electron_count_data, all_energy_axes)):
            # Count invalid values for quality assessment
            data_nan_count = np.isnan(electron_count_data).sum()
            data_inf_count = np.isinf(electron_count_data).sum()
            
            # Only check energy axis quality if it exists (EELS data)
            if energy_axis is not None:
                energy_nan_count = np.isnan(energy_axis).sum()
                energy_inf_count = np.isinf(energy_axis).sum()
            else:
                # Non-EELS data - no energy axis to check
                energy_nan_count = 0
                energy_inf_count = 0

    def _create_all_datasets_from_data(self, all_spectrum_images: list[np.ndarray], all_energy_axes: list[np.ndarray], eels_data: "DM_EELS_data", filepath: str) -> list[xr.Dataset]:
        """
        Create xarray datasets from all processed electron microscopy data and metadata.
        
        Converts processed numpy arrays into standardized xarray datasets with proper
        coordinate systems, dimensions, and metadata attributes. Handles both EELS
        and non-EELS data types with appropriate dimensionality and coordinate systems.
        
        Args:
            all_spectrum_images: List of processed spectrum/image arrays
            all_energy_axes: List of processed energy axis arrays (None for non-EELS)
            eels_data: DM_EELS_data object containing metadata and spectral information
            filepath: Path to the original DM file for provenance tracking
            
        Returns:
            list[xr.Dataset]: List of xarray datasets with proper coordinates and metadata
            
        Dataset Structure:
            EELS data: 3D with coordinates [y, x, Eloss]
            Non-EELS data: 2D with coordinates [y, x]
        """
        ELECTRON_COUNT = 'ElectronCount'
        X = 'x'
        Y = 'y'
        ELOSS = 'Eloss'
        
        ORIGINAL_NAME = 'original_name'
        DATASET_TYPE = 'dataset_type'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        IMAGE_NAME = 'image_name'
        SHAPE = 'shape'
        EELS = 'EELS'

        eels_data_processor = DataProcessorService(self._model)
        all_spectrum_metadata = list(eels_data.all_spectral_info.values())
        all_datasets = []

        for image, metadata, energy_axis in zip(all_spectrum_images, all_spectrum_metadata, all_energy_axes):
            image_name = eels_data.get_image_name(metadata)

            # Process raw data into xarray-compatible format
            processed_data = eels_data_processor.process_data_for_xarray(image, energy_axis, image_name)
            if processed_data is None:
                continue

            image, x_coordinates, y_coordinates = processed_data
            
            shape = image.shape
            len_x_axis = len(x_coordinates)
            len_y_axis = len(y_coordinates)
            
            # Determine dataset structure based on data type (EELS vs non-EELS)
            if EELS in image_name:
                # EELS data: 3D format (y, x, energy) with energy coordinates
                len_energy_axis = len(energy_axis) if energy_axis is not None else 1
                expected_shape = (len_y_axis, len_x_axis, len_energy_axis)
                coord_dims = [Y, X, ELOSS]
                energy_coords = energy_axis if energy_axis is not None else np.array([0.0])
            else:
                # Non-EELS data: 2D format (y, x) with spatial coordinates only
                expected_shape = (len_y_axis, len_x_axis)
                coord_dims = [Y, X]
                energy_coords = None
            
            # Validate that processed data matches expected dimensions
            if shape != expected_shape:
                raise DMShapeMismatchError(image_name, expected_shape, shape)
            
            # Create xarray dataset with appropriate coordinate system
            if EELS in image_name:
                dataset = xr.Dataset(
                    {ELECTRON_COUNT: (coord_dims, image)},
                    coords={Y: y_coordinates, X: x_coordinates, ELOSS: energy_coords}
                )
            else:
                dataset = xr.Dataset(
                    {ELECTRON_COUNT: (coord_dims, image)},
                    coords={Y: y_coordinates, X: x_coordinates}
                )
            # Apply data cleaning to remove NaN/inf values
            dataset = eels_data_processor.clean_dataset(dataset)
            
            # Determine appropriate dataset type for visualization routing
            dataset_type = eels_data_processor.determine_dataset_type(dataset, image_name)
            
            # Attach comprehensive metadata attributes
            dataset.attrs[ORIGINAL_NAME] = os.path.basename(filepath)
            dataset.attrs[DATASET_TYPE] = dataset_type
            dataset.attrs[BEAM_ENERGY] = eels_data.get_beam_energy(metadata)
            dataset.attrs[COLLECTION_ANGLE] = eels_data.get_collection_angle(metadata)
            dataset.attrs[CONVERGENCE_ANGLE] = eels_data.get_convergence_angle(metadata)

            # Add optional metadata with error handling
            try:
                dataset.attrs[IMAGE_NAME] = eels_data.get_image_name(metadata)
                dataset.attrs[SHAPE] = list(dataset.ElectronCount.shape)
            except Exception:
                pass
            
            all_datasets.append(dataset)

        return all_datasets

    def _handle_file_error(self, exception: Exception) -> list:
        """
        Handle file loading errors and re-raise as appropriate DM exceptions.
        
        Processes different types of file loading exceptions and re-raises them
        as specific DM error types for better error handling upstream.
        
        Args:
            exception: The exception that occurred during file loading
            
        Raises:
            DMFileLoadingError: For invalid/corrupted DM files or file size issues
            Exception: Re-raises the original exception if it doesn't match known patterns
            
        Error Categories:
            - Invalid/corrupted DM file format → DMFileLoadingError
            - File size validation failures → DMFileLoadingError
            - General file processing errors → Re-raised as original exception
        """
        error_message = str(exception)
        
        # Categorize and re-raise as appropriate DM exceptions
        if "Expected versions 3 or 4" in error_message:
            # Invalid or corrupted DM file format
            raise DMFileLoadingError(f"Invalid or corrupted DM3/DM4 file: {exception}")
        elif "File size" in error_message and "too small" in error_message:
            # File size validation failure
            raise DMFileLoadingError(f"File too small: {exception}")
        else:
            # General file processing error - re-raise original
            raise exception
