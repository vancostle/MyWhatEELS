
import numpy as np

from .umap_service import UMAPService
from .hdbscan_service import HDBSCANService
from .plot_service import PlotService
from .svm_service import SVMService

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from xarray import DataArray
    
class UMAP_HDBSCAN:
    
    def __init__(self, electron_count_data : "DataArray"):
        self._umap_service = UMAPService(electron_count_data)
        self._hdbscan_service = HDBSCANService()
        self._svm_service = SVMService(self._umap_service.data)
        self._plot_service = PlotService(
            self._umap_service.electron_count_data,
            self._umap_service.eloss,
            self._umap_service.data,
        )

        # Keep these attributes for backward compatibility with any remaining callers.
        self._electron_count_data = self._umap_service.electron_count_data
        self._eloss = self._umap_service.eloss
        self._data = self._umap_service.data
        
    def compute_umap_embedding(
        self,
        min_dist : float = 0.1,
        n_neighbors : int = 15,
        n_components : int = 2,
        metric : str = 'euclidean',
        available_norm : str = 'none',
        random_state : int = 1
        
    ) -> tuple[Any, dict]:
        """ Compute UMAP embedding of the image spectra image. """
        return self._umap_service.compute_umap_embedding(
            min_dist=min_dist,
            n_neighbors=n_neighbors,
            n_components=n_components,
            metric=metric,
            available_norm=available_norm,
            random_state=random_state,
        )

    def _apply_normalization(self, data_2d: np.ndarray, available_norm: str) -> np.ndarray:
        """Apply row-wise normalization before UMAP, preserving raw data when requested."""
        return self._umap_service.apply_normalization(data_2d, available_norm)

    def get_electron_count_data_for_norm(self, available_norm: str):
        """Return a DataArray shaped like ElectronCount after applying the selected norm."""
        return self._umap_service.get_electron_count_data_for_norm(available_norm)

    def _get_reshaped_data(self) -> Optional[np.ndarray]:
        """Reshape electron count data to 2D array for UMAP processing."""
        return self._umap_service.get_reshaped_data()
        
        
    def compute_hdbscan_on_umap(self, umap_embedding, min_samples, min_cluster_size):
        """Compute HDBSCAN clustering on the provided UMAP embedding."""
        return self._hdbscan_service.compute_hdbscan_on_umap(
            umap_embedding,
            min_samples,
            min_cluster_size,
        )

    def get_nclusters_cmap(self, hdbscan_results, n_clusters, cmap='tab20b'):
        """Return cluster colormap values for HDBSCAN outputs."""
        return self._hdbscan_service.get_nclusters_cmap(hdbscan_results, n_clusters, cmap)
    
    def evaluate_hdbscan(
        self,
        embedding,
        min_samples_min: int = 1,
        min_samples_max: int = 8,
        min_cluster_size_min: int = 100,
        min_cluster_size_max: int = 900,
        step: int = 100,
    ) -> list[tuple[int, int, int, int, float]]:
        """Evaluate HDBSCAN on a configurable parameter grid."""
        return self._hdbscan_service.evaluate_hdbscan(
            embedding=embedding,
            min_samples_min=min_samples_min,
            min_samples_max=min_samples_max,
            min_cluster_size_min=min_cluster_size_min,
            min_cluster_size_max=min_cluster_size_max,
            step=step,
        )

    def plot_hdbscan_map(self, hdbscan_results, cmap_obj):
        return self._plot_service.plot_hdbscan_map(hdbscan_results, cmap_obj)
    
    def plot_mean_spectra_per_cluster(self, hdbscan_results, cmap_obj):
        return self._plot_service.plot_mean_spectra_per_cluster(hdbscan_results, cmap_obj)

    def plot_umap_embedding_with_labels(self, embedding, labels, cmap_obj, min_samp, min_clust):
        return self._plot_service.plot_umap_embedding_with_labels(
            embedding,
            labels,
            cmap_obj,
            min_samp,
            min_clust,
        )

    def plot_cluster_heatmap(self, data, cmap='rainbow'):
        return self._plot_service.plot_cluster_heatmap(data, cmap)

    def train_svm_from_hdbscan_labels(
        self,
        hdbscan_labels,
        kernel,
        c_value=1.0,
        gamma=None,
        coef0=None,
        degree=3,
        test_size=0.25,
        cv=10,
        probability=False,
        min_size=400,
        random_state=42,
    ) -> dict:
        """Train SVM/SGD from HDBSCAN labels with class-balanced sampling."""
        return self._svm_service.train_svm_from_hdbscan_labels(
            hdbscan_labels=hdbscan_labels,
            kernel=kernel,
            c_value=c_value,
            gamma=gamma,
            coef0=coef0,
            degree=degree,
            test_size=test_size,
            cv=cv,
            probability=probability,
            min_size=min_size,
            random_state=random_state,
        )

    def reassign_outliers_with_svm(
        self,
        hdbscan_labels,
        model,
        class_map,
        outlier_label=-1,
    ) -> tuple[np.ndarray, int]:
        """Predict and reassign outliers in HDBSCAN labels using trained SVM/SGD."""
        return self._svm_service.reassign_outliers(
            hdbscan_labels=hdbscan_labels,
            model=model,
            class_map=class_map,
            outlier_label=outlier_label,
        )