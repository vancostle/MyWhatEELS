import panel as pn

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """

    def __init__(self, model, **kwargs):
        self._model = model

        self._remove_spikes_details_placeholder = pn.Column(sizing_mode='stretch_both', margin=(0, 0, 8, 0))
        self._fitting_details_placeholder = pn.Column(sizing_mode='stretch_both', margin=(0, 0, 8, 0))
        super().__init__(
            self._remove_spikes_details_placeholder,
            self._fitting_details_placeholder,
            **kwargs
        )

    def set_fitting_details(self, details) -> None:
        """Replace the multifitting section with the SimpleDetails provided by the active plot."""
        self._fitting_details_placeholder.clear()
        if details is not None:
            self._fitting_details_placeholder.append(details)
    
    def set_remove_spikes_details(self, details) -> None:
        """Replace the remove spikes section with the SimpleDetails provided by the active plot."""
        self._remove_spikes_details_placeholder.clear()
        if details is not None:
            self._remove_spikes_details_placeholder.append(details)



