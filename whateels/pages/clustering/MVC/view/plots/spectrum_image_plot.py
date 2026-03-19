"""
Clustering-specific spectrum image visualizer.

Extends the shared SpectrumImageVisualizer component with clustering capabilities:
- KMeans clustering
- Agglomerative clustering
- Spectral clustering
- Cluster center visualization
- Normalized spectrum display

All plotting is performed using HoloViews. This visualizer orchestrates UI interactions and delegates to OOP utility classes for algorithms, data preparation, and plotting.

Note: All lasso/box/region selection logic has been removed. No region selection or ROI summing is available in this clustering visualizer; only pixel hover/click and cluster center overlays are supported.
"""

import panel as pn
import numpy as np
import holoviews as hv
import time
import threading
import traceback

from whateels.helpers import SpectrumExtractor
from whateels.base.plots import BaseSpectrumImagePlot
from whateels.components import ProgressDisplay
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

    All plotting is performed using HoloViews. Lasso/box/region selection and ROI summing are not available in this visualizer; only pixel hover/click and cluster center overlays are supported.

    This class focuses on orchestrating UI interactions and delegates heavy lifting to helper modules.
    """

    def __init__(self, model: "ClusteringModel", view: "ClusteringView", dataset: "Dataset"):
        # Set notification position
        pn.state.notifications.position = 'bottom-left'  # type: ignore
        
        # Get axis name from model constants
        eloss_name = getattr(model.constants, 'ELOSS', 'Eloss') if hasattr(model, 'constants') else 'Eloss'

        # Persistent selection overlay (red dots shown after lasso) — must be set
        # before super().__init__ because that calls _setup_plots() internally.
        self._paneA_base_overlay = None
        self._selection_overlay = hv.Points([], kdims=['x', 'y'])

        # Call parent constructor to setup base visualization
        super().__init__(dataset, eloss_name)

        # Store references for clustering features
        self._model: "ClusteringModel" = model
        self._view: "ClusteringView" = view
        
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
        self._kmeans_run_button: pn.widgets.Button = self._view.right_sidebar.kmeans_run_button
        self._kmeans_run_button_watcher = self._kmeans_run_button.on_click(lambda _ : self.run_kmeans_clustering(user_click=True))
        self._agglomerative_run_button: pn.widgets.Button = self._view.right_sidebar.agglomerative_run_button
        self._agglomerative_run_button_watcher = self._agglomerative_run_button.on_click(lambda _ : self.run_agglomerative_clustering(user_click=True))
        self._spectral_run_button: pn.widgets.Button = self._view.right_sidebar.spectral_run_button
        self._spectral_run_button_watcher = self._spectral_run_button.on_click(lambda _ : self.run_spectral_clustering(user_click=True))
        
        # OOP utility instances
        self._preprocessor: DataPreprocessor = DataPreprocessor()
        self._visualizer: ClusterVisualizer | None = None  # Created after clustering
        # Cluster colors (set after clustering)
        self.cluster_colors = []
        # Progress display for clustering operations
        self._progress_display: ProgressDisplay = ProgressDisplay(name="Clustering")
        # Orchestrator for common clustering patterns
        # Use list as mutable reference for original_heatmap_data
        self._original_heatmap_ref = [None]
        self._orchestrator: ClusteringOrchestrator = ClusteringOrchestrator(
            progress_display=self._progress_display,
            model=self._model,
            view=self._view,
            preprocessor=self._preprocessor,
            data_getter_fn=self._get_data_for_clustering,
            original_heatmap_ref=self._original_heatmap_ref
        )

        # Remove region selection state (lasso/box selection)

    # --- paneA setup override: store base overlay for dot recomposition ---

    @override
    def _setup_plots(self):
        super()._setup_plots()
        self._paneA_base_overlay = self.paneA.object
        self._update_selection_overlay(self._region_pairs)

    def _update_selection_overlay(self, pairs):
        """Rebuild the red-dot selection overlay and recompose paneA.

        Always reapplies the full Overlay-level opts so paneA never loses its
        sizing behaviour when the overlay is reconstructed.
        """
        if pairs:
            xs = [col for row, col in pairs]
            ys = [row for row, col in pairs]
            self._selection_overlay = hv.Points(
                (xs, ys), kdims=['x', 'y']
            ).opts(color='red', size=5, alpha=0.5)
        else:
            self._selection_overlay = hv.Points([], kdims=['x', 'y'])
        if self._paneA_base_overlay is not None and self.paneA is not None:
            self.paneA.object = (
                self._paneA_base_overlay * self._selection_overlay  # type: ignore
            ).opts(
                hv.opts.Overlay(
                    responsive=True, aspect='equal', shared_axes=False,
                    active_tools=['lasso_select'],
                )
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
        
        # Create clustering visualization using OOP visualizer
        cluster_img = self._visualizer.plot_labels(
            labels,
            title=f"{algorithm_name} Clustering (n={n_clusters})",
        )
        
        # Update heatmap pane — re-overlay with selectors to preserve interaction streams
        if self.paneA is not None and self._selectors is not None:
            self._paneA_base_overlay = cluster_img * self._selectors  # type: ignore
            self._update_selection_overlay([])  # reset any stale red dots
        
        # Update spectrum pane to show cluster centers via base class pipe
        centers_fig = self._visualizer.plot_centers(centres, self._energy)
        self._update_paneB(centers_fig)
        
        self._clustering_active = True
        self._frozen_pixel = None  # Reset frozen state
        self._hover_disabled = False  # Enable hover by default
    
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
    
    # create_plots inherited from base class
    # create_dataset_info inherited from base class
    
    def _plot_pixel_spectrum(self, i, j, title_prefix="Hover"):
        """
        Return an hv.Overlay for a specific pixel with clustering overlays.
        """
        overlays = []
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        if spec is None:
            return hv.Overlay([])

        should_plot_original = True
        if hasattr(self, '_current_norm') and isinstance(self._current_norm, str) and self._current_norm.lower() != 'none':
            should_plot_original = False

        if should_plot_original:
            overlays.append(
                hv.Curve(
                    (self._energy, spec),
                    kdims=['x'],
                    vdims=['y']
                ).opts(
                    color='black',
                    line_width=1.5,
                    alpha=0.2,
                    title=f"{title_prefix} (i={i}, j={j})",
                    xlabel="Energy Loss (eV)",
                    ylabel="Intensity (AU)"
                )
            )

        if (hasattr(self, '_current_norm') and 
            isinstance(self._current_norm, str) and 
            self._current_norm.lower() != 'none' and
            hasattr(self, '_last_clustering_input') and
            self._last_clustering_input is not None):
            try:
                data_cube = np.asarray(self._electron_count_data.fillna(0.0))
                ny, nx = data_cube.shape[0], data_cube.shape[1]
                linear_idx = i * nx + j
                if linear_idx < len(self._last_clustering_input):
                    normalized_spec = self._last_clustering_input[linear_idx]
                    overlays.append(
                        hv.Curve(
                            (self._energy, normalized_spec),
                            kdims=['x'],
                            vdims=['y']
                        ).opts(
                            color='orange',
                            line_width=2,
                            alpha=0.2,
                            title=f"Normalized ({self._current_norm})",
                            xlabel="Energy Loss (eV)",
                            ylabel="Intensity (AU)"
                        )
                    )
            except Exception as e:
                print(f"Error plotting normalized spectrum: {e}")

        if self._clustering_active and self._clustering_results is not None:
            try:
                labels, centres = self._clustering_results
                cluster_label = labels[i, j]
                cluster_center = centres[cluster_label]
                color = self.cluster_colors[cluster_label % len(self.cluster_colors)] if self.cluster_colors else 'blue'
                overlays.append(
                    hv.Curve(
                        (self._energy, cluster_center),
                        kdims=['x'],
                        vdims=['y']
                    ).opts(
                        color=color,
                        line_width=3,
                        title=f"Cluster {cluster_label} center",
                        xlabel="Energy Loss (eV)",
                        ylabel="Intensity (AU)"
                    )
                )
            except Exception as e:
                print(f"Error plotting cluster center: {e}")

        return hv.Overlay(overlays)
    
    @override
    def _on_paneA_selected(self, index=None):
        """Ignore empty Selection1D events (Bokeh fires index=[] after committing
        a lasso, which would immediately wipe the red dots)."""
        if not index:
            return
        pairs = list(dict.fromkeys(
            (idx // self._nx, idx % self._nx) for idx in index
        ))
        self._region_pairs = pairs
        self._update_selection_overlay(pairs)
        self._show_spectrum(region_pairs=pairs)

    @override
    def _on_paneA_hover(self, x=None, y=None):
        """
        Handle PointerXY hover — show pixel spectrum unless region is selected.
        Adapts clustering overlays if active.
        """
        if x is None or y is None:
            return
        self._last_hover_point = {"x": x, "y": y}
        if self._frozen_pixel is not None or self._hover_disabled:
            return
        if not self._clustering_active:
            super()._on_paneA_hover(x, y)
            return
        i, j = int(y), int(x)
        fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
        self._update_paneB(fig)
    
    @override
    def _on_paneA_click(self, x=None, y=None):
        """
        Handle Tap click — single/double click for clustering overlays.
        Adapts to base class event signature.
        """
        if x is None or y is None:
            return
        try:
            current_time = time.time() * 1000
            time_since_last_click = current_time - self._last_click_time
            if time_since_last_click < self._DOUBLE_CLICK_MS:
                self._frozen_pixel = None
                if self._hover_disabled:
                    self._hover_disabled = False
                    self._region_pairs = []  # Clear lasso selection when unfreeze
                    self._update_selection_overlay([])  # Remove red dots
                    if self._last_hover_point is not None and self._clustering_active:
                        i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                        fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
                        self._update_paneB(fig)
                else:
                    if self._clustering_active and self._clustering_results is not None and self._visualizer is not None:
                        self._hover_disabled = True
                        _, centres = self._clustering_results
                        fig = self._visualizer.plot_centers(
                            centres,
                            self._energy,
                            title="All Cluster Centers (Double Click again to re-enable hover)"
                        )
                        self._update_paneB(fig)
                self._last_click_time = current_time - 1000
                return
            else:
                self._last_click_time = current_time
                if self._clustering_active:
                    self._frozen_pixel = (int(y), int(x))
                    fig = self._plot_pixel_spectrum(int(y), int(x), title_prefix="Click (Frozen)")
                    self._update_paneB(fig)
                else:
                    super()._on_paneA_click(x, y)
        except Exception as e:
            print(f"Error handling click: {e}")
            traceback.print_exc()

    # --- Lifecycle ---

    def cleanup(self):
        """Unwatch button callbacks, release clustering data, and call base cleanup."""
        # Unwatch on_click callbacks so lambdas capturing self are released
        for btn, watcher in [
            (self._kmeans_run_button, self._kmeans_run_button_watcher),
            (self._agglomerative_run_button, self._agglomerative_run_button_watcher),
            (self._spectral_run_button, self._spectral_run_button_watcher),
        ]:
            if btn is not None and watcher is not None:
                try:
                    btn.param.unwatch(watcher)
                except Exception:
                    pass

        # Release large numpy arrays
        self._clustering_results = None
        self._original_heatmap_data = None
        if isinstance(self._original_heatmap_ref, list):
            self._original_heatmap_ref[0] = None
        self._original_heatmap_ref = []
        self._last_clustering_matrix = None
        self._last_clustering_input = None

        # Release OOP helper objects (orchestrator holds a closure over self via data_getter_fn)
        self._orchestrator = None  # type: ignore[assignment]
        self._preprocessor = None  # type: ignore[assignment]
        self._visualizer = None
        self._progress_display = None  # type: ignore[assignment]

        # Release button and watcher refs
        self._kmeans_run_button = None  # type: ignore[assignment]
        self._agglomerative_run_button = None  # type: ignore[assignment]
        self._spectral_run_button = None  # type: ignore[assignment]
        self._kmeans_run_button_watcher = None
        self._agglomerative_run_button_watcher = None
        self._spectral_run_button_watcher = None

        # Release model/view refs
        self._model = None  # type: ignore[assignment]
        self._view = None   # type: ignore[assignment]

        # Base class: clears HoloViews streams, panes, dataset/energy refs
        super().cleanup()