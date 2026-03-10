import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import QuantificationModel

class QuantificationMainLayout(pn.Column):
    """Legacy standalone main-layout container kept for compatibility."""
    
    _STRETCH_BOTH = "stretch_both"
    
    def __init__(self, model: "QuantificationModel") -> None:
        """Initialize placeholder panes and create a no-file default layout."""
        
        # Initialize placeholders
        self._loading_placeholder = pn.pane.HTML(
            model.placeholders.LOADING_FILE,
            sizing_mode=self._STRETCH_BOTH
        )
        self._no_file_placeholder = pn.pane.HTML(
            model.placeholders.NO_FILE_LOADED,
            sizing_mode=self._STRETCH_BOTH
        )
        self._error_placeholder = pn.pane.HTML(
            model.placeholders.ERROR_FILE,
            sizing_mode=self._STRETCH_BOTH
        )
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_BOTH
        )
        
    def _create_layout(self) -> pn.Column:
        """Create the main layout container."""
        self._main_container_layout = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
        return self._main_container_layout