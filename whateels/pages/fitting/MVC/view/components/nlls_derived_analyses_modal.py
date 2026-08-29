"""Modal host for Center Analysis and White Lines controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import panel as pn

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class NLLSDerivedAnalysesModal(pn.Column):
    """Mount the live analysis controls for the currently selected NLLS run."""

    def __init__(
        self,
        custom_page: "GeneralPageTemplate | None" = None,
        **params,
    ) -> None:
        self._custom_page = custom_page
        self._controls_slot = pn.Column(
            sizing_mode="stretch_width",
            margin=0,
            styles={
                "min-width": "0",
                "max-width": "100%",
                "max-height": "68vh",
                "overflow-y": "auto",
            },
        )
        super().__init__(
            pn.pane.Markdown("## Derived analyses", margin=0),
            self._controls_slot,
            width=440,
            styles={"padding": "16px", "gap": "8px"},
            **params,
        )

    @property
    def controls_slot(self) -> pn.Column:
        return self._controls_slot

    def mount(self, controls: tuple | list) -> None:
        self._controls_slot.objects = list(controls)

    def close(self) -> None:
        """Dismiss the modal after a derived analysis has been created."""
        self.visible = False
        if self._custom_page is not None:
            self._custom_page.close_modal()
