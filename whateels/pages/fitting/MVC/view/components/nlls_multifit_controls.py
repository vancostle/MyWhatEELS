"""Sidebar controls for the dense Elemental NLLS runs drawn in the main area."""

from __future__ import annotations

import panel as pn

from ..plots.nlls_multifit_results_plot import NLLSMultifitResultsPlot


class NLLSMultifitControls(pn.Column):
    """Drive the stacked run plots from a single block in the ``Results`` tab.

    Every run keeps owning its own widgets (see ``NLLSMultifitResultsPlot.controls``).
    This block mounts exactly one of those widget sets at a time and puts the run
    selector between the map selector and the curve grid, so the top control stays
    ``Result map`` no matter how many runs are stacked in the main area.
    """

    _STRETCH_WIDTH = "stretch_width"

    def __init__(self, **params) -> None:
        self._runs: list[NLLSMultifitResultsPlot] = []

        self._run_select = pn.widgets.Select(
            name="Run",
            options={},
            value=None,
            disabled=True,
            visible=False,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        self._placeholder = pn.pane.Alert(
            "Run Elemental NLLS to inspect result maps and pixel spectra.",
            alert_type="light",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 10, 0),
        )
        self._controls_slot = pn.Column(
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={"max-width": "100%", "min-width": "0"},
        )

        self._run_select.param.watch(self._on_run_changed, "value")

        super().__init__(
            self._placeholder,
            self._controls_slot,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["nlls-multifit-controls"],
            margin=0,
            styles={
                "box-sizing": "border-box",
                "max-width": "100%",
                "min-width": "0",
                "overflow-x": "hidden",
                # The hosting SimpleDetails already insets its content by 10 px.
                "padding": "0 0 2px 0",
            },
            **params,
        )

    @property
    def run_select(self) -> pn.widgets.Select:
        return self._run_select

    @property
    def runs(self) -> tuple[NLLSMultifitResultsPlot, ...]:
        """Registered runs, newest first, matching the main-area stacking order."""
        return tuple(self._runs)

    @property
    def active_run(self) -> NLLSMultifitResultsPlot | None:
        value = self._run_select.value
        return value if isinstance(value, NLLSMultifitResultsPlot) else None

    def register(self, result_view: NLLSMultifitResultsPlot) -> None:
        """Add a freshly published run and select it."""
        if any(run is result_view for run in self._runs):
            return
        self._runs.insert(0, result_view)
        self._refresh_options(preferred=result_view)

    def unregister(self, result_view: NLLSMultifitResultsPlot) -> None:
        """Drop a run whose plots are no longer in the main area."""
        remaining = [run for run in self._runs if run is not result_view]
        if len(remaining) == len(self._runs):
            return
        self._runs = remaining
        self._refresh_options()

    def clear_runs(self) -> None:
        """Detach every run, restoring the empty-state call to action."""
        self._runs = []
        self._refresh_options()

    def _refresh_options(
        self,
        preferred: NLLSMultifitResultsPlot | None = None,
    ) -> None:
        options: dict[str, NLLSMultifitResultsPlot] = {}
        for run in self._runs:
            label = run.run_label
            if label in options:
                label = f"{label} ({id(run)})"
            options[label] = run

        current = self._run_select.value
        if preferred is not None and preferred in self._runs:
            selected = preferred
        elif any(current is run for run in self._runs):
            selected = current
        else:
            selected = self._runs[0] if self._runs else None

        self._run_select.options = options
        self._run_select.value = selected
        # A single run needs no selector: it would only repeat the plot title.
        self._run_select.visible = len(self._runs) > 1
        self._run_select.disabled = len(self._runs) < 2
        self._placeholder.visible = not self._runs
        self._mount(selected)

    def _mount(self, run: NLLSMultifitResultsPlot | None) -> None:
        """Show one run's widgets. Only one mount point may hold them at a time."""
        if run is None:
            self._controls_slot.objects = []
            return
        controls = run.controls
        # `Result map` first, then the run selector, exactly as in the reference
        # block where the area selector sits on top.
        self._controls_slot.objects = [controls[0], self._run_select, *controls[1:]]

    def _on_run_changed(self, event) -> None:
        self._mount(
            event.new if isinstance(event.new, NLLSMultifitResultsPlot) else None
        )
