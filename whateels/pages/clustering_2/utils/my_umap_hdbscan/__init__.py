
import copy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    
class UMAP_HDBSCAN:
    
    def __init__(self, data : "Dataset"):
        self._data = copy.deepcopy(data) # Deep copy to avoid modifying original data
        self._eloss = self._data.coords["Eloss"].values
    
    def cut_signal(self, min_eloss, max_eloss):
        """Cuts the signal range based on min and max eloss values."""
        self._data = self._data.sel(Eloss=slice(min_eloss, max_eloss)) # Overwrite data with cut signal range
        self._eloss = self._data.coords["Eloss"].values