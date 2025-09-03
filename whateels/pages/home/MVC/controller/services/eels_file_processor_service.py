"""
EELS File Processor for DM3/DM4 file operations.

Handles file I/O, validation, and orchestrates the file-to-dataset pipeline.
Manages temporary files and delegates data processing to EELSDataProcessor.
"""

import os, numpy as np, xarray as xr, traceback
from pathlib import Path
from whateels.errors.dm.data import DMEmptyInfoDictionary, DMNonEelsError
from whateels.helpers import TempFile
from whateels.shared_state import AppState
from ..dm_file_processing import DM_EELS_Reader
from .eels_data_processor_service import EELSDataProcessorService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..dm_file_processing.readers.dm_eels_reader import DM_EELS_data

class EELSFileProcessorService:
    """
    Handles DM3/DM4 file I/O and orchestrates file-to-dataset processing.
    
    Manages file validation, temporary files, and coordinates with EELSDataProcessor
    for scientific data operations.
    """
    
    def __init__(self, model):
        self._model = model

    # -- Public Methods --

    def process_upload(self, filename: str, file_content: bytes) -> list[xr.Dataset]:
        """
        Process uploaded DM3/DM4 file bytes into EELS xarray datasets.
        
        Args:
            filename: Name of the uploaded file
            file_content: Binary content of the uploaded file
            
        Returns:
            List of xarray.Dataset objects extracted from the file
        """
        ERROR_MESSAGE_LOADING_FILE = "Error loading DM file - Invalid or corrupted DM3/DM4 file: {}"
        ERROR_MESSAGE_FILE_UPLOAD = "Error during file upload processing: {}"
        
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
                    print(ERROR_MESSAGE_LOADING_FILE.format(filename))
                    return []
                
                return all_datasets
            except Exception as e:
                print(ERROR_MESSAGE_FILE_UPLOAD.format(e))
                traceback.print_exc()
                return []

    # -- Private Methods --

    def _load_dm_file(self, filepath) -> list[xr.Dataset]:
        """
        Load DM3/DM4 file and convert to xarray datasets with metadata.
        
        Args:
            filepath: Path to the DM3/DM4 file
            
        Returns:
            Tuple of (None or first dataset, list of all datasets)
        """
        try:
            # Check file size first
            if not self._validate_file_size(filepath):
                return None, []

            # Read the file
            dm_eels_reader = DM_EELS_Reader(filepath)

            # Get file metadata
            all_metadata_file = dm_eels_reader.file_metadata
            eels_data: DM_EELS_data = dm_eels_reader.processed_all_eels_spectrums

            # Store metadata in AppState for global access
            self._store_metadata(all_metadata_file)

            all_spectrum_images = eels_data.all_data
            all_energy_axes = eels_data.all_energy_axes

            # Check for NaN/inf in raw data
            self._log_all_data_quality(all_spectrum_images, all_energy_axes)

            # Clean energy axis for NaN/inf values
            cleaned_all_energy_axes = self._clean_all_axes(all_energy_axes)

            # Clean electron count data
            cleaned_all_electron_count_data = self._clean_all_electron_count_data(all_spectrum_images)

            # Add metadata and return
            all_datasets: list[xr.Dataset] = self._create_all_datasets_from_data(
                cleaned_all_electron_count_data, 
                cleaned_all_energy_axes,
                eels_data, 
                filepath
            )

            return all_datasets

        except Exception as exception:
            return self._handle_file_error(exception)
        
    def _clean_all_electron_count_data(self, all_electron_count_data: list[np.ndarray]) -> list[np.ndarray]:
        """
        Clean all electron count data arrays by replacing NaN and Inf values with zeros.
        
        Args:
            all_electron_count_data: List of electron count numpy arrays
            
        Returns:
            List of cleaned electron count arrays
        """
        cleaned_electron_count_data = []
        for electron_count_data in all_electron_count_data:
            cleaned_electron_count_data.append(np.nan_to_num(electron_count_data, nan=0.0, posinf=0.0, neginf=0.0))
        return cleaned_electron_count_data

    def _clean_all_axes(self, all_energy_axes) -> list[np.ndarray]:
        """
        Clean all energy axis arrays by replacing NaN and Inf values with zeros.
        
        Args:
            all_energy_axes: List of energy axis numpy arrays
            
        Returns:
            List of cleaned energy axis arrays
        """
        cleaned_energy_axes = []
        for energy_axis in all_energy_axes:
            cleaned_energy_axis = np.nan_to_num(energy_axis, nan=0.0, posinf=0.0, neginf=0.0)
            cleaned_energy_axes.append(cleaned_energy_axis)
        return cleaned_energy_axes

    def _store_metadata(self, infoDict=None):
        """
        Store file metadata from parsed info dictionary in AppState.
        
        Args:
            infoDict: Dictionary containing parsed file metadata
            
        Raises:
            DMEmptyInfoDictionary: If infoDict is None or empty
            DMNonEelsError: If storing metadata fails
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

    def _validate_file_size(self, filepath):
        """
        Validate file size for DM files.
        
        Args:
            filepath: Path to the file to validate
            
        Returns:
            bool: True if file size is valid, False otherwise
        """
        FILE_SIZE_TOO_SMALL_MESSAGE = "File size is too small for a valid DM3/DM4 file. Expected at least 1KB."
        MIN_FILE_SIZE = 1000  # Minimum size in bytes for a valid DM3/DM4 file

        file_size = os.path.getsize(filepath)

        if file_size < MIN_FILE_SIZE:  # Less than 1KB is suspicious for DM files
            print(FILE_SIZE_TOO_SMALL_MESSAGE)
            return False
        return True

    def _log_all_data_quality(self, all_electron_count_data, all_energy_axes):
        """
        Log data quality information for all spectra including NaN and Inf counts.
        
        Args:
            all_electron_count_data: List of electron count arrays to check
            all_energy_axes: List of energy axis arrays to check
        """
        
        RAW_DATA_QUALITY_ISSUES_MESSAGE = "Warning: Raw data has {} NaN values and {} Inf values"
        ENERGY_AXIS_QUALITY_ISSUES_MESSAGE = "Warning: Energy axis has {} NaN values and {} Inf values"

        for _, (electron_count_data, energy_axis) in enumerate(zip(all_electron_count_data, all_energy_axes)):
            data_nan_count = np.isnan(electron_count_data).sum()
            data_inf_count = np.isinf(electron_count_data).sum()
            energy_nan_count = np.isnan(energy_axis).sum()
            energy_inf_count = np.isinf(energy_axis).sum()
            
            # Only log if there are quality issues
            if data_nan_count > 0 or data_inf_count > 0:
                print(RAW_DATA_QUALITY_ISSUES_MESSAGE.format(data_nan_count, data_inf_count))
            if energy_nan_count > 0 or energy_inf_count > 0:
                print(ENERGY_AXIS_QUALITY_ISSUES_MESSAGE.format(energy_nan_count, energy_inf_count))

    def _create_all_datasets_from_data(self, all_spectrum_images, all_energy_axes, eels_data, filepath) -> list[xr.Dataset]:
        """
        Create xarray datasets from all processed EELS data and metadata.
        
        Args:
            all_spectrum_images: List of processed spectrum image arrays
            all_energy_axes: List of processed energy axis arrays  
            eels_data: DM_EELS_data object containing metadata and spectral info
            filepath: Path to the original DM file
            
        Returns:
            List of xarray.Dataset objects, one per spectrum/image
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
        
        eels_data_processor = EELSDataProcessorService(self._model)
        all_spectrum_metadata = list(eels_data.all_spectral_info.values())
        all_datasets = []

        for image, metadata, energy_axis in zip(all_spectrum_images, all_spectrum_metadata, all_energy_axes):
            processed_data = eels_data_processor.process_data_for_xarray(image, energy_axis)
            if processed_data is None:
                continue

            image, x_coordinates, y_coordinates = processed_data
            
            shape = image.shape
            len_x_axis = len(x_coordinates)
            len_y_axis = len(y_coordinates)
            len_energy_axis = len(energy_axis)
            
            # Validate dimensions match
            if shape != (len_y_axis, len_x_axis, len_energy_axis):
                print(f"ERROR: Shape mismatch!")
                print(f"Expected: ({len_y_axis}, {len_x_axis}, {len_energy_axis})")
                print(f"Actual: {shape}")
                return []
            
            dataset = xr.Dataset({
                ELECTRON_COUNT: ([Y, X, ELOSS], image)},
                coords={Y: y_coordinates, X: x_coordinates, ELOSS: energy_axis
            })
            
            # Clean dataset for NaN/inf values
            dataset = eels_data_processor.clean_dataset(dataset)
            
            # Determine dataset type using the data service
            dataset_type = eels_data_processor.determine_dataset_type(dataset)
            
            # Add metadata
            dataset.attrs[ORIGINAL_NAME] = os.path.basename(filepath)
            dataset.attrs[DATASET_TYPE] = dataset_type
            dataset.attrs[BEAM_ENERGY] = eels_data.get_beam_energy(metadata)
            dataset.attrs[COLLECTION_ANGLE] = eels_data.get_collection_angle(metadata)
            dataset.attrs[CONVERGENCE_ANGLE] = eels_data.get_convergence_angle(metadata)

            try:
                dataset.attrs[IMAGE_NAME] = eels_data.get_image_name(metadata)
                dataset.attrs[SHAPE] = list(dataset[ELECTRON_COUNT].shape)
            except Exception:
                pass
            
            all_datasets.append(dataset)

        return all_datasets

    def _handle_file_error(self, exception) -> list:
        """
        Handle file loading errors and return appropriate error response.
        
        Args:
            exception: The exception that occurred during file loading
            
        Returns:
            Tuple of ([]) for all error cases
        """
        error_message = str(exception)
        if "Expected versions 3 or 4" in error_message:
            print(f"Error loading DM file - Invalid or corrupted DM3/DM4 file: {exception}")
            return []
        elif "File size" in error_message and "too small" in error_message:
            print(f"Error loading DM file - File too small: {exception}")
            return []
        else:
            print(f"Error loading DM file: {exception}")
            return []
