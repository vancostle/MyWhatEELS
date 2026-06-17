"""
Processes DM3/DM4 files to xarray datasets for electron microscopy.
Pipeline: validate → extract → clean → create dataset → attach metadata → output xarray Dataset
"""

import logging
import os, numpy as np, xarray as xr
import struct

_log = logging.getLogger(__name__)
from whateels.errors.dm import (
    DMEmptyInfoDictionary, 
    DMNonEelsError, 
    DMShapeMismatchError, 
    DMFileLoadingError, 
    DMFileUploadError
)
from ..dm_file_processing import DM_EELS_Reader
from .data_processor_service import DataProcessorService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..dm_file_processing.readers.dm_eels_reader import DM_EELS_data
    from ...model import HomePageModel

class FileProcessorService:
    """
    Service for DM3/DM4 file to dataset conversion.
    """
    
    def __init__(self, model: "HomePageModel"):
        """
        Init with model config.
        """
        self._model = model

    # -- Public Methods --

    def process_upload(self, filename: str, file_content: str) -> list[xr.Dataset]:
        """
        Process the uploaded file by validating and parsing it.

        Args:
            filename (str): The name of the uploaded file.
            file_content (str): Full local path to the file on disk.

        Returns:
            list: Parsed datasets from the file.

        Raises:
            DMFileUploadError: If the file upload or processing fails.
        """
        temp_path = file_content

        # Validate file size before parsing.
        # DM4 header bytes 4-11 store the body length (total_size - 16).
        # We warn on mismatch but do not abort — the parser will handle partial files.
        on_disk_size = os.path.getsize(temp_path)
        try:
            with open(temp_path, "rb") as f:
                header = f.read(12)
            if len(header) >= 12:
                dm_version = struct.unpack(">I", header[0:4])[0]
                if dm_version == 4:
                    body_len = struct.unpack(">Q", header[4:12])[0]
                elif dm_version == 3:
                    body_len = struct.unpack(">I", header[4:8])[0]
                else:
                    body_len = None
                if body_len is not None:
                    expected_total = body_len + 16
                    if on_disk_size != expected_total:
                        _log.warning(
                            "[FileProcessor] Size mismatch for '%s': "
                            "header expects %d bytes, on_disk=%d bytes (delta=%d). "
                            "File may be incomplete — proceeding anyway.",
                            filename, expected_total, on_disk_size, on_disk_size - expected_total,
                        )
        except Exception as exc:
            _log.warning("[FileProcessor] Could not read DM header for size check: %s", exc)

        try:
            all_datasets = self._load_dm_file(temp_path)
        except Exception as e:
            raise DMFileUploadError(e)

        return all_datasets

    def process_from_path(self, filepath: str) -> list[xr.Dataset]:
        """
        Load a DM file directly from a local path.
        Bypasses the WebSocket/browser upload — no RAM buffering of the raw bytes.
        """
        if not os.path.isfile(filepath):
            raise DMFileLoadingError(f"File not found: {filepath}")
        all_datasets = self._load_dm_file(filepath)
        if not all_datasets:
            raise DMFileLoadingError(filepath)
        return all_datasets

    # -- Private Methods --

    def _load_dm_file(self, file_source) -> list[xr.Dataset]:
        """
        Load DM file and convert to xarray datasets.
        """
        try:
            # Handle file path validation if it's a string path
            if isinstance(file_source, str):
                if not self._validate_file_size(file_source):
                    return []

            # Read the DM file and extract data using file-like object or path
            dm_eels_reader = DM_EELS_Reader(file_source)

            # Extract file metadata and processed spectral data
            all_metadata_file = dm_eels_reader.file_metadata
            eels_data: DM_EELS_data = dm_eels_reader.processed_all_eels_spectrums

            # Store metadata in application state for global access
            self._store_metadata(all_metadata_file)

            # Extract raw spectral data and energy axes
            all_spectrum_images = eels_data.all_data
            all_energy_axes = eels_data.all_energy_axes

            # Create standardized xarray datasets with metadata.
            # NaN/inf cleaning is done once inside _create_all_datasets_from_data
            # via DataProcessorService.clean_dataset() — no need to pre-clean here.
            file_identifier = getattr(file_source, 'name', str(file_source))
            all_datasets: list[xr.Dataset] = self._create_all_datasets_from_data(
                all_spectrum_images, 
                all_energy_axes,
                eels_data, 
                file_identifier
            )

            return all_datasets
        except Exception as exception:
            self._handle_file_error(exception)
            return []
        
    def _store_metadata(self, infoDict: dict | None = None) -> None:
        """
        Store metadata in app state.
        """
        NOT_INFO_DICT_MESSAGE = "Expected an information dictionary from parser. None provided. {}"
        FAILED_TO_STORE_METADATA_MESSAGE = "Failed to store metadata in AppState. {}"

        if not infoDict:
            raise DMEmptyInfoDictionary(NOT_INFO_DICT_MESSAGE.format(infoDict))
        try:
            # Store metadata in AppState for application-wide access
            self._model.app_state.metadata = infoDict
        except Exception:
            raise DMNonEelsError(FAILED_TO_STORE_METADATA_MESSAGE.format(infoDict.keys() if infoDict else 'None'))

    def _validate_file_size(self, filepath: str) -> bool:
        """
        Check if file size is valid (>=1KB).
        """
        FILE_SIZE_TOO_SMALL_MESSAGE = "File size is too small for a valid DM3/DM4 file. Expected at least 1KB."
        MIN_FILE_SIZE = 1000  # Minimum size in bytes for a valid DM3/DM4 file

        file_size = os.path.getsize(filepath)

        if file_size < MIN_FILE_SIZE:
            # print(FILE_SIZE_TOO_SMALL_MESSAGE)
            return False
        return True

    def _create_all_datasets_from_data(self, all_spectrum_images: list[np.ndarray], all_energy_axes: list[np.ndarray], eels_data: "DM_EELS_data", filepath: str) -> list[xr.Dataset]:
        """
        Create xarray datasets from processed data and metadata.
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

        eels_data_processor = DataProcessorService(self._model)
        all_spectrum_metadata = list(eels_data.all_spectral_info.values())
        all_datasets = []

        for image, metadata, energy_axis in zip(all_spectrum_images, all_spectrum_metadata, all_energy_axes):            
            is_eels = self._is_metadata_eels(metadata, image)

            # Process raw data into xarray-compatible format
            processed_data = eels_data_processor.process_data_for_xarray(image, energy_axis, is_eels)
            if processed_data is None:
                continue

            image, x_coordinates, y_coordinates = processed_data
            
            shape = image.shape
            len_x_axis = len(x_coordinates)
            len_y_axis = len(y_coordinates)
            
            # Determine dataset structure based on data type (EELS vs non-EELS)
            if is_eels:
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
                image_name = eels_data.get_image_name(metadata)
                raise DMShapeMismatchError(image_name, expected_shape, shape)

            # Create xarray dataset with appropriate coordinate system
            if is_eels:
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
            dataset_type = eels_data_processor.determine_dataset_type(dataset, is_eels)

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
    
    def _is_metadata_eels(self, metadata: dict, image: np.ndarray | None = None) -> bool:
        """
        Determine if metadata or image shape indicates EELS data.
        """
        IMAGE_TAGS = 'ImageTags'
        EELS = 'EELS'
        # Check for EELS tag in metadata
        if IMAGE_TAGS in metadata and EELS in metadata[IMAGE_TAGS]:
            return True
        # If image is provided, check for 3D shape (EELS spectrum image)
        if image is not None and len(image.shape) == 3:
            return True
        return False

    def _handle_file_error(self, exception: Exception) -> list:
        """
        Handle file errors and raise DM exceptions.
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
