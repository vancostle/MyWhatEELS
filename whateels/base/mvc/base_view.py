from whateels.helpers import LoadCSS
from panel.viewable import Viewable

class BaseView:
    
    STRETCH_WIDTH = 'stretch_width'
    STRETCH_BOTH = 'stretch_both'
    STRETCH_HEIGHT = 'stretch_height'
    
    def __init__(self, css_files: list[str] | None = None):
        self._main = None  # Main content area
        self._sidebar = None  # Sidebar layout
        self._right_sidebar = None  # Right sidebar layout
        self._error = None  # Error layout
        
        # Load any provided CSS files
        if css_files:
            LoadCSS(css_files)

    @property
    def main(self) -> Viewable:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def sidebar(self) -> Viewable:
        """Sidebar layout for displaying dataset info and controls."""
        return self._sidebar
    @property
    def right_sidebar(self) -> Viewable:
        """Right sidebar layout for additional controls or info."""
        return self._right_sidebar
    @property
    def error(self) -> Viewable:
        """Error layout for displaying error messages."""
        return self._error
    
    @main.setter
    def main(self, value: Viewable):
        self._main = value
    @sidebar.setter
    def sidebar(self, value: Viewable):
        self._sidebar = value
    @right_sidebar.setter
    def right_sidebar(self, value: Viewable):
        self._right_sidebar = value
    @error.setter
    def error(self, value: Viewable):
        self._error = value
        
    @main.deleter
    def main(self):
        self._main.clear()
    @sidebar.deleter
    def sidebar(self):
        self._sidebar.clear()
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar.clear()
    @error.deleter
    def error(self):
        self._error.clear()