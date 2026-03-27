import panel as pn

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """


    def __init__(self, model, **kwargs):
        self._model = model

        self._fitting_details_placeholder = pn.Column(sizing_mode='stretch_both')

        super().__init__(
            self._fitting_details_placeholder,
            **kwargs
        )

    def set_fitting_details(self, details) -> None:
        """Replace the fitting section with the SimpleDetails provided by the active plot."""
        self._fitting_details_placeholder.clear()
        if details is not None:
            self._fitting_details_placeholder.append(details)
