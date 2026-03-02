import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate

class InfoModal(pn.Column):
    def __init__(
        self,
        custom_page : "GeneralPageTemplate",
        title="Information",
        message="This is an informational modal.",
        on_close=None,
        **kwargs
    ):
        self._custom_page = custom_page
        self._on_close = on_close
        
        close_button = pn.widgets.Button(
            name="Close",
            button_type="primary",
            sizing_mode="stretch_width",
            margin=0
        )

        close_button.on_click(self._close)
        
        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding" : "0"}),
            pn.pane.Markdown(message, margin=0, styles={"padding" : "0"}),
            pn.Spacer(height=10),
            close_button,
            **kwargs
        )
        
    def _close(self, event):
        if self._on_close:
            self._on_close()
        self.visible = False
        self._custom_page.close_modal()