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
        self.bind()
        self.on_source_changed(initial=True)

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
                inputs["model_composition"].param.watch(
                    self._on_model_composition_changed, "value"
                ),
                self.view.elemental_fit_areas_input.param.watch(
                    self._on_fit_area_selection_changed, "value"
                ),
            ]
        )
        self.view.elemental_add_edge_button.on_click(self._on_add_edge)
        self.view.elemental_build_model_button.on_click(self._on_build_model)
        self.view.elemental_fit_button.on_click(self._on_fit)
        self.view.elemental_select_all_fit_areas_button.on_click(
            self._on_select_all_fit_areas
        )
        self.view.elemental_use_current_clustering_button.on_click(
            self._on_use_current_clustering
        )
        self._watchers.append(
            self.app_state.param.watch(
                self._on_current_clustering_changed, "last_clustering_result"
            )
        )

    def cleanup(self) -> None:
        results_view = getattr(self.view, "elemental_results_view", None)
        if results_view is not None:
            results_view.set_main_plot_callback(None)
        for watcher in self._watchers:
            try:
                watcher.inst.param.unwatch(watcher)
            except Exception:
                pass
        self._watchers.clear()

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
            if not initial or self.workspace is not None:
                self.app_state.clear_nlls_state()
            self._refresh_results_view()
            self._clear_clustering_in_main()
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
        self._refresh_button_states()
        self._refresh_results_view()

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
        clustering_button.disabled = not (clustering_active or clustering_valid)

        area = workspace.areas.get("default") if workspace is not None else None
        has_continuum = bool(area and area.continuum_specs)
        self.view.elemental_build_model_button.disabled = not has_continuum

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
        fit_areas.disabled = not clustering_settings_available
        self.view.elemental_fit_area_settings_button.disabled = not (
            clustering_settings_available
        )
        self.view.elemental_select_all_fit_areas_button.disabled = not (
            clustering_settings_available
        )

        target_ids = tuple(fit_areas.value) if clustering_active else ("default",)
        targets_available = bool(target_ids and workspace is not None)
        for area_id in target_ids:
            try:
                if workspace is None or not workspace.is_area_built(area_id):
                    targets_available = False
                    break
                self._reference_mask_for_area(area_id)
            except (NLLSError, ValueError, TypeError):
                targets_available = False
                break
        self.view.elemental_fit_button.disabled = not targets_available
        # Multipixel propagation/results are a later phase; never advertise a runnable action yet.
        self.view.elemental_run_nlls_button.disabled = True
        self.view.elemental_cancel_button.disabled = True

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
            tabs = getattr(self.view, "fitting_tabs", None)
            if tabs is not None:
                tabs.active = 2

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
        workspace = self.workspace
        if workspace is None or "default" not in workspace.areas:
            return
        if workspace.areas["default"].reference_strategy == "roi_mean":
            workspace.discard_reference("default")
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
                    "default",
                    edge,
                    continuum,
                    tuple(fine_structures),
                )
                added.append(f"{edge.symbol} {'+'.join(group)}")
            workspace.refresh_clustering_from_template()
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
        return built, snapshot

    def _on_build_model(self, event) -> None:
        self.app_state.nlls_run_state = "building"
        self.view.elemental_build_model_button.loading = True
        try:
            workspace = self.workspace
            if workspace is None:
                raise ValueError("no valid NLLS workspace")
            built, snapshot = self._build_area("default")
            workspace.refresh_clustering_from_template()
            self._publish_workspace()
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
