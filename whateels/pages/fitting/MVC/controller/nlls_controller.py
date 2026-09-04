"""Panel adapter for the pure Elemental NLLS domain services."""

from __future__ import annotations

from copy import deepcopy
import json
from queue import Empty, SimpleQueue
from threading import Event, Thread
from typing import TYPE_CHECKING, Any

import numpy as np
import panel as pn
import xarray as xr

from whateels.nlls.areas import AreaDefinition, ClusteringAreaAdapter
from whateels.nlls.analysis import (
    CenterAnalysisService,
    WhiteLineRequest,
    WhiteLineService,
)
from whateels.nlls.contracts import (
    BroadeningSpec,
    ContinuumSpec,
    DatasetIdentity,
    EdgeSpec,
    ExperimentalGeometry,
    FineStructureSpec,
    FitRange,
    NLLSRunRequest,
    ReferenceFitFailure,
)
from whateels.nlls.cross_sections import OOSContinuumProvider
from whateels.nlls.defaults import (
    CHEMICAL_SHIFT_CONVENTION,
    DEFAULT_SOFTEN,
    DEFAULT_SOFTEN_SIGMA_EV,
    OOS_PROVIDER_VERSION,
    canonical_subshell_groups,
    continuum_parameter_specs,
    fine_structure_parameter_specs,
    fwhm_from_attrs,
    stable_component_token,
)
from whateels.nlls.errors import NLLSError
from whateels.nlls.model_builder import NLLSModelBuilder
from whateels.nlls.multifit import ElementalMultifitService
from whateels.nlls.provenance import validate_background_subtracted
from whateels.nlls.references import (
    ReferenceFitService,
    ReferenceSpectrumSelection,
    ReferenceSpectrumService,
)
from whateels.nlls.workspace import NLLSWorkspace
from whateels.nlls.results import FitStatus

if TYPE_CHECKING:
    from ..view import FittingView
    from . import FittingController
    from whateels.state import AppState


