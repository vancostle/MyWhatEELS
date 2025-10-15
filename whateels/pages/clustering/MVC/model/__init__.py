from whateels.base.mvc import BaseModel
from whateels.shared_state import AppState
from .constants import Constants
import numpy as np
from typing import Optional

class ClusteringModel(BaseModel):
    def __init__(self):
        super().__init__()

        self._constants = Constants()
        self._app_state = AppState()
        
    @property
    def constants(self):
        return self._constants
    
    # --- Multifit Data Access Methods ---
    
    def is_multifit_available(self) -> bool:
        """
        Check if multifit data is available in the application state.
        
        Returns:
            bool: True if multifit data exists, False otherwise
        """
        return self._app_state.multifit is not None
    
    def get_multifit_data(self) -> Optional[np.ndarray]:
        """
        Retrieve background-subtracted data from multifit results.
        
        The multifit results stored in AppState should be an xarray Dataset
        with the same structure as the original data (ElectronCount variable
        with coordinates x, y, Eloss) but with background subtracted.
        
        Returns:
            Optional[np.ndarray]: 3D array (y, x, energy) with background-subtracted data,
                                 or None if data cannot be retrieved
        """
        try:
            multifit_dataset = self._app_state.multifit
            
            if multifit_dataset is None:
                return None
            
            # Extract ElectronCount data from the multifit dataset
            # The multifit should have the same structure as original dataset
            if hasattr(multifit_dataset, 'ElectronCount'):
                multifit_data = multifit_dataset.ElectronCount
                data_cube = np.asarray(multifit_data.fillna(0.0))
                return data_cube
            elif isinstance(multifit_dataset, np.ndarray):
                # If multifit is already a numpy array
                return multifit_dataset
            else:
                return None
                
        except Exception as e:
            print(f"Error retrieving multifit data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def should_use_background_subtraction(self, switch_value: bool) -> bool:
        """
        Determine if background-subtracted data should be used for clustering.
        
        Args:
            switch_value: Current value of the background-subtraction switch
        
        Returns:
            bool: True if multifit data should be used (switch is ON and data available),
                  False otherwise
        """
        if not switch_value:
            return False
        
        if not self.is_multifit_available():
            return False
        
        return True