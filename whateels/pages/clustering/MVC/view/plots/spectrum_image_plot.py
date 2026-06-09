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
from holoviews import streams as hv_streams
import time
import threading
import traceback
import logging

_logger = logging.getLogger(__name__)

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

        # Store model/view before super().__init__ so _get_display_data() override
        # can access them when _setup_plots() runs during parent construction.
        self._model: "ClusteringModel" = model
        self._view: "ClusteringView" = view

        # Call parent constructor to setup base visualization
        super().__init__(dataset, eloss_name, ['hover'])

        try:
            if self._hover_pc is not None:
                try:
                    if self._hover_pc.running:
                        self._hover_pc.stop()
                except Exception:
                    pass
            self._HOVER_FPS = 30
            self._hover_pc = pn.state.add_periodic_callback(
                self._flush_hover_queue,
                period=max(10, int(1000 / float(self._HOVER_FPS))),
                start=False,
            )
        except Exception:
            pass
        
        # Store original plots layout to restore after clustering
        self._plots_layout = None

        # Double-click state is now handled by base DoubleTap stream.
        self._frozen_pixel = None  # Store frozen pixel (i, j) from single click
        self._hover_disabled = False  # Disable hover after showing all clusters
        self._last_hover_point = None  # Store last hover position for re-enabling
        self._suppress_click_until_ms = 0  # Ignore Tap events that follow a DoubleTap
        self._paneB_hover_flush_pending = False
        self._pending_paneB_hover_fig = None
        self._last_paneB_send_ts = None
        self._HOVER_PIPE_THROTTLE_MS = 33
        self._CLUSTER_HOVER_DEADZONE_PX = 0.9
        self._cluster_hover_install_sent = False
        self._cluster_hover_live_ready = False
        self._cluster_hover_raw_renderer = None
        self._cluster_hover_centroid_renderer = None
        self._cluster_hover_last_label = None
        self._cluster_hover_processing = False
        self._cluster_hover_latest_point = None
        self._init_kmeans_picker_after_apply = False
        self._init_agglomerative_picker_after_apply = False
        self._init_spectral_picker_after_apply = False
        self._suppress_color_picker_callbacks = False
        self._active_cluster_labels: dict[str, int | None] = {
            self._model.constants.TAB_KMEANS: None,
            self._model.constants.TAB_AGGLOMERATIVE: None,
            self._model.constants.TAB_SPECTRAL: None,
        }

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
        self._kmeans_color_picker_watcher = self._view.right_sidebar.kmeans_color_picker.param.watch(
            lambda event: self._on_color_picker_changed(self._model.constants.TAB_KMEANS, event),
            'value'
        )
        self._agglomerative_run_button: pn.widgets.Button = self._view.right_sidebar.agglomerative_run_button
        self._agglomerative_run_button_watcher = self._agglomerative_run_button.on_click(lambda _ : self.run_agglomerative_clustering(user_click=True))
        self._agglomerative_color_picker_watcher = self._view.right_sidebar.agglomerative_color_picker.param.watch(
            lambda event: self._on_color_picker_changed(self._model.constants.TAB_AGGLOMERATIVE, event),
            'value'
        )
        self._spectral_run_button: pn.widgets.Button = self._view.right_sidebar.spectral_run_button
        self._spectral_run_button_watcher = self._spectral_run_button.on_click(lambda _ : self.run_spectral_clustering(user_click=True))
        self._spectral_color_picker_watcher = self._view.right_sidebar.spectral_color_picker.param.watch(
            lambda event: self._on_color_picker_changed(self._model.constants.TAB_SPECTRAL, event),
            'value'
        )
        
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

        # Wire preprocessing switch so toggling it immediately refreshes paneA/paneB
        switch = self._view.right_sidebar.preprocessed_data_switch
        self._preprocessing_switch_ref = switch
        self._preprocessing_switch_watcher = switch.param.watch(
            lambda e: self._on_preprocessing_switch_changed(), 'value'
        )

        self._cluster_hover_idle_pc = None

        # Remove region selection state (lasso/box selection)

    # --- paneA setup / callbacks: handled by base ---

    @override
    def _get_display_data(self):
        """Return active electron count data (raw or preprocessed based on switch state)."""
        try:
            switch = self._view.right_sidebar.preprocessed_data_switch
            if switch and bool(switch.value):
                preprocessed = self._model.app_state.preprocessed_plot_dataset
                if preprocessed is not None:
                    return preprocessed["ElectronCount"]
        except AttributeError:
            pass
        return self._electron_count_data

    def _on_preprocessing_switch_changed(self):
        """Rebuild paneA heatmap and refresh paneB when the preprocessing switch is toggled."""
        
        # Disable all color pickers when toggling preprocessing switch to prevent inconsistent state
        self._view.right_sidebar.kmeans_color_picker.disabled = True
        self._view.right_sidebar.agglomerative_color_picker.disabled = True
        self._view.right_sidebar.spectral_color_picker.disabled = True
        
        # Update energy axis to match the current display data's Eloss coordinates.
        # This is critical when cut-range preprocessing has changed the axis length.
        display_data = self._get_display_data()
        try:
            self._energy = np.asarray(display_data.coords[self._eloss_name].values)  # type: ignore
        except Exception:
            self._energy = np.asarray(self._e_axis)  # fallback to original

        self._refresh_paneA()
        self._refresh_paneB()

    def _refresh_paneA(self):
        """Rebuild paneA heatmap using the current display data."""
        display_data = self._get_display_data()
        m_image_da = display_data.sum(self._eloss_name)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        ny, nx = m_image.shape
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'],
            vdims=['Intensity'],
        ).opts(
            cmap='Greys_r',
            colorbar=False,
            xaxis=None,
            yaxis=None,
            invert_yaxis=True,
            aspect='equal',
            responsive=True,
            shared_axes=False,
        )
        self._paneA_base_overlay = img * self._selectors  # type: ignore
        self._update_selection_overlay([])

    def _refresh_paneB(self):
        """Refresh paneB using the last hover point or default pixel (0, 0)."""
        self._current_x_range = None
        self._current_y_range = None
        point = self._last_hover_point if self._last_hover_point is not None else {"x": 0, "y": 0}
        if self._try_fast_hover_update(point):
            return
        self._update_paneB(self._figB_hover(point))

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
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, constants.TAB_KMEANS)
            
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
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, constants.TAB_AGGLOMERATIVE)
            
            # Finalize
            self._orchestrator.finalize_clustering(n_clusters, constants.TAB_AGGLOMERATIVE, self._plots_layout)
            pn.state.notifications.success("Agglomerative clustering completed successfully!", duration=5000) #type: ignore
            
        except Exception as e:
            self._orchestrator.handle_error(e, constants.TAB_AGGLOMERATIVE, self._plots_layout)
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
            constants = self._model.constants
            self._update_clustering_plots(labels, centres, available_norm, n_clusters, constants.TAB_SPECTRAL)
            
            # Finalize
            constants = self._model.constants
            self._orchestrator.finalize_clustering(n_clusters, constants.TAB_SPECTRAL, self._plots_layout)
            pn.state.notifications.success("Spectral clustering completed successfully!", duration=5000) #type: ignore
            
        except Exception as e:
            constants = self._model.constants
            self._orchestrator.handle_error(e, constants.TAB_SPECTRAL, self._plots_layout)
            pn.state.notifications.error(f"Spectral clustering failed: {str(e)}", duration=5000) #type: ignore
        finally:
            self._enable_all_clustering_buttons()

    # --- Helper Methods ---
    
    def _get_data_for_clustering(self):
        """Get data cube for clustering, possibly with background subtraction."""
        # Check if background-subtraction is enabled
        try:
            switch = self._view.right_sidebar.preprocessed_data_switch
            switch_value = bool(switch.value) if switch and switch.value is not None else False
            use_multifit = DataPreprocessor.should_use_multifit_data(self._model, switch_value)
        except Exception:
            use_multifit = False
        
        if use_multifit:
            # Get background-subtracted data from multifit
            data_cube = DataPreprocessor.get_multifit_data(self._model)
            if data_cube is None:
                print("Warning: Could not retrieve multifit data, using original data")
                data_cube = np.asarray(self._electron_count_data.fillna(0.0)) # type: ignore
        else:
            # Get the 3D data cube (x, y, energy) from original dataset
            data_cube = np.asarray(self._electron_count_data.fillna(0.0)) # type: ignore
        
        return data_cube

    def _get_picker_for_algorithm(self, algorithm_name):
        """Return the color picker widget associated with an algorithm tab key."""
        constants = self._model.constants
        if algorithm_name == constants.TAB_KMEANS:
            return self._view.right_sidebar.kmeans_color_picker
        if algorithm_name == constants.TAB_AGGLOMERATIVE:
            return self._view.right_sidebar.agglomerative_color_picker
        if algorithm_name == constants.TAB_SPECTRAL:
            return self._view.right_sidebar.spectral_color_picker
        return None

    def _should_init_picker_after_apply(self, algorithm_name: str) -> bool:
        """Check whether the given algorithm picker should be initialized after apply."""
        constants = self._model.constants
        if algorithm_name == constants.TAB_KMEANS:
            return self._init_kmeans_picker_after_apply
        if algorithm_name == constants.TAB_AGGLOMERATIVE:
            return self._init_agglomerative_picker_after_apply
        if algorithm_name == constants.TAB_SPECTRAL:
            return self._init_spectral_picker_after_apply
        return False

    def _set_init_picker_after_apply_flag(self, algorithm_name: str, value: bool):
        """Set algorithm-specific post-apply picker initialization flag."""
        constants = self._model.constants
        if algorithm_name == constants.TAB_KMEANS:
            self._init_kmeans_picker_after_apply = value
        elif algorithm_name == constants.TAB_AGGLOMERATIVE:
            self._init_agglomerative_picker_after_apply = value
        elif algorithm_name == constants.TAB_SPECTRAL:
            self._init_spectral_picker_after_apply = value

    def _set_picker_from_cluster(self, algorithm_name, cluster_label: int, i: int, j: int, color: str):
        """Update active label state and sync the corresponding algorithm color picker."""
        if algorithm_name in self._active_cluster_labels:
            self._active_cluster_labels[algorithm_name] = cluster_label

        picker = self._get_picker_for_algorithm(algorithm_name)
        if picker is None:
            return

        self._suppress_color_picker_callbacks = True
        try:
            picker.name = f"Cluster {cluster_label}"
            picker.value = color
            picker.disabled = False
        finally:
            self._suppress_color_picker_callbacks = False

    def _init_picker_from_default_pixel(self, algorithm_name: str, labels):
        """Initialize picker state from the default pixel (0, 0) after clustering."""
        if not self._should_init_picker_after_apply(algorithm_name):
            return

        try:
            default_i, default_j = 0, 0
            cluster_label = int(labels[default_i, default_j])
            color = self.cluster_colors[cluster_label % len(self.cluster_colors)] if self.cluster_colors else 'blue'
            self._set_picker_from_cluster(algorithm_name, cluster_label, default_i, default_j, color)
            self._last_hover_point = {"x": default_j, "y": default_i}
            self._update_paneB(self._plot_pixel_spectrum(default_i, default_j, title_prefix="Hover"))
        except Exception:
            pass
        finally:
            self._set_init_picker_after_apply_flag(algorithm_name, False)
    
    def _update_clustering_plots(self, labels, centres, norm, n_clusters, algorithm_name):
        """Update visualization after clustering."""
        self._clustering_results = (labels, centres)
        self._current_norm = norm
        
        # Create visualizer and build colors for clusters.
        # Discard any saved palette if the cluster count changed between runs
        # so that a fresh palette is generated for the new number of clusters.
        if len(self.cluster_colors) != n_clusters:
            self.cluster_colors = []
        self._visualizer = ClusterVisualizer(n_clusters, cluster_colors=self.cluster_colors or None)
        self.cluster_colors = self._visualizer.cluster_colors
        
        # Create clustering visualization using OOP visualizer
        cluster_img = self._visualizer.plot_labels(
            labels,
            title=f"{algorithm_name} Clustering (n={n_clusters})",
        )
        
        # Update heatmap pane — re-overlay with selectors to preserve interaction streams
        if self.paneA is not None and self._selectors is not None:
            try:
                setattr(self.paneA, '_whatEELS_hover_gate_attached', False)
            except Exception:
                pass
            self._paneA_base_overlay = cluster_img * self._selectors  # type: ignore
            self._update_selection_overlay([])  # reset any stale red dots
            try:
                if getattr(self, '_hover_stream', None) is not None:
                    try:
                        self._hover_stream.remove_subscriber(self._on_paneA_hover)
                    except Exception:
                        pass
                self._hover_source = cluster_img
                self._hover_stream = hv_streams.PointerXY(source=cluster_img)
                self._hover_stream.add_subscriber(self._on_paneA_hover)
            except Exception:
                _logger.exception("Failed to reattach clustering hover stream")

        # Update spectrum pane to show cluster centers via base class pipe
        centers_fig = self._visualizer.plot_centers(centres, self._energy)
        self._update_paneB(centers_fig)
        self._cluster_hover_install_sent = False
        self._cluster_hover_live_ready = False
        self._cluster_hover_raw_renderer = None
        self._cluster_hover_centroid_renderer = None
        self._cluster_hover_last_label = None
        
        self._clustering_active = True
        self._frozen_pixel = None  # Reset frozen state
        self._hover_disabled = False  # Enable hover by default

        # Initialize algorithm-specific picker state from the default pixel (0, 0)
        # before any explicit click interaction.
        self._init_picker_from_default_pixel(algorithm_name, labels)

    def _refresh_cluster_visuals(self):
        """Rebuild the clustering heatmap and spectrum panes using the current color palette."""
        if not self._clustering_active or self._clustering_results is None:
            return

        labels, centres = self._clustering_results
        n_clusters = len(self.cluster_colors) if self.cluster_colors else max(int(np.nanmax(labels)) + 1, 1)
        self._visualizer = ClusterVisualizer(n_clusters, cluster_colors=self.cluster_colors or None)

        cluster_img = self._visualizer.plot_labels(
            labels,
            title=f"{self._model.last_clustering_result.get('clustering', {}).get('type', 'Clustering')} Clustering (n={n_clusters})",
        )

        if self.paneA is not None and self._selectors is not None:
            try:
                setattr(self.paneA, '_whatEELS_hover_gate_attached', False)
            except Exception:
                pass
            self._paneA_base_overlay = cluster_img * self._selectors  # type: ignore
            self._update_selection_overlay([])
            try:
                if getattr(self, '_hover_stream', None) is not None:
                    try:
                        self._hover_stream.remove_subscriber(self._on_paneA_hover)
                    except Exception:
                        pass
                self._hover_source = cluster_img
                self._hover_stream = hv_streams.PointerXY(source=cluster_img)
                self._hover_stream.add_subscriber(self._on_paneA_hover)
            except Exception:
                _logger.exception("Failed to reattach clustering hover stream during refresh")

        if self._hover_disabled:
            self._update_paneB(self._visualizer.plot_centers(centres, self._energy))
        elif self._frozen_pixel is not None:
            i, j = self._frozen_pixel
            self._update_paneB(self._plot_pixel_spectrum(i, j, title_prefix="Click (Frozen)"))
        elif self._last_hover_point is not None:
            i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
            self._update_paneB(self._plot_pixel_spectrum(i, j, title_prefix="Hover"))
        else:
            return
        return

    def _on_color_picker_changed(self, algorithm_name, event):
        """Apply a picked color to the active cluster and refresh the plots."""
        
        if self._suppress_color_picker_callbacks or not self._clustering_active or self._clustering_results is None:
            return

        cluster_label = self._active_cluster_labels.get(algorithm_name)
        if cluster_label is None:
            return

        if not self.cluster_colors or cluster_label < 0 or cluster_label >= len(self.cluster_colors):
            return

        self.cluster_colors[cluster_label] = event.new
        self._refresh_cluster_visuals()
    
    def _disable_all_clustering_buttons(self):
        """Disable all clustering buttons."""
        self._kmeans_run_button.disabled = True
        self._agglomerative_run_button.disabled = True
        self._spectral_run_button.disabled = True
        self._view.right_sidebar.kmeans_color_picker.disabled = True
        self._view.right_sidebar.agglomerative_color_picker.disabled = True
        self._view.right_sidebar.spectral_color_picker.disabled = True

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
        # Only enable default picker sync when K-Means was explicitly triggered by user.
        self._init_kmeans_picker_after_apply = bool(user_click)
        self._init_agglomerative_picker_after_apply = False
        self._init_spectral_picker_after_apply = False
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
        self._init_kmeans_picker_after_apply = False
        self._init_agglomerative_picker_after_apply = bool(user_click)
        self._init_spectral_picker_after_apply = False
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
        self._init_kmeans_picker_after_apply = False
        self._init_agglomerative_picker_after_apply = False
        self._init_spectral_picker_after_apply = bool(user_click)
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

    def _has_active_normalization(self):
        norm = getattr(self, '_current_norm', None)
        return (
            isinstance(norm, str)
            and norm.strip().lower() != 'none'
            and getattr(self, '_last_clustering_input', None) is not None
        )

    def _get_normalized_pixel_spectrum(self, i, j):
        """Return the normalized spectrum used for clustering for a pixel, if available."""
        if not self._has_active_normalization():
            return None

        try:
            normalized_input = np.asarray(self._last_clustering_input)
            if normalized_input.ndim != 2:
                return None

            nx = None
            if self._clustering_results is not None:
                labels, _ = self._clustering_results
                if hasattr(labels, 'shape') and len(labels.shape) >= 2:
                    if i < 0 or j < 0 or i >= int(labels.shape[0]) or j >= int(labels.shape[1]):
                        return None
                    nx = int(labels.shape[1])

            if nx is None:
                data_shape = self._get_display_numpy().shape
                if i < 0 or j < 0 or i >= int(data_shape[0]) or j >= int(data_shape[1]):
                    return None
                nx = int(data_shape[1])

            linear_idx = int(i) * nx + int(j)
            if linear_idx < 0 or linear_idx >= normalized_input.shape[0]:
                return None

            spectrum = np.asarray(normalized_input[linear_idx])
            if spectrum.ndim != 1:
                return None
            return spectrum
        except Exception:
            return None
    
    def _plot_pixel_spectrum(self, i, j, title_prefix="Hover"):
        """
        Return an hv.Overlay for a specific pixel with clustering overlays.
        """
        overlays = []
        display_data = self._get_display_data()
        try:
            spec = self._get_display_numpy()[i, j, :]
        except Exception:
            spec = SpectrumExtractor.get_spectrum_from_pixel(display_data, i, j)
        normalized_spec = self._get_normalized_pixel_spectrum(i, j)
        pixel_spec = normalized_spec if normalized_spec is not None else spec
        if pixel_spec is None:
            return hv.Overlay([])

        pixel_color = 'orange' if normalized_spec is not None else 'black'
        pixel_title = (
            f"{title_prefix} Normalized ({self._current_norm}) (i={i}, j={j})"
            if normalized_spec is not None
            else f"{title_prefix} (i={i}, j={j})"
        )
        pixel_ylabel = (
            f"Normalized Intensity ({self._current_norm})"
            if normalized_spec is not None
            else "Intensity (AU)"
        )

        overlays.append(
            hv.Curve(
                (self._energy, pixel_spec),
                kdims=['x'],
                vdims=['y']
            ).opts(
                color=pixel_color,
                line_width=1.5,
                alpha=0.2,
                title=pixel_title,
                xlabel="Energy Loss (eV)",
                ylabel=pixel_ylabel
            )
        )

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

    def _build_cluster_hover_overlay(self, point, title_prefix="Hover"):
        """Build a cheap hover overlay that keeps the pixel spectrum and centroid visible."""
        i, j = int(point["y"]), int(point["x"])
        overlays = []

        try:
            spec = self._get_display_numpy()[i, j, :]
        except Exception:
            spec = SpectrumExtractor.get_spectrum_from_pixel(self._get_display_data(), i, j)
        normalized_spec = self._get_normalized_pixel_spectrum(i, j)
        if normalized_spec is not None:
            spec = normalized_spec

        if spec is not None:
            overlays.append(
                hv.Curve((self._energy, spec), kdims=['x'], vdims=['y']).opts(
                    color='orange' if normalized_spec is not None else 'black',
                    line_width=2 if normalized_spec is not None else 1.5,
                    alpha=0.7 if normalized_spec is not None else 0.2,
                    responsive=True,
                    shared_axes=False,
                    framewise=True,
                )
            )

        if self._clustering_active and self._clustering_results is not None:
            try:
                labels, centres = self._clustering_results
                cluster_label = int(labels[i, j])
                cluster_center = centres[cluster_label]
                color = self.cluster_colors[cluster_label % len(self.cluster_colors)] if self.cluster_colors else 'blue'
                overlays.append(
                    hv.Curve((self._energy, cluster_center), kdims=['x'], vdims=['y']).opts(
                        color=color,
                        line_width=3,
                        alpha=0.95,
                        responsive=True,
                        shared_axes=False,
                        framewise=True,
                    )
                )
            except Exception:
                _logger.exception("Error building cluster hover overlay")

        return hv.Overlay(overlays).opts(
            hv.opts.Overlay(
                responsive=True,
                shared_axes=False,
                framewise=True,
                tools=[],
                hooks=[self._cache_cluster_hover_renderers],
            )
        )

    def _cache_cluster_hover_renderers(self, plot, element):
        """Cache the two line renderers from the compact hover overlay once it is rendered."""
        try:
            figure = getattr(plot, 'state', None) or plot
            renderers = [renderer for renderer in getattr(figure, 'renderers', []) or [] if hasattr(renderer, 'data_source')]
            line_renderers = []
            for renderer in renderers:
                glyph = getattr(renderer, 'glyph', None)
                if glyph is None or type(glyph).__name__.lower() != 'line':
                    continue
                line_renderers.append(renderer)
            if len(line_renderers) < 2:
                return
            self._cluster_hover_raw_renderer = line_renderers[0]
            self._cluster_hover_centroid_renderer = line_renderers[1]
            self._cluster_hover_live_ready = True
        except Exception:
            _logger.exception("clustering _cache_cluster_hover_renderers failed")

    @override
    def _on_paneA_double_tap(self, x=None, y=None):
        """Toggle between hover mode and all-cluster-centers display."""
        was_hover_blocked = self._hover_blocked
        super()._on_paneA_double_tap(x, y)  # clears _hover_blocked, _region_pairs, selection overlay
        self._frozen_pixel = None
        # DoubleTap emits two Tap-like events; keep a wider suppression window
        # so the trailing Tap does not immediately re-freeze the pane.
        self._suppress_click_until_ms = self._now_ms() + 900

        def _send_paneB(fig):
            try:
                self._update_paneB(fig)
            except Exception:
                _logger.exception("clustering _on_paneA_double_tap deferred paneB update failed")

        if self._hover_disabled or was_hover_blocked:
            self._hover_disabled = False
            if self._last_hover_point is not None and self._clustering_active:
                i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
                doc = pn.state.curdoc
                if doc is not None:
                    doc.add_next_tick_callback(lambda: _send_paneB(fig))
                else:
                    _send_paneB(fig)
        else:
            if self._clustering_active and self._clustering_results is not None and self._visualizer is not None:
                self._hover_disabled = True
                _, centres = self._clustering_results
                fig = self._visualizer.plot_centers(
                    centres,
                    self._energy,
                    title="All Cluster Centers (Double Click again to re-enable hover)"
                )
                doc = pn.state.curdoc
                if doc is not None:
                    doc.add_next_tick_callback(lambda: _send_paneB(fig))
                else:
                    _send_paneB(fig)

    @override
    def _on_paneA_selected(self, index=None):
        """Delegate to base debounce logic."""
        super()._on_paneA_selected(index)

    @override
    def _on_paneA_hover(self, x=None, y=None):
        """
        Handle PointerXY hover — show pixel spectrum unless region is selected.
        Adapts clustering overlays if active.
        """
        if x is None or y is None:
            return
        self._queue_hover(x, y)

    def _queue_hover(self, x, y):
        """Queue clustering hover only when the pointer has moved enough to matter."""
        if self._hover_blocked:
            return

        current_xy = (float(x), float(y))
        last_xy = self._hover_last_event_xy
        if last_xy is not None:
            dx = abs(current_xy[0] - last_xy[0])
            dy = abs(current_xy[1] - last_xy[1])
            if max(dx, dy) < self._CLUSTER_HOVER_DEADZONE_PX:
                return

        current_pixel = (round(y), round(x))
        if self._hover_last_event_pixel == current_pixel:
            return

        self._hover_last_event_xy = current_xy
        self._hover_last_event_pixel = current_pixel
        point = {"x": x, "y": y}
        self._last_hover_point = point
        self._hover_pending_point = point
        self._hover_last_event_ts = self._now_ms()
        if self._hover_pc is not None and not self._hover_pc.running:
            self._hover_pc.start()

    def _show_spectrum(self, *, point=None, region_pairs=None, is_hover_event: bool = False):
        """Build the clustering spectrum view and update paneB with hover throttling."""
        fig = None
        if region_pairs is not None:
            if not region_pairs:
                if self._last_hover_point is not None:
                    self._show_spectrum(point=self._last_hover_point, is_hover_event=is_hover_event)
                return
            fig = self._plot_pixel_spectrum(int(point["y"]), int(point["x"]), title_prefix="Click (Frozen)") if point is not None else self._plot_pixel_spectrum(0, 0, title_prefix="Click (Frozen)")
        elif point is not None:
            i, j = int(point["y"]), int(point["x"])
            if is_hover_event:
                fig = self._build_cluster_hover_overlay(point, title_prefix=f"Hover (x={j}, y={i})")
            else:
                fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
        self._update_paneB(fig, from_hover=is_hover_event)

    def _try_fast_hover_update(self, point) -> bool:
        """Update the live clustering hover view in-place when the Bokeh model already exists."""
        if self._hover_blocked or self._hover_disabled:
            return False
        if not self._clustering_active:
            return super()._try_fast_hover_update(point)

        try:
            bokeh_plot = self._get_live_paneB_bokeh_plot()
            if bokeh_plot is None:
                return False

            if not self._cluster_hover_install_sent:
                self._cluster_hover_install_sent = True
                self._update_paneB(self._build_cluster_hover_overlay(point), from_hover=False)
                return True

            if not self._cluster_hover_live_ready or self._cluster_hover_raw_renderer is None:
                self._cache_cluster_hover_renderers(bokeh_plot, None)
                if not self._cluster_hover_live_ready or self._cluster_hover_raw_renderer is None:
                    return False

            raw_renderer = self._cluster_hover_raw_renderer
            centroid_renderer = self._cluster_hover_centroid_renderer

            labels, centres = self._clustering_results if self._clustering_results is not None else (None, None)
            if labels is None:
                return False

            i_max = int(labels.shape[0]) - 1
            j_max = int(labels.shape[1]) - 1
            i = int(np.clip(round(point['y']), 0, i_max))
            j = int(np.clip(round(point['x']), 0, j_max))
            try:
                spec = self._get_display_numpy()[i, j, :]
            except Exception:
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._get_display_data(), i, j)
            normalized_spec = self._get_normalized_pixel_spectrum(i, j)
            if normalized_spec is not None:
                spec = normalized_spec
            if spec is None:
                return False

            if raw_renderer is None:
                return False

            try:
                raw_renderer.data_source.patch({'y': [(slice(None), np.asarray(spec))]})
            except Exception:
                raw_renderer.data_source.data = {
                    'x': self._energy,
                    'y': spec,
                }

            if centres is not None and centroid_renderer is not None:
                cluster_label = int(labels[i, j])
                cluster_center = centres[cluster_label]
                if self._cluster_hover_last_label != cluster_label:
                    color = self.cluster_colors[cluster_label % len(self.cluster_colors)] if self.cluster_colors else 'blue'
                    try:
                        centroid_renderer.data_source.patch({'y': [(slice(None), np.asarray(cluster_center))]})
                    except Exception:
                        centroid_renderer.data_source.data = {
                            'x': self._energy,
                            'y': cluster_center,
                        }
                    try:
                        centroid_renderer.glyph.line_color = color
                    except Exception:
                        pass
                    self._cluster_hover_last_label = cluster_label

            if self._cluster_hover_last_label is None and self._clustering_results is not None:
                try:
                    labels, _ = self._clustering_results
                    self._cluster_hover_last_label = int(labels[i, j])
                except Exception:
                    pass

            return True
        except Exception:
            _logger.exception("clustering _try_fast_hover_update failed")
            return False

    def _flush_pending_hover_send(self):
        self._paneB_hover_flush_pending = False
        fig = self._pending_paneB_hover_fig
        self._pending_paneB_hover_fig = None
        if fig is None:
            return
        self._update_paneB(fig, from_hover=True)

    def _update_paneB(self, fig, from_hover: bool = False):
        if self._paneB_pipe is None:
            return

        if fig is not None and not isinstance(fig, hv.Overlay):
            fig = hv.Overlay([fig])

        if not from_hover:
            self._pending_paneB_hover_fig = None
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))
            self._last_paneB_send_ts = self._now_ms()
            return

        self._pending_paneB_hover_fig = None
        self._paneB_pipe.send(self._set_ranges_and_convert(fig))
        self._last_paneB_send_ts = self._now_ms()

    def _handle_hover_render(self, point):
        self._last_hover_point = point
        if self._hover_blocked or self._hover_disabled:
            return
        if not self._clustering_active:
            super()._handle_hover_render(point)
            return
        if self._frozen_pixel is not None:
            # Keep paneB frozen after click until explicit unfreeze (double-click).
            return
        if self._try_fast_hover_update(point):
            return
        self._show_spectrum(point=point, is_hover_event=True)
    
    @override
    def _on_paneA_click(self, x=None, y=None):
        """
        Handle Tap click — freeze pixel spectrum on click.
        Double-click is handled by the base DoubleTap stream via _on_paneA_double_tap.
        """
        if x is None or y is None:
            return
        if self._now_ms() < self._suppress_click_until_ms:
            return
        self._last_hover_pixel = (round(y), round(x))
        try:
            if self._clustering_active:
                i, j = int(y), int(x)
                self._frozen_pixel = (i, j)
                self._hover_blocked = True
                self._hover_pending_point = None

                if self._clustering_results is not None:
                    labels, _ = self._clustering_results
                    cluster_label = int(labels[i, j])
                    color = self.cluster_colors[cluster_label % len(self.cluster_colors)] if self.cluster_colors else 'blue'

                    # Update the picker matching the active clustering type.
                    clustering_type = self._model.last_clustering_result.get('clustering', {}).get('type', None)
                    self._set_picker_from_cluster(clustering_type, cluster_label, i, j, color)

                fig = self._plot_pixel_spectrum(i, j, title_prefix="Click (Frozen)")
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
            (self._view.right_sidebar.kmeans_color_picker, self._kmeans_color_picker_watcher),
            (self._agglomerative_run_button, self._agglomerative_run_button_watcher),
            (self._view.right_sidebar.agglomerative_color_picker, self._agglomerative_color_picker_watcher),
            (self._spectral_run_button, self._spectral_run_button_watcher),
            (self._view.right_sidebar.spectral_color_picker, self._spectral_color_picker_watcher),
        ]:
            if btn is not None and watcher is not None:
                try:
                    btn.param.unwatch(watcher)
                except Exception:
                    pass

        # Unwatch preprocessing switch
        if self._preprocessing_switch_ref is not None and self._preprocessing_switch_watcher is not None:
            try:
                self._preprocessing_switch_ref.param.unwatch(self._preprocessing_switch_watcher)
            except Exception:
                pass
        self._preprocessing_switch_ref = None
        self._preprocessing_switch_watcher = None

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
        self._kmeans_color_picker_watcher = None
        self._agglomerative_run_button_watcher = None
        self._agglomerative_color_picker_watcher = None
        self._spectral_run_button_watcher = None
        self._spectral_color_picker_watcher = None
        self._preprocessing_switch_ref = None
        self._preprocessing_switch_watcher = None

        # Release model/view refs
        self._model = None  # type: ignore[assignment]
        self._view = None   # type: ignore[assignment]

        # Base class: clears HoloViews streams, panes, dataset/energy refs
        super().cleanup()
