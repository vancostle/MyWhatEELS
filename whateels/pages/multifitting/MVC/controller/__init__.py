import param
from typing import TYPE_CHECKING
import panel as pn

if TYPE_CHECKING:
    from ..model import Model
    from ..view import View

class Controller(param.Parameterized):
    """
    Controller for the multifitting page.
    Coordinates between Model and View for multifitting display.
    """
    
    def __init__(self, model: "Model", view: "View") -> None:
        super().__init__()
        self._model = model
        self._view = view
        
        values = pn.state.location.query_params['values'] if 'values' in pn.state.location.query_params else None
        if values:
            values = tuple(map(float, values.split(","))) # Convert to tuple of floats
            print(f"Multifitting page opened with params: {values}")

        # Setup the reactive display in the view's container
        self._setup_reactive_display()
    
    def _setup_reactive_display(self):
        """Setup the reactive display component in the view's main container."""
        main_container = self._view.get_main_container()
        if main_container is not None:
            main_container.clear()
            main_container.append(self.get_multifit_component)

    @param.depends("_model._app_state.multifit")
    def get_multifit_component(self):
        """Returns the multifitting component for display."""
        if not self._model.is_multifit_available():
            return self._view.create_no_multifit_component()
        # If multifit data is available, try to render it with the view's plot component,
        # otherwise just display a basic placeholder to avoid runtime errors.
        try:
            return self._view.create_plot_component(self._model.multifit)
        except Exception:
            return pn.pane.HTML("<p>Multifit data available.</p>", sizing_mode="stretch_both")
