"""
Clustering-specific spectrum image visualizer.

Extends the base SpectrumImageVisualizer component with clustering capabilities:
- KMeans clustering
- Agglomerative clustering  
- Spectral clustering
- Cluster center visualization
- Normalized spectrum display
"""

import panel as pn
import numpy as np
import plotly.graph_objs as go

from whateels.helpers import SpectrumExtractor
from whateels.helpers.colormaps import (
    get_nclusters_cmap,
    build_discrete_colorscale,
    to_plotly_color,
)

from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.feature_extraction.image import grid_to_graph
from whateels.components.visualizers import SpectrumImageVisualizer as BaseSpectrumImageVisualizer
from typing import override, TYPE_CHECKING, Literal
from whateels.components import ResizableColumns

if TYPE_CHECKING:
    from ...model import ClusteringModel
    from ...controller import ClusteringController
    from xarray import Dataset

class SpectrumImageVisualizer(BaseSpectrumImageVisualizer):
    """
    Clustering-enhanced Spectrum Image Visualizer.
    
    Extends the base visualizer with clustering capabilities:
    - KMeans, Agglomerative, and Spectral clustering
    - Cluster center visualization
    - Normalized spectrum display
    - Background subtraction support
    """
    
    # Colormap name used to build discrete Plotly colorscales for clustering.
    # We generate the actual discrete colorscale on demand using the
    # helper `whateels.helpers.colormaps.listed` so the visualizer
    # can produce exactly `n_clusters` distinct colors.
    _CLUSTER_COLORS = 'tab20b'
    _ORDER_COLORS = [3, 7, 15, 11, 19, 
                     2, 6, 14, 10, 18, 
                     1, 5, 13, 9, 17, 
                     0, 4, 12, 8, 16]

    def __init__(self, model: "ClusteringModel", controller: "ClusteringController", dataset: "Dataset"):
        # Get axis name from model constants
        eloss_name = getattr(model.constants, 'ELOSS', 'Eloss') if hasattr(model, 'constants') else 'Eloss'
        
        # Call parent constructor to setup base visualization
        super().__init__(dataset, eloss_name)

        # Store references for clustering features
        self._model = model
        self._controller = controller

        # Double-click timing for toggling cluster display
        self._last_click_time = 0
        self._DOUBLE_CLICK_MS = 400  # Double-click threshold in milliseconds
        self._hover_disabled = False  # Disable hover after showing all clusters

        # Clustering state
        self._clustering_results = None  # Will store (labels, centres) from clustering
        self._original_heatmap_data = None  # Store original heatmap for restoration
        self._clustering_active = False
        self._current_norm = None  # Store the normalization method used in clustering

        # Clustering widgets
        self._kmeans_run_button = None
        self._agglomerative_run_button = None
        self._spectral_run_button = None

        # Setup clustering-specific widgets
        self._setup_clustering_widgets()

    # --- Vanessa's KMeans Clustering Implementation ---
    def _kmeans_clustering(self, matrix, n_cluster, available_norm, n_init=10, max_iter=300, init_method='k-means++'):
        '''
        Vanessa's KMeans clustering function adapted for the visualizer.
        
        Parameters:
        -----------
        matrix: numpy array. (x,y,eloss)
            Imagen de espectros.
        n_cluster: int.
            Número de clusters.
        available_norm: string, optional. (default='l2')
            Normalización que queremos aplicar. Opciones: 'l1', 'l2', 'max'.
        n_init: int, optional. (default=10)
            Number of times the k-means algorithm is run with different centroid seeds.
        max_iter: int, optional. (default=300)
            Maximum number of iterations of the k-means algorithm for a single run.
        init_method: string, optional. (default='k-means++')
            Method for initialization: 'k-means++', 'random', or an ndarray.
            
        Returns:
        --------
        labels: numpy array. (x,y)
            Matriz con las etiquetas de cada cluster. 
        centres: numpy array. (n_cluster,eloss)
            Matriz que contiene los centroides de cada cluster identificado.
        '''
        # Prepare and (optionally) normalize the matrix. The helper returns
        # both the reshaped matrix and the one used for clustering so other
        # methods can access them if needed.
        matrix_norm, sclust_norm = self._prepare_clustering_matrix(matrix, available_norm)

        # Determine initialization method
        allowed_init_methods: tuple[Literal['k-means++'], Literal['random']] = ('k-means++', 'random')
        init_value: Literal['k-means++', 'random'] = init_method if init_method in allowed_init_methods else 'k-means++'

        kmeans = KMeans(
            n_clusters=n_cluster, 
            init=init_value,
            n_init=n_init,
            max_iter=max_iter,
            tol=1e-9, 
            random_state=13
        )
        fitted = kmeans.fit(sclust_norm)
        centres = fitted.cluster_centers_
        labels = fitted.labels_.reshape(matrix.shape[:-1])
        return labels, centres

    def _prepare_clustering_matrix(self, matrix, available_norm: str):
        """Validate, reshape and optionally normalize the input 3D matrix.

        Returns a tuple (matrix_norm, sclust_norm) where:
        - matrix_norm: reshaped copy of the original data with shape (n_pixels, n_energy)
        - sclust_norm: the array to feed into clustering (normalized or raw)

        The method also stores the reshaped matrix on the instance as
        `self._last_clustering_matrix` so other parts of the code can access
        the preprocessed data.
        """
        allowed_norms = self._model.constants.AVAILABLE_NORMS
        if available_norm not in allowed_norms:
            raise ValueError(f"norma debe ser uno de {allowed_norms}")

        matrix_norm = matrix.copy()
        matrix_norm = matrix_norm.reshape(matrix.shape[0]*matrix.shape[1], matrix.shape[-1])

        # Si la norma es 'none', no normalizar los datos
        if isinstance(available_norm, str) and available_norm.lower() == 'none':
            sclust_norm = matrix_norm
        else:
            sclust_norm = normalize(matrix_norm, norm=available_norm, axis=1, copy=True)  # type: ignore

        # Store for later access
        try:
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
        except Exception:
            # Best-effort; don't fail if instance attributes can't be set
            pass

        return matrix_norm, sclust_norm

    def _should_use_multifit_data(self) -> bool:
        """
        Check if multifit data should be used for clustering.
        
        Delegates to the model to determine if background-subtracted data
        should be used based on switch state and data availability.
        
        Returns:
            bool: True if multifit data should be used, False otherwise
        """
        try:
            # Get switch state from view
            switch = self._controller.view.right_sidebar.background_subtraction_switch
            if switch is None:
                return False
            
            # Ensure switch.value is a boolean before passing to model
            switch_value = bool(switch.value) if switch.value is not None else False
            
            # Delegate decision to model
            return self._model.should_use_background_subtraction(switch_value)
            
        except Exception as e:
            print(f"Error checking if multifit should be used: {e}")
            return False
    
    def _get_multifit_data(self):
        """
        Retrieve background-subtracted data from the model.
        
        Delegates to the model to retrieve multifit results.
        
        Returns:
            numpy.ndarray: 3D array (y, x, energy) with background-subtracted data,
                          or None if data cannot be retrieved
        """
        try:
            data_cube = self._model.get_multifit_data()
            
            if data_cube is not None:
                print(f"Using multifit data for clustering, shape: {data_cube.shape}")
            
            return data_cube
                
        except Exception as e:
            print(f"Error retrieving multifit data from model: {e}")
            import traceback
            traceback.print_exc()
            return None

    # --- Agglomerative Clustering Implementation ---
    def _agglomerative_clustering(self, matrix, n_clusters, linkage='ward', affinity='euclidean', 
                                   available_norm='none', use_connectivity=False):
        """
        Apply Agglomerative Hierarchical Clustering to the spectrum image data.
        
        Parameters:
        -----------
        matrix: numpy array (x, y, eloss)
            Spectrum image data cube.
        n_clusters: int
            Number of clusters to form.
        linkage: string, optional (default='ward')
            Linkage criterion: 'ward', 'complete', 'average', 'single'.
            Note: 'ward' only works with 'euclidean' affinity.
        affinity: string, optional (default='euclidean')
            Distance metric: 'euclidean', 'l1', 'l2', 'manhattan', 'cosine', etc.
        available_norm: string, optional (default='none')
            Normalization to apply before clustering. Options: 'l1', 'l2', 'max', 'none'.
        use_connectivity: bool, optional (default=False)
            Whether to use spatial connectivity constraints (pixels cluster with neighbors).
            
        Returns:
        --------
        labels: numpy array (x, y)
            Cluster labels for each pixel.
        centres: numpy array (n_clusters, eloss)
            Mean spectrum for each cluster (computed after clustering).
        """
        # Prepare and (optionally) normalize the matrix using the same helper as KMeans
        matrix_norm, sclust_norm = self._prepare_clustering_matrix(matrix, available_norm)
        
        # Store original shape for reshaping labels later
        original_shape = matrix.shape
        
        # Handle 'ward' linkage constraint (only works with euclidean)
        if linkage == 'ward' and affinity != 'euclidean':
            print(f"Warning: 'ward' linkage requires 'euclidean' affinity. Changing affinity to 'euclidean'.")
            affinity = 'euclidean'
        
        # Validate linkage parameter
        allowed_linkages: tuple[Literal['ward'], Literal['complete'], Literal['average'], Literal['single']] = ('ward', 'complete', 'average', 'single')
        linkage_value: Literal['ward', 'complete', 'average', 'single'] = linkage if linkage in allowed_linkages else 'ward'
        
        # Build connectivity matrix if requested
        connectivity_matrix = None
        if use_connectivity:
            # Create spatial connectivity based on image structure
            # This ensures pixels cluster with their spatial neighbors
            ny, nx = original_shape[0], original_shape[1]
            connectivity_matrix = grid_to_graph(ny, nx)
        
        # Create and fit AgglomerativeClustering using the normalized data
        agglomerative = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=linkage_value,
            metric=affinity,
            connectivity=connectivity_matrix  # type: ignore
        )
        
        labels_1d = agglomerative.fit_predict(sclust_norm)
        labels = labels_1d.reshape(original_shape[:-1])
        
        # Compute cluster centers (mean spectrum for each cluster)
        centres = np.zeros((n_clusters, matrix.shape[-1]))
        for i in range(n_clusters):
            cluster_mask = labels_1d == i
            if np.any(cluster_mask):
                centres[i] = matrix_norm[cluster_mask].mean(axis=0)
        
        return labels, centres

    def _apply_agglomerative_clustering(self, n_clusters=5, linkage='ward', affinity='euclidean',
                                       available_norm='none', use_connectivity=False):
        """
        Apply Agglomerative clustering to the spectrum image data and update visualization.
        
        If background-subtraction switch is active and multifit results are available,
        uses the background-subtracted data from multifit instead of raw data.
        """
        try:
            # Check if background-subtraction is enabled and multifit data is available
            use_multifit_data = self._should_use_multifit_data()
            
            if use_multifit_data:
                # Get background-subtracted data from multifit
                data_cube = self._get_multifit_data()
                if data_cube is None:
                    # Fallback to original data if multifit retrieval fails
                    print("Warning: Could not retrieve multifit data, using original data")
                    data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            else:
                # Get the 3D data cube (x, y, energy) from original dataset
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            
            # Store original heatmap data if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Apply agglomerative clustering
            labels, centres = self._agglomerative_clustering(
                data_cube,
                n_clusters=n_clusters,
                linkage=linkage,
                affinity=affinity,
                available_norm=available_norm,
                use_connectivity=use_connectivity
            )
            
            self._clustering_results = (labels, centres)
            self._current_norm = available_norm  # Store for later use
            
            # Try to preserve the current paneB height
            current_b_height = None
            try:
                if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                    obj = self.paneB.object
                    if isinstance(obj, go.Figure):
                        current_b_height = obj.layout.height
                    elif isinstance(obj, dict):
                        current_b_height = obj.get('layout', {}).get('height')
                    if current_b_height is not None:
                        try:
                            current_b_height = int(current_b_height)
                        except Exception:
                            pass
            except Exception:
                current_b_height = None

            # Create clustering visualization
            clustering_fig = self._plot_kmeans_labels_plotly(labels, f"Agglomerative Clustering (n={n_clusters})")
            
            # Apply preserved height if available
            try:
                if current_b_height is not None:
                    clustering_fig.update_layout(height=current_b_height)
            except Exception:
                pass

            # Update the heatmap pane with clustering results
            if self.paneA is not None:
                self.paneA.object = self._to_plotly(clustering_fig)
                self.paneA.param.trigger('object')
            
            # Update spectrum pane to show cluster centers
            self._update_spectrum_with_clusters(centres)
            
            self._clustering_active = True
            
        except Exception as e:
            print(f"Error applying agglomerative clustering: {e}")
            import traceback
            traceback.print_exc()

    # --- Spectral Clustering Implementation ---
    def _spectral_clustering(
        self, 
        matrix, 
        n_clusters, 
        available_norm='none', 
        n_init=10,
        assign_labels='kmeans', 
        affinity='rbf', 
        n_neighbors=10, 
        gamma=1.0
    ):
        """
        Apply Spectral Clustering to the spectrum image data.
        
        Parameters:
        -----------
        matrix: numpy array (x, y, eloss)
            Spectrum image data cube.
        n_clusters: int
            Number of clusters to form.
        available_norm: string, optional (default='none')
            Normalization to apply before clustering. Options: 'l1', 'l2', 'max', 'none'.
        n_init: int, optional (default=10)
            Number of times the k-means algorithm is run with different centroid seeds
            (only used if assign_labels='kmeans').
        assign_labels: string, optional (default='kmeans')
            Strategy for assigning labels: 'kmeans', 'discretize', 'cluster_qr'.
        affinity: string, optional (default='rbf')
            How to construct the affinity matrix: 'nearest_neighbors', 'rbf', 'precomputed', etc.
        n_neighbors: int, optional (default=10)
            Number of neighbors for nearest_neighbors affinity.
        gamma: float, optional (default=1.0)
            Kernel coefficient for rbf, poly, sigmoid, laplacian and chi2 kernels.
            
        Returns:
        --------
        labels: numpy array (x, y)
            Cluster labels for each pixel.
        centres: numpy array (n_clusters, eloss)
            Mean spectrum for each cluster (computed after clustering).
        """
        # Prepare and (optionally) normalize the matrix using the same helper as KMeans
        matrix_norm, sclust_norm = self._prepare_clustering_matrix(matrix, available_norm)
        
        # Store original shape for reshaping labels later
        original_shape = matrix.shape
        
        # Validate assign_labels parameter
        allowed_assign_labels: tuple[Literal['kmeans'], Literal['discretize'], Literal['cluster_qr']] = ('kmeans', 'discretize', 'cluster_qr')
        assign_labels_value: Literal['kmeans', 'discretize', 'cluster_qr'] = assign_labels if assign_labels in allowed_assign_labels else 'kmeans'
        
        # Create and fit SpectralClustering
        # Note: For 'nearest_neighbors' affinity, increase n_neighbors if you get
        # "Graph is not fully connected" warnings. For 'rbf', adjust gamma parameter.
        spectral = SpectralClustering(
            n_clusters=n_clusters,
            n_init=n_init,
            assign_labels=assign_labels_value,
            affinity=affinity,
            n_neighbors=n_neighbors,
            gamma=gamma,
            random_state=13
        )
        
        try:
            labels_1d = spectral.fit_predict(sclust_norm)
        except Exception as e:
            print(f"Spectral clustering warning/error: {e}")
            print(f"Current parameters: affinity={affinity}, n_neighbors={n_neighbors}, gamma={gamma}")
            print("Suggestion: Try increasing n_neighbors or adjusting gamma parameter")
            raise
        labels = labels_1d.reshape(original_shape[:-1])
        
        # Compute cluster centers (mean spectrum for each cluster)
        centres = np.zeros((n_clusters, matrix.shape[-1]))
        for i in range(n_clusters):
            cluster_mask = labels_1d == i
            if np.any(cluster_mask):
                centres[i] = matrix_norm[cluster_mask].mean(axis=0)
        
        return labels, centres

    def _apply_spectral_clustering(
        self, 
        n_clusters=5, 
        available_norm='none', 
        n_init=10,
        assign_labels='kmeans', 
        affinity='rbf', 
        n_neighbors=10, 
        gamma=1.0
    ):
        """
        Apply Spectral clustering to the spectrum image data and update visualization.
        
        If background-subtraction switch is active and multifit results are available,
        uses the background-subtracted data from multifit instead of raw data.
        """
        try:
            # Check if background-subtraction is enabled and multifit data is available
            use_multifit_data = self._should_use_multifit_data()
            
            if use_multifit_data:
                # Get background-subtracted data from multifit
                data_cube = self._get_multifit_data()
                if data_cube is None:
                    # Fallback to original data if multifit retrieval fails
                    print("Warning: Could not retrieve multifit data, using original data")
                    data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            else:
                # Get the 3D data cube (x, y, energy) from original dataset
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            
            # Store original heatmap data if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Apply spectral clustering
            labels, centres = self._spectral_clustering(
                data_cube,
                n_clusters=n_clusters,
                available_norm=available_norm,
                n_init=n_init,
                assign_labels=assign_labels,
                affinity=affinity,
                n_neighbors=n_neighbors,
                gamma=gamma
            )
            
            self._clustering_results = (labels, centres)
            self._current_norm = available_norm  # Store for later use
            
            # Try to preserve the current paneB height
            current_b_height = None
            try:
                if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                    obj = self.paneB.object
                    if isinstance(obj, go.Figure):
                        current_b_height = obj.layout.height
                    elif isinstance(obj, dict):
                        current_b_height = obj.get('layout', {}).get('height')
                    if current_b_height is not None:
                        try:
                            current_b_height = int(current_b_height)
                        except Exception:
                            pass
            except Exception:
                current_b_height = None

            # Create clustering visualization
            clustering_fig = self._plot_kmeans_labels_plotly(labels, f"Spectral Clustering (n={n_clusters})")
            
            # Apply preserved height if available
            try:
                if current_b_height is not None:
                    clustering_fig.update_layout(height=current_b_height)
            except Exception:
                pass

            # Update the heatmap pane with clustering results
            if self.paneA is not None:
                self.paneA.object = self._to_plotly(clustering_fig)
                self.paneA.param.trigger('object')
            
            # Update spectrum pane to show cluster centers
            self._update_spectrum_with_clusters(centres)
            
            self._clustering_active = True
            
        except Exception as e:
            print(f"Error applying spectral clustering: {e}")
            import traceback
            traceback.print_exc()
            


    def _plot_kmeans_labels_plotly(self, labels, title="KMeans Clustering Labels"):
        """
        Plot the clustering labels using Plotly for interactive visualization.
        Adapted from Vanessa's code for integration into the visualizer.
        """
        n_clusters = len(np.unique(labels))

        # Build colors (one per cluster) and the stepped Plotly colorscale
        cluster_colors, discrete_colorscale = self._build_cluster_colors_and_scale(n_clusters)
        self.cluster_colors = cluster_colors
        self.discrete_colorscale = discrete_colorscale

        # Decide colorbar placement and margin
        try:
            ny, nx = labels.shape[-2], labels.shape[-1]
        except Exception:
            ny, nx = 1, 1

        colorbar, margin = self._build_colorbar(n_clusters, ny, nx)

        fig = go.Figure(go.Heatmap(
            z=labels,
            colorscale=self.discrete_colorscale,
            colorbar=colorbar,
            hovertemplate='x: %{x}<br>y: %{y}<br>Cluster: %{z}<extra></extra>',
            zmin=-0.5,
            zmax=n_clusters-0.5
        ))

        # Keep same layout and aspect locking as the unclustered figA but adjust margins
        fig.update_layout(
            title=title,
            height=400,
            margin=margin,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(autorange='reversed', scaleanchor='x', scaleratio=1, constrain='domain',
                         showgrid=False, zeroline=False, showticklabels=False)
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain='domain')
        return fig

    def _build_cluster_colors_and_scale(self, n_clusters: int):
        """Return (cluster_colors, discrete_colorscale) for n_clusters.

        Centralises the logic that samples the matplotlib colormap, converts
        colors to Plotly strings and builds the stepped colorscale.
        """
        # Use a preferred ordering for tab20-like palettes if available
        preferred = None
        if isinstance(self._CLUSTER_COLORS, str) and 'tab20' in self._CLUSTER_COLORS:
            preferred = list(self._ORDER_COLORS)

        listed = get_nclusters_cmap(self._CLUSTER_COLORS, n_clusters, index_order=preferred)
        cluster_colors = [to_plotly_color(c) for c in listed]
        discrete = build_discrete_colorscale(cluster_colors)
        return cluster_colors, discrete

    def _build_colorbar(self, n_clusters: int, ny: int, nx: int):
        """Construct colorbar dict and corresponding margin based on aspect.

        Returns (colorbar, margin).
        """
        tickvals = list(np.arange(n_clusters))
        ticktext = [str(i) for i in range(n_clusters)]

        if ny > nx:
            colorbar = dict(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext,
                orientation='v',
                x=1.02,
                y=0.5,
                xanchor='left',
                yanchor='middle',
                len=1.0,
                thickness=24,
            )
            margin = dict(l=16, r=80, t=50, b=20)
        else:
            colorbar = dict(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext,
                orientation='h',
                x=0.5,
                y=-0.18,
                xanchor='center',
                yanchor='top',
                len=1.0,
                thickness=20,
            )
            margin = dict(l=16, r=16, t=50, b=80)

        return colorbar, margin

    def _apply_kmeans_clustering(self, n_clusters=6, available_norm='l2', n_init=10, max_iter=300, init_method='k-means++'):
        """
        Apply KMeans clustering to the spectrum image data and update visualization.
        
        If background-subtraction switch is active and multifit results are available,
        uses the background-subtracted data from multifit instead of raw data.
        """

        try:
            # Check if background-subtraction is enabled and multifit data is available
            use_multifit_data = self._should_use_multifit_data()
            
            if use_multifit_data:
                # Get background-subtracted data from multifit
                data_cube = self._get_multifit_data()
                if data_cube is None:
                    # Fallback to original data if multifit retrieval fails
                    print("Warning: Could not retrieve multifit data, using original data")
                    data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            else:
                # Get the 3D data cube (x, y, energy) from original dataset
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            
            # Store original heatmap data if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Apply clustering with all parameters
            labels, centres = self._kmeans_clustering(
                data_cube, 
                n_clusters, 
                available_norm,
                n_init=n_init,
                max_iter=max_iter,
                init_method=init_method
            )
            
            self._clustering_results = (labels, centres)
            self._current_norm = available_norm  # Store for later use in hover/click
            
            # Try to preserve the current paneB height so the clustering view
            # initially appears with the same vertical size as the current spectrum figure.
            current_b_height = None
            try:
                if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                    obj = self.paneB.object
                    # obj can be a go.Figure or a dict (plotly json). Read layout.height if available.
                    if isinstance(obj, go.Figure):
                        current_b_height = obj.layout.height
                    elif isinstance(obj, dict):
                        current_b_height = obj.get('layout', {}).get('height')
                    if current_b_height is not None:
                        try:
                            current_b_height = int(current_b_height)
                        except Exception:
                            pass
            except Exception:
                current_b_height = None

            # Create clustering visualization
            clustering_fig = self._plot_kmeans_labels_plotly(labels, f"KMeans Clustering (n={n_clusters})")
            # If we were able to capture the current paneB height, apply it to the
            # clustering figure so it doesn't jump to a different vertical size.
            try:
                if current_b_height is not None:
                    clustering_fig.update_layout(height=current_b_height)
            except Exception:
                # best-effort only; do not fail clustering because of layout setting
                pass

            # Update the heatmap pane with clustering results (convert to plotly json)
            if self.paneA is not None:
                self.paneA.object = self._to_plotly(clustering_fig)
                self.paneA.param.trigger('object')  # Force parameter update
                # Alternative: recreate the pane entirely if needed
                # self.paneA = pn.pane.Plotly(self._to_plotly(clustering_fig), sizing_mode='stretch_both')
            
            # Update spectrum pane to show cluster centers
            self._update_spectrum_with_clusters(centres)
            
            self._clustering_active = True
            
        except Exception as e:
            print(f"Error applying clustering: {e}")
            import traceback
            traceback.print_exc()

    def _update_spectrum_with_clusters(self, centres):
        """Update the spectrum pane to show cluster centers."""
        if self.paneB is None:
            return
            
        # Create traces for each cluster center
        traces = []
        colors = self.cluster_colors  # Use the plain color list (one per cluster)

        for i, center in enumerate(centres):
            color = colors[i % len(colors)]
            traces.append(go.Scatter(
                x=self._energy,
                y=center,
                mode='lines',
                name=f'Cluster {i}',
                line=dict(color=color, width=2)
            ))
        
        fig = go.Figure(data=traces)
        fig.update_layout(
            title="Cluster Centers",
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            showlegend=True,
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.6)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
            )
        )
        
        self.paneB.object = fig
        self.paneB.param.trigger('object')  # Force parameter update

    def _restore_original_view(self):
        """Restore the original heatmap view before clustering."""
        if self._original_heatmap_data is not None and self.paneA is not None:
            # Create original heatmap
            ny, nx = self._original_heatmap_data.shape
            heat = go.Heatmap(
                z=self._original_heatmap_data,
                x=np.arange(nx),
                y=np.arange(ny),
                colorscale="Greys_r",
                showscale=False,
                hovertemplate='x: %{x}<br>y: %{y}<br>Intensity: %{z}<extra></extra>'
            )
            
            fig = go.Figure(data=[heat])
            fig.update_layout(
                title="Original Spectrum Image",
                xaxis_title="X",
                yaxis_title="Y",
                yaxis_autorange='reversed'
            )
            
            self.paneA.object = fig
            self.paneA.param.trigger('object')  # Force parameter update
            self._clustering_active = False
            print("Restored original view")

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both'
        )
        
        right_column = pn.Column(
            self.paneB,
            sizing_mode='stretch_both'
        )
        
        resizable_columns = ResizableColumns(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
 
        return resizable_columns

    @override
    def create_dataset_info(self, dataset_attrs: dict | None = None):
        return super().create_dataset_info(dataset_attrs)

    # --- Clustering Widget Setup ---
    def _setup_clustering_widgets(self):
        """Connect clustering buttons to their respective handlers."""
        if kmeans_run_button := getattr(self._controller.view.right_sidebar, "kmeans_run_button", None):
            self._kmeans_run_button = kmeans_run_button
            kmeans_run_button.on_click(self._run_kmeans_clustering)

        if agglomerative_run_button := getattr(self._controller.view.right_sidebar, "agglomerative_run_button", None):
            self._agglomerative_run_button = agglomerative_run_button
            agglomerative_run_button.on_click(self._run_agglomerative_clustering)

        if spectral_run_button := getattr(self._controller.view.right_sidebar, "spectral_run_button", None):
            self._spectral_run_button = spectral_run_button
            spectral_run_button.on_click(self._run_spectral_clustering)

    def _run_kmeans_clustering(self, event):
        """Handle clustering button click."""
        
        # self._restore_original_view()
        
        if self._kmeans_run_button is not None:
            self._kmeans_run_button.disabled = True  # Disable to prevent multiple clicks
        
        kmeans_input = self._controller.view.right_sidebar.kmeans_input
        
        n_clusters = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        available_norm = self._model.constants.DEFAULT_SELECTED_NORM
        n_init = self._model.constants.DEFAULT_NUMBER_OF_INIT
        max_iter = self._model.constants.DEFAULT_MAX_ITER
        init_method = self._model.constants.DEFAULT_INIT_METHOD

        if kmeans_input is not None:
            n_clusters = kmeans_input["n_clusters"].value
            available_norm = kmeans_input["available_norms"].value
            n_init = kmeans_input["n_init"].value
            max_iter = kmeans_input["max_iter"].value
            init_method = kmeans_input["init_method"].value

        try:
            self._apply_kmeans_clustering(
                n_clusters=n_clusters, 
                available_norm=available_norm, 
                n_init=n_init, 
                max_iter=max_iter, 
                init_method=init_method
            )
        finally:
            if self._kmeans_run_button is not None:
                self._kmeans_run_button.disabled = False  # Re-enable button after processing

    def _run_agglomerative_clustering(self, event):
        """Handle agglomerative clustering button click."""
        
        if self._agglomerative_run_button is not None:
            self._agglomerative_run_button.disabled = True  # Disable to prevent multiple clicks
        
        agglomerative_input = self._controller.view.right_sidebar.agglomerative_input
        
        # Default values
        n_clusters = 5
        linkage = 'ward'
        affinity = 'euclidean'
        available_norm = 'none'
        connectivity = False

        if agglomerative_input is not None:
            n_clusters = agglomerative_input["n_clusters"].value
            linkage = agglomerative_input["linkage"].value
            affinity = agglomerative_input["affinity"].value
            available_norm = agglomerative_input["available_norms"].value

        try:
            self._apply_agglomerative_clustering(
                n_clusters=n_clusters,
                linkage=linkage,
                affinity=affinity,
                available_norm=available_norm,
                use_connectivity=connectivity
            )
        finally:
            if self._agglomerative_run_button is not None:
                self._agglomerative_run_button.disabled = False

    def _run_spectral_clustering(self, event):
        """Handle spectral clustering button click."""
        
        if self._spectral_run_button is not None:
            self._spectral_run_button.disabled = True  # Disable to prevent multiple clicks
        
        spectral_input = self._controller.view.right_sidebar.spectral_input
        
        # Default values
        n_clusters = 5
        available_norm = 'none'
        n_init = 10
        assign_labels = 'kmeans'
        affinity = 'rbf'
        n_neighbors = 10
        gamma = 1.0

        if spectral_input is not None:
            n_clusters = spectral_input["n_clusters"].value
            available_norm = spectral_input["available_norms"].value
            n_init = spectral_input["n_init"].value
            assign_labels = spectral_input["labels_assign_method"].value
            affinity = spectral_input["spectral_affinity_metrics"].value
            n_neighbors = spectral_input["n_neighbors"].value
            gamma = spectral_input["gamma"].value

        try:
            self._apply_spectral_clustering(
                n_clusters=n_clusters,
                available_norm=available_norm,
                n_init=n_init,
                assign_labels=assign_labels,
                affinity=affinity,
                n_neighbors=n_neighbors,
                gamma=gamma
            )
        finally:
            if self._spectral_run_button is not None:
                self._spectral_run_button.disabled = False

    # --- Plot / Pane Setup Override (removed - using base class implementation) ---
    # Base class _setup_plots and _setup_callbacks handle basic visualization
    # Clustering-specific plot updates happen in clustering methods
    
    # --- Override interaction methods to add clustering-specific behavior ---
    
    @override
    def _plot_pixel_spectrum(self, i, j, title_prefix="Hover"):
        """
        Plot spectrum for a specific pixel with clustering enhancements.
        
        Shows:
        1. Original pixel spectrum (if no normalization active)
        2. Normalized pixel spectrum if available_norm != 'none'
        3. Corresponding cluster center if clustering is active
        
        Args:
            i, j: Pixel coordinates
            title_prefix: Prefix for the plot title
            
        Returns:
            go.Figure or None: Plotly figure or None if spectrum cannot be retrieved
        """
        # Get original spectrum
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        if spec is None:
            return None
        
        fig = go.Figure()
        
        # 1. Plot original spectrum unless a normalization is active
        should_plot_original = True
        if hasattr(self, '_current_norm') and isinstance(self._current_norm, str) and self._current_norm.lower() != 'none':
            should_plot_original = False

        if should_plot_original:
            fig.add_trace(go.Scatter(
                x=self._energy,
                y=spec,
                mode='lines',
                name=f"Original (i={i}, j={j})",
                opacity=0.2
            ))
        
        # 2. Plot normalized spectrum if norm != 'none' and clustering has been run
        if (hasattr(self, '_current_norm') and 
            isinstance(self._current_norm, str) and 
            self._current_norm.lower() != 'none' and
            hasattr(self, '_last_clustering_input')):
            
            # Get the linear index for the pixel
            try:
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
                ny, nx = data_cube.shape[0], data_cube.shape[1]
                linear_idx = i * nx + j
                
                if linear_idx < len(self._last_clustering_input):
                    normalized_spec = self._last_clustering_input[linear_idx]
                    fig.add_trace(go.Scatter(
                        x=self._energy,
                        y=normalized_spec,
                        mode='lines',
                        name=f"Normalized ({self._current_norm})",
                        line=dict(color='orange', width=2),
                        opacity=0.2
                    ))
            except Exception as e:
                print(f"Error plotting normalized spectrum: {e}")
        
        # 3. Plot cluster center if clustering is active
        if self._clustering_active and self._clustering_results is not None:
            try:
                labels, centres = self._clustering_results
                cluster_label = labels[i, j]
                cluster_center = centres[cluster_label]
                
                # Get the color for this cluster
                color = self.cluster_colors[cluster_label % len(self.cluster_colors)]
                
                fig.add_trace(go.Scatter(
                    x=self._energy,
                    y=cluster_center,
                    mode='lines',
                    name=f"Cluster {cluster_label} center",
                    line=dict(color=color, width=3)
                ))
            except Exception as e:
                print(f"Error plotting cluster center: {e}")
        
        fig.update_layout(
            title=f"{title_prefix} at (i={i}, j={j})",
            margin=dict(l=16, r=16, t=48, b=16),
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1,
            )
        )
        
        return fig
    
    @override
    def _on_paneA_click(self, event):
        """
        Handle single/double clicks on the heatmap with clustering features.
        
        Single click: Freezes the current pixel so hovering doesn't change the view.
        Double click: Toggles between showing all cluster centers and re-enabling hover mode.
        """
        if event.new is None:
            return
        
        try:
            import time
            current_time = time.time() * 1000  # Convert to milliseconds
            time_since_last_click = current_time - self._last_click_time
            
            # Check if this is a double-click
            if time_since_last_click < self._DOUBLE_CLICK_MS:
                # DOUBLE CLICK: Toggle between showing all clusters and re-enabling hover
                self._frozen_pixel = None  # Unfreeze
                
                if self._hover_disabled:
                    # Re-enable hover mode
                    self._hover_disabled = False
                    
                    # Trigger hover for current mouse position if available
                    if self._last_hover_point is not None:
                        i, j = int(self._last_hover_point['y']), int(self._last_hover_point['x'])
                        fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
                        if fig is not None and self.paneB is not None:
                            self.paneB.object = fig
                else:
                    # Show all clusters and disable hover
                    if self._clustering_active and self._clustering_results is not None:
                        self._hover_disabled = True  # Disable hover
                        
                        labels, centres = self._clustering_results
                        
                        # Create traces for each cluster center
                        fig = go.Figure()
                        
                        for i, center in enumerate(centres):
                            color = self.cluster_colors[i % len(self.cluster_colors)]
                            fig.add_trace(go.Scatter(
                                x=self._energy,
                                y=center,
                                mode='lines',
                                name=f'Cluster {i}',
                                line=dict(color=color, width=2)
                            ))
                        
                        fig.update_layout(
                            title="All Cluster Centers (Double Click again to re-enable hover)",
                            xaxis_title="Energy Loss (eV)",
                            yaxis_title="Intensity (AU)",
                            showlegend=True,
                            legend=dict(
                                x=0.98,
                                y=0.98,
                                xanchor='right',
                                yanchor='top',
                                bgcolor='rgba(255,255,255,0.8)',
                                bordercolor='rgba(0,0,0,0.2)',
                                borderwidth=1,
                            )
                        )
                        
                        if self.paneB is not None:
                            self.paneB.object = fig
                
                # Reset timer to prevent treating next click as double-click
                self._last_click_time = current_time - 1000
                return
                
            else:
                # SINGLE CLICK: Call parent implementation to freeze pixel
                super()._on_paneA_click(event)
                # Update last click time
                self._last_click_time = current_time
                
        except Exception as e:
            print(f"Error handling click: {e}")
            import traceback
            traceback.print_exc()