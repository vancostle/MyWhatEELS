import panel as pn

from whateels.helpers import CSS_ROOT
from whateels.components import UploadedFile, ToggleButton, SimpleDetails, ModalManager
from whateels.base.mvc import BaseView
from .modals import PeriodicTableOfElementsModal
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ..model import QuantificationModel
    from ..controller import QuantificationController
    from whateels.templates import GeneralPageTemplate

class QuantificationView(BaseView):
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"
    
    _PERIODIC_TABLE_MODAL_ID = 'Periodic Table of Elements'

    # --- Initialization ---
    def __init__(self, model: "QuantificationModel", custom_page: "GeneralPageTemplate"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "quantification.css"),
                str(CSS_ROOT / "info_panel.css")
            ]
        )

        self._model = model
        self._controller: Optional["QuantificationController"] = None

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._quanti_add_element_button = pn.widgets.Button()

        self._element_item_view_container = pn.Column(sizing_mode=self._STRETCH_BOTH)
        
        self._modal_manager = ModalManager(custom_page)
        
        self._modal_manager.register_modal(
            self._PERIODIC_TABLE_MODAL_ID,
            PeriodicTableOfElementsModal(custom_page=custom_page)
        )

        self._init_components()
    
    def set_controller(self, controller: "QuantificationController"):
        """Set the controller for this view."""
        self._controller = controller
        quant_elements = getattr(self._model.app_state, "quantification_elements", None)
        if quant_elements is not None and hasattr(quant_elements, "__iter__"):
            for element_item in quant_elements:
                self._controller.add_element_item(element_item)

    @property
    def modals(self) -> list:
        """Return a list of all modals used by this view."""
        return self._modal_manager.modals

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def quanti_input(self):
        """Access the K-Means input widgets."""
        return self._quanti_input

    @property
    def quanti_add_element_button(self) -> pn.widgets.Button:
        """Access the K-Means 'Add Element' button."""
        return self._quanti_add_element_button
    
    @property
    def element_item_view_container(self) -> pn.Column:
        """Access the container for element item views."""
        return self._element_item_view_container
    
    @property
    def quanti_run_button(self) -> pn.widgets.Button:
        """Access the 'Run Quantification' button."""
        return self._quanti_run_button
    
    @property
    def quanti_toggle_button(self):
        """Access the 'Toggle Quantification' button."""
        return self._quanti_toggle_button
    
    @property
    def plot_elements_button(self):
        """Access the 'Plot Elements' button."""
        return self._plot_elements_button

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
        self._quanti_input = {
            "element_num": pn.widgets.IntInput(
                name='Element Atomic Number',
                sizing_mode=self.STRETCH_WIDTH,
                value=1,
                start=1,
                end=99,
                margin=(0,0,10,0),
            ),
            "shells_multiselect": pn.widgets.MultiChoice(
                name="Subshells", 
                options=[],
                sizing_mode=self.STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
        }
        
        SVG = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="2" width="20" height="20" rx="2"/>
          <text x="5" y="8" font-size="4.5" font-family="Arial,sans-serif" fill="currentColor" stroke="none">Z</text>
          <text x="12" y="16" text-anchor="middle" font-size="11" font-family="Arial,sans-serif" fill="currentColor" stroke="none" font-weight="bold">E</text>
          <text x="12" y="21" text-anchor="middle" font-size="3" font-family="Arial,sans-serif" fill="currentColor" stroke="none">Element</text>
        </svg>
        """
        ACTIVE_SVG = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="2" width="20" height="20" rx="2"/>
          <text x="5" y="8" font-size="4.5" font-family="Arial,sans-serif" fill="white" stroke="none">Z</text>
          <text x="12" y="16" text-anchor="middle" font-size="11" font-family="Arial,sans-serif" fill="white" stroke="none" font-weight="bold">E</text>
          <text x="12" y="21" text-anchor="middle" font-size="3" font-family="Arial,sans-serif" fill="white" stroke="none">Element</text>
        </svg>
        """
        
        periodic_table_button = pn.widgets.ButtonIcon(
            icon=SVG,
            active_icon=ACTIVE_SVG,
            size='3em',
            margin=(21,2,0,8),
        )
        
        periodic_table_button.on_click(lambda _ : self._modal_manager.open_modal(self._PERIODIC_TABLE_MODAL_ID))
        
        element_atomic_number_wrapper = pn.Row(
            self._quanti_input["element_num"],
            periodic_table_button,
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._quanti_add_element_button = pn.widgets.Button(
            name='Add Element',
            button_type='primary',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )

        self._quanti_element_item = pn.Column(
            *[widget for widget in self._quanti_input.values()],
            sizing_mode=self.STRETCH_WIDTH
        )

        self._element_item_view_container = pn.Column(
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["element-container"],
        )

        details = SimpleDetails(
            title="Quantification Instructions",
            content=pn.Column(
                # *[widget for widget in self._quanti_input.values()],
                element_atomic_number_wrapper,
                self._quanti_input["shells_multiselect"],
                self._quanti_add_element_button,
                sizing_mode=self._STRETCH_WIDTH
            ),
            expanded=True,
            button_type_on_collapse='primary',
            button_type_on_expand='success',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0,0,10,0)
        )

        # State identifiers
        ON = 'on'
        OFF = 'off'
        
        # Dictionary keys for state properties
        NAME = 'label'
        ON_CLICK = 'on_click'
        BUTTON_TYPE = 'button_type'

        states = {
            ON: {NAME: "Hide Quantification", ON_CLICK: (lambda: print("On clicked")), BUTTON_TYPE: 'primary'},
            OFF: {NAME: "Show Quantification", ON_CLICK: (lambda: print("Off clicked")), BUTTON_TYPE: 'success'}
        }

        self._quanti_toggle_button = ToggleButton(
            sizing_mode=self._STRETCH_WIDTH,
            states=states,
            margin=0,
            height=55,
            disabled=True
        )
        
        self._quanti_run_button = pn.widgets.Button(
            name='Run Quantification',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        self._plot_elements_button = pn.widgets.Button(
            name='Plot Elements',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        right_sidebar = pn.Column(
            details,
            self._element_item_view_container,
            pn.Row(
                pn.widgets.TooltipIcon(
                    value='You also must select an area in the left plot.',
                    width=30,
                ),
                self._quanti_toggle_button,
                sizing_mode=self.STRETCH_WIDTH,
                margin=(10, 0, 0, 0)
            ),
            sizing_mode=self.STRETCH_BOTH,
        )
        return right_sidebar
    
    def should_enable_quantification_button(self) -> bool:
        """
        Determine if the quantification controls should be enabled.
        
        Returns:
            bool: True if quantification can be enabled, False otherwise
        """
        
        MIN_ELEMENTS_REQUIRED = 2
        quantification_elements = self._model.app_state.quantification_elements
        if quantification_elements is None or not isinstance(quantification_elements, list):
            return False

        has_2_elements = len(quantification_elements) >= MIN_ELEMENTS_REQUIRED
        if not has_2_elements:
            return False
        
        return True