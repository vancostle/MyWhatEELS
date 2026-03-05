import panel as pn
from whateels.components.toggle_button import ToggleButton
import numpy as np

class ComponentItemView(pn.Column):
    _STRETCH_WIDTH = 'stretch_width'

    def __init__(self, controller, component_item: "ComponentItem", model, energy, 
                view, expandable: bool = True):
        self._controller = controller
        self.component_item = component_item
        self._model = model
        self.energy = energy
        self._component_input = view.component_input
        self._fitting_add_component_button = view.fitting_add_component_button
        self._expandable = expandable
        self._view = view

        self.dict_var = {
            'Low': [3, 3, 0.1, 0.1, 0.5, 2],
            'Medium': [7, 7, 1, 1.25, 0, 3],
            'High': [15, 15, 1, 3, 0, 5],
            'Maximum': [np.inf, np.inf, 1, np.inf, 0, np.inf]
        }

        self.delete_button = pn.widgets.Button(
            name='Delete',
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
            _ON: {_NAME: "\u25B2 " + component_item.__str__(), _ON_CLICK: (), _BUTTON_TYPE: 'success'},
            _OFF: {_NAME: "\u25BC " + component_item.__str__(), _ON_CLICK: (), _BUTTON_TYPE: 'primary'}
        }

        self.slider_button = ToggleButton(
            sizing_mode=self._STRETCH_WIDTH,
            states=states,
            css_classes=["component-toggle-button"],
        )

        self.energy_center_input = pn.widgets.FloatInput(
            name='Energy Center',
            value=component_item.energy_center,
            step=1e-1,
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.energy_range_slider = pn.widgets.EditableRangeSlider(
            name='Energy Range',
            start=component_item.energy_center - 50,
            end=component_item.energy_center + 50,
            value=component_item.center_range,
            step=1,
            disabled=False,
            format='0.00a',
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.amplitude_input = pn.widgets.FloatInput(
            name='Amplitude',
            value=component_item.amplitude,
            step=1000,
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.amplitude_slider = pn.widgets.EditableRangeSlider(
            name='Amplitude Range',
            start=component_item.amplitude_range[0] * 0.5,
            end=component_item.amplitude_range[1]  * 1.5,
            value=component_item.amplitude_range,
            step=1000,
            disabled=False,
            format='0.00a',
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )

        self.sigma_input = pn.widgets.FloatInput(
            name='Sigma',
            value=component_item.sigma,
            step=1e-1,
            styles={"margin": "0", "padding": "0 1rem 1rem 2rem"},
            visible=False
        )


        self.sigma_slider = pn.widgets.EditableRangeSlider(
            name='Sigma Range',
            start=component_item.sigma_range[0] * 0.5,
            end=component_item.sigma_range[1] * 1.5,
            value=component_item.sigma_range,
            step=1e-1,
            disabled=False,
            format='0.00a',
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
                self.energy_center_input,
                self.energy_range_slider,
                self.amplitude_input,
                self.amplitude_slider,
                self.sigma_input,
                self.sigma_slider,
                sizing_mode=self._STRETCH_WIDTH,
                css_classes=["element-item"]
            )
        else:
            super().__init__(
                pn.Row(
                    pn.widgets.Markdown(f"### {component_item.__str__()}"),
                    self.delete_button,
                    sizing_mode=self._STRETCH_WIDTH
                ),
                sizing_mode=self._STRETCH_WIDTH,
                css_classes=["element-item"]
            )

        # Add watchers and callbacks
        self.energy_range_slider.param.watch(self._energy_range_watcher, 'value')
        self.delete_button.on_click(self._delete_element_watcher)
        self.slider_button.on_click(self._slider_button_watcher)
        self.energy_center_input.param.watch(self._energy_center_watcher, 'value')
        self.sigma_input.param.watch(self._sigma_watcher, 'value')
        self.sigma_slider.param.watch(self._sigma_range_watcher, 'value')
        self.amplitude_input.param.watch(self._amplitude_watcher, 'value')
        self.amplitude_slider.param.watch(self._amplitude_range_watcher, 'value')

    def _energy_center_watcher(self, event):
        self.component_item.energy_center = event.new
        if event.new > self.energy_range_slider.end or event.new < self.energy_range_slider.start:
            self.energy_range_slider.start = event.new - 50
            self.energy_range_slider.end = event.new + 50
            self.energy_range_slider.value = (event.new - 50, event.new + 10)
            self.energy_range_slider.value = (event.new - 10, event.new + 10)
        else:
            self.energy_range_slider.start = event.new - 50
            self.energy_range_slider.end = event.new + 50
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()

    def _energy_range_watcher(self, event):
        self.component_item.set_center_range(event.new[0], event.new[1])
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()

    def _sigma_range_watcher(self, event):
        self.component_item.set_sigma_range(event.new[0], event.new[1])
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()
    
    def _amplitude_range_watcher(self, event):
        self.component_item.set_amplitude_range(event.new[0], event.new[1])
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()

    def _sigma_watcher(self, event):
        self.component_item.sigma = event.new
        self.sigma_slider.start = (event.new - self.dict_var[self.component_item.flexibility][2] if event.new > self.dict_var[self.component_item.flexibility][2] else 0) * 0.5
        self.sigma_slider.end = event.new + self.dict_var[self.component_item.flexibility][3] * 1.5
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()

    def _amplitude_watcher(self, event):
        self.component_item.amplitude = event.new
        self.amplitude_slider.start = event.new *self.dict_var[self.component_item.flexibility][4] * 0.5
        self.amplitude_slider.end = event.new*self.dict_var[self.component_item.flexibility][5] * 1.5
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()  # Update component parameters in the model

    def _delete_element_watcher(self, event):
        self._view.component_item_view_container.remove(self)

        self._model.remove_component(self.component_item)

    def _slider_button_watcher(self, event):
        show = not self.energy_center_input.visible
        self.energy_center_input.visible = show
        self.energy_range_slider.visible = show
        self.sigma_input.visible = show
        self.sigma_slider.visible = show
        self.amplitude_input.visible = show
        self.amplitude_slider.visible = show
    
    def update_component_parameters(self):
        self.amplitude_input.value = self.component_item.amplitude
        self.sigma_input.value = self.component_item.sigma
        self.energy_center_input.value = self.component_item.energy_center
        self.energy_range_slider.value = self.component_item.center_range
        self.sigma_slider.value = self.component_item.sigma_range
        self.amplitude_slider.value = self.component_item.amplitude_range

    def update_component_item_name(self, reference_fit):
        self.amplitude_input.name = f'Amplitude ({reference_fit})'
        self.sigma_input.name = f'Sigma ({reference_fit})'
        self.energy_center_input.name = f'Energy Center ({reference_fit})'  
        self.energy_range_slider.name = f'Energy Range ({reference_fit})'
        self.sigma_slider.name = f'Sigma Range ({reference_fit})'
        self.amplitude_slider.name = f'Amplitude Range ({reference_fit})'