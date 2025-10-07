from .managers import LayoutManager
from whateels.base.mvc import BaseController
from whateels.shared_state import AppState

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
        print("All datasets in AppState:", all_datasets)
        
        if not isinstance(all_datasets, list) or not all_datasets:
            self.base_layout.empty_main()
            return
        
        self._layout.create_tab_and_dataset_info(all_datasets)
        
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout