from whateels.shared_state import AppState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
class Clustering2PageModel:
    
    def __init__(self):
        self._app_state = AppState()
        self._selected_dataset : "Dataset"
        
    @property
    def app_state(self) -> AppState:
        return self._app_state
    
    @property
    def selected_dataset(self) -> "Dataset":
        return self._selected_dataset
    
    @selected_dataset.setter
    def selected_dataset(self, dataset: "Dataset"):
        self._selected_dataset = dataset