from whateels.helpers import SafeConverter, URLUtils
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import ClusteringModel
    from ..view import ClusteringView

class ClusteringController:

    def __init__(self, model: "ClusteringModel", view: "ClusteringView"):
        self._view = view
        self._model = model
        
        # Register tab change handler
        self._view.set_tab_change_callback(self._on_tab_change)
        
        self._initialize_view()
        
    def _initialize_view(self) -> None:
        """Initialize the view based on the current application state."""
        TAB_PARAM = "tab"
        tab_param = URLUtils.get_query_param(TAB_PARAM)
        tab_param = SafeConverter.to_int(tab_param, default=-1)
        all_datasets = self._model.app_state.all_datasets
        
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            self._view.main.empty()
            return
        
        self._view.create_tab_and_dataset_info([all_datasets[tab_param]])
    
    def _on_tab_change(self, event):
        """Handle tab change events by updating the sidebar."""
        new_tab = event.new
        self._view.update_sidebar_for_tab(new_tab)