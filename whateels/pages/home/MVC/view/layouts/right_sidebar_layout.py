import panel as pn

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """
    
    def __init__(self, model):
        self._model = model
        
        self._remove_spikes_checkbox = pn.widgets.Checkbox(name="Remove Spikes", value=False)
        
        super().__init__(
            pn.Column(

            ),
            sizing_mode='stretch_width',
        )
        
    @property
    def remove_spikes_checkbox(self) -> pn.widgets.Checkbox:
        """Checkbox widget for toggling spike removal in spectrum image plots."""
        return self._remove_spikes_checkbox