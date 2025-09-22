import param
from typing import TYPE_CHECKING
from whateels.helpers.json_sanitizer import sanitize_for_json, is_json_serializable

if TYPE_CHECKING:
    from ..model import Model
    from ..view import View

class Controller(param.Parameterized):
    """
    Controller for the metadata page.
    Coordinates between Model and View for metadata display.
    """
    
    def __init__(self, model: "Model", view: "View") -> None:
        super().__init__()
        self._model = model
        self._view = view
        
        # Setup the reactive display in the view's container
        self._setup_reactive_display()
    
    def _setup_reactive_display(self):
        """Setup the reactive display component in the view's main container."""
        main_container = self._view.get_main_container()
        if main_container is not None:
            # Clear the loading placeholder and add the reactive component
            main_container.clear()
            main_container.append(self.get_display_component)
    
    @param.depends("_model._app_state.metadata")
    def get_display_component(self):
        """Determines what component to display based on metadata state."""
        if not self._model.is_metadata_available():
            return self._view.create_no_metadata_component()
        
        try:
            sanitized_metadata = sanitize_for_json(self._model.metadata)
            
            if is_json_serializable(sanitized_metadata):
                return self._view.create_json_component(sanitized_metadata)
            else:
                raise ValueError("Sanitized metadata is not JSON serializable")
                
        except Exception as e:
            return self._view.create_error_component()
