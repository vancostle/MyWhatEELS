"""Modal used to choose clustered reference areas for Elemental fitting."""

from __future__ import annotations

from typing import TYPE_CHECKING

import panel as pn

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class NLLSFitAreasModal(pn.Column):
    """Small, stateful selector shared by the Fit action and its controller."""

    def __init__(
        self,
        custom_page: "GeneralPageTemplate | None" = None,
        *,
        title: str = "Select Area to run fit",
        **params,
    ) -> None:
        self._custom_page = custom_page
        self._use_current_clustering_button = pn.widgets.Button(
            name="Use Current Clustering",
            button_type="primary",
            height=55,
            disabled=True,
            sizing_mode="stretch_width",
            margin=0,
        )
        self._area_selector = pn.widgets.MultiChoice(
            name="Areas to fit",
            options={},
            value=[],
            disabled=True,
            sizing_mode="stretch_width",
            margin=0,
        )
        self._select_all_button = pn.widgets.Button(
            name="Select all",
            button_type="primary",
            disabled=True,
            sizing_mode="stretch_width",
            margin=0,
        )
        self._close_button = pn.widgets.Button(
            name="Save & Close",
            button_type="success",
            sizing_mode="stretch_width",
            margin=0,
        )
        self._close_button.on_click(self._close)

        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding": "0"}),
            pn.Spacer(height=10),
            self._use_current_clustering_button,
            pn.layout.Divider(margin=(4, 0, 4, 0)),
            self._area_selector,
            self._select_all_button,
            pn.Spacer(height=10),
            self._close_button,
            width=400,
            styles={"padding": "16px", "gap": "10px"},
            **params,
        )

    @property
    def area_selector(self) -> pn.widgets.MultiChoice:
        return self._area_selector

    @property
    def use_current_clustering_button(self) -> pn.widgets.Button:
        return self._use_current_clustering_button

    @property
    def select_all_button(self) -> pn.widgets.Button:
        return self._select_all_button

    def _close(self, event) -> None:
        self.visible = False
        if self._custom_page is not None:
            self._custom_page.close_modal()
