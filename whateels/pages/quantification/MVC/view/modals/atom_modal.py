import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class AtomModal(pn.Column):
    def __init__(self, custom_page: "GeneralPageTemplate", on_close=None):
        self._custom_page = custom_page
        self._on_close = on_close

        X_SVG = """
        <svg xmlns='http://www.w3.org/2000/svg' width='26' height='26' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
          <line x1='18' y1='6' x2='6' y2='18'/>
          <line x1='6' y1='6' x2='18' y2='18'/>
        </svg>
        """

        close_button = pn.widgets.ButtonIcon(
            icon=X_SVG,
            width=40,
            height=40,
            margin=(8, 8, 0, 0),
            styles={"background": "#fff", "border": "none"},
        )
        close_button.on_click(self._close)

        super().__init__(
            pn.Row(
                pn.Spacer(),
                close_button,
                sizing_mode="stretch_width",
                styles={"justify-content": "flex-end", "align-items": "flex-start"},
            ),
            pn.Spacer(),
            sizing_mode="stretch_both",
            styles={
                "padding": "8px",
                "background": "rgba(255,255,255,0.98)",
                "maxWidth": "98vw",
                "maxHeight": "98vh",
                "boxShadow": "0 0 32px 8px #0002",
            },
        )

    def _close(self, *_):
        self.visible = False
        if self._on_close:
            self._on_close()
        self._custom_page.close_modal()
