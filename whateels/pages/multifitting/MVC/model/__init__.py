from whateels.shared_state import AppState
from whateels.helpers.fitting.multifitting import MultiFit
import numpy as np

class Model:
    """
    Model for the multifitting page.
    Handles data and business logic for multifitting and metadata information.
    """
    set_fit_range = None
    
    # Default background model for fitting from lmfit.models
    BACKGROUND_MODEL = 'PowerLawModel'
    
    def __init__(self):
        self._app_state = AppState()

    def is_dataset_available(self) -> bool:
        """Check if dataset is available."""
        return self._app_state.plot_dataset is not None

    @property
    def dataset(self):
        """Get raw dataset."""
        return self._app_state.plot_dataset

    def is_multifit_available(self) -> bool:
        """Check if multifit is available."""
        return self._app_state.multifit is not None

    @property
    def multifit(self):
        """Get raw multifit data."""
        return self._app_state.multifit
    
    def perform_multifit(self, dataset, fit_range=None):
        """Perform multifit on the dataset within the specified fit range.

        Expects an xarray Dataset with coords including self.constants.ELOSS and
        variable self.constants.ELECTRON_COUNT as a 3D cube (y,x,E).
        
        Returns an xarray.Dataset with the same structure as input, where
        ElectronCount contains the background-subtracted data (original - fit).
        """
        import lmfit
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
        return self.Constants()

    class Constants:
        TITLE = "Multifitting for the Spectral Data"
        HEADER_BACKGROUND = "#0066cc"
        # Coordinate and data variable names expected by visualizers
        ELOSS = 'Eloss'
        ELECTRON_COUNT = 'ElectronCount'
