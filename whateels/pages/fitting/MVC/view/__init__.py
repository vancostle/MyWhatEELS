import panel as pn

from whateels.helpers import CSS_ROOT
from whateels.components import UploadedFile, ToggleButton, SimpleDetails
from whateels.base.mvc import BaseView
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ..model import FittingModel
    from ..controller import FittingController

class FittingView(BaseView):
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    # --- Initialization ---
    def __init__(self, model: "FittingModel"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "quantification.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )

        self._model = model
        self._controller: Optional["NllsController"] = None

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._fitting_add_compontent_button = None
        self._quanti_element_item = None
        
        # self._main_layout = NllsMainLayout(model)
        # self._left_sidebar_layout = QuanficationLeftSidebarLayout(model)
        # self._right_sidebar_layout = NllsRightSidebarLayout(model)

        self._init_components()
    
    def set_controller(self, controller: "FittingController"):
        """Set the controller for this view."""
        self._controller = controller

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def component_input(self):
        """Access the K-Means input widgets."""
        return self._component_model_input
    @property
    def fitting_add_component_button(self):
        """Access the K-Means 'Add Element' button."""
        return self._fitting_add_compontent_button

    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component

    def _init_components(self):
        self.left_sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        self.right_sidebar = self._right_sidebar_layout()

    def _left_sidebar_layout(self):
        
        uploaded_file = UploadedFile(
            filename=str(self._model.get_uploaded_filename()), 
            sizing_mode=self._STRETCH_WIDTH, 
            margin=(0,0,10,0)
        )
 
        left_sidebar_container_layout = pn.Column(
            uploaded_file,
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
    
    def _right_sidebar_layout(self) -> pn.Column:
        self._component_model_input = {
            "energy_center": pn.widgets.IntInput(
                name='Energy Center',
                sizing_mode=self.STRETCH_WIDTH,
                value=1,
                start=1,
                end=10000,
                margin=(0,0,10,0),
            ),
            "model_select": pn.widgets.Select(
                name="Select Model", 
                options=["GaussianModel",
                        "LorentzianModel",
                        "PseudoVoigtModel",
                        "SplitLorentzianModel"
                        ],
                sizing_mode=self.STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
        }

        self._fitting_add_compontent_button = pn.widgets.Button(
            name='Add Component',
            button_type='primary',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )

        self._quanti_element_item = pn.Column(
            *[widget for widget in self._component_model_input.values()],
            sizing_mode=self.STRETCH_WIDTH
        )
        
        details = SimpleDetails(
            title="Nlls Instructions",
            content=pn.Column(
                *[widget for widget in self._component_model_input.values()],
                self._fitting_add_compontent_button,
                sizing_mode=self._STRETCH_WIDTH
            ),
            expanded=True,
            button_type_on_collapse='primary',
            button_type_on_expand='success',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0,0,10,0)
        )

        self.config_button = pn.widgets.Button(
            name = 'Configure Model',
            button_type='primary',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        self.model_button = pn.widgets.Button(
            name = 'View Model Summary',
            button_type='primary',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        right_sidebar = pn.Column(
            details,
            self.config_button,
            self.model_button,
            sizing_mode=self.STRETCH_BOTH,
        )
        return right_sidebar