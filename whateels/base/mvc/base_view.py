from whateels.helpers import LoadCSS
from panel.viewable import Viewable
from panel.pane import HTML
from panel import Column
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whateels.base.mvc.base_model import BaseModel
    
class BaseView:
    
    STRETCH_WIDTH = 'stretch_width'
    STRETCH_BOTH = 'stretch_both'
    STRETCH_HEIGHT = 'stretch_height'
    
    def __init__(self, model: "BaseModel", css_files: list[str] | None = None):
        self._model = model

        # Layout components
        self._main = None
        self._sidebar = None
        self._right_sidebar = None
        
        # Initialize placeholders
        self._loading_placeholder = None
        self._no_file_placeholder = None
        self._error_placeholder = None
        
        # Load any provided CSS files
        if css_files and len(css_files) > 0:
            LoadCSS(css_files)
            
        self._initialize_placeholders(model)

    @property
    def main(self) -> Viewable:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def sidebar(self) -> Viewable:
        """Sidebar layout for displaying info and controls."""
        return self._sidebar
    @property
    def right_sidebar(self) -> Viewable:
        """Right sidebar layout for additional controls or info."""
        return self._right_sidebar
    @property
    def loading_placeholder(self) -> HTML:
        """HTML placeholder shown while a file is being processed."""
        return self._loading_placeholder
    @property
    def no_file_placeholder(self) -> HTML:
        """HTML placeholder shown when no file is loaded."""
        return self._no_file_placeholder
    @property
    def error_placeholder(self) -> HTML:
        """HTML placeholder shown when an error occurs."""
        return self._error_placeholder
    
    @main.setter
    def main(self, value: Viewable):
        self._main = value
    @sidebar.setter
    def sidebar(self, value: Viewable):
        self._sidebar = value
    @right_sidebar.setter
    def right_sidebar(self, value: Viewable):
        self._right_sidebar = value
        
    @main.deleter
    def main(self):
        self._main.clear()
    @sidebar.deleter
    def sidebar(self):
        self._sidebar.clear()
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar.clear()
        
    def _initialize_placeholders(self, model: "BaseModel"):
        self._no_file_placeholder = HTML(
            model.placeholders.NO_FILE_LOADED,
            sizing_mode=self.STRETCH_BOTH
        )
        self._loading_placeholder = Column(
            HTML(
                model.placeholders.LOADING_FILE,
                sizing_mode=self.STRETCH_BOTH
            ),
            sizing_mode=self.STRETCH_BOTH,
        )
        self._error_placeholder = HTML(
            model.placeholders.ERROR_FILE,
            sizing_mode=self.STRETCH_BOTH
        )