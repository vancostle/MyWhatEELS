from whateels.helpers import SafeConverter, URLUtils
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
        
    def _on_umap_run_button_click(self) -> None:
        """Event handler for UMAP run button click."""
        # Start UMAP computation for all parameter combinations
        self._model.is_umap_computing = True
        self._model.was_umap_computing_canceled = False # Reset cancellation flag
        self._model.completed_umap_count = 0 # Reset completed count
        self._view.right_sidebar.download_results_button.disabled = True # Disable download button during computation
        
        # print all params for debugging
        print("Starting UMAP embedding computations with parameters:")
        print(f"min_dist: {self._view.right_sidebar.params.min_dist}")
        print(f"n_neighbors: {self._view.right_sidebar.params.n_neighbors}")
        print(f"n_components: {self._view.right_sidebar.params.n_components}")
        print(f"metric: {self._view.right_sidebar.params.metric}")
        print(f"random_state: {self._view.right_sidebar.params.random_state}")
        
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
                print("UMAP computation cancelled by user.")
                pn.state.notifications.warning("UMAP embedding computations cancelled.", duration=5000) # type: ignore
                self._model.is_umap_computing = False
                self._view.right_sidebar.compute_umap_embedding_run_button.disabled = False
                
                # Only enable download button if at least one computation completed
                if self._model.completed_umap_count > 0:
                    self._view.right_sidebar.download_results_button.disabled = False
                return
            
            if index >= len(combinations):
                pn.state.notifications.success("UMAP embedding computations completed.") # type: ignore
                
                self._model.is_umap_computing = False
                self._view.right_sidebar.compute_umap_embedding_run_button.toggle()
                
                # Enable download button if at least one computation completed
                if self._model.completed_umap_count > 0:
                    self._view.right_sidebar.download_results_button.disabled = False
                return
            
            # Set current placeholder to loading state
            result_panels[index].is_loading = True
            min_dist, n_neighbors = combinations[index]
            self._model.umap_data_dict = dict()  # Reset UMAP data dict for this computation
            
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
        
        electron_count = self._model.selected_dataset["ElectronCount"]
        if electron_count is None:
            print("Warning: 'ElectronCount' attribute not found in the selected dataset.")
        
        umap_hdbscan = UMAP_HDBSCAN(electron_count_data=electron_count)

        embeddings = []
        umap_data_dicts = dict()
        
        embedding, umap_data_dict = umap_hdbscan.compute_umap_embedding(
            min_dist,
            n_neighbors,
            n_components,
            metric
        )
        
        embeddings.append(embedding)
        umap_data_dicts.update(umap_data_dict)
        
        return umap_data_dicts
    
    def _on_umap_cancel_button_click(self) -> None:
        """Event handler for UMAP cancel button click."""
        self._model.was_umap_computing_canceled = True
        
        if (self._model.is_umap_computing):
            self._view.right_sidebar.compute_umap_embedding_run_button.disabled = True
        
        # Trigger disappear animation for all non-loading placeholders
        self._view.disappear_non_loading_placeholders()

        pn.state.notifications.warning("UMAP embedding computations cancellation requested.", duration=5000) # type: ignore