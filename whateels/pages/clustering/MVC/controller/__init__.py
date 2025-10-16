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

    @property
    def view(self) -> "ClusteringView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]