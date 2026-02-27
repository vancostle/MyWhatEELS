import panel as pn
from whateels.components.toggle_button import ToggleButton

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
        self._right_sidebar = view.right_sidebar

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
            start=energy[0],
            end=energy[-1],
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
            start=0,
            end=3000000,
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
            start=0,
            end=20,
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
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()

    def _amplitude_watcher(self, event):
        self.component_item.amplitude = event.new
        self._model.create_model()  # Recreate model with updated component range
        self._model.fit_reference()  # Refit with updated model
        self.update_component_parameters()  # Update component parameters in the model

    def _delete_element_watcher(self, event):
        self._right_sidebar.remove(self)

        self._model.remove_component(self.component_item)

        add_element_button = self._quanti_add_element_button
        if add_element_button is None:
            return

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