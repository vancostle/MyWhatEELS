import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base_model import BaseModel

class BaseView:
    def __init__(self, base_model: "BaseModel"):
        self._base_model = base_model

        self._main = None  # Main content area
        self._sidebar = None  # Sidebar layout
        self._right_sidebar = None  # Right sidebar layout
        self._error = None  # Error layout

    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def sidebar(self) -> pn.Column:
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
    def sidebar(self, value: pn.Column):
        self._sidebar = value
    @right_sidebar.setter
    def right_sidebar(self, value: pn.Column):
        self._right_sidebar = value
    @error.setter
    def error(self, value: pn.Column):
        self._error = value
        
    @main.deleter
    def main(self):
        self._main.clear()
        self._main = None
    @sidebar.deleter
    def sidebar(self):
        self._sidebar.clear()
        self._sidebar = None
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar.clear()
        self._right_sidebar = None
    @error.deleter
    def error(self):
        self._error.clear()
        self._error = None