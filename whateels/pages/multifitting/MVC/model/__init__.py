from whateels.shared_state import get_cached_app_state
from whateels.helpers.fitting.multifitting import MultiFit
import numpy as np
import lmfit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.shared_state import AppState
    
class MultifittingModel:
    """
    Model for the multifitting page.
    Handles data and business logic for multifitting and metadata information.
    """

    # Default background model for fitting from lmfit.models
    BACKGROUND_MODEL = 'PowerLawModel'

    def __init__(self):
        self._app_state = get_cached_app_state()
        self._fit_range = None

    @property
    def app_state(self) -> "AppState":
        """Get the shared application state instance."""
        return self._app_state
    @property
    def dataset(self):
        """Get raw dataset."""
        return self._app_state.plot_dataset
    @property
    def multifit(self):
        """Get raw multifit data."""
        return self._app_state.multifit
    @property
    def fit_range(self):
        """Get the current fit range."""
        return self._fit_range
    
    @fit_range.setter
    def fit_range(self, value):
        """Set the fit range and trigger multifit update."""
        self._fit_range = value
    
    def is_multifit_available(self) -> bool:
        """Check if multifit is available."""
        return self._app_state.multifit is not None
    def is_dataset_available(self) -> bool:
        """Check if dataset is available."""
        return self._app_state.plot_dataset is not None
    def perform_multifit(self, dataset, fit_range=None):
        """Perform multifit on the dataset within the specified fit range.

        Expects an xarray Dataset with coords including self.constants.ELOSS and
        variable self.constants.ELECTRON_COUNT as a 3D cube (y,x,E).
        
        Returns an xarray.Dataset with the same structure as input, where
        ElectronCount contains the background-subtracted data (original - fit).
        """
        ModelClass = getattr(lmfit.models, self.BACKGROUND_MODEL, None)

        # Extract energy axis for fit_range
        try:
            eloss_name = self.constants.ELOSS
            e_axis = np.asarray(dataset.coords[eloss_name].values)
        except Exception as e:
            raise RuntimeError(f"Invalid dataset structure for multifit: {e}")

        # Pass the ENTIRE xarray Dataset to MultiFit so it preserves structure
        multifit = MultiFit(dataset, model=ModelClass, Eloss_x=e_axis, fit_range=fit_range)
        result = multifit.run(mode='subtracted')  # Background removal by default
        
        # Get the fitted dataset (xarray.Dataset with same structure as input)
        fitted_dataset = result.to_dataset()
        
        # Store fitted data array in app state for potential future use
        self._app_state.multifit = result.get_fitted_data()
        
        # Return the xarray.Dataset with background-subtracted data
        return fitted_dataset

    @property
    def constants(self) -> "Constants":
        """Expose constants for the multifitting page."""
        return Constants()

class Constants:
    TITLE = "Multifitting for the Spectral Data"
    HEADER_BACKGROUND = "#0066cc"
    # Coordinate and data variable names expected by visualizers
    ELOSS = 'Eloss'
    ELECTRON_COUNT = 'ElectronCount'
