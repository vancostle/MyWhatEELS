import os

import numpy as np
from whateels.errors import *

class DM_EELS_data:
    """
    The idea of this class is to extract relevant EELS data from the
    parsed dictionary. It acts as a handler, as it can retrieve the
    relevant information for its later usage
    """

    # Supported types to be read using numpy from file.
    _supported_dtypes = {
        1: "int16",
        2: "float32",
        6: "uint8",
        7: "int32",
        9: "int8",
        10: "uint16",
        11: "uint32",
        12: "float64",
        23: "float32"
    }
    
    _IMAGE_TAGS = "ImageTags"
    _IMAGE_DATA = "ImageData"
    _EXPERIMENTAL_CONDITIONS = "Experimental Conditions"
    _DIMENSIONS = "Dimensions"
    _DIMENSION = "Dimension"
    _CALIBRATIONS = "Calibrations"

    def __init__(self):
        """Initialize instance attributes."""
        self._all_spectral_info = {}
        self._spectral_info = None
        self._file = None
        self.data = None

    # ==================== PUBLIC INTERFACE ====================
    
    def get_file_data(self, file, infoDict=None):
        """
        Store metadata and filter spectrum images from parsed info dictionary.
        
        This method combines metadata storage and spectrum filtering for backward compatibility.
        """

        self._file = file
        
        if not infoDict:
            message = f"Expected an information dictionary from parser. None provided : {infoDict =}"
            raise DMEmptyInfoDictionary(message)

        self._all_spectral_info = self._filter_spectrum_images(infoDict)
    
    def handle_eels_data(self):
        self.all_data = self._get_eels_data()
        return self

    # ==================== PUBLIC PROPERTIES ====================
    
    def get_shape(self, image: np.ndarray) -> tuple:
        """
        Get the shape of a spectrum image from its metadata dictionary.
        Returns
        -------
        tuple
            Shape of the image, reversed as in the current property.
        """
        dims = tuple(
            [el[1] for el in image[self._IMAGE_DATA][self._DIMENSIONS].items()]
        )
        return dims[::-1]

    def get_image_name(self, image: dict) -> str:
        """Get the name of a specific spectrum image from its metadata dictionary."""
        NAME = "Name"
        NO_NAME = "Unnamed Image"
        return image.get(NAME, NO_NAME)
    
    def get_beam_energy(self, image) -> float:
        """
        Get beam energy for a specific spectrum image.
        """
        IMAGE_TAGS = self._IMAGE_TAGS
        MICROSCOPE_INFO = "Microscope Info"
        VOLTAGE = "Voltage"
        VOLT_TO_KILOVOLT = 1000
        try:
            microscope_voltage = image[IMAGE_TAGS][MICROSCOPE_INFO][VOLTAGE]
            return microscope_voltage / VOLT_TO_KILOVOLT
        except (KeyError, TypeError):
            # Return a default value if not found
            return 0.0
    
    def get_convergence_angle(self, image: dict) -> float:
        """Get convergence angle for a specific spectrum image."""
        
        EELS = "EELS"

        CONVERGENCE_SEMI_ANGLE = "Convergence semi-angle (mrad)"
        WARNING_MESSAGE = "Expected a value for the convergence angle. No such value in the parsed dictionary found"
        
        alpha = 0 # Default value in mrad
        
        try:
            alpha = image[self._IMAGE_TAGS][EELS][self._EXPERIMENTAL_CONDITIONS][CONVERGENCE_SEMI_ANGLE]
        except KeyError as e:
            self._recursively_add_key(
                image, [self._IMAGE_TAGS, EELS, self._EXPERIMENTAL_CONDITIONS]
            )
        return alpha

    def get_collection_angle(self, image: dict) -> float:
        """"Get collection angle for a specific spectrum image."""

        EELS = "EELS"
        COLLECTION_SEMI_ANGLE = "Collection semi-angle (mrad)"
        
        beta = 0 # Default value in mrad

        try:
            beta = image[self._IMAGE_TAGS][EELS][self._EXPERIMENTAL_CONDITIONS][COLLECTION_SEMI_ANGLE]
        except KeyError as e:

            self._recursively_add_key(
                image, 
                [self._IMAGE_TAGS, EELS, self._EXPERIMENTAL_CONDITIONS]
            )

        return beta

    @property
    def all_energy_axes(self) -> list[np.ndarray]:
        """
        Get the energy axes for all spectrum images.

        Returns
        -------
        list[np.ndarray] or np.ndarray
            If there are multiple images, returns a list of energy axis arrays (one per image).
            If there is a single 3D image, returns a single energy axis array for that image.
        """
        
        EELS_IMAGE_NUM_AXES = 3
        
        energy_axes = []
        
        for image_dict in self._all_spectral_info.values():
            shape = self.get_shape(image_dict)
            
            scale = self._get_scales_of_one_image(image_dict)
            origin = self._get_unit_origins_of_one_image(image_dict)

            if len(shape) == EELS_IMAGE_NUM_AXES:
                # For 3D images, return energy axis based on the first dimension
                energy_axes.append(np.arange(shape[0]) * scale[0] + origin[0])
                continue

            # For Slines and single spectra, this works ...
            energy_axes.append(np.arange(shape[-1]) * scale[-1] + origin[-1])

        return energy_axes
    
    @property
    def all_spectral_info(self):
        return self._all_spectral_info

    # ==================== PRIVATE METHODS ====================

    def _filter_spectrum_images(self, infoDict):
        """
        Filter and extract spectrum images from metadata dictionary.

        Uses a two-pass strategy:
        - Pass 1 (strict): images with non-trivial ImageTags (more than just GMS Version).
        - Pass 2 (lenient): any image with ImageData present, for minimal-metadata files
          such as test/synthetic DM files.
        
        Parameters
        ----------
        infoDict : dict
            Metadata dictionary containing ImageList
            
        Returns
        -------
        dict
            Filtered spectrum images with valid data
            
        Raises
        ------
        DMNonEelsError
            If no valid images found in either pass
        """
        IMAGE_LIST = "ImageList"
        GMS_VERSION = "GMS Version"

        try:
            all_blocks = infoDict[IMAGE_LIST]

            # Pass 1 — prefer images with rich ImageTags metadata.
            strict = {
                k: v for k, v in all_blocks.items()
                if (
                    isinstance(v, dict)
                    and self._IMAGE_DATA in v
                    and self._IMAGE_TAGS in v
                    and isinstance(v[self._IMAGE_TAGS], dict)
                    and len(v[self._IMAGE_TAGS]) > 0
                    and not (len(v[self._IMAGE_TAGS]) == 1 and GMS_VERSION in v[self._IMAGE_TAGS])
                )
            }
            if strict:
                return strict

            # Pass 2 — fall back to any block that has ImageData (e.g. test/synthetic files
            # where ImageTags is minimal or only carries GMS Version).
            lenient = {
                k: v for k, v in all_blocks.items()
                if isinstance(v, dict) and self._IMAGE_DATA in v
            }
            if lenient:
                return lenient

            raise ValueError("No valid image data found")

        except Exception:
            message = f"The dictionary provided after parsing the file does not contain spectral information.\n{infoDict.keys()}"
            raise DMNonEelsError(message)

    def _get_eels_data(self) -> list[np.ndarray]:
        """This method will extract all EELS data from the spectrum images."""
        
        DATA_TYPE = 'DataType'
        DATA = 'Data'
        BYTES_SIZE = 'bytes_size'
        OFFSET = 'offset'
        SIZE = 'size'
        KEY_ERROR_MESSAGE = "Data Type index ({idx}) read from file ({filename}) not supported."
        READABLE_ERROR_MESSAGE = "Size_in_bytes / Number_of_items = {bSize} != from NumPy expected size for {nItems} = {dtype}"

        all_eels_data = []
        if self._file is None:
            raise ValueError("File handle is not initialized")
        file_obj = self._file

        for _, image_data in self._all_spectral_info.items():
            idx = image_data[self._IMAGE_DATA][DATA_TYPE]
            try:
                dtype = self._supported_dtypes[idx]
            except KeyError:
                message = KEY_ERROR_MESSAGE.format(idx=idx, filename=getattr(file_obj, 'name', 'unknown'))
                raise DMNonSupportedDataType(message)

            bSize = image_data[self._IMAGE_DATA][DATA][BYTES_SIZE]
            offset = image_data[self._IMAGE_DATA][DATA][OFFSET]
            nItems = image_data[self._IMAGE_DATA][DATA][SIZE]

            # Checking that the info is readable
            if bSize / nItems != np.dtype(dtype).itemsize:
                message = READABLE_ERROR_MESSAGE.format(bSize=bSize, nItems=nItems, dtype=dtype)
                raise DMConflictingDataTypeRead(message)

            shape = self.get_shape(image_data)

            # Prefer disk-backed memory mapping for real files. This avoids allocating
            # one huge bytes object on every upload/reupload cycle.
            file_name = getattr(file_obj, 'name', None)
            can_memmap = isinstance(file_name, str) and os.path.isfile(file_name)

            if can_memmap:
                assert isinstance(file_name, str)
                array_data = np.memmap(
                    file_name,
                    dtype=dtype,
                    mode='r',
                    offset=offset,
                    shape=shape,
                    order='C',
                )
            else:
                # Fallback for in-memory file-like objects (e.g. BytesIO uploads).
                file_obj.seek(offset)  # Seek to the data offset
                bytes_to_read = nItems * np.dtype(dtype).itemsize
                binary_data = file_obj.read(bytes_to_read)

                if len(binary_data) != bytes_to_read:
                    raise ValueError(f"Expected to read {bytes_to_read} bytes, but got {len(binary_data)} bytes")

                # Convert binary data to numpy array with specified dtype
                array_data = np.frombuffer(binary_data, dtype=dtype, count=nItems).reshape(shape)

            all_eels_data.append(array_data)

        return all_eels_data

    def _recursively_add_key(self, infoD, keylist):
        """Method used to expand the dictionary recursevely, if a keyError is raised during
        the info reading. This is useful to create the dictionary structure expected for the
        E0, alpha and beta values later on. So, if a _setter function is called for these
        parameters, the correct route is in place to modify them
        """
        for el in keylist:
            if el not in infoD:
                infoD[el] = dict()
            infoD = infoD[el]

    def _get_scales_of_one_image(self, image_dict):
        """Get scale properties for a single image."""
        SCALE = 'Scale'
        # TODO safeguard for the cases where the dimensions cannot be read from file
        scale = [
            el[SCALE]
            for k, el in image_dict[self._IMAGE_DATA][self._CALIBRATIONS][self._DIMENSION].items()
        ]
        return np.array(scale)[::-1]
    
    def _get_origins_of_one_image(self, image_dict):
        """Get origins for the dimensions of a single image."""
        # TODO safeguard for the cases where the dimensions cannot be read from file
        ORIGIN = 'Origin'
        orig = [
            el[ORIGIN]
            for k, el in image_dict[self._IMAGE_DATA][self._CALIBRATIONS][self._DIMENSION].items()
        ]
        return np.array(orig)[::-1]

    def _get_unit_origins_of_one_image(self, image_dict):
        """Origins for the dimensions of a single image that include the scaling factors"""
        return -1 * self._get_origins_of_one_image(image_dict) * self._get_scales_of_one_image(image_dict)

    def _get_units(self):
        """Units for the scales involved, one per each dimension"""
        
        UNITS = 'Units'
        
        # TODO safeguard for the cases where the dimensions cannot be read from file
        units = []
        for k, el in self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][
            self._DIMENSION
        ].items():
            if not el[UNITS]:
                # self.spectralInfo['ImageData']['Calibrations']['Dimension'][k]['Units'] = 'a.u.'
                el[UNITS] = "a.u."
            units.append(el[UNITS])
        return tuple(units[::-1])
    
    def _get_units(self):
        """Units for the scales involved, one per each dimension"""
        
        UNITS = 'Units'
        
        # TODO safeguard for the cases where the dimensions cannot be read from file
        units = []
        for k, el in self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][
            self._DIMENSION
        ].items():
            if not el[UNITS]:
                # self.spectralInfo['ImageData']['Calibrations']['Dimension'][k]['Units'] = 'a.u.'
                el[UNITS] = "a.u."
            units.append(el[UNITS])
        return tuple(units[::-1])

    # TODO - CHECK IF WE NEED THIS BECAUSE IT'S NOT USED ANYWHERE
    # IF WE DO, UNCOMMENT AND UPDATE DUE TO THIS FUNCTIONS WAS DESIGN FOR A SINGLE IMAGE AND CODE WAS REMAKE TO HANDLE MULTIPLE IMAGES.
    # SO UPDATE "self._spectral_info"
    # def _set_energy_scale(self, scale_val):
    #     """Method that sets a new value for the energy scale
    #     Raises ValueError whenever we face an spectrum dataset with ill-defined units
    #     """
    #     scale_items = [
    #         k
    #         for k, el in self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][
    #             self._DIMENSION
    #         ].items()
    #         if el["Units"] == "eV"
    #     ]
    #     if len(scale_items) != 1:
    #         raise ValueError
    #     self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][self._DIMENSION][scale_items[0]][
    #         "Scale"
    #     ] = scale_val

    # TODO - CHECK IF WE NEED THIS BECAUSE IT'S NOT USED ANYWHERE
    # IF WE DO, UNCOMMENT AND UPDATE DUE TO THIS FUNCTIONS WAS DESIGN FOR A SINGLE IMAGE AND CODE WAS REMAKE TO HANDLE MULTIPLE IMAGES.
    # SO UPDATE "self._spectral_info"
    # def _set_energy_origin(self, offset_val):
    #     """Method that changes the offset value of the energy axis"""
    #     scale_items = [
    #         k
    #         for k, el in self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][
    #             self._DIMENSION
    #         ].items()
    #         if el["Units"] == "eV"
    #     ]
    #     if len(scale_items) != 1:
    #         raise ValueError
    #     self._spectral_info[self._IMAGE_DATA][self._CALIBRATIONS][self._DIMENSION][scale_items[0]][
    #         "Origin"
    #     ] = offset_val

