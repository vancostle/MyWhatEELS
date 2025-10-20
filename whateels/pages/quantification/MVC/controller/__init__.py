from .managers import LayoutManager
from whateels.shared_state import AppState
from whateels.base.mvc.base_controller import BaseController

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import QuantificationModel
    from ..view import QuantificationView

class QuantificationController(BaseController):

    def __init__(self, model: "QuantificationModel", view: "QuantificationView"):
        super().__init__(model, view)

        self._model = model
        self._view = view

        self._layout = LayoutManager(view, self, model)
        
        app_state = AppState()
        all_datasets = app_state.all_datasets

        if not isinstance(all_datasets, list) or not all_datasets:
            self.base_layout.empty_main()
            return
        
        eels = self._get_only_eels_datasets(all_datasets)
        self._layout.create_tab_and_dataset_info(eels)

    @property
    def view(self) -> "QuantificationView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _quantification_user_update(self, view: "QuantificationView"):
        """Debug method to print the Quantification input widgets."""
        ## Placeholder for future quantification input watchers
        ## a sota posa les funcions del callback
        view._quanti_element_item['element_num'].param.watch(self._element_num_watcher, 'value')
        view._quanti_element_item['shells_multiselect'].param.watch(self._shells_multiselect_watcher, 'value')

    def _element_num_watcher(self, event):
        """Watcher for changes in the element number selection."""
        self._current_element_num_value = event.new
    
    def _shells_multiselect_watcher(self, event):
        """Watcher for changes in the shells multiselect selection."""
        self._current_shells_multiselect_value = event.new
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]