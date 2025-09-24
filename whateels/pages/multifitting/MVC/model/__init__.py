from whateels.shared_state import AppState

class Model:
    """
    Model for the metadata page.
    Handles data and business logic for metadata information.
    """
    
    def __init__(self):
        self._app_state = AppState()
    
    def is_multifit_available(self) -> bool:
        """Check if multifit is available."""
        return self._app_state.multifit is not None

    @property
    def multifit(self):
        """Get raw multifit data."""
        return self._app_state.multifit

    @property
    def constants(self) -> "Constants":
        """Expose constants for the multifitting page."""
        return self.Constants()

    class Constants:
        TITLE = "Multifitting for the Spectral Data"
        HEADER_BACKGROUND = "#0066cc"
