from typing import TYPE_CHECKING
from panel.viewable import Viewable

if TYPE_CHECKING:
    from whateels.base.mvc.base_view import BaseView
    from whateels.base.mvc.base_model import BaseModel
    from whateels.base.mvc.base_controller import BaseController
    
class BaseController:
    def __init__(self, model: "BaseModel", view: "BaseView"):
        self._view = view
        self._model = model
        
        self._base_layout = _BaseLayoutManager(
            model, 
            view, 
            controller=self
        )
        
    @property
    def model(self) -> "BaseModel":
        return self._model
    @property
    def view(self) -> "BaseView":
        return self._view
    @property
    def base_layout(self) -> "_BaseLayoutManager":
        return self._base_layout
    

class _BaseLayoutManager:

    def __init__(self,  model: "BaseModel", view: "BaseView", controller: "BaseController"):
        self._view = view
        self._controller = controller
        self._model = model
            
    def loading_main(self):
        """Show the loading placeholder in the main layout."""
        del self._view.main
        self._view.main.append(self._view.loading_placeholder)
        
    def empty_main(self):
        """Reset the main layout to the no-file placeholder."""
        del self._view.main
        self._view.main.append(self._view.no_file_placeholder)

    def update_main(self, plot_component):
        """Update the main layout with a new plot component."""
        del self._view.main
        self._view.main.append(plot_component)
        
    def error_main(self):
        """Show the error placeholder in the main layout."""
        del self._view.main
        self._view.main.append(self._view.error_placeholder)