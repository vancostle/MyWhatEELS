import numpy as np
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    from param.parameterized import Event
 
class SpectrumExtractor:
    
    @staticmethod
    def get_spectrum_from_pixel(electron_count_data: "Dataset", y: int, x: int) -> np.ndarray:
        """
        Extract the spectrum for a single pixel (y, x) from the electron_count_data cube.

        Parameters:
            electron_count_data (xarray.DataArray):
                The 3D data cube containing electron counts (shape: [y, x, energy]).
            y (int):
                Row index (y coordinate).
            x (int):
                Column index (x coordinate).

        Returns:
            np.ndarray: 1D array of spectrum values for the selected pixel (energy axis).

        If the indexing order is not [y, x, energy], attempts [x, y, energy].
        Returns zeros if extraction fails.
        """
        try:
            spec = electron_count_data.values[int(y), int(x), :].astype(float)
            return spec
        except Exception:
            # Try alternative indexing order (x,y,E) if needed
            try:
                spec = electron_count_data.values[int(x), int(y), :].astype(float)
                return spec
            except Exception:
                return np.zeros(electron_count_data.shape[-1])

    @staticmethod
    def get_spectrum_from_indices(electron_count_data: "Dataset", pairs) -> tuple[np.ndarray, int] | None:
        """
        Extract the summed spectrum from a list of pixel indices in the electron_count_data cube.

        Parameters:
            electron_count_data (xarray.DataArray):
                The 3D data cube containing electron counts (shape: [y, x, energy]).
            pairs (list[tuple[int, int]]):
                List of (row, column) pixel indices.

        Returns:
            tuple[np.ndarray, int] | None:
                Tuple of (summed spectrum, number of pixels) or None if extraction fails.

        If the indexing order is not [y, x, energy], attempts [x, y, energy].
        """
        if not pairs:
            return None
        try:
            ii, jj = zip(*pairs)
            block = electron_count_data.values[np.asarray(ii), np.asarray(jj), :]  # (N, nE)
            return block.sum(axis=0), len(pairs)
        except Exception:
            # attempt swap if indexing order different
            try:
                ii, jj = zip(*pairs)
                block = electron_count_data.values[np.asarray(jj), np.asarray(ii), :]
                return block.sum(axis=0), len(pairs)
            except Exception:
                return None

    @staticmethod
    def extract_point(event: "Event") -> dict | None:
        """
        Extract a single point's data from a Panel/Plotly event payload.

        Parameters:
            event (Event):
                Panel event object containing Plotly hover/click data.

        Returns:
            dict | None:
                Dictionary with keys 'x', 'y', and 'curve' for the selected point, or None if not available.

        The returned dictionary contains:
            - 'x': x coordinate of the point
            - 'y': y coordinate of the point
            - 'curve': curve number (if available)
        """
        X = 'x'
        Y = 'y'
        POINTS = 'points'
        CURVE = 'curve'
        CURVE_NUMBER = 'curveNumber'

        point_data = event.new
        try:
            if not point_data or POINTS not in point_data or not point_data[POINTS]:
                return None
            p = point_data[POINTS][0]
            return {X: p.get(X), Y: p.get(Y), CURVE: p.get(CURVE_NUMBER, None)}
        except Exception:
            return None

    @staticmethod
    def extract_region(event: "Event") -> list[tuple[int, int]]:
        """
        Extract a region's data (multiple points) from a Panel/Plotly event payload.

        Parameters:
            event (Event):
                Panel event object containing Plotly selection data.

        Returns:
            list[tuple[int, int]]:
                List of (row, column) pixel indices for the selected region.

        The returned list contains tuples of (row, column) for each selected pixel.
        Duplicates are removed, order is preserved. Returns an empty list if no valid points are found.
        """
        X = 'x'
        Y = 'y'
        POINTS = 'points'
        
        point_data = event.new
        try:
            if not point_data or POINTS not in point_data or not point_data[POINTS]:
                return []
            pairs = []
            for p in point_data[POINTS]:
                x = p.get(X)
                y = p.get(Y)
                if x is None or y is None:
                    continue
                pairs.append((int(y), int(x)))
            # Remove duplicates preserving order
            pairs = list(dict.fromkeys(pairs))
            return pairs
        except Exception:
            return []
