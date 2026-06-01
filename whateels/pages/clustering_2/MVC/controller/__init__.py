from whateels.helpers import SafeConverter, URLUtils
import itertools, panel as pn, threading
from ..view.plots import Clustering2SpectrumImagePlot

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...MVC import Clustering2PageModel, Clustering2PageView

from ...utils import UMAP_HDBSCAN
class Clustering2PageController:
    
    def __init__(self, model: "Clustering2PageModel", view: "Clustering2PageView") -> None:
        TAB_PARAM = "tab"
        
        self._is_valid_tab_and_dataset = False

        self._model = model
        self._view = view
        
        tab_param = URLUtils.get_query_param(TAB_PARAM) # Get tab index from URL
        tab_param = SafeConverter.to_int(tab_param, default=-1) # Get tab index as int, default to -1 if invalid
        
        all_datasets = self._model.app_state.all_datasets

        # Register callback for when UMAP data is loaded from file
        view.left_sidebar.set_on_umap_loaded_callback(self._on_umap_loaded_from_file)
        view.left_sidebar.set_on_file_removed_callback(self._on_file_removed)

        # Check if valid tab and datasets exist
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            # Show placeholder for when no DM file is uploaded
            main_placeholder = self._view.main.none_dm_file_uploaded_placeholder
            self._view.main.append_once(main_placeholder)
            return

        self._is_valid_tab_and_dataset = True
        
        # Show placeholder for when DM file is uploaded
        main_placeholder = self._view.main.dm_file_uploaded_placeholder
        self._view.main.append_once(main_placeholder)

        # Set selected dataset in the model
        self._model.selected_dataset = all_datasets[tab_param]

        # Build UMAP/HDBSCAN backend from the active data source (raw or Home-preprocessed).
        self._hdbscan = UMAP_HDBSCAN(electron_count_data=self._resolve_electron_count_data())

        # Spectrum image visualizer for the HDBSCAN results section.
        # create_plots() is called once here so paneA/paneB Bokeh models are
        # never duplicated across multiple Panel trees.
        self._spectrum_plot = Clustering2SpectrumImagePlot(
            self._model.selected_dataset,
            eloss_name='Eloss',
        )
        self._spectrum_plot_layout = self._spectrum_plot.create_plots()

        view.right_sidebar.use_preprocessed_data_switch.param.watch(
            self._on_use_preprocessed_data_switch_changed,
            'value',
        )
        
        view.right_sidebar.hdbscan_activate_button.on_click(self._hdbscan_active_button_event) # Register callback for HDBSCAN activate button click
        
        view.right_sidebar.compute_umap_embedding_run_button.on_click_by_state(True, self._on_umap_run_button_click)
        view.right_sidebar.compute_umap_embedding_run_button.on_click_by_state(False, self._on_umap_cancel_button_click)
        
        view.right_sidebar.compute_hdbscan_embedding_run_button.on_click(self._compute_hdbscan_on_umap_event)
        
    def is_valid_tab_and_dataset(self) -> bool:
        """Returns True if the controller was initialized with a valid tab and dataset, else False."""
        return self._is_valid_tab_and_dataset

    def _has_valid_preprocessed_data(self, notify: bool = False) -> bool:
        """Validate that Home-preprocessed data exists and is compatible with current dataset shape."""
        if not self._model.is_preprocessed_data_available():
            if notify:
                pn.state.notifications.warning(
                    "No preprocessed data available. Apply preprocessing in Home first.",
                    duration=5000,
                ) # type: ignore
            return False

        raw_electron_count = self._model.selected_dataset["ElectronCount"]
        preprocessed = self._model.app_state.preprocessed_plot_dataset["ElectronCount"]

        try:
            if preprocessed is None or len(preprocessed.shape) != 3:
                raise ValueError("Expected a 3D preprocessed ElectronCount DataArray.")
            if preprocessed.shape[0] != raw_electron_count.shape[0] or preprocessed.shape[1] != raw_electron_count.shape[1]:
                raise ValueError(
                    f"Spatial shape mismatch. Raw={raw_electron_count.shape[:2]}, preprocessed={preprocessed.shape[:2]}"
                )
        except Exception as e:
            if notify:
                pn.state.notifications.warning(
                    f"Preprocessed data is not compatible with this tab. Using raw data. Details: {e}",
                    duration=6000,
                ) # type: ignore
            return False

        return True

    def _resolve_electron_count_data(self):
        """Return ElectronCount source according to the sidebar switch."""
        use_preprocessed = self._model.should_use_preprocessed_data(
            bool(self._view.right_sidebar.use_preprocessed_data_switch.value)
        )

        if use_preprocessed and self._has_valid_preprocessed_data(notify=True):
            return self._model.app_state.preprocessed_plot_dataset["ElectronCount"]

        if use_preprocessed and self._view.right_sidebar.use_preprocessed_data_switch.value:
            self._view.right_sidebar.use_preprocessed_data_switch.value = False

        return self._model.selected_dataset["ElectronCount"]

    def _reset_results_for_new_data_source(self) -> None:
        """Clear previous results because they belong to a different input data source."""
        self._model.umap_data_dict = dict()
        self._model.completed_umap_count = 0
        
        self._view.main.clear() # Clear all results and placeholders from the main layout

        self._view.right_sidebar.download_results_button.disabled = True
        self._view.right_sidebar.hdbscan_selected_umap.options = {}
        self._view.right_sidebar.svm_selected_umap.options = {}
        self._view.right_sidebar.disable_hdbscan_controls()

    def _on_use_preprocessed_data_switch_changed(self, event) -> None:
        """Swap the data source the page uses without clearing computed results."""
        if event.new and not self._has_valid_preprocessed_data(notify=True):
            self._view.right_sidebar.use_preprocessed_data_switch.value = False
            return

        self._hdbscan = UMAP_HDBSCAN(electron_count_data=self._resolve_electron_count_data())
        source_name = "Home preprocessed" if event.new else "raw"
        self._reset_results_for_new_data_source() # Clear previous results because they belong to a different input data source
        pn.state.notifications.info(
            f"Clustering input switched to {source_name} data. Recompute UMAP to apply.",
            duration=3500,
        ) # type: ignore
        
    def _on_umap_run_button_click(self) -> None:
        """Event handler for UMAP run button click."""
        # Refresh backend in case Home preprocessing changed while this page remained open.
        self._hdbscan = UMAP_HDBSCAN(electron_count_data=self._resolve_electron_count_data())

        # Start UMAP computation for all parameter combinations
        self._model.is_umap_computing = True
        self._model.was_umap_computing_canceled = False # Reset cancellation flag
        self._model.completed_umap_count = 0 # Reset completed count
        self._model.umap_data_dict = dict()  # Reset UMAP data dict for all computations
        self._view.right_sidebar.download_results_button.disabled = True # Disable download button during computation
        self._view.left_sidebar.disable_controls()  # Disable controls in the left sidebar during computation
        self._view.right_sidebar.disable_hdbscan_controls()  # Disable hdbscan controls in the right sidebar during computation
        
        available_norm = str(self._view.right_sidebar.params.available_norms)
        min_dist_list = self._view.right_sidebar.params.min_dist
        n_neighbors_list = self._view.right_sidebar.params.n_neighbors
        n_components = SafeConverter.to_int(self._view.right_sidebar.params.n_components, default=2)
        metric = str(self._view.right_sidebar.params.metric)
        
        # Ensure both are lists or iterables
        if not isinstance(min_dist_list, (list, tuple)) or not isinstance(n_neighbors_list, (list, tuple)):
            raise ValueError("min_dist and n_neighbors must be lists or tuples.")
        
        # Generate all combinations of min_dist and n_neighbors
        combinations = list(itertools.product(min_dist_list, n_neighbors_list))
        
        # Display all placeholders and get reference to them
        result_panels = self._view.display_all_combination_placeholders(combinations)
        
        # Wait a moment for UI to render before starting calculations
        pn.state.add_periodic_callback(
            lambda: self._start_compute_umap_embedding(combinations, result_panels, n_components, metric, available_norm),
            period=1000,  # 1000ms delay to let UI render
            count=1
        )
        
    def _start_compute_umap_embedding(
        self, 
        combinations : list[tuple[float, int]], 
        result_panels, 
        n_components : int, 
        metric : str,
        available_norm : str,
    ) -> None:
        """Start UMAP calculation sequentially for each combination."""
        
        n_components = n_components  # Capture n_components for use in nested function
        metric = metric  # Capture metric for use in nested function
        
        def process_next(index):
            # Check cancellation first, before checking completion
            if self._model.was_umap_computing_canceled:
                pn.state.notifications.warning("UMAP embedding computations cancelled.", duration=5000) # type: ignore
                self._model.is_umap_computing = False
                self._view.left_sidebar.enable_controls()  # Re-enable controls in the left sidebar
                self._view.right_sidebar.compute_umap_embedding_run_button.disabled = False
                
                # Only enable download button if at least one computation completed
                if self._model.completed_umap_count > 0:
                    self._view.right_sidebar.download_results_button.disabled = False
                    self._view.right_sidebar.enable_hdbscan_controls() # Enable HDBSCAN controls if at least one computation completed
                    self._view.right_sidebar.hdbscan_selected_umap.options = self._model.umap_data_dict # Update HDBSCAN UMAP selection options based on available UMAP embeddings in the model
                    self._view.right_sidebar.svm_selected_umap.options = self._model.umap_data_dict
                    
                    return
                
                self._view.right_sidebar.hdbscan_selected_umap.options = [] # Clear HDBSCAN UMAP selection options when cancelled
                self._view.right_sidebar.svm_selected_umap.options = []
                return
            
            # Check if all combinations have been processed
            if index >= len(combinations):
                pn.state.notifications.success("UMAP embedding computations completed.") # type: ignore
                
                self._model.is_umap_computing = False
                self._view.left_sidebar.enable_controls()  # Re-enable controls in the left sidebar
                self._view.right_sidebar.enable_hdbscan_controls() # Enable HDBSCAN controls after UMAP computations are done
                self._view.right_sidebar.compute_umap_embedding_run_button.toggle()
                
                # Enable download button if at least one computation completed
                if self._model.completed_umap_count > 0:
                    self._view.right_sidebar.download_results_button.disabled = False
                    self._view.right_sidebar.hdbscan_selected_umap.options = self._model.umap_data_dict # Update HDBSCAN UMAP selection options based on available UMAP embeddings in the model
                    self._view.right_sidebar.svm_selected_umap.options = self._model.umap_data_dict
                return
            
            # Set current placeholder to loading state
            result_panels[index].is_loading = True
            min_dist, n_neighbors = combinations[index]
            
            def compute_and_callback():
                # This runs in a separate thread to avoid blocking UI
                nonlocal n_components, metric
                umap_data = self._compute_umap_embedding_event(min_dist, n_neighbors, n_components, metric, available_norm)
                self._model.umap_data_dict.update(umap_data) # Get UMAP data
                # Execute callback on main thread (thread-safe method for Panel)
                pn.state.execute(on_complete)

            #  Callback to be called when calculation is done
            def on_complete():
                self._view.replace_placeholder_with_umap_embedding(
                    index, 
                    min_dist, 
                    n_neighbors, 
                    available_norm,
                    self._model.umap_data_dict,
                )
                
                # Increment completed count
                self._model.completed_umap_count += 1
            
                # Process next placeholder
                process_next(index + 1)
    
            # Start computation thread for this index
            threading.Thread(target=compute_and_callback).start()
        
        # Start with the first placeholder
        process_next(index=0)
        
    def _compute_umap_embedding_event(self, min_dist: float, n_neighbors: int, n_components: int, metric: str, available_norm: str) -> dict:
        """Event handler for computing UMAP embedding when the button is clicked."""

        umap_data_dicts = dict()
        
        _, umap_data_dict = self._hdbscan.compute_umap_embedding(
            min_dist,
            n_neighbors,
            n_components,
            metric,
            available_norm,
        )
        
        umap_data_dicts.update(umap_data_dict)
        
        return umap_data_dicts
    
    def _compute_hdbscan_on_umap_event(self, event):
        """Event handler for computing HDBSCAN on UMAP embedding when the button is clicked."""

        self._view.main.hdbscan_wrapper.clear() # Clear previous HDBSCAN results from the main layout

        selected_umap_dict = self._view.right_sidebar.hdbscan_selected_umap.value
        
        embedding_obj = selected_umap_dict
        # If embedding_obj is a dict or has 'embedding_' attribute, extract the array
        embedding = getattr(embedding_obj, 'embedding_', embedding_obj)
        available_norm = getattr(embedding_obj, 'whateels_norm', 'none')
        # Get HDBSCAN parameters from UI
        min_samples = SafeConverter.to_int(self._view.right_sidebar.params.hdbscan_min_samples, default=4)
        min_cluster_size = SafeConverter.to_int(self._view.right_sidebar.params.hdbscan_min_cluster_size, default=100)
        hdbscan_results = self._hdbscan.compute_hdbscan_on_umap(embedding, min_samples, min_cluster_size)
        cmap_obj = self._hdbscan.get_nclusters_cmap(hdbscan_results, n_clusters=len(set(hdbscan_results.labels_)))
        
        hdbscan_umap_embedding_width_labels_plot = self._hdbscan.plot_umap_embedding_with_labels(
            embedding, 
            hdbscan_results.labels_, 
            cmap_obj, min_samples, min_cluster_size
        )
        
        self._spectrum_plot.update_hdbscan_results(
            hdbscan_results,
            cmap_obj,
            electron_count_data=self._hdbscan.get_electron_count_data_for_norm(available_norm),
            available_norm=available_norm,
        )
        self._view.main.hdbscan_wrapper.append(self._spectrum_plot_layout)
        
        self._view.main.append_once(self._view.main.hdbscan_wrapper) # Re-append the HDBSCAN wrapper to ensure it is visible after clearing
        
        self._view.main.umap_embedding_wrapper.clear() # Clear UMAP embedding results from the main layout to emphasize HDBSCAN results
        self._view.main.umap_embedding_wrapper.append(hdbscan_umap_embedding_width_labels_plot) # Show UMAP embedding with HDBSCAN labels in the UMAP embedding wrapper for reference
        self._view.main.append_once(self._view.main.umap_embedding_wrapper) # Re-append the UMAP embedding wrapper to ensure it is visible after clearing
    
    def _on_umap_cancel_button_click(self) -> None:
        """Event handler for UMAP cancel button click."""
        self._model.was_umap_computing_canceled = True
        
        if (self._model.is_umap_computing):
            self._view.right_sidebar.compute_umap_embedding_run_button.disabled = True
        
        # Trigger disappear animation for all non-loading placeholders
        self._view.disappear_non_loading_placeholders()

        pn.state.notifications.warning("UMAP embedding computations cancellation requested.", duration=5000) # type: ignore
    
    def _on_umap_loaded_from_file(self, min_dist: float, n_neighbors: int, umap_data_dict: dict, filename: str) -> None:
        """Event handler for when UMAP data is loaded from file."""
        
        self._view.right_sidebar.hdbscan_selected_umap.options = umap_data_dict # Update HDBSCAN UMAP selection options based on available UMAP embeddings in the model
        self._view.right_sidebar.svm_selected_umap.options = umap_data_dict
        self._view.right_sidebar.disable_controls()
        self._view.right_sidebar.enable_hdbscan_controls() # Enable HDBSCAN controls when UMAP data is loaded from file
        
        combinations = [(min_dist, n_neighbors)]
        self._view.display_all_combination_placeholders(combinations)
        umap_obj = next(iter(umap_data_dict.values()))
        norm = getattr(umap_obj, 'whateels_norm', 'none')
        self._view.replace_placeholder_with_umap_embedding(0, min_dist, n_neighbors, norm, umap_data_dict)
    
    def _on_file_removed(self) -> None:
        """Event handler for when file is removed."""
        
        # Reset model state related to UMAP data
        if (self._is_valid_tab_and_dataset):
            main_placeholder = self._view.main.dm_file_uploaded_placeholder
        else:
            main_placeholder = self._view.main.none_dm_file_uploaded_placeholder

        self._view.main.clear()  # Show default placeholder when file is removed
        self._view.main.append_once(main_placeholder)  # Re-append the main placeholder after clearing
        self._view.right_sidebar.enable_controls()  # Re-enable controls in the right sidebar
        self._view.right_sidebar.disable_hdbscan_controls()  # Disable HDBSCAN controls when file is removed
        
    def _hdbscan_active_button_event(self, event):
        """Event handler for HDBSCAN activate button click."""
        selected_umap_dict = self._view.right_sidebar.hdbscan_selected_umap.value
        
        embedding_obj = selected_umap_dict
        embedding = getattr(embedding_obj, 'embedding_', embedding_obj)

        min_samples_min = SafeConverter.to_int(
            self._view.right_sidebar.params.hdbscan_grid_min_samples,
            default=1,
        )
        min_samples_max = SafeConverter.to_int(
            self._view.right_sidebar.params.hdbscan_grid_max_samples,
            default=8,
        )
        min_cluster_size_min = SafeConverter.to_int(
            self._view.right_sidebar.params.hdbscan_grid_min_cluster_size,
            default=100,
        )
        min_cluster_size_max = SafeConverter.to_int(
            self._view.right_sidebar.params.hdbscan_grid_max_cluster_size,
            default=900,
        )
        step = SafeConverter.to_int(
            self._view.right_sidebar.params.hdbscan_grid_step,
            default=100,
        )
        
        data : list[tuple[int, int, int, int, float]] = self._hdbscan.evaluate_hdbscan(
            embedding,
            min_samples_min=min_samples_min,
            min_samples_max=min_samples_max,
            min_cluster_size_min=min_cluster_size_min,
            min_cluster_size_max=min_cluster_size_max,
            step=step,
        )
        heatmap_overlay = self._hdbscan.plot_cluster_heatmap(data)
        
        
        self._view.main.heatmap_wrapper.clear() # Clear previous heatmap from the main layout
        self._view.main.heatmap_wrapper.append(heatmap_overlay)
        
        self._view.main.append_once(self._view.main.heatmap_wrapper) # Re-append the heatmap wrapper to ensure it is visible after clearing