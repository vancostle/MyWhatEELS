from whateels.state import CacheManager

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    from whateels.state import AppState

class Clustering2PageModel:

    def __init__(self):
        self._app_state = CacheManager.get_cached_app_state()
        self._selected_dataset : "Dataset"
        self._current_image_name: Optional[str] = None
        self._is_umap_computing = False
        self._was_umap_computing_canceled = False
        self._umap_data_dict = dict()
        self._completed_umap_count: int = 0
        self._extra_umap_params_key: str = "Extra UMAP Parameters"
        self._hdbscan_grid_params_key: str = "Configure grid for evaluation"
        self._svm_settings_key: str = "Configure SVM settings"
        self._svm_train_settings_key: str = "Configure Train SVM settings"
        self._loaded_umap_data = None
        self._hdbscan_last_result: dict = {}
        self._svm_model = None
        self._svm_last_result: dict = {}
        
    @property
    def app_state(self) -> "AppState":
        return self._app_state
    @property
    def selected_dataset(self) -> "Dataset":
        return self._selected_dataset
    @property
    def current_image_name(self) -> Optional[str]:
        return self._current_image_name
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
    def hdbscan_grid_params_key(self) -> str:
        return self._hdbscan_grid_params_key
    @property
    def svm_settings_key(self) -> str:
        return self._svm_settings_key
    @property
    def svm_train_settings_key(self) -> str:
        return self._svm_train_settings_key
    @property
    def loaded_umap_data(self):
        return self._loaded_umap_data
    @property
    def hdbscan_last_result(self) -> dict:
        return self._hdbscan_last_result
    @property
    def svm_model(self):
        return self._svm_model
    @property
    def svm_last_result(self) -> dict:
        return self._svm_last_result

    def is_preprocessed_data_available(self) -> bool:
        """Return True when Home has published preprocessed ElectronCount data."""
        return self._app_state.preprocessed_plot_dataset is not None

    def should_use_preprocessed_data(self, switch_value: bool) -> bool:
        """Return True when the UI switch is on and preprocessed data is available."""
        if not switch_value:
            return False
        return self.is_preprocessed_data_available()

    @selected_dataset.setter
    def selected_dataset(self, dataset: "Dataset"):
        self._selected_dataset = dataset

    @current_image_name.setter
    def current_image_name(self, name: Optional[str]):
        self._current_image_name = name
        
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

    @hdbscan_last_result.setter
    def hdbscan_last_result(self, result: dict):
        self._hdbscan_last_result = result

    @svm_model.setter
    def svm_model(self, model):
        self._svm_model = model

    @svm_last_result.setter
    def svm_last_result(self, result: dict):
        self._svm_last_result = result
