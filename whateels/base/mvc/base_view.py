from whateels.helpers import LoadCSS

import panel as pn

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
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def sidebar(self) -> pn.viewable.Viewable:
        """Sidebar layout for displaying dataset info and controls."""
        return self._sidebar
    @property
    def right_sidebar(self) -> pn.Column:
        """Right sidebar layout for additional controls or info."""
        return self._right_sidebar
    @property
    def error(self) -> pn.Column:
        """Error layout for displaying error messages."""
        return self._error
    
    @main.setter
    def main(self, value: pn.Column):
        self._main = value
    @sidebar.setter
    def sidebar(self, value: pn.viewable.Viewable):
        self._sidebar = value
    @right_sidebar.setter
    def right_sidebar(self, value: pn.Column):
        self._right_sidebar = value
    @error.setter
    def error(self, value: pn.Column):
        self._error = value
        
    @main.deleter
    def main(self):
        self._main = None
    @sidebar.deleter
    def sidebar(self):
        self._sidebar = None
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar = None
    @error.deleter
    def error(self):
        self._error = None