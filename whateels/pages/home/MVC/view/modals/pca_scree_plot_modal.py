"""Popup modal containing the PCA scree plot."""

from __future__ import annotations

from typing import TYPE_CHECKING

import holoviews as hv
import numpy as np
import panel as pn

if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


_X_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='26' height='26'
     viewBox='0 0 24 24' fill='none' stroke='currentColor'
     stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
  <line x1='18' y1='6' x2='6' y2='18'/>
  <line x1='6' y1='6' x2='18' y2='18'/>
</svg>
"""


class PCAScreePlotModal(pn.Column):
    """Reusable Home-page modal for PCA explained-variance results."""

    def __init__(self, custom_page: "GeneralPageTemplate", **params):
        self._custom_page = custom_page

        self._summary = pn.pane.Markdown(
            "Run the PCA decomposition to display its explained variance.",
            margin=(0, 0, 8, 0),
            sizing_mode="stretch_width",
        )
        self._plot_pane = pn.pane.HoloViews(
            hv.Curve([]),
            sizing_mode="stretch_width",
            height=500,
            margin=0,
        )
        self._close_button = pn.widgets.ButtonIcon(
            icon=_X_SVG,
            width=40,
            height=40,
            margin=(0, 0, 0, 8),
            styles={"background": "#fff", "border": "none"},
        )
        self._close_button.on_click(self._close)

        super().__init__(
            pn.Row(
                pn.pane.Markdown(
                    "## PCA Scree Plot",
                    margin=0,
                    styles={"padding": "0"},
                ),
                pn.Spacer(),
                self._close_button,
                sizing_mode="stretch_width",
                styles={
                    "align-items": "flex-start",
                    "justify-content": "flex-end",
                },
            ),
            self._summary,
            self._plot_pane,
            sizing_mode="stretch_width",
            styles={
                "background": "rgba(255, 255, 255, 0.98)",
                "boxShadow": "0 0 32px 8px #0002",
                "maxHeight": "94vh",
                "maxWidth": "920px",
                "minWidth": "680px",
                "overflow": "auto",
                "padding": "18px",
                "width": "88vw",
            },
            **params,
        )

    def set_results(
        self,
        explained_variance_ratio,
        scree_components: int,
        selected_components: int,
        dataset_name: str | None = None,
    ) -> None:
        """Replace the modal contents with a fitted decomposition."""
        ratios = np.nan_to_num(
            np.asarray(explained_variance_ratio, dtype=float),
            copy=True,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        if ratios.ndim != 1 or ratios.size == 0:
            raise ValueError("PCA explained-variance results are empty.")

        ratios = np.clip(ratios, 0.0, None)
        displayed = max(1, min(int(scree_components), int(ratios.size)))
        selected = max(1, int(selected_components))
        displayed_ratios = ratios[:displayed]
        components = np.arange(1, displayed + 1, dtype=int)
        individual_percent = displayed_ratios * 100.0
        cumulative_percent = np.clip(
            np.cumsum(individual_percent),
            0.0,
            100.0,
        )
        available_cumulative_percent = np.clip(
            np.cumsum(ratios * 100.0),
            0.0,
            100.0,
        )

        individual_curve = hv.Curve(
            (components, individual_percent),
            kdims=["Principal Component"],
            vdims=["Explained Variance (%)"],
            label="Individual",
        ).opts(
            color="#4d4dc9",
            line_width=2,
            tools=["hover"],
        )
        individual_points = hv.Scatter(
            (components, individual_percent),
            kdims=["Principal Component"],
            vdims=["Explained Variance (%)"],
            label="Individual components",
        ).opts(
            color="#4d4dc9",
            marker="circle",
            size=6,
            tools=["hover"],
        )
        cumulative_curve = hv.Curve(
            (components, cumulative_percent),
            kdims=["Principal Component"],
            vdims=["Explained Variance (%)"],
            label="Cumulative",
        ).opts(
            color="#b63fb5",
            line_dash="dashed",
            line_width=2,
            tools=["hover"],
        )
        plot = (
            individual_curve
            * individual_points
            * cumulative_curve
        )
        if selected <= displayed:
            selected_marker = hv.VLine(selected).opts(
                color="#198754",
                line_dash="dotted",
                line_width=3,
            )
            plot = plot * selected_marker

        self._plot_pane.object = plot.opts(
            hv.opts.Overlay(
                height=500,
                legend_position="top_right",
                responsive=True,
                show_grid=True,
                title="Explained variance by principal component",
                xlim=(0.5, float(displayed) + 0.5),
                ylim=(0.0, 105.0),
            )
        )

        dataset_label = f" for **{dataset_name}**" if dataset_name else ""
        if selected <= ratios.size:
            selected_variance = float(
                available_cumulative_percent[selected - 1]
            )
            selected_summary = (
                f"**{selected}** selected for reconstruction, capturing "
                f"**{selected_variance:.2f}%** of cumulative variance"
            )
        else:
            selected_summary = (
                f"**{selected}** selected for reconstruction; those additional "
                "components will be calculated when reconstruction is applied"
            )
        visibility_note = (
            ""
            if selected <= displayed
            else " (the reconstruction selection is outside the visible scree range)"
        )
        self._summary.object = (
            f"PCA{dataset_label}: displaying the first **{displayed}** calculated "
            f"components. {selected_summary}{visibility_note}."
        )

    def clear_results(self) -> None:
        """Release references to the previous decomposition plot."""
        self._summary.object = "Run the PCA decomposition to display its explained variance."
        self._plot_pane.object = hv.Curve([])

    def close(self) -> None:
        """Hide the popup, tolerating a template that is still initializing."""
        self.visible = False
        try:
            self._custom_page.close_modal()
        except Exception:
            pass

    def _close(self, *_):
        self.close()
