from typing import TYPE_CHECKING, Optional
from whateels.helpers import HTML_ROOT, CSS_ROOT
from whateels.components import UploadedFile, ToggleButton
from whateels.base.mvc import BaseView
from whateels.shared_state import AppState

import panel as pn

if TYPE_CHECKING:
    from ..model import QuantificationModel

class QuantificationView(BaseView):
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    # --- Initialization ---
    def __init__(self, model: "QuantificationModel"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "clustering.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )

        self._model = model

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._init_components()

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout

    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component

    def _init_components(self):
        self.left_sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        self.right_sidebar = self._right_sidebar_layout()

    def _left_sidebar_layout(self):
 
        left_sidebar_container_layout = pn.Column(
            pn.pane.Markdown("### Upload EELS Data", sizing_mode=self._STRETCH_WIDTH),
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return left_sidebar_container_layout


    def _main_layout(self):
        
        self._main_container_layout = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )

        return self._main_container_layout
    
    def _right_sidebar_layout(self):
        quantification_input_label = pn.pane.Markdown(
            "### Quantification Input", 
        )

        self._quantification_input = {
            "element_num": pn.widgets.IntInput(
                name='Element Numbering Scheme',
                sizing_mode=self.STRETCH_WIDTH
            ),
            "shells_multiselect": pn.widgets.MultiChoice(
                name="Shells", 
                options=[],
                sizing_mode=self.STRETCH_WIDTH
            ),
        }

        self._quanti_add_element_button = pn.widgets.Button(
            name='Add Element',
            button_type='primary',
            height=55,
            margin=(0,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        _quanti_element_item = pn.Column(
            self._quantification_input["element_num"],
            self._quantification_input["shells_multiselect"],
            sizing_mode=self.STRETCH_WIDTH
        )
        
        self._quanti_run_button = pn.widgets.Button(
            name='Run Quantification',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        right_sidebar = pn.Column(
            quantification_input_label,
            _quanti_element_item,
            sizing_mode=self.STRETCH_BOTH
        )
        return right_sidebar
    