"""Reactive reference-fit results for the Elemental NLLS workflow."""

from __future__ import annotations

from html import escape
import math
from typing import Mapping

import holoviews as hv
import numpy as np
import panel as pn

from whateels.nlls.contracts import ReferenceFitSnapshot


class NLLSResultsView(pn.Column):
    """Render portable ``ReferenceFitSnapshot`` objects without retaining lmfit state."""

    _STRETCH_WIDTH = "stretch_width"
    _FIT_COLOR = "#ca4bc8"
    _SECONDARY_COLOR = "#7373da"
    _COMPONENT_COLORS = (
        "#7373da",
        "#f28e2b",
        "#59a14f",
        "#e15759",
        "#76b7b2",
        "#edc949",
        "#af7aa1",
        "#ff9da7",
    )

    def __init__(self, **params) -> None:
        self._snapshots: dict[str, ReferenceFitSnapshot] = {}
        self._area_labels: dict[str, str] = {}
        self._eloss = np.array([], dtype=float)

        self._area_select = pn.widgets.Select(
            name="Reference area",
            options={},
            value=None,
            disabled=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._layer_selector = pn.widgets.CheckButtonGroup(
            name="Visible curves",
            options=["Reference", "Best fit", "Components"],
            value=["Reference", "Best fit", "Components"],
            button_type="default",
            disabled=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            stylesheets=["""
                :host .bk-btn-group {
                    display: flex !important;
                    flex-wrap: wrap !important;
                    max-width: 100% !important;
                    min-width: 0 !important;
                }
                :host .bk-btn {
                    flex: 1 1 auto !important;
                    min-width: 0 !important;
                }
            """],
        )
        self._placeholder = pn.pane.Alert(
            "Fit a reference to inspect the spectrum, best fit, components and residual.",
            alert_type="light",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 10, 0),
        )
        self._summary_pane = pn.pane.HTML(
            "",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 10, 0),
            visible=False,
        )
        self._plot_pane = pn.pane.HoloViews(
            self._empty_curve("Reference fit"),
            sizing_mode=self._STRETCH_WIDTH,
            height=285,
            margin=0,
            visible=False,
        )
        self._residual_pane = pn.pane.HoloViews(
            self._empty_curve("Residual"),
            sizing_mode=self._STRETCH_WIDTH,
            height=180,
            margin=(8, 0, 0, 0),
            visible=False,
        )
        self._parameter_pane = pn.pane.HTML(
            "",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            visible=False,
        )

        controls = pn.Column(
            self._area_select,
            pn.pane.Markdown(
                "**Curves**",
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0, 0, 2, 0),
            ),
            self._layer_selector,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={"max-width": "100%", "min-width": "0"},
        )
        body = pn.Column(
            self._placeholder,
            controls,
            self._summary_pane,
            self._plot_pane,
            self._residual_pane,
            self._parameter_pane,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={
                "box-sizing": "border-box",
                "max-width": "100%",
                "min-width": "0",
                "overflow-x": "hidden",
                "padding": "0 10px 12px 10px",
            },
        )

        self._area_select.param.watch(self._on_selection_changed, "value")
        self._layer_selector.param.watch(self._on_selection_changed, "value")

        super().__init__(
            body,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["nlls-results-view"],
            margin=0,
            styles={
                "box-sizing": "border-box",
                "max-width": "100%",
                "min-width": "0",
                "overflow-x": "hidden",
            },
            **params,
        )

    @property
    def area_select(self) -> pn.widgets.Select:
        return self._area_select

    @property
    def layer_selector(self) -> pn.widgets.CheckButtonGroup:
        return self._layer_selector

    @property
    def summary_pane(self) -> pn.pane.HTML:
        return self._summary_pane

    @property
    def plot_pane(self) -> pn.pane.HoloViews:
        return self._plot_pane

    @property
    def residual_pane(self) -> pn.pane.HoloViews:
        return self._residual_pane

    @property
    def parameter_pane(self) -> pn.pane.HTML:
        return self._parameter_pane

    def clear(self, message: str | None = None) -> None:
        """Remove stale results and restore the empty-state call to action."""
        self._snapshots = {}
        self._area_labels = {}
        self._eloss = np.array([], dtype=float)
        self._area_select.options = {}
        self._area_select.value = None
        self._area_select.disabled = True
        self._layer_selector.disabled = True
        self._placeholder.object = message or (
            "Fit a reference to inspect the spectrum, best fit, components and residual."
        )
        self._placeholder.visible = True
        self._summary_pane.visible = False
        self._plot_pane.visible = False
        self._residual_pane.visible = False
        self._parameter_pane.visible = False

    def render(
        self,
        snapshots: Mapping[str, ReferenceFitSnapshot],
        area_labels: Mapping[str, str],
        eloss: np.ndarray,
        *,
        preferred_area: str | None = None,
    ) -> None:
        """Publish current reference snapshots and render the preferred one."""
        valid = {
            str(area_id): snapshot
            for area_id, snapshot in snapshots.items()
            if snapshot.success
        }
        if not valid:
            self.clear()
            return

        self._snapshots = valid
        self._area_labels = {
            area_id: str(area_labels.get(area_id, area_id)) for area_id in valid
        }
        self._eloss = np.asarray(eloss, dtype=float).reshape(-1)

        options: dict[str, str] = {}
        for area_id in valid:
            label = self._area_labels[area_id]
            option_label = label if label not in options else f"{label} ({area_id})"
            options[option_label] = area_id

        current = self._area_select.value
        selected = (
            preferred_area
            if preferred_area in valid
            else current if current in valid else next(iter(valid))
        )
        self._area_select.options = options
        self._area_select.value = selected
        self._area_select.disabled = len(valid) < 2
        self._layer_selector.disabled = False
        self._placeholder.visible = False
        self._render_selected()

    def _on_selection_changed(self, event) -> None:
        self._render_selected()

    def _render_selected(self) -> None:
        area_id = self._area_select.value
        snapshot = self._snapshots.get(str(area_id))
        if snapshot is None:
            return

        self._summary_pane.object = self._summary_html(snapshot)
        self._plot_pane.object = self._fit_overlay(snapshot)
        self._residual_pane.object = self._residual_overlay(snapshot)
        self._parameter_pane.object = self._parameter_table_html(snapshot)
        self._summary_pane.visible = True
        self._plot_pane.visible = True
        self._residual_pane.visible = True
        self._parameter_pane.visible = True

    def _axis_for(self, values: np.ndarray) -> np.ndarray:
        values = np.asarray(values).reshape(-1)
        if self._eloss.size == values.size:
            return self._eloss
        return np.arange(values.size, dtype=float)

    @staticmethod
    def _finite_curve(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_values = np.asarray(x, dtype=float).reshape(-1)
        y_values = np.asarray(y, dtype=float).reshape(-1)
        size = min(x_values.size, y_values.size)
        x_values = x_values[:size]
        y_values = y_values[:size]
        finite = np.isfinite(x_values) & np.isfinite(y_values)
        return x_values[finite], y_values[finite]

    def _curve(self, x: np.ndarray, y: np.ndarray, label: str, **opts):
        curve_x, curve_y = self._finite_curve(x, y)
        return hv.Curve(
            (curve_x, curve_y),
            kdims=["Energy loss (eV)"],
            vdims=["Electron count"],
            label=label,
        ).opts(**opts)

    def _fit_overlay(self, snapshot: ReferenceFitSnapshot):
        layers = set(self._layer_selector.value)
        axis = self._axis_for(snapshot.reference_spectrum)
        curves = []
        if "Reference" in layers:
            curves.append(
                self._curve(
                    axis,
                    snapshot.reference_spectrum,
                    "Reference",
                    color="#202020",
                    line_width=1.7,
                    alpha=0.88,
                )
            )
        if "Best fit" in layers:
            curves.append(
                self._curve(
                    axis,
                    snapshot.best_fit,
                    "Best fit",
                    color=self._FIT_COLOR,
                    line_width=2.2,
                )
            )
        if "Components" in layers:
            for index, (name, values) in enumerate(snapshot.components.items()):
                curves.append(
                    self._curve(
                        self._axis_for(values),
                        values,
                        self._component_label(name),
                        color=self._COMPONENT_COLORS[index % len(self._COMPONENT_COLORS)],
                        line_width=1.25,
                        line_dash="dashed",
                        alpha=0.9,
                    )
                )
        if not curves:
            curves.append(self._empty_curve("Reference fit"))

        curves.extend(
            [
                hv.VLine(snapshot.fit_range.minimum).opts(
                    color=self._SECONDARY_COLOR,
                    line_dash="dotted",
                    line_width=1,
                    alpha=0.55,
                ),
                hv.VLine(snapshot.fit_range.maximum).opts(
                    color=self._SECONDARY_COLOR,
                    line_dash="dotted",
                    line_width=1,
                    alpha=0.55,
                ),
            ]
        )
        return hv.Overlay(curves).opts(
            hv.opts.Overlay(
                responsive=True,
                height=275,
                shared_axes=False,
                framewise=True,
                show_legend=True,
                legend_position="top_left",
                tools=["hover", "wheel_zoom", "pan", "reset"],
                active_tools=["wheel_zoom"],
                xlabel="Energy loss (eV)",
                ylabel="Electron count",
                title=f"Reference fit — {self._area_labels.get(snapshot.area_id, snapshot.area_id)}",
            )
        )

    def _residual_overlay(self, snapshot: ReferenceFitSnapshot):
        residual = self._curve(
            self._axis_for(snapshot.residual),
            snapshot.residual,
            "Residual",
            color=self._SECONDARY_COLOR,
            line_width=1.4,
        )
        zero = hv.HLine(0.0).opts(
            color="#666666", line_dash="dashed", line_width=1, alpha=0.6
        )
        return (residual * zero).opts(
            hv.opts.Overlay(
                responsive=True,
                height=170,
                shared_axes=False,
                framewise=True,
                show_legend=False,
                tools=["hover", "wheel_zoom", "pan", "reset"],
                active_tools=["wheel_zoom"],
                xlabel="Energy loss (eV)",
                ylabel="Residual",
                title="Residual (data − best fit)",
            )
        )

    @staticmethod
    def _component_label(name: str) -> str:
        label = str(name).rstrip("_").replace("_", " ")
        return label or "Component"

    @staticmethod
    def _empty_curve(title: str):
        return hv.Curve(
            ([], []), kdims=["Energy loss (eV)"], vdims=["Electron count"]
        ).opts(
            responsive=True,
            height=250,
            title=title,
            xlabel="Energy loss (eV)",
            ylabel="Electron count",
        )

    def _summary_html(self, snapshot: ReferenceFitSnapshot) -> str:
        label = escape(self._area_labels.get(snapshot.area_id, snapshot.area_id))
        strategy = {
            "roi_mean": "Current ROI mean",
            "central_mean": "Central window mean",
            "clustering_mean": "Cluster mean",
        }.get(snapshot.reference_strategy, snapshot.reference_strategy)
        composition = {
            "continuum_only": "Continuum only",
            "continuum_plus_elnes": "Continuum + ELNES",
        }.get(snapshot.model_composition.value, snapshot.model_composition.value)
        message = escape(snapshot.message or "Converged")
        return f"""
        <div style="box-sizing:border-box;max-width:100%;border-radius:4px;
                    box-shadow:0 0 5px #d8d8d8;background:#f7f7f7;overflow:hidden;">
          <div style="background:{self._FIT_COLOR};color:white;padding:8px 10px;
                      font-weight:600;text-align:center;">{label}</div>
          <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
                      gap:7px;padding:10px;">
            {self._metric_html("Reduced χ²", self._format_number(snapshot.redchi))}
            {self._metric_html("Pixels", str(snapshot.reference_pixel_count))}
            {self._metric_html("Reference", escape(str(strategy)))}
            {self._metric_html("Model", escape(composition))}
          </div>
          <div style="border-top:1px solid #dedede;padding:7px 10px;font-size:0.78rem;
                      line-height:1.35;overflow-wrap:anywhere;">
            <b>Method:</b> {escape(snapshot.method)} ·
            <b>Fit range:</b> {snapshot.fit_range.minimum:g}–{snapshot.fit_range.maximum:g} eV<br>
            <span style="color:#555;">{message}</span>
          </div>
        </div>
        """

    @staticmethod
    def _metric_html(label: str, value: str) -> str:
        return f"""
        <div style="min-width:0;border:1px solid #e0e0e0;border-radius:4px;
                    background:white;padding:6px;text-align:center;overflow:hidden;">
          <div style="color:#666;font-size:0.68rem;text-transform:uppercase;
                      letter-spacing:0.03em;">{label}</div>
          <div style="font-size:0.84rem;font-weight:600;overflow-wrap:anywhere;">{value}</div>
        </div>
        """

    def _parameter_table_html(self, snapshot: ReferenceFitSnapshot) -> str:
        rows = []
        for parameter in snapshot.params:
            name = escape(str(parameter.get("name", "")))
            value = self._format_number(parameter.get("value"))
            stderr = self._format_number(parameter.get("stderr"), missing="—")
            bounds = (
                f"{self._format_number(parameter.get('min'))} … "
                f"{self._format_number(parameter.get('max'))}"
            )
            state = "free" if parameter.get("vary", False) else "fixed"
            rows.append(
                "<tr>"
                f"<td>{name}</td><td>{value}</td><td>{stderr}</td>"
                f"<td>{bounds}</td><td>{state}</td>"
                "</tr>"
            )
        rows_html = "".join(rows) or (
            '<tr><td colspan="5" style="text-align:center;">No fitted parameters</td></tr>'
        )
        return f"""
        <div style="box-sizing:border-box;max-width:100%;border-radius:4px;
                    box-shadow:0 0 5px #d8d8d8;background:#f7f7f7;overflow:hidden;">
          <div style="background:{self._SECONDARY_COLOR};color:white;padding:8px 10px;
                      font-weight:600;text-align:center;">Fitted parameters</div>
          <div style="max-width:100%;overflow-x:auto;">
            <table style="border-collapse:collapse;width:100%;font-size:0.72rem;">
              <thead><tr style="background:#eeeeee;">
                <th style="text-align:left;padding:6px;">Parameter</th>
                <th style="text-align:right;padding:6px;">Value</th>
                <th style="text-align:right;padding:6px;">Std. err.</th>
                <th style="text-align:right;padding:6px;">Bounds</th>
                <th style="text-align:left;padding:6px;">State</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>
        """

    @staticmethod
    def _format_number(value, *, missing: str = "—") -> str:
        if value is None:
            return missing
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return escape(str(value))
        if math.isnan(numeric):
            return missing
        if math.isinf(numeric):
            return "−∞" if numeric < 0 else "∞"
        return f"{numeric:.6g}"
