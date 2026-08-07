"""
Clustering orchestration utilities.

Handles common patterns in clustering execution flow:
- Progress management
- Data preparation
- Result storage
- UI finalization
"""

import time, panel as pn, traceback
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from whateels.components import ProgressDisplay
    from ..MVC.model import ClusteringModel
    from ..MVC.view import ClusteringView
    from .preprocessing import DataPreprocessor


class ClusteringOrchestrator:
    """
    Orchestrates common clustering execution patterns.
    
    Extracts repeated logic from clustering methods to reduce duplication:
    - Progress initialization and updates
    - Data loading and preparation
    - Result storage in model
    - UI finalization (completion, error handling)
    """
    
    def __init__(
        self, 
        progress_display: "ProgressDisplay",
        model: "ClusteringModel",
        view: "ClusteringView",
        preprocessor: "DataPreprocessor",
        data_getter_fn,
        original_heatmap_ref
    ):
        """
        Initialize orchestrator with required components.
        
        Args:
            progress_display: Progress display component
            model: Clustering model for state management
            view: Clustering view for UI updates
            preprocessor: Data preprocessor instance
            data_getter_fn: Function to get data cube for clustering
            original_heatmap_ref: Reference to store original heatmap data
        """
        self.progress = progress_display
        self.model = model
        self.view = view
        self.preprocessor = preprocessor
        self.data_getter_fn = data_getter_fn
        self.original_heatmap_ref = original_heatmap_ref
    
    def initialize_progress(self):
        """Reset and show progress display."""
        self.progress.reset()
        self.progress.visible = True
        
        # Show progress in main view
        try:
            tab = pn.Tabs((
                f"Running Clustering on {self.model.current_image_name}...", 
                self.progress
            ))
            if self.view and hasattr(self.view, 'main'):
                self.view.main.update(tab)
        except Exception as e:
            print(f"Error showing clustering progress: {e}")
    
    def load_and_prepare_data(self, algorithm_name: str, available_norm: Literal['l1', 'l2', 'max', 'none']):
        """
        Load data and prepare it for clustering.
        
        Args:
            algorithm_name: Name of clustering algorithm (for progress messages)
            available_norm: Normalization method to apply
            
        Returns:
            Tuple of (data_cube, matrix_norm, sclust_norm)
        """
        # Load data
        self.progress.update(5, f"Loading {algorithm_name} data...", level='info')
        data_cube = self.data_getter_fn()
        time.sleep(0.1)
        
        # Store original heatmap if not already stored
        if self.original_heatmap_ref[0] is None:
            self.original_heatmap_ref[0] = data_cube.sum(axis=-1)
        
        # Prepare data - step 1
        self.progress.update(15, f"Preparing {algorithm_name} data - normalizing...", level='info')
        time.sleep(0.1)
        
        # Apply preprocessing
        matrix_norm, sclust_norm = self.preprocessor.prepare_matrix(data_cube, available_norm)
        
        # Prepare data - step 2
        self.progress.update(25, f"Preparing {algorithm_name} data - reshaping...", level='info')
        time.sleep(0.1)
        
        return data_cube, matrix_norm, sclust_norm
    
    def save_clustering_result(self, clustering_type: str, inputs: dict, labels, centres):
        """
        Save clustering result to model state.
        
        Args:
            clustering_type: Type constant (e.g., TAB_KMEANS)
            inputs: Dictionary of input parameters
            labels: Cluster labels array
            centres: Cluster centers array
        """
        result = {
            "clustering": {
                "file": self.model.get_uploaded_filename(),
                "spectrum_image": self.model.current_image_name,
                "type": clustering_type,
                "inputs": inputs,
                "outputs": {
                    "labels": labels,
                    "centres": centres,
                }
            }
        }
        self.model.last_clustering_result = result
        # Publish immediately so Fitting can consume the current clustering without
        # requiring the user to download its JSON first.
        self.model.app_state.last_clustering_result = result
    
    def finalize_clustering(self, n_clusters: int, algorithm_name: str, plots_layout):
        """
        Finalize clustering with progress completion and UI updates.
        
        Args:
            n_clusters: Number of clusters
            algorithm_name: Name of algorithm for messages
            plots_layout: Plots layout to restore
        """
        # Show completion
        self.progress.update(85, f"Finalizing {algorithm_name} clustering...", level='info')
        time.sleep(0.1)
        
        # Mark complete
        self.progress.completion(f"{algorithm_name} clustering complete! (n={n_clusters})")
        
        # Small delay to show completion message
        time.sleep(0.2)
        
        # Restore plots layout
        self._restore_plots_layout(plots_layout)
        
        # Enable store button
        if hasattr(self.view.right_sidebar, 'store_button') and self.view.right_sidebar.store_button is not None:
            self.view.right_sidebar.store_button.disabled = False
    
    def handle_error(self, e: Exception, algorithm_name: str, plots_layout):
        """
        Handle clustering error with cleanup.
        
        Args:
            e: Exception that occurred
            algorithm_name: Name of algorithm for error message
            plots_layout: Plots layout to restore
        """
        print(f"Error applying {algorithm_name} clustering: {e}")
        traceback.print_exc()
        self.progress.error(f"Clustering failed: {str(e)}")
        
        # Restore plots after error
        time.sleep(2)
        self._restore_plots_layout(plots_layout)
    
    def _restore_plots_layout(self, plots_layout):
        """Restore the plots layout after clustering completes."""
        try:
            if self.view and hasattr(self.view, 'main') and plots_layout is not None:
                last_clustering_type = self.model.last_clustering_result.get('clustering', {}).get('type', 'Clustering')
                tab = pn.Tabs((f"Applied {last_clustering_type} Clustering on {self.model.current_image_name}", plots_layout))
                self.view.main.update(tab)
        except Exception as e:
            print(f"Error restoring plots layout: {e}")
