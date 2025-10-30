import param
from typing import TYPE_CHECKING
import panel as pn

from whateels.shared_state import AppState

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

        # Parse fit_range from URL query parameters
        fit_range = None
        if pn.state.location and getattr(pn.state.location, 'query_params', None):
            fit_range = pn.state.location.query_params.get('values', None)
        if fit_range:
            fit_range = tuple(map(float, fit_range.split(",")))
            if hasattr(self._model, 'set_fit_range') and callable(getattr(self._model, 'set_fit_range', None)):
                self._model.set_fit_range(fit_range)
            else:
                self._model.set_fit_range = fit_range  # fallback for legacy code

        # Mount the multifit component into the view's container
        main_container = self._view.get_main_container()
        
        if main_container is None:
            return
        
        main_container.clear()
        
        # Spinner indicator while loading
        spinner = self._view.loader_spinner
        main_container.append(spinner)

        # Call the loading spinner display function
        pn.state.onload(lambda : self._display_loading_spinner(fit_range=fit_range, main_container=main_container))

    def _display_loading_spinner(self, fit_range=None, main_container=None):
        if fit_range:
            component = self.plot_multifit()
        else:
            try:
                component = self.get_dataset_component()
            except Exception:
                component = pn.pane.HTML(
                    "<p>Error rendering multifit component.</p>", 
                    sizing_mode="stretch_both"
                )

        main_container.clear()
        main_container.append(component)

    def collect_dataset(self):
        """
        Collect the xarray Dataset and perform multifitting.

        Returns the background-subtracted dataset or None if not found.
        """
        try:
            ds = AppState().plot_dataset
            if ds is not None:
                self.ds = ds
                multifit_data = self._model.perform_multifit(ds, fit_range=self._model.set_fit_range)
                return multifit_data
        except Exception:
            pass
        return None
    
    def plot_multifit(self):
        """Create and return the multifit plot component."""
        ds = self.collect_dataset()
        data = self._view.create_plot_component(ds)
        return data
      
    @param.depends("_model._app_state.metadata")
    def get_dataset_component(self):
        """Return a simple component describing the dataset available to multifit.

        This is non-reactive helper retained for compatibility with callers that
        expect a Panel component. It retrieves the dataset via `collect_dataset()`
        and returns a simple HTML pane or the view's "no multifit" component.
        """
        ds = self.collect_dataset()
        if ds is None:
            # Prefer a view-provided fallback if available
            if hasattr(self._view, 'create_no_multifit_component'):
                return self._view.create_no_multifit_component()
            return pn.pane.HTML("<p>No dataset available for multifitting :c .</p>", sizing_mode="stretch_both")
        # Return a small informative pane (avoid dumping the full dataset)
        try:
            display = f"<p>Dataset available: {ds}</p>"
            return pn.pane.HTML(display, sizing_mode="stretch_both")
        except Exception:
            return pn.pane.HTML("<p>Dataset available.</p>", sizing_mode="stretch_both")