import numpy as np

from whateels.pages import clustering
from whateels.shared_state import AppState
from .placeholders import Placeholders
from .constants import Constants
from typing import Optional

class ClusteringModel:
    def __init__(self):
        super().__init__()
        
        self._placeholders = Placeholders()
        self._constants = Constants()
        self._app_state = AppState()
        
        # Example structure for last clustering result
        self._last_clustering_result = {
            "clustering" : {
                "file" : None,
                "spectrum_image" : None,
                "type" : None,
                "inputs" : {
                    "n_clusters" : None,
                    "norm" : None,
                    "n_init" : None,
                    "max_iter" : None,
                    "init_method" : None,
                },
                "outputs" : {
                    "labels" : None,
                    "centres" : None,
                }
            }
        }
        
    @property
    def constants(self):
        return self._constants
    @property
    def placeholders(self) -> Placeholders:
        return self._placeholders
    @property
    def app_state(self) -> AppState:
        """
        Get the shared application state instance.
        
        Returns:
            AppState: The shared application state
        """
        return self._app_state
    @property
    def last_clustering_result(self) -> dict:
        return self._last_clustering_result
    
    @last_clustering_result.setter
    def last_clustering_result(self, result: dict):
        """
        Set the last clustering result with validation.
        
        Args:
            result: Dictionary containing clustering results
            
        Raises:
            ValueError: If required keys are missing from the result dictionary
        """
        # Validate top-level structure
        if "clustering" not in result:
            raise ValueError("Missing 'clustering' key in result dictionary")
        
        clustering = result["clustering"]
        
        # Validate required top-level clustering keys
        required_keys = ["file", "spectrum_image", "type", "inputs", "outputs"]
        missing_keys = [key for key in required_keys if key not in clustering]
        if missing_keys:
            raise ValueError(f"Missing required keys in 'clustering': {missing_keys}")
        
        # Validate inputs structure
        required_input_keys = ["n_clusters", "norm", "n_init", "max_iter", "init_method"]
        missing_input_keys = [key for key in required_input_keys if key not in clustering["inputs"]]
        if missing_input_keys:
            raise ValueError(f"Missing required keys in 'inputs': {missing_input_keys}")
        
        # Validate outputs structure
        required_output_keys = ["labels", "centres"]
        missing_output_keys = [key for key in required_output_keys if key not in clustering["outputs"]]
        if missing_output_keys:
            raise ValueError(f"Missing required keys in 'outputs': {missing_output_keys}")
        
        self._last_clustering_result = result

    def get_uploaded_filename(self) -> str:
        """
        Get the filename of the currently uploaded dataset from shared state.
        
        Returns:
            str: Uploaded filename, or empty string if none
        """
        return str(self.app_state.filename) if self.app_state.filename is not None else "No file uploaded"
    
    # --- Multifit Data Access Methods ---
    
    def is_multifit_available(self) -> bool:
        """
        Check if multifit data is available in the application state.
        
        Returns:
            bool: True if multifit data exists, False otherwise
        """
        return self.app_state.multifit is not None
    
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
            multifit_dataset = self.app_state.multifit
            
            if multifit_dataset is None:
                return None
            
            # Extract ElectronCount data from the multifit dataset
            # The multifit should have the same structure as original dataset
            if hasattr(multifit_dataset, 'ElectronCount'):
                multifit_data = getattr(multifit_dataset, 'ElectronCount', None)
                if multifit_data is not None:
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