from .managers import LayoutManager
from whateels.base.mvc import BaseController
from whateels.shared_state import AppState
from whateels.helpers.safe_converter import SafeConverter
import panel as pn

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
        
        all_datasets = AppState().all_datasets
        
        # Get 'tab' query parameter from URL
        tab_param = self._get_query_param("tab")
        # Convert to integer with default -1
        tab_param = SafeConverter.to_int(tab_param, default=-1) # -1 indicates invalid index in this context
        
        # Validate datasets and tab index
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            self.base_layout.empty_main()
            return
        
        self._layout.create_tab_and_dataset_info([all_datasets[tab_param]])

    @property
    def view(self) -> "ClusteringView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _get_query_param(self, param_name: str) -> str | None:
        """Retrieve a specific query parameter from the URL, handling both list and single value cases."""
        params = pn.state.location.query_params if pn.state.location else {}
        value = params.get(param_name, None)
        if isinstance(value, list):
            return value[0]
        return value