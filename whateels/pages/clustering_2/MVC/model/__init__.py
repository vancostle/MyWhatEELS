from whateels.shared_state import AppState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset

class Clustering2PageModel:

    def __init__(self):
        self._app_state = AppState()
        self._selected_dataset : "Dataset"
        self._is_umap_computing = False
        self._was_umap_computing_canceled = False
        self._umap_data_dict = dict()
        
    @property
    def app_state(self) -> AppState:
        return self._app_state
    @property
    def selected_dataset(self) -> "Dataset":
        return self._selected_dataset
    @property
    def is_umap_computing(self) -> bool:
        return self._is_umap_computing
    @property
    def was_umap_computing_canceled(self) -> bool:
        return self._was_umap_computing_canceled
    @property
    def umap_data_dict(self) -> dict:
        return self._umap_data_dict
    
    @selected_dataset.setter
    def selected_dataset(self, dataset: "Dataset"):
        self._selected_dataset = dataset
        
    @is_umap_computing.setter
    def is_umap_computing(self, is_computing: bool):
        self._is_umap_computing = is_computing
    
    @was_umap_computing_canceled.setter
    def was_umap_computing_canceled(self, was_canceled: bool):
        self._was_umap_computing_canceled = was_canceled
    
    @umap_data_dict.setter
    def umap_data_dict(self, data_dict: dict):
        self._umap_data_dict = data_dict