
import copy, panel as pn
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xarray import Dataset
    
class UMAP_HDBSCAN:
    
    def __init__(self, data : "Dataset"):
        # Set notification position
        pn.state.notifications.position = 'bottom_left' # type: ignore
        
        self._data = copy.deepcopy(data) # Deep copy to avoid modifying original data
        self._eloss = self._data.coords["Eloss"].values
    
    def cut_signal(self, min_eloss, max_eloss):
        """Cuts the signal range based on min and max eloss values."""
        self._data = self._data.sel(Eloss=slice(min_eloss, max_eloss)) # Overwrite data with cut signal range
        self._eloss = self._data.coords["Eloss"].values # Update eloss values accordingly
        
        # Show success notification
        pn.state.notifications.success( # type: ignore
            f"Signal cut to Eloss range: {min_eloss} - {max_eloss}",
            duration=3000,
        )