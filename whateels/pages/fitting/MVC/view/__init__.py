import panel as pn

from whateels.helpers import CSS_ROOT
from whateels.components import UploadedFile, ToggleButton, SimpleDetails
from whateels.base.mvc import BaseView
from typing import TYPE_CHECKING, Optional

from whateels.shared_state import AppState
if TYPE_CHECKING:
    from ..model import FittingModel
    from ..controller import FittingController

class FittingView(BaseView):
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    ELEMENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD = 4
    COMPONENT_EAXIS_THRESHOLD_VALUE = 50

    # --- Initialization ---
    def __init__(self, model: "FittingModel"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "fitting.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )

        self._model = model
        self._controller: Optional["FittingController"] = None

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._fitting_add_compontent_button: Optional[pn.widgets.Button] = None
        self._component_model_input: dict[str, pn.widgets.Widget] = {}
        self._background_subtraction_switch: Optional[pn.widgets.Switch] = None
        
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
    def component_input(self) -> dict[str, pn.widgets.Widget]:
        """Access the K-Means input widgets."""
        return self._component_model_input
    @property
    def fitting_add_component_button(self) -> Optional[pn.widgets.Button]:
        """Access the K-Means 'Add Element' button."""
        return self._fitting_add_compontent_button
    
    @property
    def background_subtraction_switch(self) -> pn.widgets.Switch:
        """Access the background subtraction switch."""
        return self._background_subtraction_switch
    
    @property
    def energy_map_toggle_button(self) -> ToggleButton:
        """Access the energy map toggle button."""
        return self._energy_map_toggle_button
    
    @property
    def component_item_view_container(self) -> pn.Column:
        """Access the container for component item views."""
        return self._component_item_view_container


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

        

        background_subtraction_label = pn.pane.Markdown(
            "### Background-subtraction", 
        )

        self._background_subtraction_switch = pn.widgets.Switch(
            name="Background-subtraction", 
            value=False, 
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )

        is_multifitting_available = self._model.is_multifit_available()
        self._background_subtraction_switch.disabled = not is_multifitting_available

        subtraction_bg_tooltip = (
            "Enable background-subtraction from multifit results." 
            if is_multifitting_available else "Must do Multifitting to enable the switch."
        )
        background_subtraction_container = pn.Row(
            pn.widgets.TooltipIcon(
                value=subtraction_bg_tooltip, 
                css_classes=["tooltip-icon"]
            ),
            background_subtraction_label,
            self._background_subtraction_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"]
        )
        # get dataset energy range for setting the energy range slider limits
        self._component_model_input = {
            "energy_center": pn.widgets.IntInput(
                name='Energy Center',
                sizing_mode=self.STRETCH_WIDTH,
                value=500,
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
            "energy_range": pn.widgets.EditableRangeSlider(
                name='Energy Range',
                sizing_mode=self.STRETCH_WIDTH,
                value=  (540 - self.COMPONENT_EAXIS_THRESHOLD_VALUE, 540 + self.COMPONENT_EAXIS_THRESHOLD_VALUE),
                start=540 - self.COMPONENT_EAXIS_THRESHOLD,
                end=540 + self.COMPONENT_EAXIS_THRESHOLD,
                margin=(0,0,10,0),
            ),
            "flexibility": pn.widgets.Select(
                name="Flexibility",
                options=["Low", "Medium", "High", "Maximum"],  
                sizing_mode=self.STRETCH_WIDTH,
                margin=(0,0,10,0)
                )
        }

        self._fitting_add_compontent_button = pn.widgets.Button(
            name='Add Component',
            button_type='primary',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=False,
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

        # State identifiers
        _ON = 'on'
        _OFF = 'off'
        
        # Dictionary keys for state properties
        _NAME = 'label'
        _ON_CLICK = 'on_click'
        _BUTTON_TYPE = 'button_type'

        states = {
            _ON: {_NAME: "Hide Energy Map", _ON_CLICK: (lambda: print("Off clicked")), _BUTTON_TYPE: 'primary'},
            _OFF: {_NAME: "Show Energy Map", _ON_CLICK: (lambda: print("On clicked")), _BUTTON_TYPE: 'success'}
        }

        self._energy_map_toggle_button = ToggleButton(
            states = states,
            margin=0,
            height=55,
            disabled=False,
            sizing_mode=self._STRETCH_WIDTH
        )

        self._component_item_view_container = pn.Column(sizing_mode=self._STRETCH_BOTH, css_classes=["component-container"])

        right_sidebar = pn.Column(
            background_subtraction_container,
            details,
            self._component_item_view_container,
            self._energy_map_toggle_button,
            sizing_mode=self.STRETCH_BOTH,
        )
        return right_sidebar