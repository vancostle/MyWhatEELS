"""Modal host for the filters of the currently selected Elemental NLLS run."""

from __future__ import annotations

from typing import TYPE_CHECKING

import panel as pn

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class NLLSResultFiltersModal(pn.Column):
    """Mount one run's live filter widgets without copying their state."""

    def __init__(
        self,
        custom_page: "GeneralPageTemplate | None" = None,
        **params,
    ) -> None:
        self._custom_page = custom_page
        self._controls_slot = pn.Column(
            sizing_mode="stretch_width",
            margin=0,
            styles={"min-width": "0", "max-width": "100%"},
        )
        self._close_button = pn.widgets.Button(
            name="Close",
            button_type="primary",
            sizing_mode="stretch_width",
            height=42,
            margin=0,
        )
        self._close_button.on_click(self._close)

        super().__init__(
            pn.pane.Markdown("## Elemental NLLS result filters", margin=0),
            pn.pane.Markdown(
                "Filters update the active result map and its pixel spectrum immediately.",
                margin=(0, 0, 6, 0),
            ),
            self._controls_slot,
            pn.Spacer(height=8),
            self._close_button,
            width=440,
            styles={"padding": "16px", "gap": "8px"},
            **params,
        )

    @property
    def controls_slot(self) -> pn.Column:
        return self._controls_slot

    def mount(self, controls: tuple | list) -> None:
        """Show the actual widgets owned by the active run."""
        self._controls_slot.objects = list(controls)

    def clear(self) -> None:
        self._controls_slot.objects = []

    def _close(self, event) -> None:
        self.visible = False
        if self._custom_page is not None:
            self._custom_page.close_modal()
