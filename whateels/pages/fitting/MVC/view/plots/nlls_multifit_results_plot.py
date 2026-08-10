"""Interactive main-area plots for dense Elemental NLLS results."""

from __future__ import annotations

import json
from html import escape

import holoviews as hv
from holoviews import streams as hv_streams
import numpy as np
import panel as pn
import xarray as xr

from whateels.components import SplitJs
from whateels.nlls.results import FIT_STATUS_LABELS, FitStatus


class NLLSMultifitResultsPlot(pn.Column):
    """Show a result map and the fitted curves of a selected pixel.

    The block only owns the two plots. Its widgets are created here but mounted by
    the ``Results`` sidebar tab, so the main area holds plots and nothing else.
    """

    _STRETCH_BOTH = "stretch_both"
    _STRETCH_WIDTH = "stretch_width"
    _FIT_COLOR = "#ca4bc8"
    _RESIDUAL_COLOR = "#dc3545"
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
    _BASE_MAPS = {
        "Reduced χ²": "ReducedChiSquare",
        "Fit status": "FitStatus",
        "Area label": "AreaLabel",
    }

    def __init__(
        self,
        results: xr.Dataset,
        *,
        run_number: int = 1,
        **params,
    ) -> None:
        self._validate_results(results)
        self._results = results
        self._run_number = int(run_number)
        self._watchers = []
        self._tap_stream = None

        self._component_variables = tuple(
            name
            for name, values in results.data_vars.items()
            if values.dims == ("y", "x", "Eloss")
            and name.endswith("__component")
        )
        self._map_variables = self._build_map_options(results)
        first_map = next(iter(self._map_variables.values()))
        self._map_select = pn.widgets.Select(
            name="Result map",
            options=self._map_variables,
            value=first_map,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._layer_selector = pn.widgets.CheckButtonGroup(
            name="Visible curves",
            options=["Original", "Best fit", "Components", "Residual"],
            value=["Original", "Best fit", "Components", "Residual"],
            button_type="default",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            stylesheets=["""
                :host .bk-btn-group {
                    display: grid !important;
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                    grid-auto-rows: 32px !important;
                    gap: 4px !important;
                    width: 100% !important;
                    min-width: 0 !important;
                }
                :host .bk-btn-group .bk-btn {
                    box-sizing: border-box !important;
                    width: 100% !important;
                    height: 32px !important;
                    min-height: 32px !important;
                    margin: 0 !important;
                    border-radius: 4px !important;
                }
            """],
        )
        self._run_summary = pn.pane.HTML(
            self._run_summary_html(),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._pixel_summary = pn.pane.HTML(
            "",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )

        ny, nx = self._spatial_shape
        xx, yy = np.meshgrid(np.arange(nx), np.arange(ny))
        self._selectors = hv.Points(
            np.column_stack([xx.ravel(), yy.ravel()]),
            kdims=["x", "y"],
        ).opts(
            size=0,
            alpha=0,
            nonselection_alpha=0,
            tools=["tap"],
            shared_axes=False,
        )
        self._selected_pixel = self._default_pixel()
        self._map_pane = pn.pane.HoloViews(
            self._empty_image(),
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
            styles={"margin": "auto"},
        )
        self._map_pane._splitjs_xy_ratio = float(nx) / float(ny) if ny else 1.0
        self._spectrum_pane = pn.pane.HoloViews(
            self._empty_curve(),
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
        )

        left_column = pn.Column(
            self._map_pane,
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
            styles={"min-height": "0", "min-width": "0"},
        )
        right_column = pn.Column(
            self._spectrum_pane,
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
            styles={"min-height": "0", "min-width": "0"},
        )
        split = SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
        )

        # Sidebar widgets, in display order. They are deliberately NOT children of this
        # Column: the Results tab mounts them so a single menu drives the selected run.
        self._control_widgets = (
            self._map_select,
            pn.pane.Markdown(
                "**Curves**",
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0, 0, 2, 0),
            ),
            self._layer_selector,
            self._run_summary,
            self._pixel_summary,
        )

        self._watchers.extend(
            [
                self._map_select.param.watch(self._on_map_changed, "value"),
                self._layer_selector.param.watch(self._on_layers_changed, "value"),
            ]
        )
        self._tap_stream = hv_streams.Tap(source=self._selectors)
        self._tap_stream.add_subscriber(self._on_pixel_tapped)
        self._render_map()
        self._render_spectrum()

        params.setdefault("height", 620)
        params.setdefault("sizing_mode", self._STRETCH_WIDTH)
        params.setdefault("margin", (0, 0, 12, 0))
        params.setdefault("css_classes", ["nlls-multifit-result"])
        params.setdefault(
            "styles",
            {
                "box-sizing": "border-box",
                "max-width": "100%",
                "min-height": "0",
                "min-width": "0",
                "overflow": "hidden",
                "padding": "8px 0",
            },
        )
        super().__init__(split, **params)

    @staticmethod
    def _validate_results(results: xr.Dataset) -> None:
        if not isinstance(results, xr.Dataset):
            raise TypeError("Elemental NLLS plots require an xarray Dataset")
        required = {
            "OriginalData",
            "AreaLabel",
            "FitStatus",
            "ReducedChiSquare",
            "BestFit",
            "Residuals",
        }
        missing = required.difference(results.data_vars)
        if missing:
            raise ValueError(
                "Elemental NLLS result is missing: " + ", ".join(sorted(missing))
            )
        if results["OriginalData"].dims != ("y", "x", "Eloss"):
            raise ValueError("Elemental NLLS result dimensions must be y, x, Eloss")

    @property
    def results(self) -> xr.Dataset:
        return self._results

    @property
    def controls(self) -> tuple:
        """Sidebar widgets for this run, in display order, mounted by the Results tab."""
        return self._control_widgets

    @property
    def map_select(self) -> pn.widgets.Select:
        return self._map_select

    @property
    def layer_selector(self) -> pn.widgets.CheckButtonGroup:
        return self._layer_selector

    @property
    def map_pane(self) -> pn.pane.HoloViews:
        return self._map_pane

    @property
    def spectrum_pane(self) -> pn.pane.HoloViews:
        return self._spectrum_pane

    @property
    def pixel_summary(self) -> pn.pane.HTML:
        return self._pixel_summary

    @property
    def selected_pixel(self) -> tuple[int, int]:
        return self._selected_pixel

    @property
    def _spatial_shape(self) -> tuple[int, int]:
        shape = self._results["FitStatus"].shape
        return int(shape[0]), int(shape[1])

    @classmethod
    def _build_map_options(cls, results: xr.Dataset) -> dict[str, str]:
        options = dict(cls._BASE_MAPS)
        reserved = set(cls._BASE_MAPS.values())
        for name, values in results.data_vars.items():
            if values.dims != ("y", "x") or name in reserved:
                continue
            if name.endswith("__stderr"):
                base_name = name.removesuffix("__stderr")
                label = f"Std. error — {cls._friendly_name(base_name)}"
            else:
                label = f"Parameter — {cls._friendly_name(name)}"
            if label in options:
                label = f"{label} ({name})"
            options[label] = name
        return options

    @staticmethod
    def _friendly_name(name: str) -> str:
        return str(name).replace("__", " · ").replace("_", " ").strip()

    def _default_pixel(self) -> tuple[int, int]:
        status = np.asarray(self._results["FitStatus"].values, dtype=int)
        candidates = np.argwhere(status == int(FitStatus.SUCCESS))
        if candidates.size == 0:
            candidates = np.argwhere(status != int(FitStatus.NOT_SELECTED))
        if candidates.size == 0:
            return 0, 0
        row, column = candidates[0]
        return int(row), int(column)

    @property
    def run_number(self) -> int:
        return self._run_number

    @property
    def run_label(self) -> str:
        """Option text for the sidebar run selector."""
        state = "complete" if bool(self._results.attrs.get("complete", False)) else "incomplete"
        return f"Run {self._run_number} — {self._selected_area_text()} — {state}"

    def _selected_area_text(self) -> str:
        raw = self._results.attrs.get("selected_areas", "")
        try:
            values = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(values, (list, tuple)) and values:
                return ", ".join(str(value) for value in values)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return "selected areas"

    def _run_summary_html(self) -> str:
        processed = int(self._results.attrs.get("processed_pixels", 0))
        selected = int(self._results.attrs.get("selected_pixels", 0))
        method = escape(str(self._results.attrs.get("method", "unknown")))
        return (
            '<div style="box-sizing:border-box;border:1px solid #dedee8;'
            'border-radius:5px;background:#f7f7fb;padding:7px 9px;">'
            f"<strong>Run {self._run_number}</strong> · {processed}/{selected} pixels · "
            f"method={method}</div>"
        )

    @staticmethod
    def _status_name(code: int) -> str:
        return FIT_STATUS_LABELS.get(int(code), f"unknown ({code})").replace("_", " ")

    def _pixel_summary_html(self, row: int, column: int) -> str:
        status = int(self._results["FitStatus"].values[row, column])
        area = int(self._results["AreaLabel"].values[row, column])
        redchi = float(self._results["ReducedChiSquare"].values[row, column])
        redchi_text = f"{redchi:.6g}" if np.isfinite(redchi) else "N/A"
        return (
            '<div style="box-sizing:border-box;border-left:4px solid #ca4bc8;'
            'background:#faf4fa;padding:6px 9px;">'
            f"<strong>Pixel:</strong> y={row}, x={column}<br>"
            f"<strong>Status:</strong> {escape(self._status_name(status))} · "
            f"<strong>Area:</strong> {area} · <strong>Reduced χ²:</strong> {redchi_text}"
            "</div>"
        )

    @staticmethod
    def _integer_colorbar_hook(labels: dict[int, str]):
        def hook(plot, element) -> None:
            try:
                from bokeh.models import CustomJSTickFormatter, FixedTicker

                figure = plot.state
                ticks = sorted(int(value) for value in labels)
                formatter_labels = json.dumps({str(key): value for key, value in labels.items()})
                for colorbar in getattr(figure, "right", ()):
                    if not hasattr(colorbar, "ticker"):
                        continue
                    colorbar.ticker = FixedTicker(ticks=ticks)
                    colorbar.formatter = CustomJSTickFormatter(
                        code=(
                            f"const labels = {formatter_labels}; "
                            "return labels[String(Math.round(tick))] ?? String(tick);"
                        )
                    )
            except Exception:
                return

        return hook

    def _map_plot(self):
        variable = str(self._map_select.value)
        values = np.asarray(self._results[variable].values, dtype=float)
        ny, nx = self._spatial_shape
        label = next(
            (text for text, name in self._map_variables.items() if name == variable),
            self._friendly_name(variable),
        )
        options = {
            "colorbar": True,
            "invert_yaxis": True,
            "xaxis": None,
            "yaxis": None,
            "responsive": True,
            "shared_axes": False,
            "aspect": "equal",
            "framewise": True,
            "tools": ["hover", "tap", "wheel_zoom", "pan", "reset"],
            "active_tools": ["wheel_zoom"],
            # Without the old card header the run number would be unreadable in a
            # stack of runs, so each plot carries it in its own title.
            "title": f"Run {self._run_number} · {label}",
        }
        if variable == "FitStatus":
            colors = ["#f0f0f0", "#edc949", "#59a14f", "#f28e2b", "#e15759", "#af7aa1"]
            options.update(
                cmap=colors,
                clim=(-0.5, len(FitStatus) - 0.5),
                hooks=[self._integer_colorbar_hook(FIT_STATUS_LABELS)],
            )
        elif variable == "AreaLabel":
            finite_labels = sorted(int(value) for value in np.unique(values[np.isfinite(values)]))
            options.update(
                cmap="Category20",
                hooks=[
                    self._integer_colorbar_hook(
                        {value: str(value) for value in finite_labels}
                    )
                ],
            )
        else:
            options.update(cmap="Viridis")

        image = hv.Image(
            (np.arange(nx), np.arange(ny), values),
            kdims=["x", "y"],
            vdims=[label],
        ).opts(**options)
        row, column = self._selected_pixel
        marker = hv.Points([(column, row)], kdims=["x", "y"]).opts(
            color=self._FIT_COLOR,
            fill_color="white",
            line_color=self._FIT_COLOR,
            line_width=3,
            marker="circle",
            size=11,
            tools=[],
        )
        return (image * self._selectors * marker).opts(
            hv.opts.Overlay(
                responsive=True,
                shared_axes=False,
                aspect="equal",
                framewise=True,
            )
        )

    def _render_map(self) -> None:
        self._map_pane.object = self._map_plot()

    @staticmethod
    def _finite_curve(x, y) -> tuple[np.ndarray, np.ndarray]:
        x_values = np.asarray(x, dtype=float).reshape(-1)
        y_values = np.asarray(y, dtype=float).reshape(-1)
        size = min(x_values.size, y_values.size)
        finite = np.isfinite(x_values[:size]) & np.isfinite(y_values[:size])
        return x_values[:size][finite], y_values[:size][finite]

    def _curve(self, x, y, label: str, **opts):
        finite_x, finite_y = self._finite_curve(x, y)
        return hv.Curve(
            (finite_x, finite_y),
            kdims=["Energy loss (eV)"],
            vdims=["Electron count"],
            label=label,
        ).opts(**opts)

    def _spectrum_plot(self, row: int, column: int):
        layers = set(self._layer_selector.value)
        eloss = np.asarray(self._results.coords["Eloss"].values, dtype=float)
        curves = []
        if "Original" in layers:
            curves.append(
                self._curve(
                    eloss,
                    self._results["OriginalData"].values[row, column, :],
                    "Original",
                    color="#202020",
                    line_width=1.7,
                    alpha=0.9,
                )
            )
        if "Best fit" in layers:
            curves.append(
                self._curve(
                    eloss,
                    self._results["BestFit"].values[row, column, :],
                    "Best fit",
                    color=self._FIT_COLOR,
                    line_width=2.2,
                )
            )
        if "Components" in layers:
            for index, variable in enumerate(self._component_variables):
                curves.append(
                    self._curve(
                        eloss,
                        self._results[variable].values[row, column, :],
                        self._friendly_name(variable.removesuffix("__component")),
                        color=self._COMPONENT_COLORS[index % len(self._COMPONENT_COLORS)],
                        line_width=1.3,
                        line_dash="dashed",
                        alpha=0.9,
                    )
                )
        if "Residual" in layers:
            curves.extend(
                [
                    self._curve(
                        eloss,
                        self._results["Residuals"].values[row, column, :],
                        "Residual",
                        color=self._RESIDUAL_COLOR,
                        line_width=1.4,
                    ),
                    hv.HLine(0.0).opts(
                        color="#666666",
                        line_dash="dashed",
                        line_width=1,
                        alpha=0.55,
                    ),
                ]
            )
        if not curves:
            curves.append(self._empty_curve())
        status = int(self._results["FitStatus"].values[row, column])
        return hv.Overlay(curves).opts(
            hv.opts.Overlay(
                responsive=True,
                shared_axes=False,
                framewise=True,
                show_legend=True,
                legend_position="top_left",
                tools=["hover", "wheel_zoom", "pan", "reset"],
                active_tools=["wheel_zoom"],
                xlabel="Energy loss (eV)",
                ylabel="Electron count",
                title=(
                    f"Run {self._run_number} · Pixel y={row}, x={column}"
                    f" — {self._status_name(status)}"
                ),
            )
        )

    def _render_spectrum(self) -> None:
        row, column = self._selected_pixel
        self._pixel_summary.object = self._pixel_summary_html(row, column)
        self._spectrum_pane.object = self._spectrum_plot(row, column)

    def _on_map_changed(self, event) -> None:
        self._render_map()

    def _on_layers_changed(self, event) -> None:
        self._render_spectrum()

    def _on_pixel_tapped(self, x=None, y=None) -> None:
        if x is None or y is None:
            return
        ny, nx = self._spatial_shape
        column = int(np.clip(round(float(x)), 0, nx - 1))
        row = int(np.clip(round(float(y)), 0, ny - 1))
        if (row, column) == self._selected_pixel:
            return
        self._selected_pixel = (row, column)
        self._render_map()
        self._render_spectrum()

    @staticmethod
    def _empty_image():
        return hv.Image((np.arange(1), np.arange(1), np.zeros((1, 1))))

    @staticmethod
    def _empty_curve():
        return hv.Curve(
            ([], []),
            kdims=["Energy loss (eV)"],
            vdims=["Electron count"],
        )

    def cleanup(self) -> None:
        for watcher in self._watchers:
            try:
                watcher.inst.param.unwatch(watcher)
            except Exception:
                pass
        self._watchers.clear()
        if self._tap_stream is not None:
            try:
                self._tap_stream.remove_subscriber(self._on_pixel_tapped)
                self._tap_stream.clear()
            except Exception:
                pass
        self._tap_stream = None
