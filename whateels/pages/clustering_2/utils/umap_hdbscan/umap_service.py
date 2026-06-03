import copy

import numpy as np
import umap

from sklearn.preprocessing import normalize

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from xarray import DataArray


class UMAPService:
    """Encapsulates UMAP-related data preparation and embedding logic."""

    def __init__(self, electron_count_data: "DataArray"):
        # Keep an isolated copy to avoid side effects on upstream data.
        self._electron_count_data = copy.deepcopy(electron_count_data)
        self._eloss = self._electron_count_data.coords["Eloss"].values
        self._data = np.array(self._electron_count_data)

    @property
    def electron_count_data(self):
        return self._electron_count_data

    @property
    def eloss(self):
        return self._eloss

    @property
    def data(self):
        return self._data

    def compute_umap_embedding(
        self,
        min_dist: float = 0.1,
        n_neighbors: int = 15,
        n_components: int = 2,
        metric: str = 'euclidean',
        available_norm: str = 'none',
        random_state: int = 1,
    ) -> tuple[Any, dict]:
        """Compute UMAP embedding for ElectronCount data."""
        data_2d = self.get_reshaped_data()
        if data_2d is None:
            raise ValueError("Could not prepare data for UMAP embedding.")

        data_2d = self.apply_normalization(data_2d, available_norm)

        mapper = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            random_state=random_state,
            metric=metric,
        )
        embedding = mapper.fit_transform(data_2d)
        mapper.whateels_norm = available_norm

        umap_data_dict = {
            'umap_data_{}_{}_{}'.format(available_norm, min_dist, n_neighbors): mapper
        }
        return embedding, umap_data_dict

    def apply_normalization(self, data_2d: np.ndarray, available_norm: str) -> np.ndarray:
        """Apply row-wise normalization before UMAP, preserving raw data when requested."""
        norm = str(available_norm).lower()
        if norm == 'none':
            return data_2d

        finite_data = np.where(np.isfinite(data_2d), data_2d, 0.0)
        return normalize(finite_data, norm=norm, axis=1, copy=True)

    def get_electron_count_data_for_norm(self, available_norm: str):
        """Return a DataArray shaped like ElectronCount after applying the selected norm."""
        norm = str(available_norm).lower()
        if norm == 'none':
            return self._electron_count_data.copy()

        data_2d = self.get_reshaped_data()
        if data_2d is None:
            raise ValueError("Could not prepare data for normalization.")

        normalized_2d = self.apply_normalization(data_2d, norm)
        normalized_values = normalized_2d.reshape(self._electron_count_data.shape)
        return self._electron_count_data.copy(data=normalized_values)

    def get_reshaped_data(self) -> Optional[np.ndarray]:
        """Reshape electron count data to 2D array for UMAP processing."""
        try:
            shape = self._electron_count_data.shape
            if len(shape) == 2:
                arr = np.array(self._electron_count_data, dtype=float)
            elif len(shape) == 3:
                n_y, n_x, n_eloss = shape
                arr = np.array(self._electron_count_data, dtype=float).reshape(n_y * n_x, n_eloss)
            else:
                raise ValueError("Electron count data must be 2D or 3D.")

            if not np.all(np.isfinite(arr)):
                arr = np.where(np.isfinite(arr), arr, 0.0)
            return arr
        except Exception as e:
            print(f"Error processing electron count data: {e}")
            return None