"""
Clustering algorithms for EELS spectrum image data.

OOP-based clustering implementations with a base class and specific algorithms.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Literal, TYPE_CHECKING
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.feature_extraction.image import grid_to_graph

if TYPE_CHECKING:
    from numpy import ndarray


class ClusteringAlgorithm(ABC):
    """
    Abstract base class for clustering algorithms.
    
    All clustering algorithms should:
    1. Accept a data cube (x, y, eloss)
    2. Return (labels, centers) where labels is (x, y) and centers is (n_clusters, eloss)
    """
    
    def __init__(self, n_clusters: int, norm: Literal['l1', 'l2', 'max', 'none'] = 'l2'):
        """
        Initialize the clustering algorithm.
        
        Args:
            n_clusters: Number of clusters to form
            norm: Normalization method ('l1', 'l2', 'max', 'none')
        """
        self.n_clusters = n_clusters
        self.norm = norm
        self._matrix_norm: "ndarray | None" = None
        self._sclust_norm: "ndarray | None" = None
    
    def fit(
        self,
        matrix: "ndarray",
        matrix_norm: "ndarray | None" = None,
        sclust_norm: "ndarray | None" = None
    ) -> tuple["ndarray", "ndarray"]:
        """
        Fit the clustering algorithm and return results.
        
        Args:
            matrix: 3D spectrum image data (x, y, eloss)
            matrix_norm: Pre-normalized matrix (optional)
            sclust_norm: Pre-normalized clustering input (optional)
        
        Returns:
            Tuple of (labels, centers):
            - labels: 2D array (x, y) with cluster assignments
            - centers: 2D array (n_clusters, eloss) with cluster centers
        """
        from .preprocessing import DataPreprocessor
        
        # Use provided normalized matrices or prepare them
        if matrix_norm is None or sclust_norm is None:
            preprocessor = DataPreprocessor()
            self._matrix_norm, self._sclust_norm = preprocessor.prepare_matrix(matrix, self.norm)  # type: ignore
        else:
            self._matrix_norm = matrix_norm
            self._sclust_norm = sclust_norm
        
        # Delegate to subclass implementation
        return self._fit_impl(matrix)
    
    @abstractmethod
    def _fit_impl(self, matrix: "ndarray") -> tuple["ndarray", "ndarray"]:
        """
        Subclass-specific clustering implementation.
        
        Args:
            matrix: Original 3D data cube
        
        Returns:
            Tuple of (labels, centers)
        """
        pass
    
    def _compute_centers_from_labels(
        self,
        labels_1d: "ndarray",
        matrix: "ndarray"
    ) -> "ndarray":
        """
        Compute cluster centers as mean spectrum for each cluster.
        
        Args:
            labels_1d: 1D array of cluster labels
            matrix: Original 3D data cube
        
        Returns:
            2D array (n_clusters, eloss) with cluster centers
        """
        centers = np.zeros((self.n_clusters, matrix.shape[-1]))
        for i in range(self.n_clusters):
            cluster_mask = labels_1d == i
            if np.any(cluster_mask) and self._matrix_norm is not None:
                centers[i] = self._matrix_norm[cluster_mask].mean(axis=0)
        return centers


class KMeansClusteringAlgorithm(ClusteringAlgorithm):
    """
    K-Means clustering algorithm for EELS data.
    
    Fast and efficient for large datasets. Works by iteratively assigning
    pixels to the nearest cluster center and updating centers.
    """
    
    def __init__(
        self,
        n_clusters: int,
        norm: Literal['l1', 'l2', 'max', 'none'] = 'l2',
        n_init: int = 10,
        max_iter: int = 300,
        init_method: Literal['k-means++', 'random'] = 'k-means++'
    ):
        """
        Initialize K-Means algorithm.
        
        Args:
            n_clusters: Number of clusters
            norm: Normalization method
            n_init: Number of random initializations
            max_iter: Maximum iterations per run
            init_method: Initialization strategy
        """
        super().__init__(n_clusters, norm)
        self.n_init = n_init
        self.max_iter = max_iter
        self.init_method = init_method
    
    def _fit_impl(self, matrix: "ndarray") -> tuple["ndarray", "ndarray"]:
        """Run K-Means clustering."""
        if self._sclust_norm is None:
            raise RuntimeError("Data must be normalized before clustering")
        
        init_val: Literal['k-means++', 'random'] = self.init_method  # type: ignore
        kmeans = KMeans(
            n_clusters=self.n_clusters,
            init=init_val,
            n_init=self.n_init,
            max_iter=self.max_iter,
            tol=1e-9,
            random_state=13
        )
        fitted = kmeans.fit(self._sclust_norm)
        centers = fitted.cluster_centers_
        labels = fitted.labels_.reshape(matrix.shape[:-1])
        
        return labels, centers


class AgglomerativeClusteringAlgorithm(ClusteringAlgorithm):
    """
    Agglomerative Hierarchical clustering for EELS data.
    
    Builds a hierarchy of clusters by iteratively merging the most similar pairs.
    Can use spatial connectivity constraints.
    """
    
    def __init__(
        self,
        n_clusters: int,
        norm: Literal['l1', 'l2', 'max', 'none'] = 'none',
        linkage: Literal['ward', 'complete', 'average', 'single'] = 'ward',
        affinity: str = 'euclidean',
        use_connectivity: bool = False
    ):
        """
        Initialize Agglomerative clustering.
        
        Args:
            n_clusters: Number of clusters
            norm: Normalization method
            linkage: Linkage criterion (ward, complete, average, single)
            affinity: Distance metric
            use_connectivity: Use spatial connectivity constraints
        """
        super().__init__(n_clusters, norm)
        self.linkage = linkage
        self.affinity = affinity
        self.use_connectivity = use_connectivity
    
    def _fit_impl(self, matrix: "ndarray") -> tuple["ndarray", "ndarray"]:
        """Run Agglomerative clustering."""
        if self._sclust_norm is None:
            raise RuntimeError("Data must be normalized before clustering")
        
        # Handle 'ward' linkage constraint
        affinity = self.affinity
        if self.linkage == 'ward' and affinity != 'euclidean':
            print(f"Warning: 'ward' linkage requires 'euclidean' affinity. Changing affinity to 'euclidean'.")
            affinity = 'euclidean'
        
        # Build connectivity matrix if requested
        connectivity_matrix = None
        if self.use_connectivity:
            ny, nx = matrix.shape[0], matrix.shape[1]
            connectivity_matrix = grid_to_graph(ny, nx)
        
        # Create and fit
        linkage_val: Literal['ward', 'complete', 'average', 'single'] = self.linkage  # type: ignore
        agglomerative = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage=linkage_val,
            metric=affinity,
            connectivity=connectivity_matrix  # type: ignore
        )
        
        labels_1d = agglomerative.fit_predict(self._sclust_norm)
        labels = labels_1d.reshape(matrix.shape[:-1])
        
        # Compute cluster centers
        centers = self._compute_centers_from_labels(labels_1d, matrix)
        
        return labels, centers


class SpectralClusteringAlgorithm(ClusteringAlgorithm):
    """
    Spectral clustering for EELS data.
    
    Uses graph-based similarity and spectral embedding before clustering.
    Good for non-convex cluster shapes.
    """
    
    def __init__(
        self,
        n_clusters: int,
        norm: Literal['l1', 'l2', 'max', 'none'] = 'none',
        n_init: int = 10,
        assign_labels: Literal['kmeans', 'discretize', 'cluster_qr'] = 'kmeans',
        affinity: str = 'rbf',
        n_neighbors: int = 10,
        gamma: float = 1.0
    ):
        """
        Initialize Spectral clustering.
        
        Args:
            n_clusters: Number of clusters
            norm: Normalization method
            n_init: Number of K-means initializations
            assign_labels: Label assignment strategy
            affinity: Affinity matrix construction method
            n_neighbors: Number of neighbors for nearest_neighbors affinity
            gamma: Kernel coefficient for rbf kernel
        """
        super().__init__(n_clusters, norm)
        self.n_init = n_init
        self.assign_labels = assign_labels
        self.affinity = affinity
        self.n_neighbors = n_neighbors
        self.gamma = gamma
    
    def _fit_impl(self, matrix: "ndarray") -> tuple["ndarray", "ndarray"]:
        """Run Spectral clustering."""
        if self._sclust_norm is None:
            raise RuntimeError("Data must be normalized before clustering")
        
        assign_val: Literal['kmeans', 'discretize', 'cluster_qr'] = self.assign_labels  # type: ignore
        spectral = SpectralClustering(
            n_clusters=self.n_clusters,
            n_init=self.n_init,
            assign_labels=assign_val,
            affinity=self.affinity,
            n_neighbors=self.n_neighbors,
            gamma=self.gamma,
            random_state=13
        )
        
        try:
            labels_1d = spectral.fit_predict(self._sclust_norm)
        except Exception as e:
            print(f"Spectral clustering warning/error: {e}")
            print(f"Current parameters: affinity={self.affinity}, n_neighbors={self.n_neighbors}, gamma={self.gamma}")
            print("Suggestion: Try increasing n_neighbors or adjusting gamma parameter")
            raise
        
        labels = labels_1d.reshape(matrix.shape[:-1])
        
        # Compute cluster centers
        centers = self._compute_centers_from_labels(labels_1d, matrix)
        
        return labels, centers