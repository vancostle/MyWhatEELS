"""Interactive main-area plots for dense Elemental NLLS results."""

from __future__ import annotations

import json
from html import escape

import holoviews as hv
from holoviews import streams as hv_streams
import numpy as np
import panel as pn
import xarray as xr

from whateels.helpers.bokeh_geometry import square_pixel_plot_hook
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
    }
    _INTERNAL_MAPS = {"AreaLabel"}

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
        present_status_codes = tuple(
            int(code)
            for code in sorted(
                np.unique(np.asarray(results["FitStatus"].values, dtype=int))
            )
        )
        self._status_filter = pn.widgets.MultiChoice(
            name="Fit status filter",
            options={self._status_name(code): code for code in present_status_codes},
            value=list(present_status_codes),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._max_redchi = pn.widgets.FloatInput(
            name="Maximum reduced chi-square",
            value=None,
            start=0.0,
            placeholder="No limit",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._max_relative_error = pn.widgets.FloatInput(
            name="Maximum relative error",
            value=None,
            start=0.0,
            placeholder="No limit",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._log_redchi = pn.widgets.Checkbox(
            name="Logarithmic reduced chi-square",
            value=False,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 6, 0),
        )
        self._area_fill_button = pn.widgets.Toggle(
            name="Fill",
            value=True,
            button_type="default",
            sizing_mode=self._STRETCH_WIDTH,
            height=32,
            margin=0,
        )
        self._area_boundaries_button = pn.widgets.Toggle(
            name="Boundaries",
            value=True,
            button_type="default",
            sizing_mode=self._STRETCH_WIDTH,
            height=32,
            margin=0,
        )
        self._area_overlay_controls = pn.Row(
            self._area_fill_button,
            self._area_boundaries_button,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            styles={
                "display": "flex",
                "gap": "4px",
                "min-width": "0",
                "max-width": "100%",
            },
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
        self._pixel_summary = pn.pane.HTML(
            "",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._filter_summary = pn.pane.HTML(
            "",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )

        self._selected_pixel = self._default_pixel()
        self._map_pane = pn.pane.HoloViews(
            self._empty_image(),
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
            styles={
                "min-height": "0",
                "min-width": "0",
            },
        )
        self._spectrum_pane = pn.pane.HoloViews(
            self._empty_curve(),
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
        )
        self._map_pipe = None
        self._map_dmap = None
        self._map_structure = None
        self._map_current_plot = None
        self._spectrum_pipe = None
        self._spectrum_dmap = None
        self._spectrum_structure = None

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
        split = pn.Row(
            left_column,
            pn.Spacer(
                width=10,
                sizing_mode="fixed",
                margin=0,
                styles={"background": "#eeeeee"},
            ),
            right_column,
            sizing_mode=self._STRETCH_BOTH,
            margin=0,
        )
        self._split = split

        # Sidebar widgets, in display order. They are deliberately NOT children of this
        # Column: the Results tab mounts them so a single menu drives the selected run.
        self._control_widgets = (
            self._map_select,
            pn.pane.Markdown(
                "**Area overlay**",
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0, 0, 2, 0),
            ),
            self._area_overlay_controls,
            pn.pane.Markdown(
                "**Curves**",
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0, 0, 2, 0),
            ),
            self._layer_selector,
            self._pixel_summary,
        )
        self._filter_widgets = (
            self._status_filter,
            self._max_redchi,
            self._max_relative_error,
            self._log_redchi,
            self._filter_summary,
        )

        self._watchers.extend(
            [
                self._map_select.param.watch(self._on_map_changed, "value"),
                self._layer_selector.param.watch(self._on_layers_changed, "value"),
                self._area_fill_button.param.watch(
                    self._on_overlay_changed, "value"
                ),
                self._area_boundaries_button.param.watch(
                    self._on_overlay_changed, "value"
                ),
                self._status_filter.param.watch(self._on_filter_changed, "value"),
                self._max_redchi.param.watch(self._on_filter_changed, "value"),
                self._max_relative_error.param.watch(
                    self._on_filter_changed, "value"
                ),
                self._log_redchi.param.watch(self._on_map_changed, "value"),
            ]
        )
        self._update_filter_availability()
        self._render_map()
        self._render_spectrum()

        params.setdefault("height", 620)
        params.setdefault("min_height", 620)
        params.setdefault("max_height", 620)
        params.setdefault("sizing_mode", self._STRETCH_WIDTH)
        params.setdefault("margin", (0, 0, 12, 0))
        params.setdefault("css_classes", ["nlls-multifit-result"])
        params.setdefault(
            "styles",
            {
                "box-sizing": "border-box",
                "flex": "0 0 620px",
                "height": "620px",
                "max-width": "100%",
                "min-height": "620px",
                "min-width": "0",
                # Do not paint-clip Bokeh's title/axes/colorbar while its
                # layout solver is settling after a sibling is published.
                "overflow": "visible",
                "padding": "8px 0",
                "contain": "layout",
                "isolation": "isolate",
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
    def filter_controls(self) -> tuple:
        """Live pixel filters mounted by the Results modal for this run."""
        return self._filter_widgets

    @property
    def map_select(self) -> pn.widgets.Select:
        return self._map_select

    @property
    def layer_selector(self) -> pn.widgets.CheckButtonGroup:
        return self._layer_selector

    @property
    def status_filter(self) -> pn.widgets.MultiChoice:
        return self._status_filter

    @property
    def max_redchi_input(self) -> pn.widgets.FloatInput:
        return self._max_redchi

    @property
    def max_relative_error_input(self) -> pn.widgets.FloatInput:
        return self._max_relative_error

    @property
    def area_overlay_controls(self) -> pn.Row:
        return self._area_overlay_controls

    @property
    def area_fill_button(self) -> pn.widgets.Toggle:
        return self._area_fill_button

    @property
    def area_boundaries_button(self) -> pn.widgets.Toggle:
        return self._area_boundaries_button

    @property
    def visible_pixel_mask(self) -> np.ndarray:
        """Current shared mask used by the map and pixel-spectrum selection."""
        return np.array(self._visibility_mask(), copy=True)

    @property
    def split(self) -> pn.Row:
        """Native two-pane row hosting this run's map and spectrum."""
        return self._split

    @property
    def map_pane(self) -> pn.pane.HoloViews:
        return self._map_pane

    @property
    def spectrum_pane(self) -> pn.pane.HoloViews:
        return self._spectrum_pane

    @property
    def current_map_plot(self):
        """Latest map frame sent through the persistent HoloViews pipe."""
        return self._map_current_plot

    @property
    def current_spectrum_plot(self):
        """Latest spectrum frame sent through the persistent HoloViews pipe."""
        return self._spectrum_pipe.data if self._spectrum_pipe is not None else None

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
        reserved = set(cls._BASE_MAPS.values()) | cls._INTERNAL_MAPS
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

    def _area_ids_by_label(self) -> dict[int, str]:
        raw = self._results["AreaLabel"].attrs.get("area_ids_by_label", "")
        try:
            values = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(values, dict):
                return {int(label): str(area_id) for label, area_id in values.items()}
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return {}

    def _area_name(self, label: int) -> str:
        if int(label) < 0:
            return "not selected"
        return self._area_ids_by_label().get(int(label), f"area {int(label)}")

    def _parameter_error_variables(self) -> tuple[str, str] | None:
        variable = str(self._map_select.value)
        if variable.endswith("__stderr"):
            value_variable = variable.removesuffix("__stderr")
            if value_variable in self._results:
                return value_variable, variable
            return None
        stderr_variable = f"{variable}__stderr"
        if stderr_variable in self._results:
            return variable, stderr_variable
        return None

    @staticmethod
    def _active_limit(value) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if np.isfinite(numeric) and numeric >= 0.0 else None

    def _relative_error(self) -> np.ndarray | None:
        variables = self._parameter_error_variables()
        if variables is None:
            return None
        value_variable, stderr_variable = variables
        values = np.asarray(self._results[value_variable].values, dtype=float)
        stderr = np.asarray(self._results[stderr_variable].values, dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            relative = np.abs(stderr) / np.abs(values)
        return relative

    def _visibility_mask(self) -> np.ndarray:
        status = np.asarray(self._results["FitStatus"].values, dtype=int)
        selected_codes = np.asarray(tuple(self._status_filter.value), dtype=int)
        if selected_codes.size:
            mask = np.isin(status, selected_codes)
        else:
            mask = np.zeros(status.shape, dtype=bool)

        redchi_limit = self._active_limit(self._max_redchi.value)
        if redchi_limit is not None:
            redchi = np.asarray(
                self._results["ReducedChiSquare"].values, dtype=float
            )
            mask &= np.isfinite(redchi) & (redchi <= redchi_limit)

        relative_limit = self._active_limit(self._max_relative_error.value)
        relative_error = self._relative_error()
        if relative_limit is not None and relative_error is not None:
            mask &= np.isfinite(relative_error) & (relative_error <= relative_limit)
        return mask

    def _ensure_visible_selection(self) -> bool:
        mask = self._visibility_mask()
        row, column = self._selected_pixel
        if mask[row, column]:
            return True
        status = np.asarray(self._results["FitStatus"].values, dtype=int)
        candidates = np.argwhere(mask & (status == int(FitStatus.SUCCESS)))
        if candidates.size == 0:
            candidates = np.argwhere(mask)
        if candidates.size == 0:
            return False
        row, column = candidates[0]
        self._selected_pixel = int(row), int(column)
        return True

    def _update_filter_availability(self) -> None:
        variable = str(self._map_select.value)
        self._max_relative_error.disabled = (
            self._parameter_error_variables() is None
        )
        self._log_redchi.disabled = variable != "ReducedChiSquare"

    def _filter_summary_html(self) -> str:
        visible = int(np.count_nonzero(self._visibility_mask()))
        total = int(np.prod(self._spatial_shape))
        return (
            '<div style="box-sizing:border-box;border:1px solid #dedee8;'
            'border-radius:5px;background:#f7f7fb;padding:6px 9px;">'
            f"<strong>Visible pixels:</strong> {visible}/{total}</div>"
        )

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

    @staticmethod
    def _status_name(code: int) -> str:
        return FIT_STATUS_LABELS.get(int(code), f"unknown ({code})").replace("_", " ")

    def _pixel_summary_html(self, row: int, column: int) -> str:
        status = int(self._results["FitStatus"].values[row, column])
        area = int(self._results["AreaLabel"].values[row, column])
        redchi = float(self._results["ReducedChiSquare"].values[row, column])
        redchi_text = f"{redchi:.6g}" if np.isfinite(redchi) else "N/A"
        relative_error = self._relative_error()
        relative_text = ""
        if relative_error is not None:
            value = float(relative_error[row, column])
            formatted = f"{value:.3g}" if np.isfinite(value) else "N/A"
            relative_text = f" · <strong>Relative error:</strong> {formatted}"
        return (
            '<div style="box-sizing:border-box;border-left:4px solid #ca4bc8;'
            'background:#faf4fa;padding:6px 9px;">'
            f"<strong>Pixel:</strong> y={row}, x={column}<br>"
            f"<strong>Status:</strong> {escape(self._status_name(status))} · "
            f"<strong>Area:</strong> {escape(self._area_name(area))} · "
            f"<strong>Reduced χ²:</strong> {redchi_text}{relative_text}"
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

    def _area_overlay_image(self):
        labels = np.asarray(self._results["AreaLabel"].values, dtype=float)
        labels = np.where(labels >= 0, labels, np.nan)
        ny, nx = self._spatial_shape
        return hv.Image(
            (np.arange(nx), np.arange(ny), labels),
            kdims=["x", "y"],
            vdims=["Area overlay"],
        ).opts(
            cmap="Category20",
            alpha=0.24,
            colorbar=False,
            invert_yaxis=True,
            responsive=True,
            shared_axes=False,
            tools=[],
        )

    def _area_boundary_segments(self) -> tuple[tuple[float, float, float, float], ...]:
        labels = np.asarray(self._results["AreaLabel"].values, dtype=int)
        ny, nx = labels.shape
        segments: set[tuple[float, float, float, float]] = set()

        def add(x0: float, y0: float, x1: float, y1: float) -> None:
            first = (float(x0), float(y0))
            second = (float(x1), float(y1))
            if second < first:
                first, second = second, first
            segments.add((*first, *second))

        for row, column in np.argwhere(labels >= 0):
            label = labels[row, column]
            x0, x1 = column - 0.5, column + 0.5
            y0, y1 = row - 0.5, row + 0.5
            if row == 0 or labels[row - 1, column] != label:
                add(x0, y0, x1, y0)
            if row == ny - 1 or labels[row + 1, column] != label:
                add(x0, y1, x1, y1)
            if column == 0 or labels[row, column - 1] != label:
                add(x0, y0, x0, y1)
            if column == nx - 1 or labels[row, column + 1] != label:
                add(x1, y0, x1, y1)
        return tuple(sorted(segments))

    def _area_boundaries(self):
        segments = self._area_boundary_segments()
        # ``hv.Segments`` treats a tuple as column-oriented input
        # ``(x0, y0, x1, y1)``.  ``_area_boundary_segments`` is row-oriented,
        # so passing its tuple directly made HoloViews consume only the first
        # four rows as four malformed columns.  An explicit (N, 4) ndarray
        # preserves every calculated boundary segment.
        segment_data = np.asarray(segments, dtype=float).reshape((-1, 4))
        outline = hv.Segments(
            segment_data,
            kdims=["x0", "y0", "x1", "y1"],
        ).opts(color="#202020", line_width=3.5, alpha=0.8, tools=[])
        highlight = hv.Segments(
            segment_data,
            kdims=["x0", "y0", "x1", "y1"],
        ).opts(color="#ffffff", line_width=1.4, alpha=1.0, tools=[])
        return outline * highlight

    @staticmethod
    def _robust_clim(values: np.ndarray) -> tuple[float, float] | None:
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size < 2:
            return None
        lower, upper = np.nanpercentile(finite, (2.0, 98.0))
        if not np.isfinite(lower) or not np.isfinite(upper) or lower == upper:
            return None
        return float(lower), float(upper)

    def _map_plot(self):
        variable = str(self._map_select.value)
        values = np.asarray(self._results[variable].values, dtype=float)
        values = np.where(self._visibility_mask(), values, np.nan)
        ny, nx = self._spatial_shape
        label = next(
            (text for text, name in self._map_variables.items() if name == variable),
            self._friendly_name(variable),
        )
        if variable == "ReducedChiSquare" and bool(self._log_redchi.value):
            with np.errstate(divide="ignore", invalid="ignore"):
                values = np.where(values > 0.0, np.log10(values), np.nan)
            label = f"log10 {label}"
        options = {
            "colorbar": True,
            "invert_yaxis": True,
            "xaxis": None,
            "yaxis": None,
            "responsive": True,
            "shared_axes": False,
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
        else:
            options.update(cmap="Viridis")
            robust_clim = self._robust_clim(values)
            if robust_clim is not None:
                options["clim"] = robust_clim

        image = hv.Image(
            (np.arange(nx), np.arange(ny), values),
            kdims=["x", "y"],
            vdims=[label],
        ).opts(**options)
        layers = [image]
        if self._area_fill_button.value:
            layers.append(self._area_overlay_image())
        if self._area_boundaries_button.value:
            layers.append(self._area_boundaries())
        row, column = self._selected_pixel
        marker_data = (
            [(column, row)] if self._visibility_mask()[row, column] else []
        )
        layers.append(
            hv.Points(marker_data, kdims=["x", "y"]).opts(
                color=self._FIT_COLOR,
                fill_color="white",
                line_color=self._FIT_COLOR,
                line_width=3,
                marker="circle",
                size=11,
                tools=[],
            )
        )
        return hv.Overlay(layers).opts(
            hv.opts.Overlay(
                responsive=True,
                shared_axes=False,
                framewise=True,
                hooks=[square_pixel_plot_hook],
            )
        )

    @staticmethod
    def _plot_structure(plot) -> tuple:
        """Return the renderer structure that a DynamicMap may update in-place."""
        try:
            elements = list(plot.values()) if isinstance(plot, hv.Overlay) else [plot]
        except Exception:
            elements = [plot]
        return tuple(
            (
                type(element).__name__,
                str(getattr(element, "group", "")),
                str(getattr(element, "label", "")),
            )
            for element in elements
        )

    def _push_map_plot(self, plot) -> None:
        """Update map data without replacing the rendered Bokeh layout."""
        structure = self._plot_structure(plot)
        if self._map_pipe is not None and structure == self._map_structure:
            self._map_current_plot = plot
            self._map_pipe.send(plot)
            return
        self._dispose_tap_stream()
        self._map_pipe = hv_streams.Pipe(data=None)
        # The Tap stream must be an input of the rendered DynamicMap. Binding it
        # to an element returned *inside* a Pipe-backed DynamicMap does not
        # register a Bokeh ``tap`` event callback, so browser clicks never reach
        # Python even though direct calls to ``_on_pixel_tapped`` appear to work.
        self._tap_stream = hv_streams.Tap(x=None, y=None)
        self._map_dmap = hv.DynamicMap(
            self._map_dynamic_frame,
            streams=[self._map_pipe, self._tap_stream],
        )
        self._map_current_plot = plot
        self._map_pipe.send(plot)
        self._map_structure = structure
        self._map_pane.object = self._map_dmap

    def _dispose_tap_stream(self) -> None:
        """Clear the Tap input before replacing its DynamicMap."""
        stream = self._tap_stream
        if stream is None:
            return
        try:
            stream.clear()
        except Exception:
            pass
        self._tap_stream = None

    def _map_dynamic_frame(self, data, x=None, y=None):
        """Return a tapped map frame without recursively sending its own Pipe."""
        frame = data
        if x is not None and y is not None and self._select_pixel(x=x, y=y):
            frame = self._map_plot()
        self._map_current_plot = frame
        return frame

    def _push_spectrum_plot(self, plot) -> None:
        """Update selected-pixel curves without rebuilding their Bokeh figure."""
        structure = self._plot_structure(plot)
        if self._spectrum_pipe is not None and structure == self._spectrum_structure:
            self._spectrum_pipe.send(plot)
            return
        self._spectrum_pipe = hv_streams.Pipe(data=None)
        self._spectrum_dmap = hv.DynamicMap(
            lambda data: data,
            streams=[self._spectrum_pipe],
        )
        self._spectrum_pipe.send(plot)
        self._spectrum_structure = structure
        self._spectrum_pane.object = self._spectrum_dmap

    def _render_map(self) -> None:
        self._push_map_plot(self._map_plot())

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
        self._filter_summary.object = self._filter_summary_html()
        if not self._ensure_visible_selection():
            self._pixel_summary.object = (
                '<div style="box-sizing:border-box;border-left:4px solid #dc3545;'
                'background:#fff4f4;padding:6px 9px;">'
                "No pixels match the active filters.</div>"
            )
            empty_plot = hv.Overlay([self._empty_curve()]).opts(
                hv.opts.Overlay(
                    responsive=True,
                    shared_axes=False,
                    framewise=True,
                    xlabel="Energy loss (eV)",
                    ylabel="Electron count",
                    title=f"Run {self._run_number} · No pixels match filters",
                )
            )
            self._push_spectrum_plot(empty_plot)
            return
        row, column = self._selected_pixel
        self._pixel_summary.object = self._pixel_summary_html(row, column)
        self._push_spectrum_plot(self._spectrum_plot(row, column))

    def _on_map_changed(self, event) -> None:
        self._update_filter_availability()
        self._ensure_visible_selection()
        self._render_map()
        self._render_spectrum()

    def _on_layers_changed(self, event) -> None:
        self._render_spectrum()

    def _on_overlay_changed(self, event) -> None:
        self._render_map()

    def _on_filter_changed(self, event) -> None:
        self._ensure_visible_selection()
        self._render_map()
        self._render_spectrum()

    def _select_pixel(self, x=None, y=None) -> bool:
        """Apply a map coordinate and update its spectrum; return whether it changed."""
        if x is None or y is None:
            return False
        ny, nx = self._spatial_shape
        x_value = float(x)
        y_value = float(y)
        # match_aspect may letterbox the map. Clicking that empty padding must
        # not become a false selection on the nearest border pixel.
        if not (-0.5 <= x_value < nx - 0.5 and -0.5 <= y_value < ny - 0.5):
            return False
        column = int(np.clip(round(x_value), 0, nx - 1))
        row = int(np.clip(round(y_value), 0, ny - 1))
        if not self._visibility_mask()[row, column]:
            return False
        if (row, column) == self._selected_pixel:
            return False
        self._selected_pixel = (row, column)
        self._render_spectrum()
        return True

    def _on_pixel_tapped(self, x=None, y=None) -> None:
        """Compatibility entry point for non-DynamicMap callers."""
        if self._select_pixel(x=x, y=y):
            self._render_map()

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
        for pipe in (self._map_pipe, self._spectrum_pipe):
            try:
                pipe.clear()
            except Exception:
                pass
        self._map_pipe = None
        self._map_dmap = None
        self._map_current_plot = None
        self._spectrum_pipe = None
        self._spectrum_dmap = None
        self._dispose_tap_stream()
