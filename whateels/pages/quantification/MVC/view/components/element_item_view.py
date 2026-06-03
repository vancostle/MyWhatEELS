import panel as pn
from whateels.components.toggle_button import ToggleButton

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...view import QuantificationView

class ElementItemView(pn.Column):
    _STRETCH_WIDTH = 'stretch_width'
    _EXPANDED_COLOR = "#ca4bc8"
    _COLLAPSED_COLOR = "#7373da"
    _DELETE_COLOR = "#dc3545"
    _BUTTON_TEXT_COLOR = "#ffffff"

    def __init__(self, controller, element_item: "ElementItem", model, energy, 
                view : "QuantificationView", expandable: bool = True):
        self._controller = controller
        self.element_item = element_item
        self._model = model
        self.energy = energy
        self._view = view
        self._element_item_view_container = view._element_item_view_container
        self._quanti_input = view._quanti_input
        self._quanti_add_element_button = view._quanti_add_element_button
        self._quanti_toggle_button = view._quanti_toggle_button
        self._expandable = expandable

        self.delete_button = pn.widgets.Button(
            name='Delete',
            button_type='default',
            stylesheets=[f"""
            button, .bk-btn {{
                background-color: {self._DELETE_COLOR} !important;
                border-color: {self._DELETE_COLOR} !important;
                color: {self._BUTTON_TEXT_COLOR} !important;
            }}
            """],
        )

        # State identifiers
        _ON = 'on'
        _OFF = 'off'

        # Dictionary keys for state properties
        _NAME = 'label'
        _ON_CLICK = 'on_click'
        _BUTTON_TYPE = 'button_type'
        _COLOR = 'color'
        _TEXT_COLOR = 'text_color'

        states = {
            _ON: {
                _NAME: "\u25B2 " + element_item.__str__(),
                _ON_CLICK: (),
                _BUTTON_TYPE: 'default',
                _COLOR: self._EXPANDED_COLOR,
                _TEXT_COLOR: self._BUTTON_TEXT_COLOR,
            },
            _OFF: {
                _NAME: "\u25BC " + element_item.__str__(),
                _ON_CLICK: (),
                _BUTTON_TYPE: 'default',
                _COLOR: self._COLLAPSED_COLOR,
                _TEXT_COLOR: self._BUTTON_TEXT_COLOR,
            },
        }

        self.slider_button = ToggleButton(
            sizing_mode=self._STRETCH_WIDTH,
            states=states,
            css_classes=["element-toggle-button"],
        )

        self.chemical_shift_input = pn.widgets.FloatInput(
            name='Chemical Shift',
            value=0.,
            step=1e-1,
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.element_item.set_fit_range([energy[0], energy[1] - element_item.chemical_shift])

        self.fit_slider = pn.widgets.EditableRangeSlider(
            name='fit range',
            start=energy[0],
            end=energy[1] - element_item.chemical_shift,
            value=(energy[0], energy[1]),
            step=1,
            disabled=False,
            format='0.00a',
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.quant_width_input = pn.widgets.FloatInput(
            name='Quantification Width',
            value=element_item.quant_width,
            step=1e-1,
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        # Initialize the parent class (pn.Column) with the layout
        if self._expandable:
            super().__init__(
                pn.Row(
                    self.slider_button,
                    self.delete_button,
                    sizing_mode=self._STRETCH_WIDTH
                ),
                self.chemical_shift_input,
                self.fit_slider,
                self.quant_width_input,
                sizing_mode=self._STRETCH_WIDTH,
                css_classes=["element-item"]
            )
        else:
            super().__init__(
                pn.Row(
                    pn.widgets.Markdown(f"### {element_item.__str__()}"),
                    self.delete_button,
                    sizing_mode=self._STRETCH_WIDTH
                ),
                sizing_mode=self._STRETCH_WIDTH,
                css_classes=["element-item"]
            )

        # Add watchers and callbacks
        self.fit_slider.param.watch(self._fit_range_watcher, 'value')
        self.quant_width_input.param.watch(self._quant_width_watcher, 'value')
        self.delete_button.on_click(self._delete_element_watcher)
        self.slider_button.on_click(self._slider_button_watcher)
        self.chemical_shift_input.param.watch(self._chemical_shift_watcher, 'value')

    def _chemical_shift_watcher(self, event):
        self.element_item.chemical_shift = event.new
        self[2].end = self.energy[1] - self.element_item.chemical_shift
        self.element_item._refresh_quant_range()
        self._controller.plot_elements()

    def _fit_range_watcher(self, event):
        self.element_item.set_fit_range(event.new)
        self._controller.plot_elements()

    def _quant_width_watcher(self, event):
        self.element_item.set_quant_width(event.new)
        self._controller.plot_elements()

    def _delete_element_watcher(self, event):
        self._element_item_view_container.remove(self)
        self._model.app_state.quantification_elements.remove(self.element_item)

        current_atomic_number = self._quanti_input["element_num"].value
        atomic_number_of_added_element = self.element_item.element

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
        isDisabled = self._view.should_enable_quantification_button()
        self._quanti_toggle_button.disabled = not isDisabled

        self._controller.plot_elements()

    def _slider_button_watcher(self, event):
        show = not self.chemical_shift_input.visible
        self.chemical_shift_input.visible = show
        self.fit_slider.visible = show
        self.quant_width_input.visible = show
