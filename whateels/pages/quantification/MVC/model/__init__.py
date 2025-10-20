from whateels.base.mvc import BaseModel
from whateels.shared_state import AppState
from .constants import Constants

class QuantificationModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._constants = Constants()
        self._app_state = AppState()


    @property
    def constants(self) -> Constants:
        return self._constants