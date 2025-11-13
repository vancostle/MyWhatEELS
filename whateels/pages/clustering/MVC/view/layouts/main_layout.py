import panel as pn

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import ClusteringModel

class ClusteringMainLayout(pn.Column):
    """Manages the main layout for the Clustering View."""
    
    _STRETCH_BOTH = 'stretch_both'

    def __init__(self, model: 'ClusteringModel'):
        self._model = model
        
        self._no_file_placeholder = None # Placeholder for no file loaded
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_BOTH
        )
        
    @property
    def no_file_placeholder(self) -> Optional[pn.Column]:
        """Placeholder layout shown when no file is loaded."""
        return self._no_file_placeholder
        
    def _create_layout(self) -> pn.Column:
        """Create the main layout structure."""
        self._no_file_placeholder = pn.Column(
            pn.pane.HTML(
                self._model.placeholders.NO_FILE_LOADED,
                sizing_mode=self._STRETCH_BOTH
            ),
            sizing_mode=self._STRETCH_BOTH,
        )

        return pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
        
    def empty(self):
        """Reset the main layout to the no-file placeholder."""
        self.clear()
        self.append(self._no_file_placeholder)

    def update(self, plot_component):
        """Update the main layout with a new plot component."""
        self.clear()
        self.append(plot_component)