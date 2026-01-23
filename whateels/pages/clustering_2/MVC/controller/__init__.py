
from whateels.helpers import SafeConverter, URLUtils
import time

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...MVC import Clustering2PageModel, Clustering2PageView

from ...utils import UMAP_HDBSCAN
class Clustering2PageController:
    
    def __init__(self, model: "Clustering2PageModel", view: "Clustering2PageView") -> None:
        TAB_PARAM = "tab"
        tab_param = URLUtils.get_query_param(TAB_PARAM) # Get tab index from URL
        tab_param = SafeConverter.to_int(tab_param, default=-1) # Get tab index as int, default to -1 if invalid
        all_datasets = model.app_state.all_datasets

        # Display nothing if no valid tab or datasets
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            print("No valid datasets or tab index.")
            return

        # Set selected dataset in the model
        model.selected_dataset = all_datasets[tab_param]
        
        eloss = model.selected_dataset["Eloss"].values # Get Eloss values from the selected dataset
        eloss_min = float(eloss.min())
        eloss_max = float(eloss.max())
        
        electron_count = model.selected_dataset["ElectronCount"]
        if electron_count is None:
            print("Warning: 'ElectronCount' attribute not found in the selected dataset.")
        
        umap_hdbscan = UMAP_HDBSCAN(electron_count_data=electron_count)
        
        min_dist_list = [0.1, 0.5, 0.9]
        n_neighbors_list = [100, 500, 900]
        
        # TODO: I have to put the same amount of combinations in the controller as in the view by using Splitjs component and with a max of 3 per row
        amount_of_combinations = len(min_dist_list) * len(n_neighbors_list)
        
        # TODO: Adapt the original code to compute umap embedding one by one
        
        embeddings = []
        umap_data_dicts = dict()
        
        for min_dist in min_dist_list:
            for n_neighbors in n_neighbors_list:
                t0 = time.time()
                embedding, umap_data_dict = umap_hdbscan.compute_umap_embedding(
                    min_dist=min_dist_list[0],
                    n_neighbors=n_neighbors_list[0],
                )
                t1 = time.time()
                time_lapsed = round(t1 - t0, 2) # Time in seconds
                print(f"Initial UMAP computed in {time_lapsed} seconds.")
                
                embeddings.append(embedding)
                umap_data_dicts.update(umap_data_dict)
        
        view.right_sidebar.min_cut_signal.value = eloss_min
        view.right_sidebar.min_cut_signal.start = eloss_min
        view.right_sidebar.min_cut_signal.end = eloss_max
        
        view.right_sidebar.max_cut_signal.value = eloss_max
        view.right_sidebar.max_cut_signal.start = eloss_min
        view.right_sidebar.max_cut_signal.end = eloss_max

    def _get_form_values(self, view: "Clustering2PageView") -> dict:
        """Helper to get current form values from the view's right sidebar."""
        form_values = {
            "min_cut_signal": view.right_sidebar.min_cut_signal.value,
            "max_cut_signal": view.right_sidebar.max_cut_signal.value,
            "n_neighbors": view.right_sidebar.n_neighbors.value,
            "min_dist": view.right_sidebar.min_dist.value,
        }
        return form_values