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
import traceback

from whateels.helpers import SpectrumExtractor
from whateels.base.plots import BaseSpectrumImagePlot
from whateels.components import SplitJs, ProgressDisplay
from typing import override, TYPE_CHECKING


# Import clustering page utilities (OOP classes)
from ....utils import (
    DataPreprocessor,
    KMeansClusteringAlgorithm,
    AgglomerativeClusteringAlgorithm,
    SpectralClusteringAlgorithm,
    ClusterVisualizer,
    ClusteringOrchestrator,
)

if TYPE_CHECKING:
    from ...model import ClusteringModel
    from .. import ClusteringView
    from xarray import Dataset


class SpectrumImagePlot(BaseSpectrumImagePlot):
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
        # Set notification position
        pn.state.notifications.position = 'bottom-left'  # type: ignore
        
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
        self._frozen_pixel = None  # Store frozen pixel (i, j) from single click
        self._hover_disabled = False  # Disable hover after showing all clusters
        self._last_hover_point = None  # Store last hover position for re-enabling

        # Clustering state
        self._clustering_results = None  # Will store (labels, centres) from clustering
        self._original_heatmap_data = None  # Store original heatmap for restoration
        self._clustering_active = False
        self._current_norm = None  # Store the normalization method used in clustering
        
        # Store normalized data for visualization
        self._last_clustering_matrix = None
        self._last_clustering_input = None

        # Clustering widgets
        self._kmeans_run_button = self._view.right_sidebar.kmeans_run_button
        self._kmeans_run_button.on_click(lambda _ : self.run_kmeans_clustering(user_click=True))
        
        self._agglomerative_run_button = self._view.right_sidebar.agglomerative_run_button
        self._agglomerative_run_button.on_click(lambda _ : self.run_agglomerative_clustering(user_click=True))
        
        self._spectral_run_button = self._view.right_sidebar.spectral_run_button
        self._spectral_run_button.on_click(lambda _ : self.run_spectral_clustering(user_click=True))
        
        # OOP utility instances
        self._preprocessor = DataPreprocessor()
        self._visualizer: ClusterVisualizer | None = None  # Created after clustering
        
        # Cluster colors (set after clustering)
        self.cluster_colors = []
        
        # Progress display for clustering operations
        self._progress_display = ProgressDisplay(name="Clustering")
        
        # Orchestrator for common clustering patterns
        # Use list as mutable reference for original_heatmap_data
        self._original_heatmap_ref = [None]
        self._orchestrator = ClusteringOrchestrator(
            progress_display=self._progress_display,
            model=self._model,
            view=self._view,
            preprocessor=self._preprocessor,
            data_getter_fn=self._get_data_for_clustering,
            original_heatmap_ref=self._original_heatmap_ref
        )

    # --- Clustering Application Methods ---
    
    def _apply_kmeans_clustering(self, n_clusters, available_norm, n_init, max_iter, init_method):
        """Apply KMeans clustering and update visualization."""
        try:
            # Initialize progress display
            self._orchestrator.initialize_progress()
            
            # Load and prepare data
            data_cube, matrix_norm, sclust_norm = self._orchestrator.load_and_prepare_data("K-Means", available_norm)
            
            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            self._original_heatmap_data = self._original_heatmap_ref[0]  # Sync from ref
            
            # Run algorithm
            self._progress_display.update(35, "Running K-Means algorithm - initializing...", level='info')
            time.sleep(0.1)
            
            init_val = 'k-means++' if init_method == 'k-means++' else 'random'
            algorithm = KMeansClusteringAlgorithm(
                n_clusters=n_clusters,
                norm=available_norm,  # type: ignore
                n_init=n_init,
                max_iter=max_iter,
                init_method=init_val
            )
            
            self._progress_display.update(50, f"Running K-Means algorithm - clustering (n={n_clusters})...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            # Save result
            constants = self._model.constants
            self._orchestrator.save_clustering_result(
                clustering_type=constants.TAB_KMEANS,
                inputs={
                    constants.INPUT_N_CLUSTERS: n_clusters,
                    constants.INPUT_AVAILABLE_NORMS: available_norm,
                    constants.INPUT_N_INIT: n_init,
                    constants.INPUT_MAX_ITER: max_iter,
                    constants.INPUT_INIT_METHOD: init_val,
                },
                labels=labels,
                centres=centres
            )
            
            # Update visualization
            self._progress_display.update(65, "Visualizing K-Means results - creating heatmap...", level='info')
            time.sleep(0.1)
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "KMeans")
            
            # Finalize
            self._orchestrator.finalize_clustering(n_clusters, "K-Means", self._plots_layout)
            pn.state.notifications.success("K-Means clustering completed successfully!", duration=5000) #type: ignore
            
        except Exception as e:
            self._orchestrator.handle_error(e, "KMeans", self._plots_layout)
            pn.state.notifications.error(f"K-Means clustering failed: {str(e)}", duration=5000) #type: ignore
        finally:
            self._enable_all_clustering_buttons()

    def _apply_agglomerative_clustering(self, n_clusters, linkage, affinity, available_norm):
        """Apply Agglomerative clustering and update visualization."""
        try:
            # Initialize progress display
            self._orchestrator.initialize_progress()
            
            # Load and prepare data
            data_cube, matrix_norm, sclust_norm = self._orchestrator.load_and_prepare_data("Agglomerative", available_norm)
            
            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            self._original_heatmap_data = self._original_heatmap_ref[0]  # Sync from ref
            
            # Run algorithm
            self._progress_display.update(35, "Running Agglomerative algorithm - building hierarchy...", level='info')
            time.sleep(0.1)
            
            connectivity = False
            linkage_val = linkage if linkage in ('ward', 'complete', 'average', 'single') else 'ward'
            algorithm = AgglomerativeClusteringAlgorithm(
                n_clusters=n_clusters,
                norm=available_norm,  # type: ignore
                linkage=linkage_val,  # type: ignore
                affinity=affinity,
                use_connectivity=connectivity
            )
            
            self._progress_display.update(50, f"Running Agglomerative algorithm - clustering (n={n_clusters})...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            # Save result
            constants = self._model.constants
            self._orchestrator.save_clustering_result(
                clustering_type=constants.TAB_AGGLOMERATIVE,
                inputs={
                    constants.INPUT_AVAILABLE_NORMS: available_norm,
                    constants.INPUT_N_CLUSTERS: n_clusters,
                    constants.INPUT_LINKAGE: linkage_val,
                    constants.INPUT_AFFINITY: affinity,
                },
                labels=labels,
                centres=centres
            )
            
            # Update visualization
            self._progress_display.update(65, "Visualizing Agglomerative results - creating heatmap...", level='info')
            time.sleep(0.1)
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "Agglomerative")
            
            # Finalize
            self._orchestrator.finalize_clustering(n_clusters, "Agglomerative", self._plots_layout)
            pn.state.notifications.success("Agglomerative clustering completed successfully!", duration=5000) #type: ignore
            
        except Exception as e:
            self._orchestrator.handle_error(e, "Agglomerative", self._plots_layout)
            pn.state.notifications.error(f"Agglomerative clustering failed: {str(e)}", duration=5000) #type: ignore
        finally:
            self._enable_all_clustering_buttons()

    def _apply_spectral_clustering(self, n_clusters, available_norm, n_init, assign_labels, affinity, n_neighbors, gamma):
        """Apply Spectral clustering and update visualization."""
        try:
            # Initialize progress display
            self._orchestrator.initialize_progress()
            
            # Load and prepare data
            data_cube, matrix_norm, sclust_norm = self._orchestrator.load_and_prepare_data("Spectral", available_norm)
            
            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            self._original_heatmap_data = self._original_heatmap_ref[0]  # Sync from ref
            
            # Run algorithm
            self._progress_display.update(35, "Running Spectral algorithm - computing affinity...", level='info')
            time.sleep(0.1)
            
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
            
            self._progress_display.update(50, "Running Spectral algorithm...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            # Save result
            constants = self._model.constants
            self._orchestrator.save_clustering_result(
                clustering_type=constants.TAB_SPECTRAL,
                inputs={
                    constants.INPUT_AVAILABLE_NORMS: available_norm,
                    constants.INPUT_N_CLUSTERS: n_clusters,
                    constants.INPUT_N_INIT: n_init,
                    constants.INPUT_LABELS_ASSIGN_METHOD: assign_val,
                    constants.INPUT_SPECTRAL_AFFINITY: affinity,
                    constants.INPUT_SPECTRAL_N_NEIGHBORS: n_neighbors,
                    constants.INPUT_SPECTRAL_GAMMA: gamma,
                },
                labels=labels,
                centres=centres
            )
            
            # Update visualization
            self._progress_display.update(65, "Visualizing Spectral results - creating heatmap...", level='info')
            time.sleep(0.1)
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "Spectral")
            
            # Finalize
            self._orchestrator.finalize_clustering(n_clusters, "Spectral", self._plots_layout)
            pn.state.notifications.success("Spectral clustering completed successfully!", duration=5000) #type: ignore
            
        except Exception as e:
            self._orchestrator.handle_error(e, "Spectral", self._plots_layout)
            pn.state.notifications.error(f"Spectral clustering failed: {str(e)}", duration=5000) #type: ignore
        finally:
            self._enable_all_clustering_buttons()

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
    
    def _update_clustering_plots(self, labels, centres, norm, n_clusters, algorithm_name):
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
            self.paneA.object = clustering_fig
            self.paneA.param.trigger('object')
        
        # Update spectrum pane to show cluster centers
        centers_fig = self._visualizer.plot_centers(centres, self._energy)
        if self.paneB is not None:
            self.paneB.object = centers_fig
            self.paneB.param.trigger('object')
        
        self._clustering_active = True
        self._frozen_pixel = None  # Reset frozen state
        self._hover_disabled = False  # Enable hover by default
    
    def _get_current_pane_height(self):
        """Get current paneB height to preserve it."""
        try:
            if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                obj = self.paneB.object
                if isinstance(obj, go.Figure):

                    
                    return obj.layout.height # type: ignore
                elif isinstance(obj, dict):
                    return obj.get('layout', {}).get('height')
        except Exception:
            pass
        return None
    
    def _disable_all_clustering_buttons(self):
        """Disable all clustering buttons."""
        self._kmeans_run_button.disabled = True
        self._agglomerative_run_button.disabled = True
        self._spectral_run_button.disabled = True

    def _enable_all_clustering_buttons(self):
        """Enable all clustering buttons."""
        self._kmeans_run_button.disabled = False
        self._agglomerative_run_button.disabled = False
        self._spectral_run_button.disabled = False

    def _get_kmeans_params(self, user_click):
        """Get KMeans clustering parameters from widgets or saved state."""
        constants = self._model.constants
        
        if user_click:
            # User clicked Run - read current widget values
            kmeans_input = self._view.right_sidebar.kmeans_input
            if kmeans_input is not None:
                return (
                    int(kmeans_input["n_clusters"].value),
                    str(kmeans_input["available_norms"].value),
                    int(kmeans_input["n_init"].value),
                    int(kmeans_input["max_iter"].value),
                    str(kmeans_input["init_method"].value)
                )
            # Widget not available, use defaults
            return (
                constants.DEFAULT_NUMBER_OF_CLUSTERS,
                constants.DEFAULT_SELECTED_NORM,
                constants.DEFAULT_NUMBER_OF_INIT,
                constants.DEFAULT_MAX_ITER,
                constants.DEFAULT_INIT_METHOD
            )
        else:
            # Page load/restore - use saved values
            last_result = getattr(self._model.app_state, 'last_clustering_result', None)
            saved_inputs = last_result.get("clustering", {}).get("inputs", None) if last_result else None
            
            if saved_inputs:
                return (
                    int(saved_inputs[constants.INPUT_N_CLUSTERS]),
                    str(saved_inputs[constants.INPUT_AVAILABLE_NORMS]),
                    int(saved_inputs[constants.INPUT_N_INIT]),
                    int(saved_inputs[constants.INPUT_MAX_ITER]),
                    str(saved_inputs[constants.INPUT_INIT_METHOD])
                )
            # No saved result, use defaults
            return (
                constants.DEFAULT_NUMBER_OF_CLUSTERS,
                constants.DEFAULT_SELECTED_NORM,
                constants.DEFAULT_NUMBER_OF_INIT,
                constants.DEFAULT_MAX_ITER,
                constants.DEFAULT_INIT_METHOD
            )

    def _get_agglomerative_params(self, user_click):
        """Get Agglomerative clustering parameters from widgets or saved state."""
        constants = self._model.constants
        
        if user_click:
            # User clicked Run - read current widget values
            agglomerative_input = self._view.right_sidebar.agglomerative_input
            if agglomerative_input is not None:
                return (
                    int(agglomerative_input[constants.INPUT_N_CLUSTERS].value),
                    str(agglomerative_input[constants.INPUT_LINKAGE].value),
                    str(agglomerative_input[constants.INPUT_AFFINITY].value),
                    str(agglomerative_input[constants.INPUT_AVAILABLE_NORMS].value)
                )
            # Widget not available, use defaults
            return (5, 'ward', 'euclidean', 'none')
        else:
            # Page load/restore - use saved values
            last_result = getattr(self._model.app_state, 'last_clustering_result', None)
            saved_inputs = last_result.get("clustering", {}).get("inputs", None) if last_result else None
            
            if saved_inputs:
                return (
                    int(saved_inputs[constants.INPUT_N_CLUSTERS]),
                    str(saved_inputs[constants.INPUT_LINKAGE]),
                    str(saved_inputs[constants.INPUT_AFFINITY]),
                    str(saved_inputs[constants.INPUT_AVAILABLE_NORMS])
                )
            # No saved result, use defaults
            return (5, 'ward', 'euclidean', 'none')

    def _get_spectral_params(self, user_click):
        """Get Spectral clustering parameters from widgets or saved state."""
        constants = self._model.constants
        
        if user_click:
            # User clicked Run - read current widget values
            spectral_input = self._view.right_sidebar.spectral_input
            if spectral_input is not None:
                return (
                    int(spectral_input[constants.INPUT_N_CLUSTERS].value),
                    str(spectral_input[constants.INPUT_AVAILABLE_NORMS].value),
                    int(spectral_input[constants.INPUT_N_INIT].value),
                    str(spectral_input[constants.INPUT_LABELS_ASSIGN_METHOD].value),
                    str(spectral_input[constants.INPUT_SPECTRAL_AFFINITY].value),
                    int(spectral_input[constants.INPUT_SPECTRAL_N_NEIGHBORS].value),
                    float(spectral_input[constants.INPUT_SPECTRAL_GAMMA].value)
                )
            # Widget not available, use defaults
            return (5, 'none', 10, 'kmeans', 'rbf', 10, 1.0)
        else:
            # Page load/restore - use saved values
            last_result = getattr(self._model.app_state, 'last_clustering_result', None)
            saved_inputs = last_result.get("clustering", {}).get("inputs", None) if last_result else None
            
            if saved_inputs:
                return (
                    int(saved_inputs[constants.INPUT_N_CLUSTERS]),
                    str(saved_inputs[constants.INPUT_AVAILABLE_NORMS]),
                    int(saved_inputs[constants.INPUT_N_INIT]),
                    str(saved_inputs[constants.INPUT_LABELS_ASSIGN_METHOD]),
                    str(saved_inputs[constants.INPUT_SPECTRAL_AFFINITY]),
                    int(saved_inputs[constants.INPUT_SPECTRAL_N_NEIGHBORS]),
                    float(saved_inputs[constants.INPUT_SPECTRAL_GAMMA])
                )
            # No saved result, use defaults
            return (5, 'none', 10, 'kmeans', 'rbf', 10, 1.0)

    # --- Event Handlers ---
    
    def run_kmeans_clustering(self, user_click=False):
        """Handle KMeans clustering button click."""
        self._disable_all_clustering_buttons()

        # Unlock Panel I/O for background processing
        pn.io.unlocked()
        
        pn.state.notifications.info("K-Means clustering started...", duration=3000) #type: ignore
        
        # Define a wrapper that reads params at execution time (ensures sync)
        def run_with_params():
            # Small delay to ensure Panel's parameter system has propagated changes
            if user_click:
                time.sleep(0.1)
            params = self._get_kmeans_params(user_click)
            self._apply_kmeans_clustering(*params)
        
        # Run in background thread
        thread = threading.Thread(
            target=run_with_params,
            daemon=True
        )
        thread.start()

    def run_agglomerative_clustering(self, user_click=False):
        """Handle Agglomerative clustering button click."""

        self._disable_all_clustering_buttons()
        pn.io.unlocked()
        
        pn.state.notifications.info("Agglomerative clustering started...", duration=3000) #type: ignore
        
        # Define a wrapper that reads params at execution time (ensures sync)
        def run_with_params():
            # Small delay to ensure Panel's parameter system has propagated changes
            if user_click:
                time.sleep(0.1)
            params = self._get_agglomerative_params(user_click)
            self._apply_agglomerative_clustering(*params)
        
        # Run in background thread
        thread = threading.Thread(
            target=run_with_params,
            daemon=True
        )
        thread.start()

    def run_spectral_clustering(self, user_click=False):
        """Handle Spectral clustering button click."""
                
        self._disable_all_clustering_buttons()
        pn.io.unlocked()
        
        pn.state.notifications.info("Spectral clustering started...", duration=3000) #type: ignore
        
        # Define a wrapper that reads params at execution time (ensures sync)
        def run_with_params():
            # Small delay to ensure Panel's parameter system has propagated changes
            if user_click:
                time.sleep(0.1)
            params = self._get_spectral_params(user_click)
            self._apply_spectral_clustering(*params)
        
        # Run in background thread
        thread = threading.Thread(
            target=run_with_params,
            daemon=True
        )
        thread.start()

    # --- Public Layout Builders ---
    
    @override
    def create_plots(self):
        """Create the splitjs two-column layout."""
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both',
            margin=0
        )
        
        right_column = pn.Column(
            self.paneB,
            sizing_mode='stretch_both',
            margin=0
        )
        
        splitjs = SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
        
        # Store the plots layout so we can restore it after clustering
        self._plots_layout = splitjs

        container = pn.Column( 
            splitjs,
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
    def _on_paneA_hover(self, event):
        """
        Handle hover on heatmap to show single-pixel spectrum.
        
        Shows:
        1. Original pixel spectrum (if no norm active)
        2. Normalized pixel spectrum if available_norm != 'none'
        3. Corresponding cluster center if clustering is active
        
        Note: If a pixel is frozen (via single click) or hover is disabled 
        (after double-click to show all clusters), hover is ignored.
        """
        if event.new is None:
            return
        
        # Store the hover point for later use
        if 'points' in event.new and len(event.new['points']) > 0:
            self._last_hover_point = event.new['points'][0]
        
        # If pixel is frozen or hover is disabled, don't override
        if self._frozen_pixel is not None or self._hover_disabled:
            return
        
        if not self._clustering_active:
            # Before clustering - use parent implementation
            super()._on_paneA_hover(event)
            return
        
        # After clustering - process hover
        try:
            # Extract pixel coordinates from hover event
            if 'points' in event.new and len(event.new['points']) > 0:
                point = event.new['points'][0]
                i, j = int(point['y']), int(point['x'])
                
                # Plot the spectrum for the hovered pixel
                fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
                if fig is not None and self.paneB is not None:
                    self.paneB.object = fig
        except Exception as e:
            print(f"Error handling hover: {e}")
            traceback.print_exc()
    
    @override
    def _on_paneA_click(self, event):
        """
        Handle single/double clicks on the heatmap.
        
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
                self._frozen_pixel = None  # Always unfreeze on double-click
                
                if self._hover_disabled:
                    # Re-enable hover mode
                    self._hover_disabled = False
                    
                    # Trigger hover for current mouse position if available
                    if self._last_hover_point is not None and self._clustering_active:
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
                # SINGLE CLICK: Freeze pixel
                self._last_click_time = current_time
                
                if self._clustering_active:
                    # Extract coordinates from click event
                    point = event.new['points'][0]
                    i, j = int(point['y']), int(point['x'])
                    self._frozen_pixel = (i, j)  # Freeze this pixel
                    
                    # Plot the frozen pixel spectrum
                    fig = self._plot_pixel_spectrum(i, j, title_prefix="Click (Frozen)")
                    if fig is not None and self.paneB is not None:
                        self.paneB.object = fig
                else:
                    # Call parent implementation for non-clustering mode
                    super()._on_paneA_click(event)
                
        except Exception as e:
            print(f"Error handling click: {e}")
            traceback.print_exc()
