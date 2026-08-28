from typing import TYPE_CHECKING

import panel as pn

from whateels.helpers import ASSETS_ROOT

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class PeriodicTableOfElementsModal(pn.Column):
    """Shared periodic-table reference modal."""

    def __init__(self, custom_page: "GeneralPageTemplate", on_close=None):
        self._custom_page = custom_page

        close_svg = """
        <svg xmlns='http://www.w3.org/2000/svg' width='26' height='26' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
          <line x1='18' y1='6' x2='6' y2='18'/>
          <line x1='6' y1='6' x2='18' y2='18'/>
        </svg>
        """
        self._svg = pn.pane.SVG(
            str(ASSETS_ROOT / "img" / "periodic_table.svg"),
            styles={
                "display": "block",
                "margin": "0 auto",
                "width": "auto",
                "height": "100%",
            },
        )
        self._close_button = pn.widgets.ButtonIcon(
            icon=close_svg,
            width=40,
            height=40,
            margin=(8, 8, 0, 0),
            styles={"background": "#fff", "border": "none"},
        )
        self._close_button.on_click(self._close)
        self._on_close = on_close
        super().__init__(
            pn.Row(
                pn.Spacer(),
                self._close_button,
                sizing_mode="stretch_width",
                styles={"justify-content": "flex-end", "align-items": "flex-start"},
            ),
            self._svg,
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
