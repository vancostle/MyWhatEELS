"""Demo View - View class for demo page."""

from .main_layout import DemoMainLayout
from .right_sidebar_layout import DemoRightSidebarLayout
from whateels.helpers import CSS_ROOT, LoadCSS
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import DemoModel


class DemoView:
    """View for demo progress display page."""
    
    def __init__(self, model: "DemoModel"):
        """Initialize demo view."""
        self._model = model
        
        # Load CSS
        css_files = [str(CSS_ROOT / "home.css")]
        LoadCSS(css_files)
        
        # Create layouts
        self._main = DemoMainLayout()
        self._right_sidebar = DemoRightSidebarLayout()
    
    @property
    def main(self) -> DemoMainLayout:
        """Main content layout."""
        return self._main
    
    @property
    def right_sidebar(self) -> DemoRightSidebarLayout:
        """Right sidebar layout."""
        return self._right_sidebar
