import param
from typing import TYPE_CHECKING
import panel as pn

if TYPE_CHECKING:
    from ..model import MultifittingModel
    from ..view import MultifittingView

class MultifittingController(param.Parameterized):
    """
    Controller for the multifitting page.
    Coordinates between Model and View for multifitting display.
    """
    
    def __init__(self, model: "MultifittingModel", view: "MultifittingView") -> None:
        super().__init__()
        self._model = model
        self._view = view

        # Parse fit_range from URL query parameters
        fit_range = None
        if pn.state.location and getattr(pn.state.location, 'query_params', None):
            fit_range = pn.state.location.query_params.get('values', None)
        if fit_range:
            fit_range = tuple(map(float, fit_range.split(",")))
            self._model.fit_range = fit_range  # fallback for legacy code

        # Mount the multifit component into the view's container
        self._main_container = self._view.get_main_container()
        
        if self._main_container is None:
            return
        
        self._main_container.clear()
        
        # Spinner indicator while loading
        spinner = self._view.loader_spinner
        self._main_container.append(spinner)

        # Call the loading spinner display function
        pn.state.onload(lambda : self._display_loading_spinner(fit_range=fit_range))

    def _display_loading_spinner(self, fit_range=None):
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

        self._main_container.clear()
        self._main_container.append(component)

    def collect_dataset(self):
        """
        Collect the xarray Dataset and perform multifitting.

        Returns the background-subtracted dataset or None if not found.
        """
        try:
            ds = self._model.app_state.plot_dataset
            if ds is not None:
                self.ds = ds
                multifit_data = self._model.perform_multifit(ds, fit_range=self._model.fit_range)
                return multifit_data
        except Exception:
            pass
        return None
    
    def plot_multifit(self):
        """Create and return the multifit plot component."""
        ds = self.collect_dataset()
        data = self._view.create_plot_component(ds)
        return data
      
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