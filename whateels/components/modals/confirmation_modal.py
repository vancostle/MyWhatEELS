import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate

class ConfirmationModal(pn.Column):
    
    def __init__(
        self,
        custom_page : "GeneralPageTemplate",
        title="Are you sure?",
        message="Please confirm your action.",
        on_confirm=None,
        on_cancel=None,
        **kwargs
    ):     
        self._custom_page = custom_page
           
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        
        confirm_button = pn.widgets.Button(
            name="Confirm",
            button_type="primary",
            sizing_mode="stretch_width",
            margin=0
        )
        
        cancel_button = pn.widgets.Button(
            name="Cancel",
            button_type="danger",
            sizing_mode="stretch_width",
            margin=0
        )

        confirm_button.on_click(self._confirm)
        cancel_button.on_click(self._cancel)
        
        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding" : "0"}),
            pn.pane.Markdown(message, margin=0, styles={"padding" : "0"}),
            pn.Spacer(height=10),
            pn.Row(
                cancel_button,
                confirm_button,
                sizing_mode="stretch_width",
                styles={"display": "flex", "justify-content": "space-between", "gap": "10px", "margin-top": "10px"}
            ),
            **kwargs
        )
        
    def _confirm(self, event):
        if self._on_confirm:
            self._on_confirm()
        self.visible = False
        self._custom_page.close_modal()

    def _cancel(self, event):
        if self._on_cancel:
            self._on_cancel()
        self.visible = False
        self._custom_page.close_modal()