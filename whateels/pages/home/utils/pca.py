"""Numerical helpers for PCA decomposition and spectrum-image reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
from sklearn.decomposition import PCA


PCA_RECONSTRUCTION_BLOCK_SIZE = 8192


def sanitize_pca_matrix(matrix: np.ndarray) -> np.ndarray:
    """Return a finite, float64, two-dimensional PCA input matrix.

    Spectrum-image pixels are samples and energy-loss channels are features.
    Non-finite samples are replaced with zero, matching the dataset cleaning
    convention used when data is loaded by the application.
    """
    finite_matrix = np.asarray(matrix, dtype=np.float64)
    if finite_matrix.ndim != 2:
        raise ValueError(
            f"PCA expects a 2D samples-by-features matrix, got shape={finite_matrix.shape}."
        )
    if finite_matrix.shape[0] < 1 or finite_matrix.shape[1] < 1:
        raise ValueError("PCA requires at least one sample and one feature.")
    if np.all(np.isfinite(finite_matrix)):
        return finite_matrix
    return np.nan_to_num(
        finite_matrix,
        copy=True,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )


@dataclass(frozen=True, slots=True)
class PCADecomposition:
    """The reusable parts of a fitted PCA decomposition."""

    mean: np.ndarray
    components: np.ndarray
    explained_variance_ratio: np.ndarray

    @classmethod
    def fit(
        cls,
        matrix: np.ndarray,
        n_components: int | None = None,
    ) -> "PCADecomposition":
        """Fit the requested number of principal components.

        ``None`` retains the previous helper behaviour and fits the complete
        available rank. The Home-page UI normally passes the user-selected
        scree-plot size so large spectrum images do not calculate unused
        components.
        """
        finite_matrix = sanitize_pca_matrix(matrix)
        maximum = min(finite_matrix.shape)
        requested_components = (
            maximum
            if n_components is None
            else int(n_components)
        )
        if not 1 <= requested_components <= maximum:
            raise ValueError(
                f"PCA components to calculate must be between 1 and {maximum}; "
                f"received {requested_components}."
            )

        # ``auto`` lets sklearn choose an efficient solver for the requested
        # rank. A one-pixel or constant cube can emit a harmless divide-by-zero
        # warning; those variance ratios are normalized to zero below.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            fitted = PCA(
                n_components=requested_components,
                svd_solver="auto",
            ).fit(finite_matrix)

        ratios = np.nan_to_num(
            np.asarray(fitted.explained_variance_ratio_, dtype=np.float64),
            copy=True,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        return cls(
            mean=np.asarray(fitted.mean_, dtype=np.float64),
            components=np.asarray(fitted.components_, dtype=np.float64),
            explained_variance_ratio=ratios,
        )

    @property
    def max_components(self) -> int:
        """Maximum number of components available for reconstruction."""
        return int(self.components.shape[0])

    def reconstruct(
        self,
        matrix: np.ndarray,
        n_components: int,
        *,
        block_size: int = PCA_RECONSTRUCTION_BLOCK_SIZE,
    ) -> np.ndarray:
        """Reconstruct a matrix with the first ``n_components`` components."""
        finite_matrix = sanitize_pca_matrix(matrix)
        if finite_matrix.shape[1] != self.components.shape[1]:
            raise ValueError(
                "PCA reconstruction feature count does not match the fitted decomposition."
            )

        selected_components = int(n_components)
        if not 1 <= selected_components <= self.max_components:
            raise ValueError(
                f"PCA components must be between 1 and {self.max_components}; "
                f"received {selected_components}."
            )

        chunk_size = max(1, int(block_size))
        basis = self.components[:selected_components]
        reconstructed = np.empty_like(finite_matrix)

        for start in range(0, finite_matrix.shape[0], chunk_size):
            stop = min(start + chunk_size, finite_matrix.shape[0])
            centered = finite_matrix[start:stop] - self.mean
            reconstructed[start:stop] = (centered @ basis.T) @ basis + self.mean

        return reconstructed
