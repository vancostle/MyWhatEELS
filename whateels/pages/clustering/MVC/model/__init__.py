from whateels.base.mvc import BaseModel
from .constants import Constants

class ClusteringModel(BaseModel):
    def __init__(self):
        super().__init__()

        self._constants = Constants()
        
    @property
    def constants(self):
        return self._constants