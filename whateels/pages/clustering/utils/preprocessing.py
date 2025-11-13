"""
Data preprocessing utilities for clustering.

OOP-based preprocessing and normalization for data before clustering,
including multifit data retrieval for background subtraction.
"""

from typing import TYPE_CHECKING, Literal
from sklearn.preprocessing import normalize

if TYPE_CHECKING:
    from numpy import ndarray
    from ..MVC.model import ClusteringModel

class DataPreprocessor:
    """
    Handles data preprocessing and normalization for clustering.
    
    Provides methods for:
    - Data validation and reshaping
    - Normalization (l1, l2, max, or none)
    - Background-subtracted data retrieval
    """
    
    # Allowed normalization methods
    ALLOWED_NORMS = ('l1', 'l2', 'max', 'none')
    
    def __init__(self, allowed_norms: tuple[str, ...] = ALLOWED_NORMS):
        """
        Initialize the preprocessor.
        
        Args:
            allowed_norms: Tuple of allowed normalization methods
        """
        self.allowed_norms = allowed_norms
    
    def prepare_matrix(
        self,
        matrix: "ndarray",
        norm: Literal['l1', 'l2', 'max', 'none']
    ) -> tuple["ndarray", "ndarray"]:
        """
        Validate, reshape and optionally normalize the input 3D matrix.
        
        Args:
            matrix: Original 3D spectrum image data (x, y, eloss)
            norm: Normalization to apply ('l1', 'l2', 'max', 'none')
        
        Returns:
            Tuple of (matrix_norm, sclust_norm):
            - matrix_norm: Reshaped copy of original data (n_pixels, n_energy)
            - sclust_norm: Array to feed into clustering (normalized or raw)
        
        Raises:
            ValueError: If norm is not in allowed_norms
        """
        if norm not in self.allowed_norms:
            raise ValueError(f"norm must be one of {self.allowed_norms}, got '{norm}'")
        
        # Reshape from (x, y, eloss) to (n_pixels, n_energy)
        matrix_norm = matrix.copy()
        matrix_norm = matrix_norm.reshape(matrix.shape[0] * matrix.shape[1], matrix.shape[-1])
        
        # Apply normalization if requested
        if isinstance(norm, str) and norm.lower() == 'none':
            sclust_norm = matrix_norm
        else:
            sclust_norm = normalize(matrix_norm, norm=norm, axis=1, copy=True)  # type: ignore
        
        return matrix_norm, sclust_norm
    
    @staticmethod
    def should_use_multifit_data(model: "ClusteringModel", switch_value: bool) -> bool:
        """
        Check if multifit data should be used for clustering.
        
        Delegates to the model to determine if background-subtracted data
        should be used based on switch state and data availability.
        
        Args:
            model: The clustering model instance
            switch_value: Current state of the background subtraction switch
        
        Returns:
            True if multifit data should be used, False otherwise
        """
        try:
            return model.should_use_background_subtraction(switch_value)
        except Exception as e:
            print(f"Error checking if multifit should be used: {e}")
            return False
    
    @staticmethod
    def get_multifit_data(model: "ClusteringModel") -> "ndarray | None":
        """
        Retrieve background-subtracted data from the model.
        
        Args:
            model: The clustering model instance
        
        Returns:
            3D array (y, x, energy) with background-subtracted data,
            or None if data cannot be retrieved
        """
        try:
            data_cube = model.get_multifit_data()
            
            if data_cube is not None:
                print(f"Using multifit data for clustering, shape: {data_cube.shape}")
            
            return data_cube
                
        except Exception as e:
            print(f"Error retrieving multifit data from model: {e}")
            import traceback
            traceback.print_exc()
            return None
