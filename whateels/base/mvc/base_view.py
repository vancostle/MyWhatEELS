from whateels.helpers import LoadCSS
from panel.viewable import Viewable
from panel import Column
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
        
        # Load any provided CSS files
        if css_files and len(css_files) > 0:
            LoadCSS(css_files)

        # Initialize placeholders
        self._loading_placeholder = Column(
            HTML(
                model.placeholders.LOADING_FILE,
                sizing_mode=self.STRETCH_BOTH
            ),
            sizing_mode=self.STRETCH_BOTH,
        )
        self._no_file_placeholder = Column(
            HTML(
                model.placeholders.NO_FILE_LOADED,
                sizing_mode=self.STRETCH_BOTH
            ),
            sizing_mode=self.STRETCH_BOTH,
        )
        self._error_placeholder = Column(
            HTML(
                model.placeholders.ERROR_FILE,
                sizing_mode=self.STRETCH_BOTH
            ),
            sizing_mode=self.STRETCH_BOTH,
        )

        # Layout components
        self._main = Column(
            self._no_file_placeholder,
            sizing_mode=self.STRETCH_BOTH
        )
        self._left_sidebar = Column(sizing_mode=self.STRETCH_WIDTH)
        self._right_sidebar = Column(sizing_mode=self.STRETCH_WIDTH)

    @property
    def main(self) -> Viewable:
        """Main content area layout for displaying plots or placeholders."""
        return self._main
    @property
    def left_sidebar(self) -> Viewable:
        """Left sidebar layout for displaying info and controls."""
        return self._left_sidebar
    @property
    def right_sidebar(self) -> Viewable:
        """Right sidebar layout for additional controls or info."""
        return self._right_sidebar
    @property
    def loading_placeholder(self) -> Viewable:
        """HTML placeholder shown while a file is being processed."""
        return self._loading_placeholder
    @property
    def no_file_placeholder(self) -> Viewable:
        """HTML placeholder shown when no file is loaded."""
        return self._no_file_placeholder
    @property
    def error_placeholder(self) -> Viewable:
        """HTML placeholder shown when an error occurs."""
        return self._error_placeholder
    
    @main.setter
    def main(self, value: Column):
        self._main = value
    @left_sidebar.setter
    def left_sidebar(self, value: Column):
        self._left_sidebar = value
    @right_sidebar.setter
    def right_sidebar(self, value: Column):
        self._right_sidebar = value
        
    @main.deleter
    def main(self):
        self._main.clear()
    @left_sidebar.deleter
    def left_sidebar(self):
        self._left_sidebar.clear()
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar.clear()