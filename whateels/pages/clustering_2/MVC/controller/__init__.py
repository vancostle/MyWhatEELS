from whateels.helpers import SafeConverter, URLUtils
from whateels.components import SplitJs
import itertools, panel as pn, threading

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...MVC import Clustering2PageModel, Clustering2PageView

from ...utils import UMAP_HDBSCAN
class Clustering2PageController:
    
    def __init__(self, model: "Clustering2PageModel", view: "Clustering2PageView") -> None:
        TAB_PARAM = "tab"

        self._model = model
        self._view = view
        
        tab_param = URLUtils.get_query_param(TAB_PARAM) # Get tab index from URL
        tab_param = SafeConverter.to_int(tab_param, default=-1) # Get tab index as int, default to -1 if invalid
        all_datasets = self._model.app_state.all_datasets

        # Display nothing if no valid tab or datasets
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            print("No valid datasets or tab index.")
            return

        # Set selected dataset in the model
        self._model.selected_dataset = all_datasets[tab_param]

        electron_count = self._model.selected_dataset["ElectronCount"]
        self._hdbscan = UMAP_HDBSCAN(electron_count_data=electron_count) # Initialize UMAP_HDBSCAN with electron count data from the selected dataset

        eloss = self._model.selected_dataset["Eloss"].values # Get Eloss values from the selected dataset
        eloss_min = float(eloss.min())
        eloss_max = float(eloss.max())

        view.right_sidebar.min_cut_signal.value = eloss_min
        view.right_sidebar.min_cut_signal.start = eloss_min
        view.right_sidebar.min_cut_signal.end = eloss_max
        
        view.right_sidebar.max_cut_signal.value = eloss_max
        view.right_sidebar.max_cut_signal.start = eloss_min
        view.right_sidebar.max_cut_signal.end = eloss_max
        
        view.right_sidebar.compute_umap_embedding_run_button.on_click_by_state(True, self._on_umap_run_button_click)
        view.right_sidebar.compute_umap_embedding_run_button.on_click_by_state(False, self._on_umap_cancel_button_click)
        
        view.right_sidebar.compute_hdbscan_embedding_run_button.on_click(self._compute_hdbscan_on_umap_event)
        
        # Register callback for when UMAP data is loaded from file
        view.left_sidebar.set_on_umap_loaded_callback(self._on_umap_loaded_from_file)
        view.left_sidebar.set_on_file_removed_callback(self._on_file_removed)
        
    def _on_umap_run_button_click(self) -> None:
        """Event handler for UMAP run button click."""
        # Start UMAP computation for all parameter combinations
        self._model.is_umap_computing = True
        self._model.was_umap_computing_canceled = False # Reset cancellation flag
        self._model.completed_umap_count = 0 # Reset completed count
        self._model.umap_data_dict = dict()  # Reset UMAP data dict for all computations
        self._view.right_sidebar.download_results_button.disabled = True # Disable download button during computation
        self._view.left_sidebar.disable_controls()  # Disable controls in the left sidebar during computation
        self._view.right_sidebar.disable_hdbscan_controls()  # Disable hdbscan controls in the right sidebar during computation
        
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
            lambda: self._start_compute_umap_embedding(combinations, result_panels, n_components, metric),
            period=1000,  # 1000ms delay to let UI render
            count=1
        )
        
    def _start_compute_umap_embedding(
        self, 
        combinations : list[tuple[float, int]], 
        result_panels, 
        n_components : int, 
        metric : str
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
                    
                    print("keys in umap_data_dict:", self._model.umap_data_dict.keys())
                    
                    return
                
                self._view.right_sidebar.hdbscan_selected_umap.options = [] # Clear HDBSCAN UMAP selection options when cancelled
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
                    print("keys in umap_data_dict:", self._model.umap_data_dict.keys())
                return
            
            # Set current placeholder to loading state
            result_panels[index].is_loading = True
            min_dist, n_neighbors = combinations[index]
            
            def compute_and_callback():
                # This runs in a separate thread to avoid blocking UI
                nonlocal n_components, metric
                umap_data = self._compute_umap_embedding_event(min_dist, n_neighbors, n_components, metric)
                self._model.umap_data_dict.update(umap_data) # Get UMAP data
                # Execute callback on main thread (thread-safe method for Panel)
                pn.state.execute(on_complete)

            #  Callback to be called when calculation is done
            def on_complete():
                self._view.replace_placeholder_with_umap_embedding(
                    index, 
                    min_dist, 
                    n_neighbors, 
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
        
    def _compute_umap_embedding_event(self, min_dist: float, n_neighbors: int, n_components: int, metric: str) -> dict:
        """Event handler for computing UMAP embedding when the button is clicked."""
        
        embeddings = []
        umap_data_dicts = dict()
        
        embedding, umap_data_dict = self._hdbscan.compute_umap_embedding(
            min_dist,
            n_neighbors,
            n_components,
            metric
        )
        
        embeddings.append(embedding)
        umap_data_dicts.update(umap_data_dict)
        
        return umap_data_dicts
    
    def _compute_hdbscan_on_umap_event(self, event):
        """Event handler for computing HDBSCAN on UMAP embedding when the button is clicked."""
        
        self._view.main.hdbscan_wrapper.clear() # Clear previous HDBSCAN results from the main layout
        
        # Extract the first embedding from the model's UMAP data dict
        umap_dict = self._model.umap_data_dict

        # Get the first embedding object
        first_key = next(iter(umap_dict))
        embedding_obj = umap_dict[first_key]
        # If embedding_obj is a dict or has 'embedding_' attribute, extract the array
        embedding = getattr(embedding_obj, 'embedding_', embedding_obj)
        # Get HDBSCAN parameters from UI
        min_samples = SafeConverter.to_int(self._view.right_sidebar.params.hdbscan_min_samples, default=4)
        min_cluster_size = SafeConverter.to_int(self._view.right_sidebar.params.hdbscan_min_cluster_size, default=100)
        hdbscan_results = self._hdbscan.compute_hdbscan_on_umap(embedding, min_samples, min_cluster_size)
        cmap_obj = self._hdbscan.get_nclusters_cmap(hdbscan_results, n_clusters=len(set(hdbscan_results.labels_)))
        
        # Create the Plotly figures and wrap them in Panel panes
        hdbscan_map_plot = self._hdbscan.plot_hdbscan_map(hdbscan_results, cmap_obj)
        hdbscan_mean_spectra_plot = self._hdbscan.plot_mean_spectra_per_cluster(hdbscan_results, cmap_obj)
        
        self._view.main.hdbscan_wrapper.append(
            pn.Row(
                pn.pane.Plotly(hdbscan_map_plot, sizing_mode='stretch_both', margin=0),
                pn.pane.Plotly(hdbscan_mean_spectra_plot, sizing_mode='stretch_both', margin=0),
                sizing_mode='stretch_width',
                margin=0,
            )
        )
        
        # print("Computing HDBSCAN on UMAP embedding with parameters:")
        # print("Min samples:", min_samples)
        # print("Min cluster size:", min_cluster_size)
        # print("UMAP embedding shape:", embedding.shape)

        # return hdbscan_results
    
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
        self._view.right_sidebar.disable_controls()
        self._view.right_sidebar.enable_hdbscan_controls() # Enable HDBSCAN controls when UMAP data is loaded from file
        
        combinations = [(min_dist, n_neighbors)]
        self._view.display_all_combination_placeholders(combinations)
        self._view.replace_placeholder_with_umap_embedding(0, min_dist, n_neighbors, umap_data_dict)
    
    def _on_file_removed(self) -> None:
        """Event handler for when file is removed."""
        main_placeholder = self._view.main.placeholder
        self._view.main.clear()  # Show default placeholder when file is removed
        self._view.main.append(main_placeholder)  # Re-append the main placeholder after clearing
        self._view.right_sidebar.enable_controls()  # Re-enable controls in the right sidebar
        self._view.right_sidebar.disable_hdbscan_controls()  # Disable HDBSCAN controls when file is removed