class NLLSController:
    """Bind Elemental widgets without changing the manual fitting callbacks."""

    _SUBSHELL_ONSET_COLOR = "#5f6368"
    _SUBSHELL_ONSET_HIGHLIGHT_COLOR = "#d1d5db"

    def __init__(
        self,
        parent: "FittingController",
        view: "FittingView",
        app_state: "AppState",
        provider: OOSContinuumProvider | None = None,
    ):
        self.parent = parent
        self.view = view
        self.app_state = app_state
        self.provider = provider or OOSContinuumProvider()
        self.builder = NLLSModelBuilder(self.provider)
        self.reference_service = ReferenceFitService(self.builder)
        self.multifit_service = ElementalMultifitService(self.builder)
        self.center_analysis_service = CenterAnalysisService()
        self.white_line_service = WhiteLineService()
        self._source_error: str | None = None
        self._geometry_error: str | None = None
        self._validated_geometry: ExperimentalGeometry | None = None
        # None until the first validation pass, so that pass always applies the gate.
        self._sections_unlocked: bool | None = None
        self._watchers: list[Any] = []
        self._run_cancel_event: Event | None = None
        self._run_thread: Thread | None = None
        self._run_events: SimpleQueue[tuple[Any, ...]] = SimpleQueue()
        self._run_poll_callback: Any | None = None
        self._active_run_request: NLLSRunRequest | None = None
        self._prior_complete_results: xr.Dataset | None = None
        self._published_result_ids: set[int] = set()
        self._syncing_edge_controls = False
        self.bind()
        self.on_source_changed(initial=True)
        self._restore_existing_multifit_result()

    @property
    def workspace(self) -> NLLSWorkspace | None:
        value = self.app_state.nlls_workspace
        return value if isinstance(value, NLLSWorkspace) else None

    def bind(self) -> None:
        inputs = self.view.elemental_input
        results_view = getattr(self.view, "elemental_results_view", None)
        if results_view is not None:
            results_view.set_main_plot_callback(self._on_main_result_plot_changed)
        self._watchers.extend(
            [
                inputs["element_atomic_number"].param.watch(self._on_element_changed, "value"),
                inputs["subshells"].param.watch(self._on_subshell_changed, "value"),
                inputs["chemical_shift"].param.watch(
                    self._on_chemical_shift_changed, "value"
                ),
                inputs["soften_edge"].param.watch(
                    self._on_edge_preview_input_changed, "value"
                ),
                inputs["soften_strength"].param.watch(
                    self._on_edge_preview_input_changed, "value"
                ),
                inputs["model_composition"].param.watch(
                    self._on_model_composition_changed, "value"
                ),
                inputs["execution_mode"].param.watch(
                    self._on_execution_mode_changed, "value"
                ),
                self.view.elemental_fit_areas_input.param.watch(
                    self._on_fit_area_selection_changed, "value"
                ),
            ]
        )
        tabs = getattr(self.view, "fitting_tabs", None)
        if tabs is not None:
            self._watchers.append(
                tabs.param.watch(self._on_fitting_tab_changed, "active")
            )
        if getattr(self.view, "edge_added_modal", None) is not None:
            self.view.edge_added_modal.set_change_callback(self._on_edge_modal_changed)
        model_editor = getattr(self.view, "elemental_model_editor", None)
        if model_editor is not None:
            model_editor.set_change_callback(self._on_model_editor_changed)
        self.view.elemental_add_edge_button.on_click(self._on_add_edge)
        self.view.elemental_fit_button.on_click(self._on_fit)
        self.view.elemental_run_nlls_button.on_click(
            self._on_run_elemental_nlls
        )
        self.view.elemental_cancel_button.on_click(
            self._on_cancel_elemental_nlls
        )
        self.view.elemental_select_all_fit_areas_button.on_click(
            self._on_select_all_fit_areas
        )
        self.view.elemental_use_current_clustering_button.on_click(
            self._on_use_current_clustering
        )
        multifit_controls = getattr(self.view, "elemental_multifit_controls", None)
        if multifit_controls is not None:
            multifit_controls.center_button.on_click(self._on_compute_center_analysis)
            multifit_controls.white_button.on_click(self._on_compute_white_lines)
        self._watchers.append(
            self.app_state.param.watch(
                self._on_current_clustering_changed, "last_clustering_result"
            )
        )
        # E0/alpha/beta are edited in the shared Dataset Information card, which republishes
        # all_datasets after writing dataset.attrs. Without this watcher a geometry fixed
        # from that card would leave the Elemental sections locked until the source is switched.
        self._watchers.append(
            self.app_state.param.watch(self._on_dataset_metadata_changed, "all_datasets")
        )

    def cleanup(self) -> None:
        if self._run_cancel_event is not None:
            self._run_cancel_event.set()
        self._stop_run_polling()
        self._clear_edge_preview()
        results_view = getattr(self.view, "elemental_results_view", None)
        if results_view is not None:
            results_view.set_main_plot_callback(None)
        for watcher in self._watchers:
            try:
                watcher.inst.param.unwatch(watcher)
            except Exception:
                pass
        self._watchers.clear()

    def _on_edge_modal_changed(self) -> None:
        """Refresh model cards after the edge-management modal changes."""
        model_editor = getattr(self.view, "elemental_model_editor", None)
        if model_editor is not None:
            model_editor.refresh()
        self._on_model_editor_changed()

    def _on_model_editor_changed(self) -> None:
        """Persist a card edit and redraw all downstream Elemental state."""
        workspace = self.workspace
        if workspace is not None:
            self._publish_workspace()
            self._sync_edge_controls_from_selection()
            self._refresh_edge_preview()
            self._refresh_button_states()

    def _active_dataset(self):
        return self.app_state.plot_dataset

    def _source_kind(self, dataset) -> str:
        return (
            "preprocessed"
            if dataset is not None and dataset is self.app_state.preprocessed_plot_dataset
            else "raw"
        )

    def _current_fit_range(self) -> FitRange:
        dataset = self._active_dataset()
        if dataset is None or "Eloss" not in getattr(dataset, "coords", {}):
            raise ValueError("active NLLS source has no Eloss coordinate")
        eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float).reshape(-1)
        finite = eloss[np.isfinite(eloss)]
        if finite.size < 2:
            raise ValueError("active NLLS source needs at least two finite Eloss values")
        minimum = float(np.min(finite))
        maximum = float(np.max(finite))
        if minimum >= maximum:
            raise ValueError("active NLLS source has an invalid Eloss range")
        return FitRange(minimum, maximum)

    def on_source_changed(self, initial: bool = False) -> None:
        """Invalidate stale NLLS artifacts and resynchronize all Elemental controls."""
        dataset = self._active_dataset()
        try:
            history = validate_background_subtracted(dataset)
            self._source_error = None
        except NLLSError as exc:
            history = ()
            self._source_error = str(exc)
        try:
            geometry = ExperimentalGeometry.from_dataset(dataset)
            self._geometry_error = None
            self._validated_geometry = geometry
        except (NLLSError, AttributeError, TypeError) as exc:
            geometry = None
            self._geometry_error = str(exc)
            self._validated_geometry = None

        if self._source_error or self._geometry_error or geometry is None:
            if self._active_run_request is not None:
                self._request_run_cancellation(notify=False)
            if not initial or self.workspace is not None:
                self.app_state.clear_nlls_state()
            self._refresh_results_view()
            self._clear_clustering_in_main()
            self._clear_edge_preview()
            self._update_validation_status()
            self._refresh_element_catalog()
            model_editor = getattr(self.view, "elemental_model_editor", None)
            if model_editor is not None:
                model_editor.refresh()
            self._refresh_button_states()
            return

        identity = DatasetIdentity.from_dataset(
            dataset,
            tab_index=self.app_state.selected_tab_index_dataset,
            source_kind=self._source_kind(dataset),
            preprocessing_history=history,
            background_subtracted=True,
        )

        active_request = self._active_run_request
        if active_request is not None and (
            identity.source_revision != active_request.dataset_source_revision
            or self.workspace is None
            or self.workspace.geometry != geometry
        ):
            self._request_run_cancellation(notify=False)

        workspace = self.workspace
        workspace_replaced = workspace is None or workspace.dataset_identity != identity
        if workspace_replaced:
            workspace = NLLSWorkspace.create(identity, geometry)
            workspace.set_model_composition(
                workspace.active_area,
                self.view.elemental_input["model_composition"].value,
            )
            self.app_state.nlls_workspace = workspace
            self.app_state.nlls_results = None
            self.app_state.nlls_run_state = "idle"
            self.app_state.nlls_revision += 1
            self._clear_clustering_in_main()
        elif workspace.geometry != geometry:
            workspace.geometry = geometry
            workspace.invalidate_all()
            self._publish_workspace()

        self._update_validation_status()
        self._refresh_element_catalog()
        self._sync_edge_controls_from_selection()
        model_editor = getattr(self.view, "elemental_model_editor", None)
        if model_editor is not None:
            model_editor.refresh()
        self._refresh_button_states()
        self._refresh_results_view()
        self._refresh_edge_preview()

    def _active_visualizer(self):
        visualizers = getattr(getattr(self.parent, "layout", None), "_chosen_visualizers", ())
        return visualizers[0] if visualizers else None

    def _on_main_result_plot_changed(self, plot) -> None:
        """Route the selected Results plot to the large spectrum pane."""
        visualizer = self._active_visualizer()
        if visualizer is None:
            return
        try:
            if plot is None:
                clear = getattr(visualizer, "clear_nlls_reference_result", None)
                if clear is not None:
                    clear()
            else:
                show = getattr(visualizer, "show_nlls_reference_result", None)
                if show is not None:
                    show(plot)
        except Exception:
            # A visualization failure must never roll back an already committed fit.
            pass

    def _clear_clustering_in_main(self) -> None:
        visualizer = self._active_visualizer()
        clear = getattr(visualizer, "clear_nlls_clustering", None)
        if clear is not None:
            try:
                clear()
            except Exception:
                pass

    def _show_clustering_in_main(self) -> None:
        """Display current labels and cluster means, never saved normalized centres."""
        workspace = self.workspace
        visualizer = self._active_visualizer()
        if workspace is None or visualizer is None:
            return
        show = getattr(visualizer, "show_nlls_clustering", None)
        if show is None:
            return

        result = self.app_state.last_clustering_result
        labels = np.asarray(result["clustering"]["outputs"]["labels"])
        eloss = np.asarray(self._active_dataset().coords["Eloss"].values, dtype=float)
        cluster_spectra = []
        for area_id in workspace.runnable_area_ids:
            area = workspace.areas[area_id]
            if area.clustering_label is None:
                continue
            try:
                selection = self._reference_selection_for_area(area_id)
            except (NLLSError, ValueError, TypeError):
                continue
            cluster_spectra.append(
                (int(area.clustering_label), area.label, selection.spectrum)
            )
        try:
            show(labels, eloss, tuple(cluster_spectra))
        except Exception as exc:
            self._notify(
                "warning",
                f"Clustering areas were applied, but their plots could not be shown: {exc}",
                7000,
            )

    def _update_validation_status(self) -> None:
        """Publish both gates and keep the Elemental sections consistent with them.

        A valid gate publishes no alert at all: the section stack then starts at the top
        of the tab. An invalid gate keeps its own alert visible and locks both sections
        closed, because neither an edge nor a model can be defined against that source.
        """
        background = self.view.elemental_background_status
        geometry = self.view.elemental_geometry_status
        if self._source_error:
            background.object = f"**Background status:** blocked — {self._source_error}."
            background.alert_type = "danger"
        else:
            background.object = (
                "**Background status:** valid power-law pre-edge subtraction provenance "
                "for the active preprocessed source."
            )
            background.alert_type = "success"
        if self._geometry_error:
            geometry.object = f"**Geometry status:** blocked — {self._geometry_error}."
            geometry.alert_type = "danger"
        elif self._validated_geometry is not None:
            value = self._validated_geometry
            geometry.object = (
                "**Geometry status:** valid — "
                f"E0={value.beam_energy_keV:g} keV, "
                f"alpha={value.convergence_angle_mrad:g} mrad, "
                f"beta={value.collection_angle_mrad:g} mrad."
            )
            geometry.alert_type = "success"
        else:
            geometry.object = "**Geometry status:** waiting for a valid NLLS source."
            geometry.alert_type = "warning"

        background_valid = not self._source_error
        geometry_valid = not self._geometry_error and self._validated_geometry is not None
        background.visible = not background_valid
        geometry.visible = not geometry_valid
        self._apply_section_availability(background_valid and geometry_valid)

    def _apply_section_availability(self, unlocked: bool) -> None:
        """Lock/unlock all Elemental definition cards as one gated block.

        Sections are opened only on the transition into a valid source, so a user who
        folds one of them while working keeps it folded across later refreshes.
        """
        just_unlocked = unlocked and self._sections_unlocked is not True
        for name in (
            "elemental_edge_section",
            "elemental_model_section",
            "elemental_continuum_section",
            "elemental_elnes_section",
        ):
            section = getattr(self.view, name, None)
            if section is None:
                continue
            section.set_locked(not unlocked)
            if just_unlocked:
                section.set_expanded(True)
        self._sections_unlocked = unlocked

    def _refresh_element_catalog(self) -> None:
        atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
        shells_widget = self.view.elemental_input["subshells"]
        try:
            shells = list(self.provider.available_edges(atomic_number))
            raw_edges = [self.provider.load_raw(atomic_number, shell) for shell in shells]
            current = [shell for shell in shells_widget.value if shell in shells]
            shells_widget.stylesheets = [
                self._subshell_onset_stylesheet(
                    {raw.shell: raw.onset_eV for raw in raw_edges}
                )
            ]
            shells_widget.options = shells
            shells_widget.value = current
            shells_widget.disabled = not bool(shells)
            self._update_selected_onset()
        except NLLSError:
            shells_widget.stylesheets = []
            shells_widget.options = []
            shells_widget.value = []
            shells_widget.disabled = True
            self.view.elemental_onset_readout.value = "Onset (eV): -"

    @classmethod
    def _subshell_onset_stylesheet(cls, onsets_eV: dict[str, float]) -> str:
        """Render catalogue onsets as secondary, right-aligned option text.

        The underlying option values stay as plain subshell names, so the
        presentation does not leak into selection state or persisted models.
        """
        base_rules = (
            """
            :host .choices__list--dropdown .choices__item--choice[data-choice-selectable],
            :host .choices__list[aria-expanded] .choices__item--choice[data-choice-selectable] {
                align-items: center;
                column-gap: 1rem;
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) auto;
                padding-right: 10px !important;
                word-break: normal;
            }

            :host .choices__list--dropdown .choices__item--choice[data-choice-selectable]::after,
            :host .choices__list[aria-expanded] .choices__item--choice[data-choice-selectable]::after {
                color: __ONSET_COLOR__;
                content: var(--subshell-onset) !important;
                font-size: 0.875em;
                font-variant-numeric: tabular-nums;
                font-weight: 400;
                opacity: 1;
                position: static;
                text-align: right;
                transform: none;
                white-space: nowrap;
            }

            :host .choices__list--dropdown .choices__item--choice.is-highlighted[data-choice-selectable]::after,
            :host .choices__list[aria-expanded] .choices__item--choice.is-highlighted[data-choice-selectable]::after {
                color: __ONSET_HIGHLIGHT_COLOR__ !important;
            }
            """
            .replace("__ONSET_COLOR__", cls._SUBSHELL_ONSET_COLOR)
            .replace("__ONSET_HIGHLIGHT_COLOR__", cls._SUBSHELL_ONSET_HIGHLIGHT_COLOR)
        )
        rules = [base_rules]
        for shell, onset_eV in onsets_eV.items():
            shell_literal = json.dumps(str(shell))
            onset_literal = json.dumps(f"{float(onset_eV):.0f} eV")
            rules.append(
                ":host .choices__item--choice[data-choice-selectable]"
                f"[data-value={shell_literal}] {{ --subshell-onset: {onset_literal}; }}"
            )
        return "\n".join(rules)

    def _update_selected_onset(self) -> None:
        atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
        selected = tuple(self.view.elemental_input["subshells"].value)
        if not selected:
            self.view.elemental_onset_readout.value = "Onset (eV): -"
            return
        raws = [self.provider.load_raw(atomic_number, shell) for shell in selected]
        self.view.elemental_onset_readout.value = (
            "Onset (eV): " + ", ".join(f"{raw.shell}={raw.onset_eV:g}" for raw in raws)
        )

    def _validate_selected_curves(self):
        if self.workspace is None:
            raise ValueError(self._source_error or self._geometry_error or "no valid workspace")
        atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
        selected = tuple(self.view.elemental_input["subshells"].value)
        available = self.provider.available_edges(atomic_number)
        groups = canonical_subshell_groups(selected, available)
        if not groups:
            raise ValueError("select at least one OOS subshell")
        continuum_parameter_specs(
            float(self.view.elemental_input["chemical_shift"].value)
        )
        broadening = BroadeningSpec(
            enabled=bool(self.view.elemental_input["soften_edge"].value),
            sigma_eV=float(self.view.elemental_input["soften_strength"].value),
        )
        eloss = np.asarray(self._active_dataset().coords["Eloss"].values, dtype=float)
        snapshots = tuple(
            self.provider.curve(
                atomic_number,
                group,
                self.workspace.geometry,
                eloss,
                broadening,
                self._current_fit_range(),
            )
            for group in groups
        )
        return groups, snapshots, broadening

    def _selected_continuum_ids(self) -> tuple[str, ...]:
        """Return stable IDs for the shell groups selected in Edge Definition."""
        atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
        selected = tuple(self.view.elemental_input["subshells"].value)
        if not selected:
            return ()
        available = self.provider.available_edges(atomic_number)
        groups = canonical_subshell_groups(selected, available)
        if not groups:
            return ()
        _, symbol = self.provider.element_info(atomic_number)
        return tuple(
            f"{stable_component_token(symbol or f'z{atomic_number}', group)}_continuum"
            for group in groups
        )

    def _sync_edge_controls_from_selection(self) -> None:
        """Load the saved shift/broadening for an exact edge selection."""
        if self._syncing_edge_controls:
            return
        workspace = self.workspace
        if workspace is None or "default" not in workspace.areas:
            return
        try:
            continuum_ids = self._selected_continuum_ids()
        except (NLLSError, ValueError, TypeError):
            return
        if not continuum_ids:
            return
        by_id = {
            continuum.id: continuum
            for continuum in workspace.areas["default"].continuum_specs
        }
        broadening = None
        if any(continuum_id not in by_id for continuum_id in continuum_ids):
            shift_value = 0.0
            broadening = BroadeningSpec(
                enabled=DEFAULT_SOFTEN,
                sigma_eV=DEFAULT_SOFTEN_SIGMA_EV,
            )
        else:
            shifts = {
                float(by_id[continuum_id].chemical_shift.value)
                for continuum_id in continuum_ids
            }
            shift_value = shifts.pop() if len(shifts) == 1 else None
            broadenings = {
                by_id[continuum_id].broadening
                for continuum_id in continuum_ids
            }
            if len(broadenings) == 1:
                broadening = broadenings.pop()

        shift_widget = self.view.elemental_input["chemical_shift"]
        soften_widget = self.view.elemental_input["soften_edge"]
        strength_widget = self.view.elemental_input["soften_strength"]
        self._syncing_edge_controls = True
        try:
            if (
                shift_value is not None
                and float(shift_widget.value) != shift_value
            ):
                shift_widget.value = shift_value
            if broadening is not None:
                if bool(soften_widget.value) != bool(broadening.enabled):
                    soften_widget.value = bool(broadening.enabled)
                if float(strength_widget.value) != float(broadening.sigma_eV):
                    strength_widget.value = float(broadening.sigma_eV)
        finally:
            self._syncing_edge_controls = False

    def _edge_definition_tab_active(self) -> bool:
        """Return whether the Elemental tab owns the shared spectrum pane."""
        tabs = getattr(self.view, "fitting_tabs", None)
        if tabs is None:
            return True
        try:
            return int(tabs.active) == 1
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _shifted_oos_preview(snapshot, eloss: np.ndarray, chemical_shift: float) -> np.ndarray:
        """Evaluate an OOS snapshot with the same sign convention as the model.

        The preview must never draw a flat 0 or a fake upward ramp where the OOS
        table has no real data. Zero-valued samples are treated as absent instead
        of as visible line segments, while valid non-zero data remain intact.
        """
        axis = np.asarray(eloss, dtype=float)
        shifted_axis = axis + float(chemical_shift)
        support = np.asarray(snapshot.energy_eV, dtype=float)
        curve = np.asarray(snapshot.normalized_shape, dtype=float)

        finite_curve = np.isfinite(curve)
        if np.count_nonzero(finite_curve) == 0:
            return np.full(axis.shape, np.nan, dtype=float)

        interpolated = np.interp(
            shifted_axis,
            support,
            np.where(finite_curve, curve, 0.0),
            left=np.nan,
            right=np.nan,
        )
        onset = min(float(value) for value in snapshot.onsets_eV)
        interpolated[shifted_axis < onset] = np.nan
        interpolated[np.isclose(interpolated, 0.0, atol=0.0)] = np.nan
        return interpolated

    def _edge_preview_reference(self):
        """Return a stable mean spectrum for positioning Edge Definition curves."""
        dataset = self._active_dataset()
        cube = np.asarray(dataset["ElectronCount"].values, dtype=float)
        if cube.ndim != 3:
            raise ValueError("active NLLS source must be a spectrum image")
        pairs = self._roi_pairs()
        if pairs:
            try:
                mask = ReferenceSpectrumService.roi_mask(cube.shape[:2], pairs)
                selection = ReferenceSpectrumService.select_from_mask(
                    cube, mask, "roi_mean"
                )
                return selection, f"ROI mean ({selection.pixel_count} pixels)"
            except (NLLSError, ValueError, TypeError):
                pass
        mask = ReferenceSpectrumService.central_mask(cube.shape[:2])
        selection = ReferenceSpectrumService.select_from_mask(
            cube, mask, "central_mean"
        )
        return selection, f"Central-window mean ({selection.pixel_count} pixels)"

    @staticmethod
    def _initial_elnes_center_offset(
        eloss: np.ndarray,
        spectrum: np.ndarray | None,
        shifted_onset: float,
        next_shifted_onset: float | None,
    ) -> float:
        """Estimate a white-line center inside its onset-constrained window.

        The lower bound is the shifted onset and the default upper bound is
        14 eV above it.  For the lower member of a doublet, stop before the
        next onset so its initial peak cannot lock onto the other white line.
        """
        default_offset = 7.0
        if spectrum is None:
            return default_offset
        energy = np.asarray(eloss, dtype=float)
        values = np.asarray(spectrum, dtype=float)
        if energy.shape != values.shape:
            return default_offset
        upper = float(shifted_onset) + 14.0
        if next_shifted_onset is not None:
            upper = min(upper, float(next_shifted_onset))
        mask = (
            np.isfinite(energy)
            & np.isfinite(values)
            & (energy >= float(shifted_onset))
            & (energy < upper)
        )
        if not np.any(mask):
            return default_offset
        candidates = np.flatnonzero(mask)
        peak_index = candidates[int(np.argmax(values[candidates]))]
        return float(np.clip(energy[peak_index] - shifted_onset, 0.0, 14.0))

    def _clear_edge_preview(self) -> None:
        visualizer = self._active_visualizer()
        clear = getattr(visualizer, "clear_nlls_edge_preview", None)
        if clear is not None:
            try:
                clear()
            except Exception:
                pass

    def _refresh_edge_preview(self) -> None:
        """Plot saved continua/ELNES plus the current OOS candidate selection.

        The candidate is included before ``Add Edge`` so the shift can be aligned
        interactively.  Once an edge exists, the shift watcher updates its saved
        ``ContinuumSpec`` and this same route redraws the committed definition.
        Fine-structure curves are evaluated through ``NLLSModelBuilder`` so their
        live preview cannot diverge from Build semantics.
        """
        if not self._edge_definition_tab_active():
            self._clear_edge_preview()
            return
        workspace = self.workspace
        visualizer = self._active_visualizer()
        show = getattr(visualizer, "show_nlls_edge_preview", None)
        if workspace is None or visualizer is None or show is None:
            return
        dataset = self._active_dataset()
        if dataset is None or "Eloss" not in getattr(dataset, "coords", {}):
            self._clear_edge_preview()
            return

        try:
            eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float)
            fit_range = self._current_fit_range()
            entries: dict[str, tuple[str, np.ndarray, np.ndarray]] = {}
            scale_bases: dict[str, np.ndarray] = {}
            candidate_entries: dict[str, tuple[str, np.ndarray, np.ndarray]] = {}
            candidate_bases: dict[str, np.ndarray] = {}
            try:
                groups, snapshots, _broadening = self._validate_selected_curves()
                atomic_number = int(
                    self.view.elemental_input["element_atomic_number"].value
                )
                _, symbol = self.provider.element_info(atomic_number)
                shift = float(self.view.elemental_input["chemical_shift"].value)
                for group, snapshot in zip(groups, snapshots):
                    token = stable_component_token(
                        symbol or f"z{atomic_number}", group
                    )
                    label = (
                        f"{symbol or f'Z{atomic_number}'} {'+'.join(group)} OOS "
                        f"(shift {shift:+g} eV)"
                    )
                    component_id = f"{token}_continuum"
                    candidate_curve = self._shifted_oos_preview(
                        snapshot, eloss, shift
                    )
                    candidate_entries[component_id] = (
                        label,
                        eloss,
                        candidate_curve,
                    )
                    candidate_bases[component_id] = candidate_curve
            except (NLLSError, ValueError, TypeError):
                pass

            area = workspace.areas["default"]
            for continuum in area.continuum_specs:
                # A saved continuum is always rendered from its committed
                # definition. Candidate controls update that definition before
                # this method is called, so preview and Build cannot diverge.
                candidate_entries.pop(continuum.id, None)
                snapshot = self.provider.curve(
                    continuum.atomic_number,
                    continuum.shells,
                    workspace.geometry,
                    eloss,
                    continuum.broadening,
                    fit_range,
                )
                shift = float(continuum.chemical_shift.value)
                unit_curve = self._shifted_oos_preview(snapshot, eloss, shift)
                label = (
                    f"{continuum.symbol} {'+'.join(continuum.shells)} OOS "
                    f"(A {continuum.amplitude.value:g}, shift {shift:+g} eV)"
                )
                entries[continuum.id] = (
                    label,
                    eloss,
                    float(continuum.amplitude.value) * unit_curve,
                )
                scale_bases[continuum.id] = unit_curve
            entries.update(candidate_entries)
            scale_bases.update(candidate_bases)

            if area.model_composition.value == "continuum_plus_elnes":
                edge_by_id = {edge.id: edge for edge in area.edges}
                continuum_by_edge = {
                    continuum.edge_id: continuum
                    for continuum in area.continuum_specs
                }
                for component in area.fine_structure_specs:
                    if not component.enabled:
                        continue
                    continuum = continuum_by_edge.get(component.edge_id)
                    if continuum is None:
                        continue
                    shift = float(continuum.chemical_shift.value)
                    curve = self.builder.evaluate_fine_structure(
                        component, eloss, chemical_shift=shift
                    )
                    unit_curve = self.builder.evaluate_fine_structure(
                        component,
                        eloss,
                        chemical_shift=shift,
                        amplitude=1.0,
                    )
                    center = self.builder.absolute_center_spec(component, shift)
                    edge = edge_by_id.get(component.edge_id)
                    symbol = edge.symbol if edge is not None else "ELNES"
                    shape_name = component.shape.removesuffix("Model")
                    label = (
                        f"{symbol} {component.shell} {shape_name} "
                        f"(center {center.value:g} eV, "
                        f"sigma {component.sigma.value:g} eV, "
                        f"amplitude {component.amplitude.value:g})"
                    )
                    entries[component.id] = (label, eloss, curve)
                    scale_bases[component.id] = unit_curve

            if not entries:
                self._clear_edge_preview()
                return
            selection, spectrum_label = self._edge_preview_reference()
            try:
                show(
                    eloss,
                    selection.spectrum,
                    tuple(entries.values()),
                    spectrum_label=spectrum_label,
                    scale_bases=tuple(
                        scale_bases[component_id] for component_id in entries
                    ),
                )
            except Exception:
                # Preview rendering is advisory and must never roll back a
                # valid edge definition or break a widget callback.
                self._clear_edge_preview()
        except (NLLSError, ValueError, TypeError, KeyError, AttributeError):
            self._clear_edge_preview()

    def _current_clustering_definitions(self) -> tuple[AreaDefinition, ...]:
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        cube = np.asarray(self._active_dataset()["ElectronCount"].values)
        if cube.ndim != 3:
            raise ValueError("active NLLS source must be a spectrum image")
        return ClusteringAreaAdapter.from_result(
            self.app_state.last_clustering_result,
            workspace.dataset_identity,
            tuple(int(value) for value in cube.shape[:2]),
        )

    def _roi_pairs(self) -> tuple[tuple[int, int], ...]:
        visualizers = getattr(self.parent.layout, "_chosen_visualizers", ())
        if not visualizers:
            return ()
        pairs = getattr(visualizers[0], "_region_pairs", ()) or ()
        return tuple((int(row), int(column)) for row, column in pairs)

    def _reference_mask_for_area(self, area_id: str) -> tuple[np.ndarray, str]:
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        cube = np.asarray(self._active_dataset()["ElectronCount"].values)
        if cube.ndim != 3:
            raise ValueError("active NLLS source must be a spectrum image")
        area = workspace.areas[area_id]
        if area.mask is not None:
            return np.asarray(area.mask, dtype=bool), "clustering_mean"
        if area.reference_strategy == "roi_mean":
            return ReferenceSpectrumService.roi_mask(cube.shape[:2], self._roi_pairs()), "roi_mean"
        if area.reference_strategy == "central_mean":
            return ReferenceSpectrumService.central_mask(cube.shape[:2]), "central_mean"
        raise ValueError(f"unsupported reference strategy: {area.reference_strategy}")

    def _reference_selection_for_area(self, area_id: str) -> ReferenceSpectrumSelection:
        cube = np.asarray(self._active_dataset()["ElectronCount"].values, dtype=float)
        mask, strategy = self._reference_mask_for_area(area_id)
        return ReferenceSpectrumService.select_from_mask(cube, mask, strategy)

    def _reference_is_current(self, area_id: str) -> bool:
        workspace = self.workspace
        if workspace is None or not workspace.is_area_built(area_id):
            return False
        snapshot = workspace.reference_fits.get(area_id)
        if snapshot is None or not snapshot.success:
            return False
        area = workspace.areas[area_id]
        try:
            mask, strategy = self._reference_mask_for_area(area_id)
        except (NLLSError, ValueError, TypeError):
            return False
        return bool(
            snapshot.area_revision == area.revision
            and snapshot.dataset_source_revision
            == workspace.dataset_identity.source_revision
            and snapshot.model_composition == area.model_composition
            and snapshot.fit_range == self._current_fit_range()
            and snapshot.reference_strategy == strategy
            and snapshot.reference_mask_fingerprint
            == ReferenceSpectrumService.mask_fingerprint(mask)
        )

    def _refresh_button_states(self) -> None:
        workspace = self.workspace
        run_active = self._active_run_request is not None
        edge_modal = getattr(self.view, "edge_added_modal", None)
        if edge_modal is not None:
            edge_modal.set_editable(not run_active)
        model_editor = getattr(self.view, "elemental_model_editor", None)
        if model_editor is not None:
            model_editor.set_editable(not run_active)
        selected_valid = False
        if workspace is not None:
            try:
                self._validate_selected_curves()
                selected_valid = True
            except (NLLSError, ValueError):
                selected_valid = False
        self.view.elemental_add_edge_button.disabled = run_active or not selected_valid

        clustering_definitions: tuple[AreaDefinition, ...] = ()
        if workspace is not None and self.app_state.last_clustering_result is not None:
            try:
                clustering_definitions = self._current_clustering_definitions()
            except (NLLSError, ValueError, TypeError):
                clustering_definitions = ()
        clustering_valid = bool(clustering_definitions)
        clustering_active = bool(workspace and workspace.clustering_active)
        clustering_button = self.view.elemental_use_current_clustering_button
        clustering_button.name = (
            "Use Preprocessed Data" if clustering_active else "Use Current Clustering"
        )
        clustering_button.button_type = "warning" if clustering_active else "primary"
        clustering_button.disabled = run_active or not (
            clustering_active or clustering_valid
        )

        fit_areas = self.view.elemental_fit_areas_input
        if clustering_active and workspace is not None:
            cluster_ids = workspace.runnable_area_ids
            options = {
                workspace.areas[area_id].label: area_id for area_id in cluster_ids
            }
        else:
            cluster_ids = tuple(
                definition.area_id for definition in clustering_definitions
            )
            options = {
                definition.label: definition.area_id
                for definition in clustering_definitions
            }
        previous_options = fit_areas.options if isinstance(fit_areas.options, dict) else {}
        previous_ids = tuple(previous_options.values())
        if previous_ids != tuple(cluster_ids):
            fit_areas.param.update(options=options, value=list(cluster_ids))
        else:
            selected = [area_id for area_id in fit_areas.value if area_id in cluster_ids]
            if selected != list(fit_areas.value):
                fit_areas.value = selected
        clustering_settings_available = clustering_active or clustering_valid
        fit_areas.disabled = run_active or not clustering_settings_available
        self.view.elemental_fit_area_settings_button.disabled = (
            run_active or not clustering_settings_available
        )
        self.view.elemental_select_all_fit_areas_button.disabled = (
            run_active or not clustering_settings_available
        )

        target_ids = (
            tuple(fit_areas.value) if clustering_active else ("default",)
        )
        targets_available = bool(target_ids and workspace is not None)
        for area_id in target_ids:
            try:
                if workspace is None or area_id not in workspace.areas:
                    targets_available = False
                    break
                if not workspace.areas[area_id].continuum_specs:
                    targets_available = False
                    break
                self._reference_mask_for_area(area_id)
            except (NLLSError, ValueError, TypeError):
                targets_available = False
                break
        self.view.elemental_fit_button.disabled = (
            run_active or not targets_available
        )

        run_ready = targets_available and all(
            workspace is not None and workspace.is_area_built(area_id)
            for area_id in target_ids
        )
        if run_ready:
            for area_id in target_ids:
                if not self._reference_is_current(area_id):
                    run_ready = False
                    break
        self.view.elemental_run_nlls_button.disabled = run_active or not run_ready
        cancel_requested = bool(
            self._run_cancel_event is not None and self._run_cancel_event.is_set()
        )
        self.view.elemental_cancel_button.disabled = not run_active or cancel_requested

        # A run owns an immutable configuration snapshot. Lock all inputs that could
        # otherwise make the request stale while the worker is fitting pixels.
        for key, widget in self.view.elemental_input.items():
            if key == "subshells":
                widget.disabled = run_active or not bool(widget.options)
            else:
                widget.disabled = run_active
        self.view.elemental_input["workers"].disabled = bool(
            run_active or not self.view.elemental_input["execution_mode"].value
        )

    def _publish_workspace(self) -> None:
        self.app_state.nlls_workspace = self.workspace
        self.app_state.nlls_revision += 1
        self.app_state.nlls_results = None
        self._refresh_results_view()

    def _refresh_results_view(
        self,
        preferred_area: str | None = None,
        *,
        activate: bool = False,
    ) -> None:
        """Render only reference snapshots that still match the active workspace."""
        results_view = getattr(self.view, "elemental_results_view", None)
        workspace = self.workspace
        dataset = self._active_dataset()
        if (
            results_view is None
            or workspace is None
            or dataset is None
            or "Eloss" not in getattr(dataset, "coords", {})
        ):
            if results_view is not None:
                results_view.clear()
            return

        valid_snapshots = {
            area_id: snapshot
            for area_id, snapshot in workspace.reference_fits.items()
            if area_id in workspace.areas and self._reference_is_current(area_id)
        }
        labels = {
            area_id: workspace.areas[area_id].label for area_id in valid_snapshots
        }
        eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float)
        results_view.render(
            valid_snapshots,
            labels,
            eloss,
            preferred_area=preferred_area,
        )
        if activate and valid_snapshots:
            self._activate_results_tab()

    def _activate_results_tab(self) -> None:
        tabs = getattr(self.view, "fitting_tabs", None)
        if tabs is not None:
            tabs.active = 2

    @staticmethod
    def _notify(level: str, message: str, duration: int = 5000) -> None:
        try:
            getattr(pn.state.notifications, level)(message, duration=duration)
        except Exception:
            pass

    def _selected_run_area_ids(self) -> tuple[str, ...]:
        workspace = self.workspace
        if workspace is None:
            return ()
        if workspace.clustering_active:
            return tuple(str(value) for value in self.view.elemental_fit_areas_input.value)
        return ("default",)

    def _active_analysis_result(self) -> xr.Dataset:
        controls = getattr(self.view, "elemental_multifit_controls", None)
        active_view = getattr(controls, "active_run", None)
        result = getattr(active_view, "results", None)
        if not isinstance(result, xr.Dataset):
            raise ValueError("select an Elemental NLLS run")
        return result

    def _publish_derived_analysis(self, result: xr.Dataset) -> None:
        layout = getattr(self.parent, "layout", None)
        add_result = getattr(layout, "add_nlls_derived_result_plot", None)
        if add_result is None:
            raise ValueError("the Fitting plot stack cannot publish derived analyses")
        add_result(result)
        self._activate_results_tab()

    def _on_compute_center_analysis(self, event) -> None:
        controls = getattr(self.view, "elemental_multifit_controls", None)
        try:
            if controls is None:
                raise ValueError("Center Analysis controls are unavailable")
            result = self.center_analysis_service.compute(
                self._active_analysis_result(),
                str(controls.center_a.value),
                str(controls.center_b.value),
            )
            self._publish_derived_analysis(result)
            self._notify("success", "Center Analysis distance map added above the runs.")
            controls.derived_analyses_modal.close()
        except Exception as exc:
            self._notify("error", f"Center Analysis failed: {exc}", 9000)

    def _on_compute_white_lines(self, event) -> None:
        controls = getattr(self.view, "elemental_multifit_controls", None)
        try:
            if controls is None:
                raise ValueError("White Lines controls are unavailable")
            manual = controls.white_mode.value == "manual"
            request = WhiteLineRequest(
                component_a=str(controls.white_a.value),
                component_b=str(controls.white_b.value),
                source=str(controls.white_source.value),
                window_mode=str(controls.white_mode.value),
                window_a=(
                    tuple(float(value) for value in controls.white_window_a.value)
                    if manual
                    else None
                ),
                window_b=(
                    tuple(float(value) for value in controls.white_window_b.value)
                    if manual
                    else None
                ),
                invert_ratio=bool(controls.white_invert.value),
            )
            result = self.white_line_service.compute(
                self._active_analysis_result(), request
            )
            self._publish_derived_analysis(result)
            self._notify("success", "White Lines ratio map added above the runs.")
            controls.derived_analyses_modal.close()
        except Exception as exc:
            self._notify("error", f"White Lines analysis failed: {exc}", 9000)

    def _freeze_run_inputs(self):
        """Build a closed request and detach every worker input from mutable GUI state."""
        if self._active_run_request is not None:
            raise ValueError("an Elemental NLLS run is already active")
        workspace = self.workspace
        source = self._active_dataset()
        if workspace is None or source is None:
            raise ValueError("no valid Elemental NLLS source")
        selected = self._selected_run_area_ids()
        if not selected:
            raise ValueError("select at least one area to run")
        for area_id in selected:
            if area_id not in workspace.areas:
                raise ValueError(f"unknown NLLS area: {area_id}")
            if not self._reference_is_current(area_id):
                raise ValueError(
                    f"area {area_id} needs a current converged reference fit"
                )

        parallel = bool(self.view.elemental_input["execution_mode"].value)
        workers = int(self.view.elemental_input["workers"].value) if parallel else 1
        request = NLLSRunRequest(
            selected_areas=selected,
            fit_range=self._current_fit_range(),
            method="leastsq",
            model_composition_by_area=tuple(
                (area_id, workspace.areas[area_id].model_composition)
                for area_id in selected
            ),
            parallel=parallel,
            workers=workers,
            dataset_source_revision=workspace.dataset_identity.source_revision,
            workspace_revision=workspace.dirty_revision,
            area_revisions=tuple(
                (area_id, workspace.areas[area_id].revision)
                for area_id in selected
            ),
        )
        frozen_source = source.copy(deep=True)
        frozen_areas = {
            area_id: deepcopy(workspace.areas[area_id]) for area_id in selected
        }
        frozen_references = {
            area_id: deepcopy(workspace.reference_fits[area_id])
            for area_id in selected
            if area_id in workspace.reference_fits
        }
        return (
            request,
            frozen_source,
            deepcopy(workspace.geometry),
            deepcopy(workspace.dataset_identity),
            frozen_areas,
            frozen_references,
        )

    def _run_request_is_current(self, request: NLLSRunRequest) -> bool:
        """Revalidate the optimistic-lock fields before committing worker output."""
        workspace = self.workspace
        if workspace is None:
            return False
        if workspace.dataset_identity.source_revision != request.dataset_source_revision:
            return False
        if workspace.dirty_revision != request.workspace_revision:
            return False
        if self._selected_run_area_ids() != request.selected_areas:
            return False
        try:
            if self._current_fit_range() != request.fit_range:
                return False
        except (NLLSError, ValueError, TypeError):
            return False
        current_parallel = bool(
            self.view.elemental_input["execution_mode"].value
        )
        current_workers = (
            int(self.view.elemental_input["workers"].value)
            if current_parallel
            else 1
        )
        if request.parallel != current_parallel or request.workers != current_workers:
            return False
        compositions = dict(request.model_composition_by_area)
        revisions = dict(request.area_revisions)
        for area_id in request.selected_areas:
            area = workspace.areas.get(area_id)
            if area is None:
                return False
            if area.model_composition != compositions[area_id]:
                return False
            if revisions and area.revision != revisions[area_id]:
                return False
            if not self._reference_is_current(area_id):
                return False
        return True

    def _start_run_polling(self) -> None:
        self._stop_run_polling()
        if pn.state.curdoc is None:
            return
        self._run_poll_callback = pn.state.add_periodic_callback(
            self._drain_run_events,
            period=100,
            start=True,
        )

    def _stop_run_polling(self) -> None:
        callback = self._run_poll_callback
        self._run_poll_callback = None
        if callback is not None:
            try:
                callback.stop()
            except Exception:
                pass

    def _finish_run(self) -> None:
        self._stop_run_polling()
        self._active_run_request = None
        self._run_cancel_event = None
        self._run_thread = None
        self._prior_complete_results = None
        self.view.elemental_run_nlls_button.loading = False
        self.view.elemental_cancel_button.loading = False
        self._refresh_button_states()

    def _publish_multifit_result_plot(
        self,
        result: xr.Dataset,
        *,
        activate: bool = True,
    ) -> None:
        """Add a committed run above the existing main plots without replacing them."""
        result_id = id(result)
        if result_id in self._published_result_ids:
            return
        layout = getattr(self.parent, "layout", None)
        add_result = getattr(layout, "add_nlls_result_plot", None)
        if add_result is None:
            return
        try:
            add_result(result)
            self._published_result_ids.add(result_id)
            # The run controls live in Results now, so a finished run has to bring
            # that tab forward exactly like a reference fit does. Restoring an older
            # result when the page is rebuilt must not steal the tab, though.
            if activate:
                self._activate_results_tab()
        except Exception as exc:
            # Plot publication is deliberately downstream from the atomic data commit.
            self._notify(
                "warning",
                f"The NLLS result was saved, but its plots could not be added: {exc}",
                9000,
            )

    def _restore_existing_multifit_result(self) -> None:
        result = self.app_state.nlls_results
        workspace = self.workspace
        if not isinstance(result, xr.Dataset) or workspace is None:
            return
        if (
            str(result.attrs.get("dataset_source_revision", ""))
            != workspace.dataset_identity.source_revision
        ):
            return
        self._publish_multifit_result_plot(result, activate=False)

    def _request_run_cancellation(self, *, notify: bool = True) -> None:
        if self._active_run_request is None or self._run_cancel_event is None:
            return
        if self._run_cancel_event.is_set():
            return
        self._run_cancel_event.set()
        self.app_state.nlls_run_state = "cancelling"
        progress = self.view.elemental_run_progress
        progress.name = "Cancelling after the active pixel..."
        progress.active = True
        self.view.elemental_cancel_button.loading = True
        self._refresh_button_states()
        if notify:
            self._notify(
                "warning",
                "Cancellation requested. The current pixel will finish first.",
            )

    def _on_cancel_elemental_nlls(self, event) -> None:
        self._request_run_cancellation()

    def _run_worker(
        self,
        request: NLLSRunRequest,
        source: xr.Dataset,
        geometry: ExperimentalGeometry,
        identity: DatasetIdentity,
        areas: dict[str, Any],
        references: dict[str, Any],
        cancel_event: Event,
    ) -> None:
        """Worker entrypoint: calculate and enqueue data, never mutate the GUI."""
        try:
            result = self.multifit_service.fit_areas(
                request,
                source,
                geometry,
                identity,
                areas,
                references,
                cancel_event=cancel_event,
                progress_callback=lambda done, total: self._run_events.put(
                    ("progress", request, int(done), int(total))
                ),
            )
            self._run_events.put(("result", request, result))
        except Exception as exc:
            self._run_events.put(
                ("error", request, type(exc).__name__, str(exc))
            )

    def _on_run_elemental_nlls(self, event) -> None:
        try:
            (
                request,
                source,
                geometry,
                identity,
                areas,
                references,
            ) = self._freeze_run_inputs()
            cancel_event = Event()
            previous = self.app_state.nlls_results
            self._prior_complete_results = (
                previous
                if isinstance(previous, xr.Dataset)
                and bool(previous.attrs.get("complete", False))
                else None
            )
            self._active_run_request = request
            self._run_cancel_event = cancel_event
            self.app_state.nlls_run_state = "running"
            progress = self.view.elemental_run_progress
            progress.param.update(
                name="Elemental NLLS: 0 / 0 pixels",
                value=0,
                active=True,
                bar_color="success",
                visible=True,
            )
            self.view.elemental_run_nlls_button.loading = True
            self._refresh_button_states()
            thread = Thread(
                target=self._run_worker,
                args=(
                    request,
                    source,
                    geometry,
                    identity,
                    areas,
                    references,
                    cancel_event,
                ),
                name=(
                    "elemental-nlls-parallel"
                    if request.parallel
                    else "elemental-nlls-serial"
                ),
                daemon=True,
            )
            self._run_thread = thread
            self._start_run_polling()
            thread.start()
        except Exception as exc:
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Cannot run Elemental NLLS: {exc}", 10000)
            self._finish_run()

    def _commit_run_result(
        self,
        request: NLLSRunRequest,
        result: xr.Dataset,
    ) -> None:
        progress = self.view.elemental_run_progress
        current = self._run_request_is_current(request)
        cancelled = bool(result.attrs.get("cancelled", False))
        if not current:
            self.app_state.nlls_run_state = "idle" if cancelled else "error"
            progress.param.update(
                name="Elemental NLLS result discarded: configuration changed",
                active=False,
                bar_color="warning",
            )
            self._notify(
                "warning",
                "The Elemental NLLS result was discarded because its source or model changed.",
                9000,
            )
            self._finish_run()
            return

        if cancelled:
            if self._prior_complete_results is None:
                self.app_state.nlls_results = result
                self.app_state.nlls_revision += 1
                self._publish_multifit_result_plot(result)
            self.app_state.nlls_run_state = "idle"
            processed = int(result.attrs.get("processed_pixels", 0))
            selected = int(result.attrs.get("selected_pixels", 0))
            progress.param.update(
                name=f"Elemental NLLS cancelled: {processed} / {selected} pixels",
                active=False,
                bar_color="warning",
            )
            self._notify(
                "warning",
                "Elemental NLLS cancelled; the previous complete result was preserved."
                if self._prior_complete_results is not None
                else "Elemental NLLS cancelled; the partial result was marked incomplete.",
                8000,
            )
            self._finish_run()
            return

        self.app_state.nlls_results = result
        self.app_state.nlls_run_state = "complete"
        self.app_state.nlls_revision += 1
        self._publish_multifit_result_plot(result)
        statuses, counts = np.unique(
            np.asarray(result["FitStatus"].values, dtype=np.int8),
            return_counts=True,
        )
        status_counts = {
            int(status): int(count) for status, count in zip(statuses, counts)
        }
        success_count = status_counts.get(int(FitStatus.SUCCESS), 0)
        error_count = status_counts.get(int(FitStatus.INSUFFICIENT_DATA), 0)
        error_count += status_counts.get(int(FitStatus.FIT_ERROR), 0)
        selected = int(result.attrs.get("selected_pixels", success_count + error_count))
        progress.param.update(
            name=f"Elemental NLLS complete: {success_count} / {selected} fitted",
            value=100,
            active=False,
            bar_color="success" if error_count == 0 else "warning",
        )
        if error_count:
            self._notify(
                "warning",
                f"Elemental NLLS completed with {success_count} successful and "
                f"{error_count} failed pixels.",
                9000,
            )
        else:
            self._notify(
                "success",
                f"Elemental NLLS completed for {success_count} pixels.",
            )
        self._finish_run()

    def _drain_run_events(self) -> None:
        """Consume worker messages on the Panel document thread."""
        while True:
            try:
                payload = self._run_events.get_nowait()
            except Empty:
                return
            kind, request, *values = payload
            if request != self._active_run_request:
                continue
            if kind == "progress":
                done, total = values
                percentage = int(round(100.0 * done / total)) if total else 0
                self.view.elemental_run_progress.param.update(
                    name=f"Elemental NLLS: {done} / {total} pixels",
                    value=max(0, min(100, percentage)),
                )
            elif kind == "result":
                self._commit_run_result(request, values[0])
                return
            elif kind == "error":
                error_type, message = values
                self.app_state.nlls_run_state = "error"
                self.view.elemental_run_progress.param.update(
                    name="Elemental NLLS failed",
                    active=False,
                    bar_color="danger",
                )
                self._notify(
                    "error",
                    f"Elemental NLLS failed ({error_type}): {message}",
                    10000,
                )
                self._finish_run()
                return

    def _on_element_changed(self, event) -> None:
        self._refresh_element_catalog()
        self._sync_edge_controls_from_selection()
        self._refresh_edge_preview()
        self._refresh_button_states()

    def _on_subshell_changed(self, event) -> None:
        try:
            self._update_selected_onset()
        except NLLSError as exc:
            self.view.elemental_onset_readout.value = "Onset (eV): -"
            self._notify("error", f"Cannot read the selected OOS edge: {exc}", 7000)
        self._sync_edge_controls_from_selection()
        self._refresh_edge_preview()
        self._refresh_button_states()

    def _on_chemical_shift_changed(self, event) -> None:
        if self._syncing_edge_controls:
            return
        workspace = self.workspace
        try:
            shift = float(event.new)
            continuum_parameter_specs(shift)
            continuum_ids = self._selected_continuum_ids()
            if workspace is not None and continuum_ids:
                saved_ids = {
                    continuum.id
                    for continuum in workspace.areas["default"].continuum_specs
                }
                matching = tuple(
                    continuum_id
                    for continuum_id in continuum_ids
                    if continuum_id in saved_ids
                )
                if matching:
                    previous_revision = workspace.dirty_revision
                    workspace.set_continuum_chemical_shift(
                        "default", matching, shift
                    )
                    if workspace.dirty_revision != previous_revision:
                        workspace.refresh_clustering_from_template()
                        self._publish_workspace()
                        model_editor = getattr(
                            self.view, "elemental_model_editor", None
                        )
                        if model_editor is not None:
                            model_editor.refresh()
                        edge_modal = getattr(self.view, "edge_added_modal", None)
                        if edge_modal is not None:
                            edge_modal.refresh()
        except (NLLSError, ValueError, TypeError):
            pass
        self._refresh_edge_preview()
        self._refresh_button_states()

    def _on_edge_preview_input_changed(self, event) -> None:
        """Persist saved OOS broadening, then redraw the visual preview."""
        if self._syncing_edge_controls:
            return
        workspace = self.workspace
        try:
            broadening = BroadeningSpec(
                enabled=bool(self.view.elemental_input["soften_edge"].value),
                sigma_eV=float(
                    self.view.elemental_input["soften_strength"].value
                ),
            )
            continuum_ids = self._selected_continuum_ids()
            if workspace is not None and continuum_ids:
                saved_ids = {
                    continuum.id
                    for continuum in workspace.areas["default"].continuum_specs
                }
                matching = tuple(
                    continuum_id
                    for continuum_id in continuum_ids
                    if continuum_id in saved_ids
                )
                if matching:
                    previous_revision = workspace.dirty_revision
                    workspace.set_continuum_broadening(
                        "default", matching, broadening
                    )
                    if workspace.dirty_revision != previous_revision:
                        workspace.refresh_clustering_from_template()
                        self._publish_workspace()
        except (NLLSError, ValueError, TypeError):
            pass
        self._refresh_edge_preview()
        self._refresh_button_states()

    def _on_fitting_tab_changed(self, event) -> None:
        """Scope the shared-pane OOS preview to the Elemental tab."""
        if int(event.new) == 1:
            self._sync_edge_controls_from_selection()
            self._refresh_edge_preview()
        else:
            self._clear_edge_preview()
        self._refresh_button_states()

    def _on_current_clustering_changed(self, event) -> None:
        self._refresh_button_states()

    def _on_dataset_metadata_changed(self, event) -> None:
        """Re-run both gates after the Dataset Information card rewrites the metadata."""
        self.on_source_changed()

    def _on_use_current_clustering(self, event) -> None:
        try:
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            if workspace.clustering_active:
                workspace.clear_clustering()
                self._publish_workspace()
                self.view.elemental_input["model_composition"].value = (
                    workspace.active_area_spec.model_composition.value
                )
                self._clear_clustering_in_main()
                self._notify("success", "Returned to the preprocessed ROI data.")
            else:
                definitions = self._current_clustering_definitions()
                areas = workspace.apply_clustering(definitions)
                self._publish_workspace()
                self.view.elemental_input["model_composition"].value = (
                    workspace.active_area_spec.model_composition.value
                )
                self._show_clustering_in_main()
                self._notify(
                    "success",
                    f"Current clustering applied to {len(areas)} NLLS areas.",
                )
        except (NLLSError, ValueError, TypeError) as exc:
            self._notify("error", f"Cannot use current clustering: {exc}", 8000)
        finally:
            self._refresh_button_states()

    def _on_fit_area_selection_changed(self, event) -> None:
        self._refresh_button_states()

    def _on_execution_mode_changed(self, event) -> None:
        self._refresh_button_states()

    def _on_select_all_fit_areas(self, event) -> None:
        selector = self.view.elemental_fit_areas_input
        options = selector.options
        selector.value = list(options.values()) if isinstance(options, dict) else list(options)
        self._refresh_button_states()

    def _on_model_composition_changed(self, event) -> None:
        if self.workspace is None:
            return
        self.workspace.set_model_composition("default", event.new)
        self.workspace.refresh_clustering_from_template()
        self._publish_workspace()
        self._refresh_button_states()

    def on_roi_changed(self) -> None:
        """Invalidate only the default reference when its committed ROI changes."""
        if self._active_run_request is not None:
            self._request_run_cancellation(notify=False)
        workspace = self.workspace
        if workspace is None or "default" not in workspace.areas:
            return
        if workspace.areas["default"].reference_strategy == "roi_mean":
            workspace.discard_reference("default")
            self._publish_workspace()
        self._refresh_edge_preview()
        self._refresh_button_states()

    def _on_add_edge(self, event) -> None:
        try:
            groups, snapshots, broadening = self._validate_selected_curves()
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
            _, symbol = self.provider.element_info(atomic_number)
            chemical_shift = float(self.view.elemental_input["chemical_shift"].value)
            amplitude_spec, shift_spec = continuum_parameter_specs(chemical_shift)
            shape = str(self.view.elemental_input["elnes_shape"].value)
            fwhm_eV = fwhm_from_attrs(self._active_dataset().attrs)
            eloss = np.asarray(
                self._active_dataset().coords["Eloss"].values, dtype=float
            )
            try:
                reference_spectrum = self._edge_preview_reference()[0].spectrum
            except (NLLSError, ValueError, TypeError, KeyError):
                reference_spectrum = None
            target_area_ids = ("default",)

            added: list[str] = []
            for group, snapshot in zip(groups, snapshots):
                token = stable_component_token(symbol or f"z{atomic_number}", group)
                edge_id = f"{token}_edge"
                onset = min(snapshot.onsets_eV)
                edge = EdgeSpec(
                    id=edge_id,
                    atomic_number=atomic_number,
                    symbol=symbol or f"Z{atomic_number}",
                    shells=tuple(group),
                    onset_eV=onset,
                )
                continuum = ContinuumSpec(
                    id=f"{token}_continuum",
                    edge_id=edge_id,
                    atomic_number=atomic_number,
                    symbol=edge.symbol,
                    shells=tuple(group),
                    prefix=f"{token}_cont_",
                    onset_eV=onset,
                    broadening=broadening,
                    amplitude=amplitude_spec,
                    chemical_shift=shift_spec,
                    provider_version=OOS_PROVIDER_VERSION,
                    chemical_shift_convention=CHEMICAL_SHIFT_CONVENTION,
                )
                fine_structures: list[FineStructureSpec] = []
                shifted_onsets = tuple(
                    float(shell_onset) - chemical_shift
                    for shell_onset in snapshot.onsets_eV
                )
                for shell, shell_onset in zip(group, snapshot.onsets_eV):
                    shifted_onset = float(shell_onset) - chemical_shift
                    next_onset = min(
                        (
                            candidate
                            for candidate in shifted_onsets
                            if candidate > shifted_onset
                        ),
                        default=None,
                    )
                    center_offset = self._initial_elnes_center_offset(
                        eloss,
                        reference_spectrum,
                        shifted_onset,
                        next_onset,
                    )
                    offset_from_onset, sigma, amplitude = (
                        fine_structure_parameter_specs(fwhm_eV, center_offset)
                    )
                    shell_token = stable_component_token(edge.symbol, (shell,))
                    fine_structures.append(
                        FineStructureSpec(
                            id=f"{shell_token}_elnes",
                            edge_id=edge_id,
                            shell=shell,
                            prefix=f"{shell_token}_elnes_",
                            shape=shape,
                            onset_eV=shell_onset,
                            offset_from_onset=offset_from_onset,
                            sigma=sigma,
                            amplitude=amplitude,
                        )
                    )
                for area_id in target_area_ids:
                    workspace.add_edge(
                        area_id,
                        edge,
                        continuum,
                        tuple(fine_structures),
                    )
                added.append(f"{edge.symbol} {'+'.join(group)}")
            workspace.refresh_clustering_from_template()
            self._publish_workspace()
            model_editor = getattr(self.view, "elemental_model_editor", None)
            if model_editor is not None:
                model_editor.refresh()
            self._refresh_edge_preview()
            self._refresh_button_states()
            self._notify("success", f"Elemental edge added: {', '.join(added)}")
        except (NLLSError, ValueError) as exc:
            self._notify("error", f"Cannot add Elemental edge: {exc}", 7000)
            self._refresh_edge_preview()
            self._refresh_button_states()

    def _build_area(self, area_id: str):
        self.on_source_changed(initial=True)
        workspace = self.workspace
        if workspace is None:
            raise ValueError(self._source_error or self._geometry_error or "invalid source")
        if area_id not in workspace.areas:
            raise ValueError(f"unknown NLLS area: {area_id}")
        area = workspace.areas[area_id]
        eloss = np.asarray(self._active_dataset().coords["Eloss"].values, dtype=float)
        built = self.builder.build(area, workspace.geometry, eloss, self._current_fit_range())
        snapshot = self.builder.snapshot(
            built,
            area,
            workspace.dataset_identity,
            eloss,
        )
        workspace.commit_model_build(snapshot)
        return built, snapshot

    def _on_build_model(self, event) -> None:
        """Compatibility hook for an explicit build; the UI builds lazily in Fit."""
        self.app_state.nlls_run_state = "building"
        try:
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            target_area_ids = ("default",)
            builds = tuple(self._build_area(area_id) for area_id in target_area_ids)
            built, snapshot = builds[0]
            workspace.refresh_clustering_from_template()
            self._publish_workspace()
            normalizations = ", ".join(
                f"{component_id}={curve.normalization_factor:.4g} {curve.units}"
                for component_id, curve in built.curve_snapshots.items()
            )
            self.app_state.nlls_run_state = "idle"
            self._notify(
                "success",
                f"Elemental model built for {', '.join(target_area_ids)}: "
                f"{len(snapshot.component_ids)} components ({normalizations}).",
                7000,
            )
        except (NLLSError, ValueError, TypeError) as exc:
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Cannot build Elemental model: {exc}", 8000)
        finally:
            self._refresh_button_states()

    def _fit_area(self, area_id: str):
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        if not workspace.is_area_built(area_id):
            self._build_area(area_id)
            workspace = self.workspace
            if workspace is None or not workspace.is_area_built(area_id):
                raise ValueError(f"area {area_id} could not be built for fitting")
        area = workspace.areas[area_id]
        dataset = self._active_dataset()
        eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float)
        reference = self._reference_selection_for_area(area_id)
        snapshot = self.reference_service.fit_area(
            area,
            workspace.geometry,
            workspace.dataset_identity,
            reference,
            eloss,
            self._current_fit_range(),
        )
        workspace.commit_reference(snapshot)
        self._publish_workspace()
        return snapshot

    def _fit_reference_batch(
        self,
        area_ids: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[ReferenceFitFailure, ...]]:
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        if not area_ids:
            raise ValueError("select at least one clustering area to fit")
        references: dict[str, ReferenceSpectrumSelection] = {}
        preparation_failures: list[ReferenceFitFailure] = []
        for area_id in area_ids:
            try:
                if not workspace.is_area_built(area_id):
                    self._build_area(area_id)
                    workspace = self.workspace
                    if workspace is None or not workspace.is_area_built(area_id):
                        raise ValueError(f"area {area_id} could not be built for fitting")
                references[area_id] = self._reference_selection_for_area(area_id)
            except Exception as exc:
                preparation_failures.append(
                    ReferenceFitFailure(area_id, type(exc).__name__, str(exc))
                )

        dataset = self._active_dataset()
        eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float)
        fit_areas = tuple(
            workspace.areas[area_id]
            for area_id in area_ids
            if area_id in references
        )
        batch = self.reference_service.fit_many(
            fit_areas,
            workspace.geometry,
            workspace.dataset_identity,
            references,
            eloss,
            self._current_fit_range(),
            method="leastsq",
        )
        commit_failures: list[ReferenceFitFailure] = []
        for snapshot in batch.snapshots:
            try:
                workspace.commit_reference(snapshot)
            except Exception as exc:
                commit_failures.append(
                    ReferenceFitFailure(snapshot.area_id, type(exc).__name__, str(exc))
                )
        failures = (
            tuple(preparation_failures) + batch.failures + tuple(commit_failures)
        )
        for failure in failures:
            workspace.discard_reference(failure.area_id)
        self._publish_workspace()
        successes = tuple(
            snapshot.area_id
            for snapshot in batch.snapshots
            if snapshot.area_id not in {failure.area_id for failure in commit_failures}
        )
        return successes, failures

    def _on_fit(self, event) -> None:
        workspace = self.workspace
        if workspace is None:
            return
        target_ids = (
            tuple(self.view.elemental_fit_areas_input.value)
            if workspace.clustering_active
            else ("default",)
        )
        self.app_state.nlls_run_state = "fitting_references"
        self.view.elemental_fit_button.loading = True
        try:
            if len(target_ids) == 1:
                snapshot = self._fit_area(target_ids[0])
                successes = (snapshot.area_id,)
                failures: tuple[ReferenceFitFailure, ...] = ()
            else:
                successes, failures = self._fit_reference_batch(target_ids)
            self.app_state.nlls_run_state = "error" if failures else "idle"
            if successes:
                self._refresh_results_view(preferred_area=successes[0], activate=True)
            if failures:
                failure_summary = "; ".join(
                    f"{failure.area_id}: {failure.message}" for failure in failures
                )
                self._notify(
                    "warning",
                    f"Reference fits completed for {', '.join(successes) or 'none'}; "
                    f"failures: {failure_summary}",
                    10000,
                )
            else:
                self._notify(
                    "success",
                    f"Reference fit converged for {', '.join(successes)}.",
                )
        except Exception as exc:
            current_workspace = self.workspace
            if current_workspace is not None:
                for area_id in target_ids:
                    current_workspace.discard_reference(area_id)
                self._publish_workspace()
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Reference fit failed: {exc}", 10000)
        finally:
            self.view.elemental_fit_button.loading = False
            self._refresh_button_states()
