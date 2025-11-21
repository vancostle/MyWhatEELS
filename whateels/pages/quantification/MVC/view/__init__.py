from typing import TYPE_CHECKING, Optional
from whateels.helpers import CSS_ROOT
from whateels.components import UploadedFile, ToggleButton
from whateels.base.mvc import BaseView
import panel as pn

if TYPE_CHECKING:
    from ..model import QuantificationModel
    from ..controller import QuantificationController, ElementItem

class QuantificationView(BaseView):
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    # --- Initialization ---
    def __init__(self, model: "QuantificationModel"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "quantification.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )

        self._model = model
        self._controller: Optional["QuantificationController"] = None

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._quanti_add_element_button = None

        self._element_item_view_container = pn.Column(sizing_mode=self._STRETCH_BOTH)

        self._init_components()
    
    def set_controller(self, controller: "QuantificationController"):
        """Set the controller for this view."""
        self._controller = controller
        for element_item in self._model.app_state.quantification_elements:
           self._controller.add_element_item(element_item)

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def quanti_input(self):
        """Access the K-Means input widgets."""
        return self._quanti_input

    @property
    def quanti_add_element_button(self):
        """Access the K-Means 'Add Element' button."""
        return self._quanti_add_element_button
    
    @property
    def element_item_view_container(self) -> pn.Column:
        """Access the container for element item views."""
        return self._element_item_view_container
    
    @property
    def quanti_run_button(self):
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

    def get_new_element_item_view(self, element_item : "ElementItem", energy) -> pn.Column:        

        delete_button = pn.widgets.Button(
            name= 'Delete',
            button_type='danger'
        )

        # State identifiers
        _ON = 'on'
        _OFF = 'off'
        
        # Dictionary keys for state properties
        _NAME = 'label'
        _ON_CLICK = 'on_click'
        _BUTTON_TYPE = 'button_type'

        states = {
            _ON: {_NAME: "\u25B2 " + element_item.__str__(), _ON_CLICK: (lambda: print("On clicked")), _BUTTON_TYPE: 'success'},
            _OFF: {_NAME: "\u25BC " + element_item.__str__(), _ON_CLICK: (lambda: print("Off clicked")), _BUTTON_TYPE: 'primary'}
        }

        slider_button = ToggleButton(
            sizing_mode=self._STRETCH_WIDTH,
            states=states,
            css_classes=["element-toggle-button"]
        )

        element_item_view = pn.Column(
            pn.Row(
                slider_button, 
                delete_button, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            sizing_mode=self._STRETCH_WIDTH, 
            css_classes=["element-item"]
        )

        chemical_shift_input = pn.widgets.FloatInput(
            name='Chemical Shift', 
            value=0., 
            step=1e-1, 
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"}, 
            visible=False
        )

        def _chemical_shift_watcher(event):
            element_item.chemical_shift = event.new
            element_item_view[2].end = energy[1] - element_item.chemical_shift
            element_item_view[3].start = energy[1] - element_item.chemical_shift
            self._controller.plot_elements()


        element_item.set_fit_range([energy[0], energy[1]- element_item.chemical_shift])

        fit_slider = pn.widgets.EditableRangeSlider(name='fit range', start=energy[0], end=energy[1] - element_item.chemical_shift, 
                value=(energy[0],energy[1]), step=1, disabled=False, format='0.00a', styles= {"margin": "0", "padding": "0 1rem 1rem 2rem"}, visible=False)
        quant_width_input = pn.widgets.FloatInput(name='Quantification Width', value=50., step=1e-1, styles= {"margin": "0", "padding": "0 1rem 1rem 2rem"}, visible=False)

        element_item_view.append(chemical_shift_input)
        element_item_view.append(fit_slider)
        element_item_view.append(quant_width_input)
            
        def _fit_range_watcher(event):
            element_item.set_fit_range(event.new)
            self._controller.plot_elements()

        def _quant_width_watcher(event):   
            element_item.set_quant_width(event.new)
            self._controller.plot_elements()
        
        



        def _delete_element_watcher(event):
            self._element_item_view_container.remove(element_item_view)
            self._model.app_state.quantification_elements.remove(element_item)  
            
            current_atomic_number = self._quanti_input["element_num"].value
            atomic_number_of_added_element = element_item.element
            
            add_element_button = self._quanti_add_element_button
            if add_element_button is None:
                return
            
            current_subshells_multiselect_value = self._quanti_input["shells_multiselect"].value
            if current_subshells_multiselect_value is None or current_atomic_number is None:
                add_element_button.disabled = True
                return
            
            if current_atomic_number == atomic_number_of_added_element:
                add_element_button.disabled = False
                add_element_button.button_type = 'primary'
                add_element_button.name = f'Add Element'
            
            # Update quantification toggle button state
            isDisabled = self.should_enable_quantification_button()
            self._quanti_toggle_button.disabled = not isDisabled 
            
            self._controller.plot_elements()

        def _slider_button_watcher(event):
            show = not chemical_shift_input.visible
            chemical_shift_input.visible = show
            fit_slider.visible = show
            quant_width_input.visible = show

        fit_slider.param.watch(_fit_range_watcher, 'value')
        quant_width_input.param.watch(_quant_width_watcher, 'value')
        delete_button.on_click(_delete_element_watcher)
        slider_button.on_click(_slider_button_watcher)
        chemical_shift_input.param.watch(_chemical_shift_watcher, 'value')

        #m.axes_manager['energy_loss'].scale
        
        return element_item_view, element_item

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

        self._quanti_add_element_button = pn.widgets.Button(
            name='Add Element',
            button_type='primary',
            height=55,
            margin=(0,0,10,0),
            sizing_mode=self.STRETCH_WIDTH,
            disabled=True,
        )

        self._quanti_element_item = pn.Column(
            *[widget for widget in self._quanti_input.values()],
            sizing_mode=self.STRETCH_WIDTH
        )

        self._element_item_view_container = pn.Column(
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["element-container"]
        )

            # State identifiers
        _ON = 'on'
        _OFF = 'off'
        
        # Dictionary keys for state properties
        _NAME = 'label'
        _ON_CLICK = 'on_click'
        _BUTTON_TYPE = 'button_type'

        states = {
            _ON: {_NAME: "Hide Quantification", _ON_CLICK: (lambda: print("On clicked")), _BUTTON_TYPE: 'primary'},
            _OFF: {_NAME: "Show Quantification", _ON_CLICK: (lambda: print("Off clicked")), _BUTTON_TYPE: 'success'}
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
            self._quanti_element_item,
            self._quanti_add_element_button,
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