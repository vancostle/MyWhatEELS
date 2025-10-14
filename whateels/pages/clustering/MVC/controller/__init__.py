from .managers import LayoutManager
from whateels.base.mvc import BaseController
from whateels.shared_state import AppState
from xarray import Dataset
# from scikit-learn.cluster import KMeans

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from ..view import ClusteringView

class ClusteringController(BaseController):

    def __init__(self, model: "ClusteringModel", view: "ClusteringView"):
        super().__init__(model, view)
        
        self._view = view
        self._model = model
        
        self._layout = LayoutManager(view, self, model)
        
        app_state = AppState()
        all_datasets = app_state.all_datasets

        if not isinstance(all_datasets, list) or not all_datasets:
            self.base_layout.empty_main()
            return
        
        eels = self._get_only_eels_datasets(all_datasets)
        self._layout.create_tab_and_dataset_info(eels)
        
        # K-Means related attributes
        self._current_available_norms_value: Optional[str] = self._model.constants.DEFAULT_SELECTED_NORM
        self._current_n_clusters_value: Optional[int] = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        
        self._kmeans_user_update(view)
        # self._handle_run_button(view)

    @property
    def view(self) -> "ClusteringView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout
        
    def _kmeans_user_update(self, view: "ClusteringView"):
        """Debug method to print the K-Means input widgets."""
        if view.kmeans_input is not None:
            view.kmeans_input["available_norms"].param.watch(self._available_norms_watcher, 'value')
            view.kmeans_input["n_clusters"].param.watch(self._n_cluster_watcher, 'value')

    def _available_norms_watcher(self, event):
        self._current_available_norms_value = event.new

    def _n_cluster_watcher(self, event):
        self._current_n_clusters_value = event.new
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]