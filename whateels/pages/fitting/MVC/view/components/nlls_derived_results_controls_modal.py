"""Modal containing controls for additive Elemental NLLS derived results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import panel as pn

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class NLLSDerivedResultsControlsModal(pn.Column):
    """Host the live controls owned by every additive derived-result plot."""

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
                "max-height": "65vh",
                "overflow-y": "auto",
            },
        )
        self._empty_state = pn.pane.Alert(
            "Compute Center Analysis or White Lines to create a derived result.",
            alert_type="light",
            sizing_mode="stretch_width",
            margin=0,
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
            pn.pane.Markdown("## Derived results control", margin=0),
            pn.pane.Markdown(
                "Select the map displayed by each additive derived-analysis plot.",
                margin=(0, 0, 6, 0),
            ),
            self._empty_state,
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
        objects = list(controls)
        self._controls_slot.objects = objects
        self._empty_state.visible = not bool(objects)

    def clear_controls(self) -> None:
        self.mount(())

    def _close(self, event) -> None:
        self.visible = False
        if self._custom_page is not None:
            self._custom_page.close_modal()
