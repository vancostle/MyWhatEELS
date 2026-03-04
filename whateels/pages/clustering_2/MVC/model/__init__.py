from whateels.shared_state import get_cached_app_state

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    from whateels.shared_state import AppState

class Clustering2PageModel:

    def __init__(self):
        self._app_state = get_cached_app_state()
        self._selected_dataset : "Dataset"
        self._is_umap_computing = False
        self._was_umap_computing_canceled = False
        self._umap_data_dict = dict()
        self._completed_umap_count: int = 0
        self._extra_umap_params_key: str = "Extra UMAP Parameters"
        self._loaded_umap_data = None
        
    @property
    def app_state(self) -> "AppState":
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
    @property
    def completed_umap_count(self) -> int:
        return self._completed_umap_count
    @property
    def extra_umap_params_key(self) -> str:
        return self._extra_umap_params_key
    @property
    def loaded_umap_data(self):
        return self._loaded_umap_data

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
    
    @completed_umap_count.setter
    def completed_umap_count(self, count: int):
        self._completed_umap_count = count
        
    @loaded_umap_data.setter
    def loaded_umap_data(self, data):
        self._loaded_umap_data = data