"""
Clustering-specific spectrum image visualizer.

Extends the shared SpectrumImageVisualizer component with clustering capabilities:
- KMeans clustering
- Agglomerative clustering  
- Spectral clustering
- Cluster center visualization
- Normalized spectrum display

This visualizer orchestrates the UI interactions and delegates to OOP utility classes
for algorithms, data preparation, and plotting.
"""

import panel as pn
import numpy as np
import plotly.graph_objs as go
import time
import threading

from whateels.helpers import SpectrumExtractor
from whateels.components.visualizers import SpectrumImageVisualizer as SharedSpectrumImageVisualizer
from whateels.components import ResizableColumns, ProgressDisplay
from typing import override, TYPE_CHECKING

# Import clustering page utilities (OOP classes)
from ....utils import (
    DataPreprocessor,
    KMeansClusteringAlgorithm,
    AgglomerativeClusteringAlgorithm,
    SpectralClusteringAlgorithm,
    ClusterVisualizer,
)

if TYPE_CHECKING:
    from ...model import ClusteringModel
    from .. import ClusteringView
    from xarray import Dataset


class SpectrumImageVisualizer(SharedSpectrumImageVisualizer):
    """
    Clustering-enhanced Spectrum Image Visualizer.
    
    Extends the shared visualizer with clustering capabilities:
    - KMeans, Agglomerative, and Spectral clustering
    - Cluster center visualization
    - Normalized spectrum display
    - Background subtraction support
    
    This class focuses on orchestrating UI interactions and delegates
    heavy lifting to helper modules.
    """

    def __init__(self, model: "ClusteringModel", view: "ClusteringView", dataset: "Dataset"):
        # Get axis name from model constants
        eloss_name = getattr(model.constants, 'ELOSS', 'Eloss') if hasattr(model, 'constants') else 'Eloss'
        
        # Call parent constructor to setup base visualization
        super().__init__(dataset, eloss_name)

        # Store references for clustering features
        self._model = model
        self._view = view
        
        # Store original plots layout to restore after clustering
        self._plots_layout = None

        # Double-click timing for toggling cluster display
        self._last_click_time = 0
        self._DOUBLE_CLICK_MS = 400  # Double-click threshold in milliseconds
        self._hover_disabled = False  # Disable hover after showing all clusters

        # Clustering state
        self._clustering_results = None  # Will store (labels, centres) from clustering
        self._original_heatmap_data = None  # Store original heatmap for restoration
        self._clustering_active = False
        self._current_norm = None  # Store the normalization method used in clustering
        
        # Store normalized data for visualization
        self._last_clustering_matrix = None
        self._last_clustering_input = None

        # Clustering widgets
        self._kmeans_run_button = None
        self._agglomerative_run_button = None
        self._spectral_run_button = None
        
        # OOP utility instances
        self._preprocessor = DataPreprocessor()
        self._visualizer: ClusterVisualizer | None = None  # Created after clustering
        
        # Cluster colors (set after clustering)
        self.cluster_colors = []
        
        # Progress display for clustering operations
        self._progress_display = ProgressDisplay(name="Clustering")

        # Setup clustering-specific widgets
        self._setup_clustering_widgets()

    # --- Clustering Application Methods ---
    
    def _apply_kmeans_clustering(
        self, 
        n_clusters=6, 
        available_norm='l2', 
        n_init=10, 
        max_iter=300, 
        init_method='k-means++'
    ):
        """Apply KMeans clustering and update visualization."""
        def run_clustering():
            try:
                # Reset and prepare progress display
                self._progress_display.reset()
                self._progress_display.visible = True
                
                # Replace main content with progress display
                self._show_clustering_progress()
                
                # Get data (possibly background-subtracted)
                self._progress_display.update(5, "Loading data...", level='info')
                data_cube = self._get_data_for_clustering()
                time.sleep(0.05)
                
                # Store original heatmap if not already stored
                if self._original_heatmap_data is None:
                    self._original_heatmap_data = data_cube.sum(axis=-1)
                
                # Update progress: preparing data - step 1
                self._progress_display.update(15, "Preparing data - normalizing...", level='info')
                time.sleep(0.05)
                
                # Prepare data using OOP preprocessor
                matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
                
                # Update progress: preparing data - step 2
                self._progress_display.update(25, "Preparing data - reshaping...", level='info')
                time.sleep(0.05)
                
                # Store for later use in visualization
                self._last_clustering_matrix = matrix_norm
                self._last_clustering_input = sclust_norm
                
                # Update progress: running algorithm - step 1
                self._progress_display.update(35, "Running algorithm - initializing...", level='info')
                time.sleep(0.05)
                
                # Apply clustering algorithm using OOP class
                init_val = 'k-means++' if init_method == 'k-means++' else 'random'
                algorithm = KMeansClusteringAlgorithm(
                    n_clusters=n_clusters,
                    norm=available_norm,  # type: ignore
                    n_init=n_init,
                    max_iter=max_iter,
                    init_method=init_val
                )
                
                # Update progress: running algorithm - step 2
                self._progress_display.update(50, "Running algorithm - clustering...", level='info')
                time.sleep(0.05)
                
                labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
                
                # Update progress: visualizing results
                self._progress_display.update(65, "Visualizing results - creating heatmap...", level='info')
                time.sleep(0.05)
                
                # Store results and update visualization
                self._update_clustering_visualization(labels, centres, available_norm, n_clusters, "KMeans")
                
                # Update progress: finishing up
                self._progress_display.update(85, "Finalizing...", level='info')
                time.sleep(0.05)
                
                # Mark as complete and restore plots
                self._progress_display.completion("K-Means clustering complete!")
                
                # Small delay to show completion message, then restore plots
                time.sleep(0.3)
                self._restore_plots_layout()
                
            except Exception as e:
                print(f"Error applying KMeans clustering: {e}")
                import traceback
                traceback.print_exc()
                self._progress_display.error(f"Clustering failed: {str(e)}")
                
                # Restore plots on error too
                time.sleep(2)
                self._restore_plots_layout()
        
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(target=run_clustering, daemon=True)
        thread.start()

    def _apply_agglomerative_clustering(
        self,
        n_clusters=5,
        linkage='ward',
        affinity='euclidean',
        available_norm='none',
        use_connectivity=False
    ):
        """Apply Agglomerative clustering and update visualization."""
        def run_clustering():
            try:
                # Reset and prepare progress display
                self._progress_display.reset()
                self._progress_display.visible = True
                
                # Replace main content with progress display
                self._show_clustering_progress()

                # Get data (possibly background-subtracted)
                self._progress_display.update(5, "Loading data...", level='info')
                data_cube = self._get_data_for_clustering()
                time.sleep(0.05)
                
                # Store original heatmap if not already stored
                if self._original_heatmap_data is None:
                    self._original_heatmap_data = data_cube.sum(axis=-1)
                
                # Update progress: preparing data - step 1
                self._progress_display.update(15, "Preparing data - normalizing...", level='info')
                time.sleep(0.05)
                
                # Prepare data using OOP preprocessor
                matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
                
                # Update progress: preparing data - step 2
                self._progress_display.update(25, "Preparing data - reshaping...", level='info')
                time.sleep(0.05)

                
                # Store for later use in visualization
                self._last_clustering_matrix = matrix_norm
                self._last_clustering_input = sclust_norm
                
                # Update progress: running algorithm - step 1
                self._progress_display.update(35, "Running algorithm - building hierarchy...", level='info')
                time.sleep(0.05)

                
                # Apply clustering algorithm using OOP class
                linkage_val = linkage if linkage in ('ward', 'complete', 'average', 'single') else 'ward'
                algorithm = AgglomerativeClusteringAlgorithm(
                    n_clusters=n_clusters,
                    norm=available_norm,  # type: ignore
                    linkage=linkage_val,  # type: ignore
                    affinity=affinity,
                    use_connectivity=use_connectivity
                )
                
                # Update progress: running algorithm - step 2
                self._progress_display.update(50, "Running algorithm - clustering...", level='info')
                time.sleep(0.05)

                
                labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
                
                # Update progress: visualizing results
                self._progress_display.update(65, "Visualizing results - creating heatmap...", level='info')
                time.sleep(0.05)

                
                # Store results and update visualization
                self._update_clustering_visualization(labels, centres, available_norm, n_clusters, "Agglomerative")
                
                # Update progress: finishing up
                self._progress_display.update(85, "Finalizing...", level='info')
                time.sleep(0.05)

                
                # Mark as complete and restore plots
                self._progress_display.completion("Agglomerative clustering complete!")
                
                # Small delay to show completion message, then restore plots
                time.sleep(0.3)
                self._restore_plots_layout()
                
            except Exception as e:
                print(f"Error applying Agglomerative clustering: {e}")
                import traceback
                traceback.print_exc()
                self._progress_display.error(f"Clustering failed: {str(e)}")
                
                # Restore plots on error too
                time.sleep(2)
                self._restore_plots_layout()
        
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(target=run_clustering, daemon=True)
        thread.start()

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
        """Apply Spectral clustering and update visualization."""
        def run_clustering():
            try:
                # Reset and prepare progress display
                self._progress_display.reset()
                self._progress_display.visible = True
                
                # Replace main content with progress display
                self._show_clustering_progress()
                
                # Get data (possibly background-subtracted)
                self._progress_display.update(5, "Loading data...", level='info')
                data_cube = self._get_data_for_clustering()
                time.sleep(0.05)

                
                # Store original heatmap if not already stored
                if self._original_heatmap_data is None:
                    self._original_heatmap_data = data_cube.sum(axis=-1)
                
                # Update progress: preparing data - step 1
                self._progress_display.update(15, "Preparing data - normalizing...", level='info')
                time.sleep(0.05)

                
                # Prepare data using OOP preprocessor
                matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
                
                # Update progress: preparing data - step 2
                self._progress_display.update(25, "Preparing data - reshaping...", level='info')
                time.sleep(0.05)

                
                # Store for later use in visualization
                self._last_clustering_matrix = matrix_norm
                self._last_clustering_input = sclust_norm
                
                # Update progress: running algorithm - step 1
                self._progress_display.update(35, "Running algorithm - computing affinity...", level='info')
                time.sleep(0.05)

                
                # Apply clustering algorithm using OOP class
                assign_val = assign_labels if assign_labels in ('kmeans', 'discretize', 'cluster_qr') else 'kmeans'
                algorithm = SpectralClusteringAlgorithm(
                    n_clusters=n_clusters,
                    norm=available_norm,  # type: ignore
                    n_init=n_init,
                    assign_labels=assign_val,  # type: ignore
                    affinity=affinity,
                    n_neighbors=n_neighbors,
                    gamma=gamma
                )
                
                # Update progress: running algorithm - step 2
                self._progress_display.update(50, "Running algorithm - eigendecomposition...", level='info')
                time.sleep(0.05)

                
                labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
                
                # Update progress: visualizing results
                self._progress_display.update(65, "Visualizing results - creating heatmap...", level='info')
                time.sleep(0.05)

                
                # Store results and update visualization
                self._update_clustering_visualization(labels, centres, available_norm, n_clusters, "Spectral")
                
                # Update progress: finishing up
                self._progress_display.update(85, "Finalizing...", level='info')
                time.sleep(0.05)

                
                # Mark as complete and restore plots
                self._progress_display.completion("Spectral clustering complete!")
                
                # Small delay to show completion message, then restore plots
                time.sleep(0.3)
                self._restore_plots_layout()
                
            except Exception as e:
                print(f"Error applying Spectral clustering: {e}")
                import traceback
                traceback.print_exc()
                self._progress_display.error(f"Clustering failed: {str(e)}")
                
                # Restore plots on error too
                time.sleep(2)
                self._restore_plots_layout()
        
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(target=run_clustering, daemon=True)
        thread.start()

    # --- Helper Methods ---
    
    def _get_data_for_clustering(self):
        """Get data cube for clustering, possibly with background subtraction."""
        # Check if background-subtraction is enabled
        try:
            switch = self._view.right_sidebar.background_subtraction_switch
            switch_value = bool(switch.value) if switch and switch.value is not None else False
            use_multifit = DataPreprocessor.should_use_multifit_data(self._model, switch_value)
        except Exception:
            use_multifit = False
        
        if use_multifit:
            # Get background-subtracted data from multifit
            data_cube = DataPreprocessor.get_multifit_data(self._model)
            if data_cube is None:
                print("Warning: Could not retrieve multifit data, using original data")
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
        else:
            # Get the 3D data cube (x, y, energy) from original dataset
            data_cube = np.asarray(self._electron_count_data.fillna(0.0))
        
        return data_cube
    
    def _update_clustering_visualization(self, labels, centres, norm, n_clusters, algorithm_name):
        """Update visualization after clustering."""
        self._clustering_results = (labels, centres)
        self._current_norm = norm
        
        # Create visualizer and build colors for clusters
        self._visualizer = ClusterVisualizer(n_clusters)
        self.cluster_colors = self._visualizer.cluster_colors
        
        # Try to preserve current paneB height
        current_b_height = self._get_current_pane_height()
        
        # Create clustering visualization using OOP visualizer
        clustering_fig = self._visualizer.plot_labels(
            labels,
            title=f"{algorithm_name} Clustering (n={n_clusters})",
            height=current_b_height
        )
        
        # Update heatmap pane
        if self.paneA is not None:
            self.paneA.object = self._to_plotly(clustering_fig)
            self.paneA.param.trigger('object')
        
        # Update spectrum pane to show cluster centers
        centers_fig = self._visualizer.plot_centers(centres, self._energy)
        if self.paneB is not None:
            self.paneB.object = centers_fig
            self.paneB.param.trigger('object')
        
        self._clustering_active = True
    
    def _get_current_pane_height(self):
        """Get current paneB height to preserve it."""
        try:
            if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                obj = self.paneB.object
                if isinstance(obj, go.Figure):
                    return obj.layout.height
                elif isinstance(obj, dict):
                    return obj.get('layout', {}).get('height')
        except Exception:
            pass
        return None
    
    def _show_clustering_progress(self):
        """Replace main content with progress display during clustering."""
        try:
            # Ensure progress display is visible before showing
            self._progress_display.visible = True
            
            if self._view and hasattr(self._view, 'main'):
                self._view.main.update(self._progress_display)
        except Exception as e:
            print(f"Error showing clustering progress: {e}")
            import traceback
            traceback.print_exc()
    
    def _restore_plots_layout(self):
        """Restore the plots layout after clustering completes."""
        try:
            if self._view and hasattr(self._view, 'main') and self._plots_layout is not None:
                self._view.main.update(self._plots_layout)
        except Exception as e:
            print(f"Error restoring plots layout: {e}")

    # --- Event Handlers ---
    
    def _run_kmeans_clustering(self, event):
        """Handle KMeans clustering button click."""
        if self._kmeans_run_button is not None:
            self._kmeans_run_button.disabled = True
        
        try:
            kmeans_input = self._view.right_sidebar.kmeans_input
            
            # Get parameters or use defaults
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

            self._apply_kmeans_clustering(
                n_clusters=n_clusters,
                available_norm=available_norm,
                n_init=n_init,
                max_iter=max_iter,
                init_method=init_method
            )
        finally:
            if self._kmeans_run_button is not None:
                self._kmeans_run_button.disabled = False

    def _run_agglomerative_clustering(self, event):
        """Handle Agglomerative clustering button click."""
        if self._agglomerative_run_button is not None:
            self._agglomerative_run_button.disabled = True
        
        try:
            agglomerative_input = self._view.right_sidebar.agglomerative_input
            
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
        """Handle Spectral clustering button click."""
        if self._spectral_run_button is not None:
            self._spectral_run_button.disabled = True
        
        try:
            spectral_input = self._view.right_sidebar.spectral_input
            
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

    # --- Widget Setup ---
    
    def _setup_clustering_widgets(self):
        """Connect clustering buttons to their respective handlers."""
        if kmeans_run_button := getattr(self._view.right_sidebar, "kmeans_run_button", None):
            self._kmeans_run_button = kmeans_run_button
            kmeans_run_button.on_click(self._run_kmeans_clustering)

        if agglomerative_run_button := getattr(self._view.right_sidebar, "agglomerative_run_button", None):
            self._agglomerative_run_button = agglomerative_run_button
            agglomerative_run_button.on_click(self._run_agglomerative_clustering)

        if spectral_run_button := getattr(self._view.right_sidebar, "spectral_run_button", None):
            self._spectral_run_button = spectral_run_button
            spectral_run_button.on_click(self._run_spectral_clustering)

    # --- Public Layout Builders ---
    
    @override
    def create_plots(self):
        """Create the resizable two-column layout."""
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
        
        # Store the plots layout so we can restore it after clustering
        self._plots_layout = resizable_columns

        container = pn.Column( 
            resizable_columns,
            sizing_mode='stretch_both'
        )
        return container

    @override
    def create_dataset_info(self, dataset_attrs: dict | None = None):
        """Create dataset info panel."""
        return super().create_dataset_info(dataset_attrs)

    # --- Override Interaction Methods ---
    
    @override
    def _plot_pixel_spectrum(self, i, j, title_prefix="Hover"):
        """
        Plot spectrum for a specific pixel with clustering enhancements.
        
        Shows:
        1. Original pixel spectrum (if no normalization active)
        2. Normalized pixel spectrum if available_norm != 'none'
        3. Corresponding cluster center if clustering is active
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
            hasattr(self, '_last_clustering_input') and
            self._last_clustering_input is not None):
            
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
                    if self._clustering_active and self._clustering_results is not None and self._visualizer is not None:
                        self._hover_disabled = True  # Disable hover
                        
                        _, centres = self._clustering_results
                        
                        # Create figure with all cluster centers using OOP visualizer
                        fig = self._visualizer.plot_centers(
                            centres,
                            self._energy,
                            title="All Cluster Centers (Double Click again to re-enable hover)"
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
