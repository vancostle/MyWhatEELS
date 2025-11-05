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
                str(CSS_ROOT / "quantification.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )

        self._model = model

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._quanti_add_element_button = None

        self._element_item_view_container = pn.Column(sizing_mode=self._STRETCH_BOTH)

        self._init_components()

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
        element_item.set_fit_range([energy[0], energy[-1]])
        element_item.set_quant_range([energy[0], energy[-1]])

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
                _ON: {_NAME: element_item.__str__() + " <", _ON_CLICK: (lambda: print("On clicked")), _BUTTON_TYPE: 'default'},
                _OFF: {_NAME: element_item.__str__() + " ˇ", _ON_CLICK: (lambda: print("Off clicked")), _BUTTON_TYPE: 'primary'}
            }

        slider_button = ToggleButton(
            sizing_mode=self._STRETCH_WIDTH,
            states=states
        )

        element_item_view = pn.Column(
            pn.Row(slider_button, delete_button, sizing_mode=self._STRETCH_WIDTH),
            sizing_mode=self._STRETCH_WIDTH, 
            css_classes=["element-item"]
        )

        fit_slider = pn.widgets.EditableRangeSlider(name='fit range', start=energy[0], end=energy[-1], 
                value=(640,680), step=1, disabled=False)
        quant_slider = pn.widgets.EditableRangeSlider(name='quant range', start=energy[0], end=energy[-1], 
                value=(640,680), step=1, disabled=False)

        def _fit_range_watcher(event):
            element_item.set_fit_range(event.new)

        def _quant_range_watcher(event):   
            element_item.set_quant_range(event.new)

        def _delete_element_watcher(event):
            self._element_item_view_container.remove(element_item_view)
            self._model.app_state.quantification_elements.remove(element_item)
            print(self._model.app_state.quantification_elements)

        slider = {"active": False}
        

        def _slider_button_watcher(event, slider=slider):
            if not slider["active"]:
                element_item_view.append(fit_slider)
                element_item_view.append(quant_slider)
                slider["active"] = True
            else:
                element_item_view.remove(fit_slider)
                element_item_view.remove(quant_slider)
                slider["active"] = False


        fit_slider.param.watch(_fit_range_watcher, 'value')
        quant_slider.param.watch(_quant_range_watcher, 'value')
        delete_button.on_click(_delete_element_watcher)
        slider_button.on_click(_slider_button_watcher)

        #m.axes_manager['energy_loss'].scale
        
        return element_item_view, element_item

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
    
    def _right_sidebar_layout(self) -> pn.Column:
        quantification_input_label = pn.pane.Markdown(
            "### Quantification Input", 
        )

        self._quanti_input = {
            "element_num": pn.widgets.IntInput(
                name='Element Atomic Number',
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

        self._quanti_element_item = pn.Column(
            *[widget for widget in self._quanti_input.values()],
            sizing_mode=self.STRETCH_WIDTH
        )

        self._element_item_view_container = pn.Column(
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["element-container"]
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
            quantification_input_label,
            self._quanti_element_item,
            self._quanti_add_element_button,
            self._element_item_view_container,
            self._plot_elements_button,
            self._quanti_run_button,
            sizing_mode=self.STRETCH_BOTH,
        )
        
        return right_sidebar
    