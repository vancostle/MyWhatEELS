import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....MVC import HomePageModel

class HomePageMainLayout(pn.Column):
    """
    Manages the main layout for the Home Page View.
    """
    
    _STRETCH_BOTH = 'stretch_both'

    def __init__(self, model: 'HomePageModel'):
        self._model = model
        
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
        """Create the main layout structure."""

        return pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
    
    # Layout state management methods
    def empty_placeholder(self):
        """Reset the main layout to the no-file placeholder."""
        self.clear()
        self.append(self._no_file_placeholder)
    def error_placeholder(self):
        """Update the main layout to show the error placeholder."""
        self.clear()
        self.append(self._error_placeholder)
    def loading_placeholder(self):
        """Update the main layout to show the loading placeholder."""
        self.clear()
        self.append(self._loading_placeholder)
        
    def update(self, plot_component):
        """Update the main layout with a new plot component."""
        self.clear()
        self.append(plot_component)