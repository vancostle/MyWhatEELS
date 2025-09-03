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

    def process_upload(self, filename: str, file_content: bytes) -> tuple[xr.Dataset | None, list[xr.Dataset]]:
        """Process uploaded file bytes into EELS dataset."""
        # Get the correct file extension from the uploaded filename
        file_extension = Path(filename).suffix
        
        # Create temporary file that will be automatically cleaned up
        with TempFile(suffix=file_extension, prefix=self._model.constants.TEMP_PREFIX) as temp_path:
            try:
                # Write the file content to a temporary file
                with open(temp_path, 'wb') as f:
                    f.write(file_content)
                
                dataset: xr.Dataset | None
                all_datasets: list[xr.Dataset] = []

                # Load the DM3/DM4 file and convert to xarray dataset
                dataset, all_datasets = self._load_dm_file(temp_path)

                if dataset is None:
                    print(f'Error loading file: {filename}')
                    return None, []
                
                return dataset, all_datasets
            except Exception as e:
                print(f"Error during file upload processing: {e}")
                traceback.print_exc()
                return None, []

    # -- Private Methods --
    
    def _load_dm_file(self, filepath) -> tuple[xr.Dataset | None, list[xr.Dataset]]:
        """Load DM3/DM4 file and convert to xarray dataset with metadata."""
        try:
            # Check file size first
            if not self._validate_file_size(filepath):
                return None, []

            # Read the file
            dm_eels_reader = DM_EELS_Reader(filepath)

            # Get file metadata
            all_metadata_file = dm_eels_reader.file_metadata
            spectrum_image: DM_EELS_data = dm_eels_reader.processed_eels_spectrum
            eels_data: DM_EELS_data = dm_eels_reader.processed_all_eels_spectrums

            # print("all_spectrum_images:", all_spectrum_images.all_data)
            # print("length:", len(all_spectrum_images.all_data))

            # Store metadata in AppState for global access
            self._store_metadata(all_metadata_file)

            # Get data and energy axis
            electron_count_data = spectrum_image.data
            energy_axis = spectrum_image.energy_axis

            all_spectrum_images = eels_data.all_data
            all_energy_axes = eels_data.all_energy_axes

            # Check for NaN/inf in raw data
            # self._log_data_quality(electron_count_data, energy_axis) # TODO - DELETE IT
            self._log_all_data_quality(all_spectrum_images, all_energy_axes)

            # Clean energy axis for NaN/inf values
            cleaned_energy_axis = np.nan_to_num(energy_axis, nan=0.0, posinf=0.0, neginf=0.0) # TODO - DELETE IT
            cleaned_all_energy_axes = self._clean_all_axes(all_energy_axes)

            # Clean electron count data
            cleaned_electron_count_data = np.nan_to_num(electron_count_data, nan=0.0, posinf=0.0, neginf=0.0) # TODO - DELETE IT
            cleaned_all_electron_count_data = self._clean_all_electron_count_data(all_spectrum_images)

            # Add metadata and return
            dataset: xr.Dataset | None = self._create_dataset_from_data(cleaned_electron_count_data, cleaned_energy_axis, spectrum_image, filepath)
            all_datasets: list[xr.Dataset] = self._create_all_datasets_from_data(cleaned_all_electron_count_data, cleaned_all_energy_axes, eels_data, filepath)

            return dataset, all_datasets

        except Exception as exception:
            return self._handle_file_error(exception)
        
    def _clean_all_electron_count_data(self, all_electron_count_data: list[np.ndarray]) -> list[np.ndarray]:
        cleaned_electron_count_data = []
        for electron_count_data in all_electron_count_data:
            cleaned_electron_count_data.append(np.nan_to_num(electron_count_data, nan=0.0, posinf=0.0, neginf=0.0))
        return cleaned_electron_count_data

    def _clean_all_axes(self, all_energy_axes) -> list[np.ndarray]:
        cleaned_energy_axes = []
        for energy_axis in all_energy_axes:
            cleaned_energy_axis = np.nan_to_num(energy_axis, nan=0.0, posinf=0.0, neginf=0.0)
            cleaned_energy_axes.append(cleaned_energy_axis)
        return cleaned_energy_axes

    def _store_metadata(self, infoDict=None):
        """
        Store file handle and metadata from parsed info dictionary.
        """
        if not infoDict:
            message = f"Expected an information dictionary from parser. None provided : {infoDict =}"
            raise DMEmptyInfoDictionary(message)
        try:
            # Store metadata in AppState for application-wide access
            AppState().metadata = infoDict
        except Exception:
            message = f"Failed to store metadata in AppState.\n{infoDict.keys() if infoDict else 'None'}"
            raise DMNonEelsError(message)

    def _validate_file_size(self, filepath):
        """Validate file size for DM files"""

        MIN_FILE_SIZE = 1000  # Minimum size in bytes for a valid DM3/DM4 file

        file_size = os.path.getsize(filepath)

        if file_size < MIN_FILE_SIZE:  # Less than 1KB is suspicious for DM files
            print(f"Error: File size ({file_size} bytes) is too small for a valid DM3/DM4 file. Expected at least 1KB.")
            return False
        return True
    
    # TODO - DELETE IT
    def _log_data_quality(self, electron_count_data, energy_axis):
        """Log data quality information"""
        data_nan_count = np.isnan(electron_count_data).sum()
        data_inf_count = np.isinf(electron_count_data).sum()
        energy_nan_count = np.isnan(energy_axis).sum()
        energy_inf_count = np.isinf(energy_axis).sum()
        
        # Only log if there are quality issues
        if data_nan_count > 0 or data_inf_count > 0:
            print(f"Warning: Raw data has {data_nan_count} NaN values and {data_inf_count} Inf values")
        if energy_nan_count > 0 or energy_inf_count > 0:
            print(f"Warning: Energy axis has {energy_nan_count} NaN values and {energy_inf_count} Inf values")

    def _log_all_data_quality(self, all_electron_count_data, all_energy_axes):
        """Log data quality information for all spectra"""
        for _, (electron_count_data, energy_axis) in enumerate(zip(all_electron_count_data, all_energy_axes)):
            data_nan_count = np.isnan(electron_count_data).sum()
            data_inf_count = np.isinf(electron_count_data).sum()
            energy_nan_count = np.isnan(energy_axis).sum()
            energy_inf_count = np.isinf(energy_axis).sum()
            
            # Only log if there are quality issues
            if data_nan_count > 0 or data_inf_count > 0:
                print(f"Warning: Raw data has {data_nan_count} NaN values and {data_inf_count} Inf values")
            if energy_nan_count > 0 or energy_inf_count > 0:
                print(f"Warning: Energy axis has {energy_nan_count} NaN values and {energy_inf_count} Inf values")

    def _create_all_datasets_from_data(self, all_spectrum_images, all_energy_axes, eels_data, filepath) -> list[xr.Dataset]:
        """
            Create xarray datasets from all processed data.
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
        all_spectrum_metadata = list(eels_data.spectrum_images.values())
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

            print(f"DATASET COLLECTION ANGLE: {dataset.attrs[COLLECTION_ANGLE]}")
            print(f"DATASET CONVERGENCE ANGLE: {dataset.attrs[CONVERGENCE_ANGLE]}")

            try:
                dataset.attrs[IMAGE_NAME] = eels_data.get_image_name(metadata)
                dataset.attrs[SHAPE] = list(dataset[ELECTRON_COUNT].shape)
            except Exception:
                pass
            
            all_datasets.append(dataset)

        return all_datasets

    def _create_dataset_from_data(self, electron_count_data, energy_axis, spectrum_image, filepath) -> xr.Dataset | None:
        """Create xarray dataset from processed data"""
        
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
        NAME = 'name'
        SHAPE = 'shape'

        eels_data_processor = EELSDataProcessorService(self._model)
        
        # Process the data using DataService
        processed_data = eels_data_processor.process_data_for_xarray(electron_count_data, energy_axis)
        
        if processed_data is None:
            return None
        
        electron_count_data, x_coordinates, y_coordinates = processed_data
        
        # Validate dimensions match
        if electron_count_data.shape != (len(y_coordinates), len(x_coordinates), len(energy_axis)):
            print(f"ERROR: Shape mismatch!")
            print(f"Expected: ({len(y_coordinates)}, {len(x_coordinates)}, {len(energy_axis)})")
            print(f"Actual: {electron_count_data.shape}")
            return None
        
        dataset = xr.Dataset({
            ELECTRON_COUNT: ([Y, X, ELOSS], electron_count_data)},
            coords={Y: y_coordinates, X: x_coordinates, ELOSS: energy_axis
        })
        
        # Clean dataset for NaN/inf values
        dataset = eels_data_processor.clean_dataset(dataset)
        
        # Determine dataset type using the data service
        dataset_type = eels_data_processor.determine_dataset_type(dataset)
        
        # Add metadata
        dataset.attrs[ORIGINAL_NAME] = os.path.basename(filepath)
        dataset.attrs[DATASET_TYPE] = dataset_type
        dataset.attrs[BEAM_ENERGY] = getattr(spectrum_image, BEAM_ENERGY, 0)
        dataset.attrs[COLLECTION_ANGLE] = getattr(spectrum_image, COLLECTION_ANGLE, 0.0)
        dataset.attrs[CONVERGENCE_ANGLE] = getattr(spectrum_image, CONVERGENCE_ANGLE, 0.0)

        try:
            dataset.attrs[IMAGE_NAME] = spectrum_image.spectral_info.get(NAME, '')
            dataset.attrs[SHAPE] = list(dataset[ELECTRON_COUNT].shape)
        except Exception:
            pass
        
        return dataset
    
    def _handle_file_error(self, exception):
        """Handle file loading errors"""
        error_message = str(exception)
        if "Expected versions 3 or 4" in error_message:
            print(f"Error loading DM file - Invalid or corrupted DM3/DM4 file: {exception}")
            return None, []
        elif "File size" in error_message and "too small" in error_message:
            print(f"Error loading DM file - File too small: {exception}")
            return None, []
        else:
            print(f"Error loading DM file: {exception}")
            return None, []
