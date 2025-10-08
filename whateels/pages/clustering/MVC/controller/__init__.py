from .managers import LayoutManager
from whateels.base.mvc import BaseController
from whateels.shared_state import AppState
from xarray import Dataset
# from scikit-learn.cluster import KMeans

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from ..view import ClusteringView

class ClusteringController(BaseController):

    def __init__(self, model: "ClusteringModel", view: "ClusteringView"):
        super().__init__(model, view)
        
        self._layout = LayoutManager(view, self, model)
        
        app_state = AppState()
        all_datasets = app_state.all_datasets
        
        if not isinstance(all_datasets, list) or not all_datasets:
            self.base_layout.empty_main()
            return
        
        eels = self._get_only_eels_datasets(all_datasets)
        self._layout.create_tab_and_dataset_info(eels)
        
        self._change_kmeans(view)
        

    def on_click_run(self, view: "ClusteringView"):
        """Handle the K-Means 'Run' button click event."""
        run_button = view.run_button
        
        # KMeans(n_clusters=hhh).fit(x)
        
        print("[ClusteringController] K-Means clustering completed.")
        
        
    def _change_kmeans(self, view: "ClusteringView"):
        """Debug method to print the K-Means input widgets."""
        n_clusters = view.kmeans_input["n_clusters"].param.watch(self._n_cluster_watcher, 'value')
        n_init = view.kmeans_input["n_init"].param.watch(self._n_init_watcher, 'value')
        max_iter = view.kmeans_input["max_iter"].param.watch(self._max_iter_watcher, 'value')
        init_method = view.kmeans_input["init_method"].param.watch(self._init_method_watcher, 'value')
                
    def _n_cluster_watcher(self, event):
        print("n_cluster ", event.new)

    def _n_init_watcher(self, event):
        print("n_init ", event.new)
        
    def _max_iter_watcher(self, event):
        print("max_iter ", event.new)
        
    def _init_method_watcher(self, event):
        print("init_method ", event.new)
        
    
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]