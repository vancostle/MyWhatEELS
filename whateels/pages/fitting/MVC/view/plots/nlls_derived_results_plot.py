"""Large additive maps for datasets derived from Elemental NLLS runs."""

from __future__ import annotations

import holoviews as hv
from holoviews import streams as hv_streams
import numpy as np
import panel as pn
import xarray as xr

from whateels.helpers.bokeh_geometry import square_pixel_plot_hook


class NLLSDerivedResultsPlot(pn.Column):
    """Render one derived dataset without embedding controls in the plot area."""

    _PRIORITY = ("Distances", "Ratio", "RelativeRatio", "IntegratedIntensity")

    def __init__(
        self,
        results: xr.Dataset,
        *,
        sequence: int = 1,
        boundaries_visible: bool = True,
        **params,
    ) -> None:
        if not isinstance(results, xr.Dataset) or "y" not in results.dims or "x" not in results.dims:
            raise ValueError("derived NLLS plot requires an xarray Dataset with y and x")
        self.results = results
        self.sequence = int(sequence)
        self._boundaries_visible = bool(boundaries_visible)
        self._watchers = []
        self._map_pipe = None
        self._map_dmap = None
        self._map_structure = None
        self._map_options = self._build_map_options(results)
        if not self._map_options:
            raise ValueError("derived NLLS dataset has no numeric map")
        ordered = sorted(
            self._map_options,
            key=lambda label: next(
                (
                    index
                    for index, name in enumerate(self._PRIORITY)
                    if label.startswith(name)
                ),
                len(self._PRIORITY),
            ),
        )
        self.map_select = pn.widgets.Select(
            name="Derived result map",
            options={label: self._map_options[label] for label in ordered},
            value=self._map_options[ordered[0]],
            sizing_mode="stretch_width",
            margin=(0, 0, 8, 0),
        )
        self.map_pane = pn.pane.HoloViews(
            self._empty_image(),
            sizing_mode="stretch_both",
            margin=0,
            min_width=0,
            min_height=0,
            styles={
                "min-height": "0",
                "min-width": "0",
            },
        )
        self.controls = (self.map_select,)
        self._watchers.append(self.map_select.param.watch(self._render, "value"))
        self._render(None)
        params.setdefault("height", 560)
        params.setdefault("min_height", 560)
        params.setdefault("max_height", 560)
        params.setdefault("sizing_mode", "stretch_width")
        params.setdefault("margin", (0, 0, 12, 0))
        params.setdefault(
            "styles",
            {
                "box-sizing": "border-box",
                "flex": "0 0 560px",
                "height": "560px",
                "max-width": "100%",
                "min-height": "560px",
                "min-width": "0",
                "overflow": "visible",
                "padding": "8px 0",
                "contain": "layout",
                "isolation": "isolate",
            },
        )
        super().__init__(self.map_pane, **params)

    @staticmethod
    def _build_map_options(results: xr.Dataset) -> dict[str, tuple[str, str | None]]:
        options: dict[str, tuple[str, str | None]] = {}
        for name, variable in results.data_vars.items():
            if name in {"FitStatus", "AreaLabel"}:
                continue
            if variable.dims == ("y", "x") and np.issubdtype(variable.dtype, np.number):
                options[name] = (name, None)
            elif variable.dims == ("edge", "y", "x"):
                for edge in results.coords["edge"].values:
                    options[f"{name} — {edge}"] = (name, str(edge))
        return options

    @staticmethod
    def _boundary_segments(labels: np.ndarray):
        labels = np.asarray(labels, dtype=int)
        ny, nx = labels.shape
        segments = set()
        for row, column in np.argwhere(labels >= 0):
            current = labels[row, column]
            for neighbour, segment in (
                ((row - 1, column), (column - 0.5, row - 0.5, column + 0.5, row - 0.5)),
                ((row + 1, column), (column - 0.5, row + 0.5, column + 0.5, row + 0.5)),
                ((row, column - 1), (column - 0.5, row - 0.5, column - 0.5, row + 0.5)),
                ((row, column + 1), (column + 0.5, row - 0.5, column + 0.5, row + 0.5)),
            ):
                nrow, ncolumn = neighbour
                if not (0 <= nrow < ny and 0 <= ncolumn < nx) or labels[nrow, ncolumn] != current:
                    segments.add(tuple(float(value) for value in segment))
        # HoloViews interprets tuples as column-oriented data.  The calculated
        # segments are rows, therefore make their (N, 4) orientation explicit.
        segment_data = np.asarray(tuple(sorted(segments)), dtype=float).reshape((-1, 4))
        return hv.Segments(
            segment_data, kdims=["x0", "y0", "x1", "y1"]
        ).opts(color="white", line_width=1.5, tools=[])

    @property
    def analysis_label(self) -> str:
        value = str(self.results.attrs.get("analysis_type", "derived analysis"))
        return value.replace("_", " ")

    @property
    def boundaries_visible(self) -> bool:
        """Whether the shared area-boundary overlay is rendered."""
        return self._boundaries_visible

    @property
    def current_map_plot(self):
        """Latest derived-map frame sent through the persistent pipe."""
        return self._map_pipe.data if self._map_pipe is not None else None

    def set_boundaries_visible(self, visible: bool) -> None:
        """Apply the global Results-tab boundary state to this derived map."""
        visible = bool(visible)
        if visible == self._boundaries_visible:
            return
        self._boundaries_visible = visible
        self._render(None)

    def _render(self, event) -> None:
        name, edge = self.map_select.value
        variable = self.results[name]
        if edge is not None:
            variable = variable.sel(edge=edge)
        values = np.asarray(variable.values, dtype=float)
        status = np.asarray(self.results["FitStatus"].values, dtype=int)
        values = np.where(status == 2, values, np.nan)
        ny, nx = values.shape
        finite = values[np.isfinite(values)]
        options = dict(
            cmap="Viridis",
            colorbar=True,
            invert_yaxis=True,
            xaxis=None,
            yaxis=None,
            responsive=True,
            shared_axes=False,
            tools=["hover", "wheel_zoom", "pan", "reset"],
            active_tools=["wheel_zoom"],
            title=f"Analysis {self.sequence} · {self.analysis_label} · {self.map_select.name}: {name}",
        )
        if finite.size > 1:
            lower, upper = np.nanpercentile(finite, (2.0, 98.0))
            if np.isfinite(lower) and np.isfinite(upper) and lower != upper:
                options["clim"] = (float(lower), float(upper))
        image = hv.Image(
            (np.arange(nx), np.arange(ny), values),
            kdims=["x", "y"],
            vdims=[f"{name}{f' — {edge}' if edge is not None else ''}"],
        ).opts(**options)
        layers = [image]
        if self._boundaries_visible and "AreaLabel" in self.results:
            layers.append(self._boundary_segments(self.results["AreaLabel"].values))
        plot = hv.Overlay(layers).opts(
            hv.opts.Overlay(
                responsive=True,
                shared_axes=False,
                framewise=True,
                hooks=[square_pixel_plot_hook],
            )
        )
        structure = tuple(
            (type(layer).__name__, str(getattr(layer, "label", "")))
            for layer in layers
        )
        if self._map_pipe is not None and structure == self._map_structure:
            self._map_pipe.send(plot)
            return
        self._map_pipe = hv_streams.Pipe(data=None)
        self._map_dmap = hv.DynamicMap(
            lambda data: data,
            streams=[self._map_pipe],
        )
        self._map_pipe.send(plot)
        self._map_structure = structure
        self.map_pane.object = self._map_dmap

    @staticmethod
    def _empty_image():
        return hv.Image((np.arange(1), np.arange(1), np.zeros((1, 1))))

    def cleanup(self) -> None:
        for watcher in self._watchers:
            try:
                watcher.inst.param.unwatch(watcher)
            except Exception:
                pass
        self._watchers.clear()
        if self._map_pipe is not None:
            try:
                self._map_pipe.clear()
            except Exception:
                pass
        self._map_pipe = None
        self._map_dmap = None
