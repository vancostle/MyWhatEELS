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
from whateels.components.plots import SpectrumImagePlot as SharedSpectrumImagePlot
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


class SpectrumImagePlot(SharedSpectrumImagePlot):
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
    
    def _apply_kmeans_clustering(self):
        """Apply KMeans clustering and update visualization."""

        CLUSTERING_TYPE = "K-Means"
        
        kmeans_input = self._view.right_sidebar.kmeans_input
        # Get parameters or use defaults
        n_clusters = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        available_norm = self._model.constants.DEFAULT_SELECTED_NORM
        n_init = self._model.constants.DEFAULT_NUMBER_OF_INIT
        max_iter = self._model.constants.DEFAULT_MAX_ITER
        init_method = self._model.constants.DEFAULT_INIT_METHOD

        try:
            # Reset and prepare progress display
            self._progress_display.reset()
            self._progress_display.visible = True
            
            # Replace main content with progress display
            self._show_clustering_progress()

            if kmeans_input is not None:
                # Read current values from widgets
                n_clusters = int(kmeans_input["n_clusters"].value)
                available_norm = str(kmeans_input["available_norms"].value)
                n_init = int(kmeans_input["n_init"].value)
                max_iter = int(kmeans_input["max_iter"].value)
                init_method = str(kmeans_input["init_method"].value)

            # Get data (possibly background-subtracted)
            self._progress_display.update(5, "Loading K-Means data...", level='info')
            data_cube = self._get_data_for_clustering()
            time.sleep(0.1)
            
            # Store original heatmap if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Update progress: preparing data - step 1
            self._progress_display.update(15, "Preparing K-Means data - normalizing...", level='info')
            time.sleep(0.1)
            
            # Prepare data using OOP preprocessor
            matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
            
            # Update progress: preparing data - step 2
            self._progress_display.update(25, "Preparing K-Means data - reshaping...", level='info')
            time.sleep(0.1)
            
            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            
            # Update progress: running algorithm - step 1
            self._progress_display.update(35, "Running K-Means algorithm - initializing...", level='info')
            time.sleep(0.1)
            
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
            self._progress_display.update(50, f"Running K-Means algorithm - clustering (n={n_clusters})...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            self._model.last_clustering_result = {
                "clustering": {
                    "file": self._model.get_uploaded_filename(),
                    "spectrum_image": self._model.current_image_name,
                    "type": CLUSTERING_TYPE,
                    "inputs": {
                        "n_clusters": n_clusters,
                        "norm": available_norm,
                        "n_init": n_init,
                        "max_iter": max_iter,
                        "init_method": init_val,
                    },
                    "outputs": {
                        "labels": labels,
                        "centres": centres,
                    }
                }
            }
            
            # Update progress: visualizing results
            self._progress_display.update(65, "Visualizing K-Means results - creating heatmap...", level='info')
            time.sleep(0.1)
            
            # Store results and update visualization
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "KMeans")
            
            # Update progress: finishing up
            self._progress_display.update(85, "Finalizing K-Means clustering...", level='info')
            time.sleep(0.1)
            
            # Mark as complete and restore plots
            self._progress_display.completion(f"K-Means clustering complete! (n={n_clusters})")
            
            # Small delay to show completion message, then restore plots
            time.sleep(0.2)
            self._restore_plots_layout()
            
        except Exception as e:
            print(f"Error applying KMeans clustering: {e}")
            traceback.print_exc()
            self._progress_display.error(f"Clustering failed: {str(e)}")
            
            # Restore plots on error too
            time.sleep(2)
            self._restore_plots_layout()
        finally:
            # Re-enable all clustering buttons after clustering completes
            self._enable_all_clustering_buttons()

    def _apply_agglomerative_clustering(self):
        """Apply Agglomerative clustering and update visualization."""
        
        CLUSTERING_TYPE = "Agglomerative"

        try:
            # Reset and prepare progress display
            self._progress_display.reset()
            self._progress_display.visible = True
            
            # Replace main content with progress display
            self._show_clustering_progress()
            
            agglomerative_input = self._view.right_sidebar.agglomerative_input
            
            # Default values
            n_clusters = 5
            linkage = 'ward'
            affinity = 'euclidean'
            available_norm = 'none'
            connectivity = False

            if agglomerative_input is not None:
                # Read current values from widgets
                n_clusters = int(agglomerative_input["n_clusters"].value)
                linkage = str(agglomerative_input["linkage"].value)
                affinity = str(agglomerative_input["affinity"].value)
                available_norm = str(agglomerative_input["available_norms"].value)

            # Get data (possibly background-subtracted)
            self._progress_display.update(5, f"Loading Agglomerative data...", level='info')
            data_cube = self._get_data_for_clustering()
            time.sleep(0.1)
            
            # Store original heatmap if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Update progress: preparing data - step 1
            self._progress_display.update(15, "Preparing Agglomerative data - normalizing...", level='info')
            time.sleep(0.1)
            
            # Prepare data using OOP preprocessor
            matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
            
            # Update progress: preparing data - step 2
            self._progress_display.update(25, "Preparing Agglomerative data - reshaping...", level='info')
            time.sleep(0.1)

            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            
            # Update progress: running algorithm - step 1
            self._progress_display.update(35, "Running Agglomerative algorithm - building hierarchy...", level='info')
            time.sleep(0.1)

            # Apply clustering algorithm using OOP class
            linkage_val = linkage if linkage in ('ward', 'complete', 'average', 'single') else 'ward'
            algorithm = AgglomerativeClusteringAlgorithm(
                n_clusters=n_clusters,
                norm=available_norm,  # type: ignore
                linkage=linkage_val,  # type: ignore
                affinity=affinity,
                use_connectivity=connectivity
            )
            
            # Update progress: running algorithm - step 2
            self._progress_display.update(50, f"Running Agglomerative algorithm - clustering (n={n_clusters})...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            self._model.last_clustering_result = {
                "clustering": {
                    "file": self._model.get_uploaded_filename(),
                    "spectrum_image": self._model.current_image_name,
                    "type": CLUSTERING_TYPE,
                    "inputs": {
                        "norm": available_norm,
                        "n_clusters": n_clusters,
                        "linkage": linkage_val,
                        "affinity": affinity,
                    },
                    "outputs": {
                        "labels": labels,
                        "centres": centres,
                    }
                }
            }
            
            # Update progress: visualizing results
            self._progress_display.update(65, "Visualizing Agglomerative results - creating heatmap...", level='info')
            time.sleep(0.1)

            # Store results and update visualization
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "Agglomerative")
            
            # Update progress: finishing up
            self._progress_display.update(85, f"Finalizing Agglomerative clustering (n={n_clusters})...", level='info')
            time.sleep(0.1)

            # Mark as complete and restore plots
            self._progress_display.completion(f"Agglomerative clustering complete! (n={n_clusters})")
            
            # Small delay to show completion message, then restore plots
            time.sleep(0.2)
            self._restore_plots_layout()
            
        except Exception as e:
            print(f"Error applying Agglomerative clustering: {e}")
            traceback.print_exc()
            self._progress_display.error(f"Clustering failed: {str(e)}")
            
            # Restore plots on error too
            time.sleep(2)
            self._restore_plots_layout()
        finally:
            # Re-enable all clustering buttons after clustering completes
            self._enable_all_clustering_buttons()

    def _apply_spectral_clustering(self):
        """Apply Spectral clustering and update visualization."""
                
        CLUSTERING_TYPE = "Spectral"

        try:
            # Reset and prepare progress display
            self._progress_display.reset()
            self._progress_display.visible = True
            
            # Replace main content with progress display
            self._show_clustering_progress()
            
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
                # Read current values from widgets
                n_clusters = int(spectral_input["n_clusters"].value)
                available_norm = str(spectral_input["available_norms"].value)
                n_init = int(spectral_input["n_init"].value)
                assign_labels = str(spectral_input["labels_assign_method"].value)
                affinity = str(spectral_input["spectral_affinity_metrics"].value)
                n_neighbors = int(spectral_input["n_neighbors"].value)
                gamma = float(spectral_input["gamma"].value)
            
            # Get data (possibly background-subtracted)
            self._progress_display.update(5, f"Loading Spectral data...", level='info')
            data_cube = self._get_data_for_clustering()
            time.sleep(0.1)

            # Store original heatmap if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Update progress: preparing data - step 1
            self._progress_display.update(15, "Preparing Spectral data - normalizing...", level='info')
            time.sleep(0.1)

            # Prepare data using OOP preprocessor
            matrix_norm, sclust_norm = self._preprocessor.prepare_matrix(data_cube, available_norm)  # type: ignore
            
            # Update progress: preparing data - step 2
            self._progress_display.update(25, "Preparing Spectral data - reshaping...", level='info')
            time.sleep(0.1)

            # Store for later use in visualization
            self._last_clustering_matrix = matrix_norm
            self._last_clustering_input = sclust_norm
            
            # Update progress: running algorithm - step 1
            self._progress_display.update(35, "Running Spectral algorithm - computing affinity...", level='info')
            time.sleep(0.1)

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
            self._progress_display.update(50, "Running Spectral algorithm...", level='info')
            time.sleep(0.1)
            
            labels, centres = algorithm.fit(data_cube, matrix_norm, sclust_norm)
            
            self._model.last_clustering_result = {
                "clustering": {
                    "file": self._model.get_uploaded_filename(),
                    "spectrum_image": self._model.current_image_name,
                    "type": CLUSTERING_TYPE,
                    "inputs": {
                        "norm": available_norm,
                        "n_clusters": n_clusters,
                        "n_init": n_init,
                        "assign_labels": assign_val,
                        "spectral_affinity": affinity,
                        "n_neighbors": n_neighbors,
                        "gamma": gamma,
                    },
                    "outputs": {
                        "labels": labels,
                        "centres": centres,
                    }
                }
            }
            
            # Update progress: visualizing results
            self._progress_display.update(65, "Visualizing Spectral results - creating heatmap...", level='info')
            time.sleep(0.1)

            # Store results and update visualization
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, "Spectral")
            
            # Update progress: finishing up
            self._progress_display.update(85, "Finalizing Spectral clustering...", level='info')
            time.sleep(0.1)

            # Mark as complete and restore plots
            self._progress_display.completion(f"Spectral clustering complete! (n={n_clusters})")
            
            # Small delay to show completion message, then restore plots
            time.sleep(0.2)
            self._restore_plots_layout()
            
        except Exception as e:
            print(f"Error applying Spectral clustering: {e}")
            traceback.print_exc()
            self._progress_display.error(f"Spectral clustering failed: {str(e)}")
            
            # Restore plots on error too
            time.sleep(2)
            self._restore_plots_layout()
        finally:
            # Re-enable all clustering buttons after clustering completes
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
            tab = pn.Tabs((
                f"Running Clustering on {self._model.current_image_name}...", 
                 self._progress_display
            ))
            
            if self._view and hasattr(self._view, 'main'):
                self._view.main.update(tab)
        except Exception as e:
            print(f"Error showing clustering progress: {e}")
            traceback.print_exc()
    

    def _restore_plots_layout(self):
        """Restore the plots layout after clustering completes."""
        try:
            if self._view and hasattr(self._view, 'main') and self._plots_layout is not None:
                last_clustering_type = self._model.last_clustering_result.get('clustering', {}).get('type', 'Clustering')
                tab = pn.Tabs((f"Applied {last_clustering_type} Clustering on {self._model.current_image_name}", self._plots_layout))
                self._view.main.update(tab)
        except Exception as e:
            print(f"Error restoring plots layout: {e}")

    def _disable_all_clustering_buttons(self):
        """Disable all clustering buttons."""
        if self._kmeans_run_button is not None:
            self._kmeans_run_button.disabled = True
        if self._agglomerative_run_button is not None:
            self._agglomerative_run_button.disabled = True
        if self._spectral_run_button is not None:
            self._spectral_run_button.disabled = True

    def _enable_all_clustering_buttons(self):
        """Enable all clustering buttons."""
        if self._kmeans_run_button is not None:
            self._kmeans_run_button.disabled = False
        if self._agglomerative_run_button is not None:
            self._agglomerative_run_button.disabled = False
        if self._spectral_run_button is not None:
            self._spectral_run_button.disabled = False

    # --- Event Handlers ---
    
    def _run_kmeans_clustering(self, event):
        """Handle KMeans clustering button click."""
        # Disable all clustering buttons immediately on click
        self._disable_all_clustering_buttons()
        
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(
            target=self._apply_kmeans_clustering, 
            daemon=True
        )
        thread.start()

    def _run_agglomerative_clustering(self, event):
        """Handle Agglomerative clustering button click."""
        # Disable all clustering buttons immediately on click
        self._disable_all_clustering_buttons()
        
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(
            target=self._apply_agglomerative_clustering, 
            daemon=True
        )
        thread.start()

    def _run_spectral_clustering(self, event):
        """Handle Spectral clustering button click."""
        # Disable all clustering buttons immediately on click
        self._disable_all_clustering_buttons()
                
        # Run in background thread to prevent UI blocking
        thread = threading.Thread(
            target=self._apply_spectral_clustering, 
            daemon=True
        )
        thread.start()

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
    def _on_paneA_hover(self, event):
        """Override hover to disable it during clustering."""
        if self._clustering_active:
            # Disable hover during clustering
            return
        # Call parent hover implementation for non-clustering mode
        super()._on_paneA_hover(event)
    
    @override
    def _on_paneA_click(self, event):
        """
        Handle single/double clicks on the heatmap with clustering features.
        
        Single click: Shows the spectrum for the clicked pixel.
        Double click: Resets to show all cluster centers.
        """
        if event.new is None:
            return
        
        try:
            current_time = time.time() * 1000  # Convert to milliseconds
            time_since_last_click = current_time - self._last_click_time
            
            # Check if this is a double-click
            if time_since_last_click < self._DOUBLE_CLICK_MS:
                # DOUBLE CLICK: Show all cluster centers
                if self._clustering_active and self._clustering_results is not None and self._visualizer is not None:
                    _, centres = self._clustering_results
                    
                    # Create figure with all cluster centers using OOP visualizer
                    fig = self._visualizer.plot_centers(
                        centres,
                        self._energy,
                        title="All Cluster Centers"
                    )
                    
                    if self.paneB is not None:
                        self.paneB.object = fig
                
                # Reset timer to prevent treating next click as double-click
                self._last_click_time = current_time - 1000
                return
                
            else:
                # SINGLE CLICK: Show spectrum for clicked pixel
                self._last_click_time = current_time
                
                if self._clustering_active:
                    # Extract coordinates from click event
                    point = event.new['points'][0]
                    i, j = int(point['y']), int(point['x'])
                    fig = self._plot_pixel_spectrum(i, j, title_prefix="Click")
                    if fig is not None and self.paneB is not None:
                        self.paneB.object = fig
                else:
                    # Call parent implementation for non-clustering mode
                    super()._on_paneA_click(event)
                
        except Exception as e:
            print(f"Error handling click: {e}")
            traceback.print_exc()
