import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.components import CustomPage

class ColorPickerModal(pn.Column):
    def __init__(
        self, 
        custom_page : "CustomPage",
        title="Modal Color Picker", 
        initial_color="#1f77b4", 
        on_color_selected=None,
        on_cancel=None,
        **kwargs
    ):
        self._custom_page = custom_page
        
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
        self._custom_page.close_modal()

    def _on_cancel(self, event):
        self._result = None
        if self._callback_on_cancel:
            self._callback_on_cancel()
        self.visible = False
        self._custom_page.close_modal()

    @property
    def result(self):
        return self._result