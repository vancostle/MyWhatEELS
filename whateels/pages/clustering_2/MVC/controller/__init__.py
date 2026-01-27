
from whateels.helpers import SafeConverter, URLUtils
import time, itertools

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
        
        view.right_sidebar.compute_umap_embedding_run_button.on_click(self._testing_event)
        
    def _testing_event(self, _) -> None:
        min_dist_list = self._view.right_sidebar.params.min_dist
        n_neighbors_list = self._view.right_sidebar.params.n_neighbors
        
        # Ensure both are lists or iterables
        if not isinstance(min_dist_list, (list, tuple)) or not isinstance(n_neighbors_list, (list, tuple)):
            raise ValueError("min_dist and n_neighbors must be lists or tuples.")
        
        # Generate all combinations of min_dist and n_neighbors
        combinations = list(itertools.product(min_dist_list, n_neighbors_list))
        
        self._view.display_all_combinations_placeholder(combinations)
        self._start_calculation()
        
    def _start_calculation(self) -> None:
        """ Start UMAP calculation. """
        time.sleep(2)  # Simulate a 2-second calculation delay
        
                
    def _compute_umap_embedding_event(self, _) -> None:
        """Event handler for computing UMAP embedding when the button is clicked."""
        
        min_dist_list = self._view.right_sidebar.params.min_dist
        n_neighbors_list = self._view.right_sidebar.params.n_neighbors
        
        # Ensure both are lists or iterables
        if not isinstance(min_dist_list, (list, tuple)) or not isinstance(n_neighbors_list, (list, tuple)):
            raise ValueError("min_dist and n_neighbors must be lists or tuples.")
        
        # Generate all combinations of min_dist and n_neighbors
        combinations = list(itertools.product(min_dist_list, n_neighbors_list))
        
        electron_count = self._model.selected_dataset["ElectronCount"]
        if electron_count is None:
            print("Warning: 'ElectronCount' attribute not found in the selected dataset.")
        
        umap_hdbscan = UMAP_HDBSCAN(electron_count_data=electron_count)

        embeddings = []
        umap_data_dicts = dict()
        
        for min_dist in min_dist_list:
            for n_neighbors in n_neighbors_list:
                t0 = time.time()
                embedding, umap_data_dict = umap_hdbscan.compute_umap_embedding(
                    min_dist,
                    n_neighbors,
                )
                t1 = time.time()
                time_lapsed = round(t1 - t0, 2) # Time in seconds
                print(f"Initial UMAP computed in {time_lapsed} seconds.")
                
                embeddings.append(embedding)
                umap_data_dicts.update(umap_data_dict)
                
                # TODO HERE IS CALLE THE METHOD TO UPDATE THE PLACEHOLDER IN THE MAIN VIEW