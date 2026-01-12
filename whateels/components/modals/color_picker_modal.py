import panel as pn

class ColorPickerModal(pn.Column):
    def __init__(
        self, 
        title="Modal Color Picker", 
        initial_color="#1f77b4", 
        on_color_selected=None,
        on_cancel=None,
        **kwargs
    ):
        self.color_picker = pn.widgets.ColorPicker(
            name="Color",
            value=initial_color,
            sizing_mode="stretch_width",
            margin=0
        )
        self._ok_button = pn.widgets.Button(
            name="OK", 
            button_type="primary", 
            sizing_mode="stretch_width",
            margin=0
        )
        self._cancel_button = pn.widgets.Button(
            name="Cancel", 
            button_type="default", 
            width=80,
            margin=0
        )
        self._callback_on_color_selected = on_color_selected
        self._callback_on_cancel = on_cancel
        self._result = None

        self._ok_button.on_click(self._on_ok)
        self._cancel_button.on_click(self._on_cancel)

        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding" : "0"}),
            self.color_picker,
            pn.Spacer(height=10),
            pn.Row(
                self._cancel_button, 
                self._ok_button, 
                sizing_mode="stretch_width",
                styles={"display": "flex", "justify-content": "space-between", "gap": "10px", "margin-top": "10px"}
            ),
            **kwargs,
        )

    def _on_ok(self, event):
        self._result = self.color_picker.value
        if self._callback_on_color_selected:
            self._callback_on_color_selected(self._result)
        self.visible = False

    def _on_cancel(self, event):
        self._result = None
        if self._callback_on_cancel:
            self._callback_on_cancel()
        self.visible = False

    @property
    def result(self):
        return self._result