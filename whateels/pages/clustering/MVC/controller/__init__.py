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
        
        # Setup background-subtraction switch based on multifit availability
        self._update_background_subtraction_switch_state()
        
        # Watch for changes in multifit availability
        app_state.param.watch(self._on_multifit_change, 'multifit')

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
            view.kmeans_input["n_init"].param.watch(self._n_init_watcher, 'value')
            view.kmeans_input["max_iter"].param.watch(self._max_iter_watcher, 'value')
            view.kmeans_input["init_method"].param.watch(self._init_method_watcher, 'value')

    def _available_norms_watcher(self, event):
        """Watcher for changes in the available norms selection."""
        self._current_available_norms_value = event.new

    def _n_cluster_watcher(self, event):
        """Watcher for changes in the number of clusters selection."""
        self._current_n_clusters_value = event.new
        
    def _n_init_watcher(self, event):
        """Watcher for changes in the number of initializations selection."""
        self._current_n_init_value = event.new
        
    def _max_iter_watcher(self, event):
        """Watcher for changes in the maximum iterations selection."""
        self._current_max_iter_value = event.new
        
    def _init_method_watcher(self, event):
        """Watcher for changes in the initialization method selection."""
        self._current_init_method_value = event.new
    
    def _update_background_subtraction_switch_state(self):
        """
        Update the background-subtraction switch enabled/disabled state
        based on multifit data availability.
        
        The switch is enabled only when multifit data is available.
        """
        if self._view.background_subtraction_switch is None:
            return
        
        is_available = self._model.is_multifit_available()
        
        # Enable switch only if multifit data is available
        self._view.background_subtraction_switch.disabled = not is_available
        
        # If multifit becomes unavailable, turn off the switch
        if not is_available and self._view.background_subtraction_switch.value:
            self._view.background_subtraction_switch.value = False
    
    def _on_multifit_change(self, event):
        """
        Callback triggered when multifit data changes in AppState.
        
        Updates the background-subtraction switch state accordingly.
        """
        self._update_background_subtraction_switch_state()
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]