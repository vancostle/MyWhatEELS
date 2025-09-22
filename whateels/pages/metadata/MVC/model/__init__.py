from whateels.shared_state import AppState

class Model:
    """
    Model for the metadata page.
    Handles data and business logic for metadata information.
    """
    
    def __init__(self):
        self._app_state = AppState()
    
    def is_metadata_available(self) -> bool:
        """Check if metadata is available."""
        return self._app_state.metadata is not None
    
    @property
    def metadata(self):
        """Get raw metadata."""
        return self._app_state.metadata

    @property
    def constants(self) -> "Constants":
        """Expose constants for the metadata page."""
        return self.Constants()

    class Constants:
        TITLE = "Eels Metadata Details"
        HEADER_BACKGROUND = "#0066cc"
