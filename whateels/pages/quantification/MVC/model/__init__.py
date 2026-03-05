from whateels.base.mvc import BaseModel
from whateels.state import CacheManager
from .constants import Constants
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.state import AppState

class QuantificationModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._constants = Constants()
        self._app_state = CacheManager.get_cached_app_state()

    @property
    def constants(self) -> Constants:
        return self._constants
    
    @property
    def app_state(self) -> "AppState":
        return self._app_state

    def get_uploaded_filename(self) -> str:
        """
        Get the filename of the currently uploaded dataset from shared state.
        
        Returns:
            str: Uploaded filename, or empty string if none
        """
        return str(self.app_state.filename) if self.app_state.filename is not None else "No file uploaded"