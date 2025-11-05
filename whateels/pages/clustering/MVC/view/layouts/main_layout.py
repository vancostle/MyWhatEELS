import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....MVC import ClusteringView, ClusteringModel

class ClusteringMainLayout(pn.Column):
    """Manages the main layout for the Clustering View."""
    
    _STRETCH_BOTH = 'stretch_both'

    def __init__(self, model: 'ClusteringModel'):
        self._model = model
        
        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_BOTH
        )
        
    def _create_layout(self) -> pn.Column:
        """Create the main layout structure."""
        no_file_placeholder = pn.Column(
            pn.pane.HTML(
                self._model.placeholders.NO_FILE_LOADED,
                sizing_mode=self._STRETCH_BOTH
            ),
            sizing_mode=self._STRETCH_BOTH,
        )

        return pn.Column(
            no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )