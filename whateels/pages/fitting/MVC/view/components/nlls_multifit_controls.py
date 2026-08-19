"""Sidebar controls for the dense Elemental NLLS runs drawn in the main area."""

from __future__ import annotations

import numpy as np
import panel as pn

from .nlls_derived_analyses_modal import NLLSDerivedAnalysesModal
from .nlls_derived_results_controls_modal import NLLSDerivedResultsControlsModal
from .nlls_result_filters_modal import NLLSResultFiltersModal
from ..plots.nlls_multifit_results_plot import NLLSMultifitResultsPlot


class NLLSMultifitControls(pn.Column):
    """Drive the stacked run plots from a single block in the ``Results`` tab.

    Every run keeps owning its own widgets (see ``NLLSMultifitResultsPlot.controls``).
    This block mounts exactly one of those widget sets at a time and puts the run
    selector between the map selector and the curve grid, so the top control stays
    ``Result map`` no matter how many runs are stacked in the main area.
    """

    _STRETCH_WIDTH = "stretch_width"
    _FILTERS_MODAL_ID = "Elemental NLLS result filters"
    _DERIVED_ANALYSES_MODAL_ID = "Derived analyses"
    _DERIVED_RESULTS_MODAL_ID = "Derived results control"

    def __init__(
        self,
        *,
        custom_page=None,
        modal_manager=None,
        **params,
    ) -> None:
        self._runs: list[NLLSMultifitResultsPlot] = []
        self._derived_views: list = []
        self._boundaries_visible = True
        self._boundary_watchers: dict[int, tuple[NLLSMultifitResultsPlot, object]] = {}
        self._synchronizing_boundaries = False
        self._modal_manager = modal_manager

        self._filters_modal = NLLSResultFiltersModal(custom_page)
        self._derived_analyses_modal = NLLSDerivedAnalysesModal(custom_page)
        self._derived_results_modal = NLLSDerivedResultsControlsModal(custom_page)
        # A hidden modal must not participate in a result publication.  Its
        # controls are populated lazily when the user explicitly opens it.
        self._derived_results_modal.visible = False
        if modal_manager is not None:
            modal_manager.register_modal(self._FILTERS_MODAL_ID, self._filters_modal)
            modal_manager.register_modal(
                self._DERIVED_ANALYSES_MODAL_ID,
                self._derived_analyses_modal,
            )
            modal_manager.register_modal(
                self._DERIVED_RESULTS_MODAL_ID,
                self._derived_results_modal,
            )
        self._filters_button = pn.widgets.Button(
            name="Filters",
            button_type="default",
            height=32,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
            disabled=True,
        )
        self._filters_button.on_click(self._open_filters)
        self._derived_analyses_button = pn.widgets.Button(
            name="Derived analyses",
            button_type="default",
            height=42,
            disabled=True,
            visible=False,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(6, 0, 0, 0),
        )
        self._derived_analyses_button.on_click(self._open_derived_analyses)
        self._derived_results_button = pn.widgets.Button(
            name="Derived results control",
            button_type="primary",
            icon="adjustments-horizontal",
            height=42,
            disabled=True,
            visible=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(6, 0, 0, 0),
        )
        self._derived_results_button.on_click(self._open_derived_results)

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
        self._center_a = pn.widgets.Select(
            name="Center A", options={}, disabled=True, sizing_mode=self._STRETCH_WIDTH
        )
        self._center_b = pn.widgets.Select(
            name="Center B", options={}, disabled=True, sizing_mode=self._STRETCH_WIDTH
        )
        self._center_button = pn.widgets.Button(
            name="Get Distances",
            button_type="primary",
            disabled=True,
            sizing_mode=self._STRETCH_WIDTH,
            height=40,
        )
        self._white_a = pn.widgets.Select(
            name="White line A", options={}, disabled=True, sizing_mode=self._STRETCH_WIDTH
        )
        self._white_b = pn.widgets.Select(
            name="White line B", options={}, disabled=True, sizing_mode=self._STRETCH_WIDTH
        )
        self._white_source = pn.widgets.Select(
            name="White-line source",
            options={"Fitted components": "fitted", "Raw spectrum": "raw"},
            value="fitted",
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._white_mode = pn.widgets.Select(
            name="White-line windows",
            options={"Auto (FWHM)": "auto", "Manual": "manual"},
            value="auto",
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._white_window_a = pn.widgets.RangeSlider(
            name="Window A (eV)", start=0.0, end=1.0, value=(0.0, 1.0), visible=False,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._white_window_b = pn.widgets.RangeSlider(
            name="Window B (eV)", start=0.0, end=1.0, value=(0.0, 1.0), visible=False,
            sizing_mode=self._STRETCH_WIDTH,
        )
        self._white_invert = pn.widgets.Checkbox(
            name="Invert ratio", value=False, sizing_mode=self._STRETCH_WIDTH
        )
        self._white_button = pn.widgets.Button(
            name="Compute White Lines",
            button_type="primary",
            disabled=True,
            sizing_mode=self._STRETCH_WIDTH,
            height=40,
        )
        self._analysis_status = pn.pane.Alert(
            "Derived analyses use the selected run and preserve its status/area masks.",
            alert_type="light",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 8, 0),
        )
        # Backwards-compatible alias used by the registration code. The slot is
        # owned by the modal and is never mounted inside the SimpleDetails.
        self._derived_controls_slot = self._derived_results_modal.controls_slot
        self._analysis_controls = pn.Column(
            self._analysis_status,
            self._center_a,
            self._center_b,
            self._center_button,
            self._white_a,
            self._white_b,
            self._white_source,
            self._white_mode,
            self._white_window_a,
            self._white_window_b,
            self._white_invert,
            self._white_button,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )
        self._derived_analyses_modal.mount([self._analysis_controls])
        self._white_mode.param.watch(self._on_white_mode_changed, "value")

        self._run_select.param.watch(self._on_run_changed, "value")

        super().__init__(
            self._placeholder,
            self._controls_slot,
            self._derived_analyses_button,
            self._derived_results_button,
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

    @property
    def filters_button(self) -> pn.widgets.Button:
        return self._filters_button

    @property
    def filters_modal(self) -> NLLSResultFiltersModal:
        return self._filters_modal

    @property
    def derived_analyses_button(self) -> pn.widgets.Button:
        return self._derived_analyses_button

    @property
    def derived_analyses_modal(self) -> NLLSDerivedAnalysesModal:
        return self._derived_analyses_modal

    @property
    def derived_results_button(self) -> pn.widgets.Button:
        return self._derived_results_button

    @property
    def derived_results_modal(self) -> NLLSDerivedResultsControlsModal:
        return self._derived_results_modal

    @property
    def center_a(self):
        return self._center_a

    @property
    def center_b(self):
        return self._center_b

    @property
    def center_button(self):
        return self._center_button

    @property
    def white_a(self):
        return self._white_a

    @property
    def white_b(self):
        return self._white_b

    @property
    def white_source(self):
        return self._white_source

    @property
    def white_mode(self):
        return self._white_mode

    @property
    def white_window_a(self):
        return self._white_window_a

    @property
    def white_window_b(self):
        return self._white_window_b

    @property
    def white_invert(self):
        return self._white_invert

    @property
    def white_button(self):
        return self._white_button

    def _on_white_mode_changed(self, event) -> None:
        manual = event.new == "manual"
        self._white_window_a.visible = manual
        self._white_window_b.visible = manual

    @staticmethod
    def _select_options(widget, values: tuple[str, ...]) -> None:
        options = {value.replace("__", " · ").replace("_", " "): value for value in values}
        widget.options = options
        widget.value = values[0] if values else None
        widget.disabled = not bool(values)

    def _configure_analysis(self, run: NLLSMultifitResultsPlot | None) -> None:
        available = run is not None
        self._derived_analyses_button.visible = available
        self._derived_analyses_button.disabled = not available
        if run is None:
            for widget in (self._center_a, self._center_b, self._white_a, self._white_b):
                self._select_options(widget, ())
            self._center_button.disabled = True
            self._white_button.disabled = True
            return
        results = run.results
        centers = tuple(
            name
            for name, variable in results.data_vars.items()
            if variable.dims == ("y", "x") and name.endswith("center")
        )
        components = tuple(
            name.removesuffix("__component")
            for name, variable in results.data_vars.items()
            if variable.dims == ("y", "x", "Eloss")
            and name.endswith("__component")
            and "elnes" in name.lower()
        )
        self._select_options(self._center_a, centers)
        self._select_options(self._center_b, centers[1:] or centers)
        self._select_options(self._white_a, components)
        self._select_options(self._white_b, components[1:] or components)
        self._center_button.disabled = len(centers) < 2
        self._white_button.disabled = len(components) < 2

        energy = np.asarray(results.coords["Eloss"].values, dtype=float)
        finite = energy[np.isfinite(energy)]
        if finite.size >= 2:
            minimum, maximum = float(np.min(finite)), float(np.max(finite))
            step = max((maximum - minimum) / max(1, finite.size - 1), 1e-9)
            midpoint = (minimum + maximum) / 2.0
            for widget, value in (
                (self._white_window_a, (minimum, midpoint)),
                (self._white_window_b, (midpoint, maximum)),
            ):
                widget.param.update(start=minimum, end=maximum, step=step, value=value)

    def register_derived(self, view) -> None:
        if view not in self._derived_views:
            self._derived_views.insert(0, view)
        view.set_boundaries_visible(self._boundaries_visible)
        self._derived_results_button.disabled = False
        if self._derived_results_modal.visible:
            self._refresh_derived_controls()

    def unregister_derived(self, view) -> None:
        self._derived_views = [item for item in self._derived_views if item is not view]
        self._derived_results_button.disabled = not bool(self._derived_views)
        if self._derived_results_modal.visible:
            self._refresh_derived_controls()

    def _refresh_derived_controls(self) -> None:
        objects = []
        for view in self._derived_views:
            objects.extend(
                [
                    pn.pane.Markdown(
                        f"**Analysis {view.sequence}: {view.analysis_label}**",
                        margin=(6, 0, 2, 0),
                    ),
                    *view.controls,
                ]
            )
        self._derived_results_modal.mount(objects)
        has_results = bool(self._derived_views)
        self._derived_results_button.visible = True
        self._derived_results_button.disabled = not has_results

    def register(self, result_view: NLLSMultifitResultsPlot) -> None:
        """Add a freshly published run and select it."""
        if any(run is result_view for run in self._runs):
            return
        result_view.area_boundaries_button.value = self._boundaries_visible
        watcher = result_view.area_boundaries_button.param.watch(
            self._on_boundaries_changed,
            "value",
        )
        self._boundary_watchers[id(result_view)] = (result_view, watcher)
        self._runs.insert(0, result_view)
        self._refresh_options(preferred=result_view)

    def unregister(self, result_view: NLLSMultifitResultsPlot) -> None:
        """Drop a run whose plots are no longer in the main area."""
        remaining = [run for run in self._runs if run is not result_view]
        if len(remaining) == len(self._runs):
            return
        self._detach_boundary_watcher(result_view)
        self._runs = remaining
        self._refresh_options()

    def clear_runs(self) -> None:
        """Detach every run, restoring the empty-state call to action."""
        for run in tuple(self._runs):
            self._detach_boundary_watcher(run)
        self._runs = []
        self._refresh_options()

    def _detach_boundary_watcher(self, run: NLLSMultifitResultsPlot) -> None:
        registered = self._boundary_watchers.pop(id(run), None)
        if registered is None:
            return
        _, watcher = registered
        try:
            run.area_boundaries_button.param.unwatch(watcher)
        except Exception:
            pass

    def _on_boundaries_changed(self, event) -> None:
        """Propagate one Boundaries toggle to every current and future result map."""
        if self._synchronizing_boundaries:
            return
        self._boundaries_visible = bool(event.new)
        self._synchronizing_boundaries = True
        try:
            for run in self._runs:
                button = run.area_boundaries_button
                if bool(button.value) != self._boundaries_visible:
                    button.value = self._boundaries_visible
            for view in self._derived_views:
                view.set_boundaries_visible(self._boundaries_visible)
        finally:
            self._synchronizing_boundaries = False

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
            self._filters_button.disabled = True
            self._filters_modal.clear()
            self._configure_analysis(None)
            return
        controls = run.controls
        # Result map remains first. Filters belongs to the Area overlay block:
        # it spans the same full width immediately below the two area buttons.
        self._controls_slot.objects = [
            controls[0],
            self._run_select,
            *controls[1:3],
            self._filters_button,
            *controls[3:],
        ]
        self._filters_button.disabled = False
        self._filters_modal.mount(run.filter_controls)
        self._configure_analysis(run)

    def _open_filters(self, event) -> None:
        run = self.active_run
        if run is None:
            return
        self._filters_modal.mount(run.filter_controls)
        if self._modal_manager is not None:
            self._modal_manager.open_modal(self._FILTERS_MODAL_ID)
        else:
            # Useful for standalone component rendering and regression tests.
            self._filters_modal.visible = True

    def _open_derived_analyses(self, event) -> None:
        if self.active_run is None:
            return
        self._derived_analyses_modal.mount([self._analysis_controls])
        if self._modal_manager is not None:
            self._modal_manager.open_modal(self._DERIVED_ANALYSES_MODAL_ID)
        else:
            self._derived_analyses_modal.visible = True

    def _open_derived_results(self, event) -> None:
        if not self._derived_views:
            return
        self._refresh_derived_controls()
        if self._modal_manager is not None:
            self._modal_manager.open_modal(self._DERIVED_RESULTS_MODAL_ID)
        else:
            self._derived_results_modal.visible = True

    def _on_run_changed(self, event) -> None:
        self._mount(
            event.new if isinstance(event.new, NLLSMultifitResultsPlot) else None
        )
