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
        self._current_init_method_value: Optional[str] = self._model.constants.DEFAULT_INIT_METHOD
        self._current_n_clusters_value: Optional[int] = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        self._current_n_init_value: Optional[int] = self._model.constants.DEFAULT_NUMBER_OF_INIT
        self._current_max_iter_value: Optional[int] = self._model.constants.DEFAULT_MAX_ITER
        
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

    # def _handle_run_button(self, view: "ClusteringView"):
    #     """Handle the K-Means 'Run' button click event."""
    #     run_button = view.run_button

    #     if run_button is not None:
    #         run_button.on_click_by_state(state=True, callback=self._run_button_on_click_event)
    #         run_button.on_click_by_state(state=False, callback=self._run_button_off_click_event)

    # def _run_button_on_click_event(self):
    #     """Execute the K-Means clustering algorithm."""
    #     print("START K-Means clustering.")
        
    # def _run_button_off_click_event(self):
    #     """Handle the K-Means 'Stop' button click event."""
    #     print("STOP K-Means clustering.")
        
    def _kmeans_user_update(self, view: "ClusteringView"):
        """Debug method to print the K-Means input widgets."""
        if view.kmeans_input is not None:
            view.kmeans_input["n_clusters"].param.watch(self._n_cluster_watcher, 'value')
            view.kmeans_input["n_init"].param.watch(self._n_init_watcher, 'value')
            view.kmeans_input["max_iter"].param.watch(self._max_iter_watcher, 'value')
            view.kmeans_input["init_method"].param.watch(self._init_method_watcher, 'value')

    def _n_cluster_watcher(self, event):
        self._current_n_clusters_value = event.new

    def _n_init_watcher(self, event):
        self._current_n_init_value = event.new
        
    def _max_iter_watcher(self, event):
        self._current_max_iter_value = event.new
        
    def _init_method_watcher(self, event):
        self._current_init_method_value = event.new
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]