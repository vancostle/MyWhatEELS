import numpy as np
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    from param.parameterized import Event
 
class SpectrumExtractor:

    _ROI_CHUNK_PIXELS = 4096

    @staticmethod
    def _as_row_col_energy(electron_count_data: "Dataset") -> np.ndarray:
        """Return a 3D array in (row, col, energy) order when possible.

        The fitting/clustering panes index spectra using image coordinates (row, col).
        When source datasets are switched (raw/preprocessed), the energy axis order can
        differ; this helper normalizes to keep hover/ROI extraction stable.
        """
        arr = np.asarray(electron_count_data.values)
        if arr.ndim != 3:
            return arr

        energy_axis = arr.ndim - 1
        try:
            dims = [str(d).lower() for d in electron_count_data.dims]
            for idx, dim_name in enumerate(dims):
                if 'eloss' in dim_name:
                    energy_axis = idx
                    break
        except Exception:
            pass

        if energy_axis != arr.ndim - 1:
            arr = np.moveaxis(arr, energy_axis, arr.ndim - 1)
        return arr
    
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
        data = SpectrumExtractor._as_row_col_energy(electron_count_data)
        try:
            spec = data[int(y), int(x), :].astype(float)
            return spec
        except Exception:
            # Try alternative indexing order (x,y,E) if needed
            try:
                spec = data[int(x), int(y), :].astype(float)
                return spec
            except Exception:
                return np.zeros(data.shape[-1] if data.ndim >= 1 else 0)

    @staticmethod
    def _sum_dtype(data: np.ndarray):
        return np.complex128 if np.iscomplexobj(data) else np.float64

    @staticmethod
    def _sum_indexed_chunked(data: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, int] | None:
        """Sum arbitrary pixel indices in chunks to avoid large advanced-index copies."""
        if data.ndim != 3 or rows.size == 0 or cols.size == 0 or rows.size != cols.size:
            return None

        if (
            int(rows.min()) < 0
            or int(cols.min()) < 0
            or int(rows.max()) >= data.shape[0]
            or int(cols.max()) >= data.shape[1]
        ):
            return None

        dtype = SpectrumExtractor._sum_dtype(data)
        n_points = int(rows.size)
        acc = np.zeros(data.shape[-1], dtype=dtype)
        chunk_size = max(1, int(SpectrumExtractor._ROI_CHUNK_PIXELS))
        for start in range(0, n_points, chunk_size):
            stop = min(start + chunk_size, n_points)
            acc += np.sum(
                data[rows[start:stop], cols[start:stop], :],
                axis=0,
                dtype=dtype,
            )
        return acc, n_points

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
        if pairs is None:
            return None
        try:
            n_pairs = len(pairs)
        except TypeError:
            pairs = list(pairs)
            n_pairs = len(pairs)
        if n_pairs == 0:
            return None
        data = SpectrumExtractor._as_row_col_energy(electron_count_data)
        try:
            ii, jj = zip(*pairs)
            result = SpectrumExtractor._sum_indexed_chunked(
                data,
                np.asarray(ii, dtype=np.int64),
                np.asarray(jj, dtype=np.int64),
            )
            if result is not None:
                return result
            raise IndexError("ROI indices do not match data shape.")
        except Exception:
            # attempt swap if indexing order different
            try:
                ii, jj = zip(*pairs)
                result = SpectrumExtractor._sum_indexed_chunked(
                    data,
                    np.asarray(jj, dtype=np.int64),
                    np.asarray(ii, dtype=np.int64),
                )
                if result is not None:
                    return result
                raise IndexError("Swapped ROI indices do not match data shape.")
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
