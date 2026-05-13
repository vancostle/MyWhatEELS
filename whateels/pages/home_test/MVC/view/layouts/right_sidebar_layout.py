import panel as pn

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """

    def __init__(self, model, **kwargs):
        self._model = model

        self._preprocessed_settings = pn.Column(sizing_mode='stretch_both', margin=0)
        super().__init__(
            self._preprocessed_settings,
            **kwargs
        )
        
    @property
    def preprocessed_settings(self):
        """Access the preprocessed settings layout for adding components."""
        return self._preprocessed_settings