from typing import TYPE_CHECKING
import panel as pn

if TYPE_CHECKING:
    from ..model import Model

class View:
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    # --- Initialization ---
    def __init__(self, model: "Model"):
        self._model = model
        
        self._main_container_layout = None
        self._sidebar_container_layout = None
        
        self._init_visualization_components()

    # --- Properties ---

    @property
    def sidebar(self) -> pn.viewable.Viewable:
        """Sidebar layout containing the file dropper and additional controls."""
        return self._sidebar_container_layout


    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main_container_layout


    @property
    def error_placeholder(self) -> pn.pane.HTML:
        """HTML placeholder shown when an error occurs."""
        return self._error_placeholder
    

    @property
    def dataset_info(self) -> pn.viewable.Viewable:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout


    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable or None)."""
        if component is not None and not isinstance(component, pn.viewable.Viewable):
            raise ValueError("Component must be a Panel Viewable")
        self._dataset_info_layout = component

    # --- Private/Internal Setup Methods ---

    def _init_visualization_components(self):
        self._sidebar_container_layout = self._sidebar_layout()
        self._main_container_layout = self._main_layout()

    def _sidebar_layout(self):
 
        self._sidebar_container_layout = pn.Column(
            pn.pane.Markdown("### Upload EELS Data", sizing_mode=self._STRETCH_WIDTH),
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return self._sidebar_container_layout

    def _main_layout(self):
        self._main_container_layout = pn.Column(
            pn.pane.Markdown("### Clustering Analysis", sizing_mode=self._STRETCH_WIDTH),
            sizing_mode=self._STRETCH_BOTH
        )
        return self._main_container_layout