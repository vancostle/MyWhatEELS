"""Panel adapter for the pure Elemental NLLS domain services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import panel as pn

from whateels.nlls.areas import AreaDefinition, ClusteringAreaAdapter
from whateels.nlls.contracts import (
    BroadeningSpec,
    ContinuumSpec,
    DatasetIdentity,
    EdgeSpec,
    ExperimentalGeometry,
    FineStructureSpec,
    FitRange,
    ModelComposition,
    ReferenceFitFailure,
)
from whateels.nlls.cross_sections import OOSContinuumProvider
from whateels.nlls.defaults import (
    CHEMICAL_SHIFT_CONVENTION,
    OOS_PROVIDER_VERSION,
    canonical_subshell_groups,
    continuum_parameter_specs,
    fine_structure_parameter_specs,
    fwhm_from_attrs,
    stable_component_token,
)
from whateels.nlls.errors import NLLSError
from whateels.nlls.model_builder import NLLSModelBuilder
from whateels.nlls.provenance import validate_background_subtracted
from whateels.nlls.references import (
    ReferenceFitService,
    ReferenceSpectrumSelection,
    ReferenceSpectrumService,
)
from whateels.nlls.workspace import NLLSWorkspace

if TYPE_CHECKING:
    from ..view import FittingView
    from . import FittingController
    from whateels.state import AppState


class NLLSController:
    """Bind Elemental widgets without changing the manual fitting callbacks."""

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
        self._source_error: str | None = None
        self._geometry_error: str | None = None
        self._validated_geometry: ExperimentalGeometry | None = None
        self._watchers: list[Any] = []
        self._configure_dataset_controls()
        self.bind()
        self.on_source_changed(initial=True)

    @property
    def workspace(self) -> NLLSWorkspace | None:
        value = self.app_state.nlls_workspace
        return value if isinstance(value, NLLSWorkspace) else None

    def bind(self) -> None:
        inputs = self.view.elemental_input
        self._watchers.extend(
            [
                inputs["element_atomic_number"].param.watch(self._on_element_changed, "value"),
                inputs["subshells"].param.watch(self._on_subshell_changed, "value"),
                inputs["model_composition"].param.watch(
                    self._on_model_composition_changed, "value"
                ),
                inputs["active_area"].param.watch(self._on_active_area_changed, "value"),
                inputs["default_reference_strategy"].param.watch(
                    self._on_default_reference_strategy_changed, "value"
                ),
                inputs["fit_range"].param.watch(self._on_fit_range_changed, "value"),
            ]
        )
        self.view.elemental_add_edge_button.on_click(self._on_add_edge)
        self.view.elemental_build_model_button.on_click(self._on_build_model)
        self.view.elemental_reset_area_button.on_click(self._on_reset_area_model)
        self.view.elemental_fit_current_reference_button.on_click(
            self._on_fit_current_reference
        )
        self.view.elemental_fit_all_references_button.on_click(self._on_fit_all_references)
        self.view.elemental_use_current_clustering_button.on_click(
            self._on_use_current_clustering
        )
        self._watchers.append(
            self.app_state.param.watch(
                self._on_current_clustering_changed, "last_clustering_result"
            )
        )

    def cleanup(self) -> None:
        for watcher in self._watchers:
            try:
                watcher.inst.param.unwatch(watcher)
            except Exception:
                pass
        self._watchers.clear()

    def _configure_dataset_controls(self) -> None:
        dataset = self.app_state.plot_dataset
        slider = self.view.elemental_input["fit_range"]
        previous_value = tuple(slider.value) if len(slider.value) == 2 else None
        if dataset is None or "Eloss" not in getattr(dataset, "coords", {}):
            slider.disabled = True
            return
        eloss = np.asarray(dataset.coords["Eloss"].values, dtype=float)
        finite = eloss[np.isfinite(eloss)]
        if finite.size < 2:
            slider.disabled = True
            return
        minimum = float(np.min(finite))
        maximum = float(np.max(finite))
        positive_steps = np.abs(np.diff(np.sort(np.unique(finite))))
        positive_steps = positive_steps[positive_steps > 0.0]
        step = float(np.median(positive_steps)) if positive_steps.size else 0.1
        slider.start = minimum
        slider.end = maximum
        slider.step = max(step, np.finfo(float).eps)
        if (
            previous_value is not None
            and minimum <= float(previous_value[0]) < float(previous_value[1]) <= maximum
        ):
            slider.value = previous_value
        else:
            slider.value = (minimum, maximum)
        slider.disabled = False

    def _active_dataset(self):
        return self.app_state.plot_dataset

    def _source_kind(self, dataset) -> str:
        return (
            "preprocessed"
            if dataset is not None and dataset is self.app_state.preprocessed_plot_dataset
            else "raw"
        )

    def _current_fit_range(self) -> FitRange:
        lower, upper = self.view.elemental_input["fit_range"].value
        return FitRange(min(float(lower), float(upper)), max(float(lower), float(upper)))

    def on_source_changed(self, initial: bool = False) -> None:
        """Invalidate stale NLLS artifacts and resynchronize all Elemental controls."""
        self._configure_dataset_controls()
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
            if not initial or self.workspace is not None:
                self.app_state.clear_nlls_state()
            self._update_validation_status()
            self._refresh_element_catalog()
            self._refresh_button_states()
            return

        identity = DatasetIdentity.from_dataset(
            dataset,
            tab_index=self.app_state.selected_tab_index_dataset,
            source_kind=self._source_kind(dataset),
            preprocessing_history=history,
            background_subtracted=True,
        )

        workspace = self.workspace
        if workspace is None or workspace.dataset_identity != identity:
            workspace = NLLSWorkspace.create(identity, geometry)
            workspace.set_model_composition(
                workspace.active_area,
                self.view.elemental_input["model_composition"].value,
            )
            workspace.set_reference_strategy(
                "default",
                self.view.elemental_input["default_reference_strategy"].value,
            )
            self.app_state.nlls_workspace = workspace
            self.app_state.nlls_results = None
            self.app_state.nlls_run_state = "idle"
            self.app_state.nlls_revision += 1
        elif workspace.geometry != geometry:
            workspace.geometry = geometry
            workspace.invalidate_all()
            self._publish_workspace()

        self._update_validation_status()
        self._refresh_area_controls()
        self._refresh_element_catalog()
        self._refresh_button_states()

    def _update_validation_status(self) -> None:
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

    def _refresh_element_catalog(self) -> None:
        atomic_number = int(self.view.elemental_input["element_atomic_number"].value)
        shells_widget = self.view.elemental_input["subshells"]
        try:
            shells = list(self.provider.available_edges(atomic_number))
            current = [shell for shell in shells_widget.value if shell in shells]
            shells_widget.options = shells
            shells_widget.value = current
            shells_widget.disabled = not bool(shells)
            self._update_selected_onset()
        except NLLSError:
            shells_widget.options = []
            shells_widget.value = []
            shells_widget.disabled = True
            self.view.elemental_onset_readout.value = "Onset (eV): -"

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
        selected_valid = False
        if workspace is not None:
            try:
                self._validate_selected_curves()
                selected_valid = True
            except (NLLSError, ValueError):
                selected_valid = False
        self.view.elemental_add_edge_button.disabled = not selected_valid

        clustering_valid = False
        if workspace is not None and self.app_state.last_clustering_result is not None:
            try:
                clustering_valid = bool(self._current_clustering_definitions())
            except (NLLSError, ValueError, TypeError):
                clustering_valid = False
        self.view.elemental_use_current_clustering_button.disabled = not clustering_valid
        area = workspace.active_area_spec if workspace is not None else None
        has_continuum = bool(area and area.continuum_specs)
        self.view.elemental_build_model_button.disabled = not has_continuum
        self.view.elemental_reset_area_button.disabled = not bool(area and area.edges)
        current_reference_available = False
        if workspace is not None and area is not None:
            try:
                self._reference_mask_for_area(area.area_id)
                current_reference_available = True
            except (NLLSError, ValueError, TypeError):
                current_reference_available = False
        self.view.elemental_fit_current_reference_button.disabled = not bool(
            area
            and workspace.is_area_built(area.area_id)
            and current_reference_available
        )
        runnable_area_ids = workspace.runnable_area_ids if workspace is not None else ()
        all_built = bool(runnable_area_ids) and all(
            workspace.is_area_built(area_id) for area_id in runnable_area_ids
        )
        all_references_available = bool(runnable_area_ids)
        for area_id in runnable_area_ids:
            try:
                self._reference_mask_for_area(area_id)
            except (NLLSError, ValueError, TypeError):
                all_references_available = False
                break
        needs_reference_fit = any(
            not self._reference_is_current(area_id) for area_id in runnable_area_ids
        )
        self.view.elemental_fit_all_references_button.disabled = not (
            all_built and all_references_available and needs_reference_fit
        )

        valid_refs = []
        if workspace is not None:
            valid_refs = [
                area_id
                for area_id, snapshot in workspace.reference_fits.items()
                if area_id in runnable_area_ids and self._reference_is_current(area_id)
            ]
        fit_areas = self.view.elemental_input["fit_areas"]
        fit_areas.options = valid_refs
        fit_areas.value = [area_id for area_id in fit_areas.value if area_id in valid_refs]
        if valid_refs and not fit_areas.value:
            fit_areas.value = list(valid_refs)
        fit_areas.disabled = not bool(valid_refs)
        # Multipixel propagation/results are a later phase; never advertise a runnable action yet.
        self.view.elemental_run_nlls_button.disabled = True
        self.view.elemental_cancel_button.disabled = True

    def _refresh_area_controls(self) -> None:
        workspace = self.workspace
        if workspace is None:
            return
        options = {
            workspace.areas[area_id].label: area_id
            for area_id in workspace.runnable_area_ids
        }
        active = self.view.elemental_input["active_area"]
        active.options = options
        if workspace.active_area not in workspace.runnable_area_ids:
            workspace.active_area = workspace.runnable_area_ids[0]
        active.value = workspace.active_area
        strategy = self.view.elemental_input["default_reference_strategy"]
        strategy.value = workspace.areas["default"].reference_strategy
        strategy.disabled = workspace.active_area != "default"

    def _publish_workspace(self) -> None:
        self.app_state.nlls_workspace = self.workspace
        self.app_state.nlls_revision += 1
        self.app_state.nlls_results = None

    @staticmethod
    def _notify(level: str, message: str, duration: int = 5000) -> None:
        try:
            getattr(pn.state.notifications, level)(message, duration=duration)
        except Exception:
            pass

    def _on_element_changed(self, event) -> None:
        self._refresh_element_catalog()
        self._refresh_button_states()

    def _on_subshell_changed(self, event) -> None:
        try:
            self._update_selected_onset()
        except NLLSError as exc:
            self.view.elemental_onset_readout.value = "Onset (eV): -"
            self._notify("error", f"Cannot read the selected OOS edge: {exc}", 7000)
        self._refresh_button_states()

    def _on_current_clustering_changed(self, event) -> None:
        self._refresh_button_states()

    def _on_use_current_clustering(self, event) -> None:
        try:
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            definitions = self._current_clustering_definitions()
            areas = workspace.apply_clustering(definitions)
            self._publish_workspace()
            self._refresh_area_controls()
            self.view.elemental_input["model_composition"].value = (
                workspace.active_area_spec.model_composition.value
            )
            self._notify("success", f"Current clustering applied to {len(areas)} NLLS areas.")
        except (NLLSError, ValueError, TypeError) as exc:
            self._notify("error", f"Cannot use current clustering: {exc}", 8000)
        finally:
            self._refresh_button_states()

    def _on_model_composition_changed(self, event) -> None:
        if self.workspace is None:
            return
        self.workspace.set_model_composition(self.workspace.active_area, event.new)
        self._publish_workspace()
        self._refresh_button_states()

    def _on_default_reference_strategy_changed(self, event) -> None:
        workspace = self.workspace
        if workspace is None or "default" not in workspace.areas:
            return
        workspace.set_reference_strategy("default", str(event.new))
        self._publish_workspace()
        self._refresh_button_states()

    def _on_active_area_changed(self, event) -> None:
        if self.workspace is None or event.new not in self.workspace.areas:
            return
        self.workspace.active_area = str(event.new)
        self.app_state.nlls_revision += 1
        composition = self.workspace.active_area_spec.model_composition.value
        self.view.elemental_input["model_composition"].value = composition
        self.view.elemental_input["default_reference_strategy"].disabled = (
            self.workspace.active_area != "default"
        )
        self._refresh_button_states()

    def on_roi_changed(self) -> None:
        """Invalidate only the default reference when its committed ROI changes."""
        workspace = self.workspace
        if workspace is None or "default" not in workspace.areas:
            return
        if workspace.areas["default"].reference_strategy == "roi_mean":
            workspace.discard_reference("default")
            self._publish_workspace()
        self._refresh_button_states()

    def _on_fit_range_changed(self, event) -> None:
        if self.workspace is not None and event.old != event.new:
            self.workspace.invalidate_all()
            self._publish_workspace()
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
                for shell, shell_onset in zip(group, snapshot.onsets_eV):
                    center, sigma, amplitude = fine_structure_parameter_specs(
                        shell_onset, fwhm_eV
                    )
                    shell_token = stable_component_token(edge.symbol, (shell,))
                    fine_structures.append(
                        FineStructureSpec(
                            id=f"{shell_token}_elnes",
                            edge_id=edge_id,
                            shell=shell,
                            prefix=f"{shell_token}_elnes_",
                            shape=shape,
                            center=center,
                            sigma=sigma,
                            amplitude=amplitude,
                        )
                    )
                workspace.add_edge(
                    workspace.active_area,
                    edge,
                    continuum,
                    tuple(fine_structures),
                )
                added.append(f"{edge.symbol} {'+'.join(group)}")
            self._publish_workspace()
            self._refresh_button_states()
            self._notify("success", f"Elemental edge added: {', '.join(added)}")
        except (NLLSError, ValueError) as exc:
            self._notify("error", f"Cannot add Elemental edge: {exc}", 7000)
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
        self._publish_workspace()
        return built, snapshot

    def _on_build_model(self, event) -> None:
        self.app_state.nlls_run_state = "building"
        self.view.elemental_build_model_button.loading = True
        try:
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            built, snapshot = self._build_area(workspace.active_area)
            normalizations = ", ".join(
                f"{component_id}={curve.normalization_factor:.4g} {curve.units}"
                for component_id, curve in built.curve_snapshots.items()
            )
            self.app_state.nlls_run_state = "idle"
            self._notify(
                "success",
                f"Elemental model built for {snapshot.area_id}: "
                f"{len(snapshot.component_ids)} components ({normalizations}).",
                7000,
            )
        except (NLLSError, ValueError, TypeError) as exc:
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Cannot build Elemental model: {exc}", 8000)
        finally:
            self.view.elemental_build_model_button.loading = False
            self._refresh_button_states()

    def _reference_for_active_area(self) -> np.ndarray:
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        return self._reference_selection_for_area(workspace.active_area).spectrum

    def _fit_area(self, area_id: str):
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        if not workspace.is_area_built(area_id):
            raise ValueError(f"area {area_id} must be built before fitting its reference")
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

    def _on_fit_current_reference(self, event) -> None:
        workspace = self.workspace
        if workspace is None:
            return
        self.app_state.nlls_run_state = "fitting_references"
        self.view.elemental_fit_current_reference_button.loading = True
        area_id = workspace.active_area
        try:
            snapshot = self._fit_area(area_id)
            self.app_state.nlls_run_state = "idle"
            self._notify(
                "success",
                f"Reference fit converged for {snapshot.area_id}: "
                f"redchi={snapshot.redchi:.6g}, "
                f"{snapshot.reference_pixel_count} reference pixels.",
                7000,
            )
        except Exception as exc:
            workspace.discard_reference(area_id)
            self._publish_workspace()
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Reference fit failed: {exc}", 8000)
        finally:
            self.view.elemental_fit_current_reference_button.loading = False
            self._refresh_button_states()

    def _fit_all_reference_batch(
        self,
    ) -> tuple[tuple[str, ...], tuple[ReferenceFitFailure, ...]]:
        workspace = self.workspace
        if workspace is None:
            raise ValueError("no valid NLLS workspace")
        area_ids = workspace.runnable_area_ids
        references: dict[str, ReferenceSpectrumSelection] = {}
        preparation_failures: list[ReferenceFitFailure] = []
        for area_id in area_ids:
            try:
                if not workspace.is_area_built(area_id):
                    raise ValueError(f"area {area_id} must be built first")
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

    def _on_fit_all_references(self, event) -> None:
        if self.workspace is None:
            return
        self.app_state.nlls_run_state = "fitting_references"
        self.view.elemental_fit_all_references_button.loading = True
        try:
            successes, failures = self._fit_all_reference_batch()
            self.app_state.nlls_run_state = "error" if failures else "idle"
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
                    f"Reference fits converged for {', '.join(successes)}.",
                )
        except Exception as exc:
            workspace = self.workspace
            if workspace is not None:
                for area_id in workspace.runnable_area_ids:
                    workspace.discard_reference(area_id)
                self._publish_workspace()
            self.app_state.nlls_run_state = "error"
            self._notify("error", f"Cannot fit all references: {exc}", 10000)
        finally:
            self.view.elemental_fit_all_references_button.loading = False
            self._refresh_button_states()

    def _on_reset_area_model(self, event) -> None:
        workspace = self.workspace
        if workspace is None:
            return
        area_id = workspace.active_area
        workspace.reset_area(area_id)
        self._publish_workspace()
        self.view.elemental_input["model_composition"].value = (
            workspace.active_area_spec.model_composition.value
        )
        self.view.elemental_input["default_reference_strategy"].value = (
            workspace.areas["default"].reference_strategy
        )
        self._notify("success", f"Elemental area {area_id} was reset.")
        self._refresh_button_states()
