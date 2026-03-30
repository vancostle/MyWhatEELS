import panel as pn
from whateels.components import ToggleButton

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """

    def __init__(self, model, **kwargs):
        self._model = model

        self._fitting_details_placeholder = pn.Column(sizing_mode='stretch_both', margin=(0, 0, 8, 0))
        self._remove_spikes_details_placeholder = pn.Column(sizing_mode='stretch_both')
        
        self._apply_active_preprocessors_toggle_button = ToggleButton(
            initial_state=False,
            states={
                "on": {"label": 'Display Raw Data', "on_click": (lambda: print("On clicked")), "button_type": 'warning'},
                "off": {"label": 'Apply Active Preprocessors', "on_click": (lambda: print("Off clicked")), "button_type": 'success'}
            },
            sizing_mode='stretch_width',
            margin=(8, 0, 0, 0),
        )

        super().__init__(
            self._fitting_details_placeholder,
            self._remove_spikes_details_placeholder,
            self._apply_active_preprocessors_toggle_button,
            **kwargs
        )

    def set_fitting_details(self, details) -> None:
        """Replace the fitting section with the SimpleDetails provided by the active plot."""
        self._fitting_details_placeholder.clear()
        if details is not None:
            self._fitting_details_placeholder.append(details)
    
    def set_remove_spikes_details(self, details) -> None:
        """Replace the remove spikes section with the SimpleDetails provided by the active plot."""
        self._remove_spikes_details_placeholder.clear()
        if details is not None:
            self._remove_spikes_details_placeholder.append(details)
