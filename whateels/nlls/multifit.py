"""Deterministic serial Elemental NLLS fitting over spectrum images."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
from typing import Any

import lmfit
import numpy as np
import xarray as xr

from .contracts import (
    AreaModelSpec,
    DatasetIdentity,
    ExperimentalGeometry,
    NLLSRunRequest,
    ReferenceFitSnapshot,
)
from .defaults import (
    CHEMICAL_SHIFT_CONVENTION,
    OOS_FORMULA_VERSION,
    OOS_PROVIDER_VERSION,
    SCHEMA_VERSION,
)
from .errors import (
    InsufficientReferenceDataError,
    InvalidRunRequestError,
    PixelFitError,
)
from .model_builder import BuiltAreaModel, NLLSModelBuilder
from .results import FitStatus, NLLSResultsAccumulator, NLLSResultsAssembler


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class PixelFitSnapshot:
    redchi: float
    best_fit: np.ndarray
    residual: np.ndarray
    components: dict[str, np.ndarray]
    parameters: dict[str, tuple[float, float | None]]


def _package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "unknown"


class ElementalMultifitService:
    """Fit selected masks serially, isolating every pixel failure."""

    def __init__(self, model_builder: NLLSModelBuilder, *, progress_chunk_size: int = 16):
        self.model_builder = model_builder
        self.progress_chunk_size = max(1, int(progress_chunk_size))

    @staticmethod
    def _is_cancelled(cancel_event: Any | None) -> bool:
        return bool(cancel_event is not None and cancel_event.is_set())

    @staticmethod
    def _area_mask(area: AreaModelSpec, spatial_shape: tuple[int, int]) -> np.ndarray:
        if area.area_id == "default" and area.mask is None:
            return np.ones(spatial_shape, dtype=bool)
        mask = np.asarray(area.mask, dtype=bool)
        if mask.shape != spatial_shape or not np.any(mask):
            raise InvalidRunRequestError(
                f"area {area.area_id} has an empty or incompatible mask"
            )
        return mask

    @staticmethod
    def _validate_request(
        request: NLLSRunRequest,
        source: xr.Dataset,
        dataset_identity: DatasetIdentity,
        areas: Mapping[str, AreaModelSpec],
        reference_fits: Mapping[str, ReferenceFitSnapshot],
    ) -> None:
        if request.parallel:
            raise InvalidRunRequestError(
                "parallel NLLS is unavailable until serial parity is validated"
            )
        if request.rerun_from is not None:
            raise InvalidRunRequestError("modified-model reruns belong to the rerun phase")
        if request.dataset_source_revision and (
            request.dataset_source_revision != dataset_identity.source_revision
        ):
            raise InvalidRunRequestError("NLLS request belongs to a stale dataset source")
        cube = np.asarray(source["ElectronCount"].values)
        if tuple(int(value) for value in cube.shape) != dataset_identity.shape:
            raise InvalidRunRequestError("NLLS source shape does not match DatasetIdentity")
        compositions = dict(request.model_composition_by_area)
        revisions = dict(request.area_revisions)
        for area_id in request.selected_areas:
            if area_id not in areas:
                raise InvalidRunRequestError(f"unknown NLLS area: {area_id}")
            area = areas[area_id]
            reference = reference_fits.get(area_id)
            if reference is None or not reference.success:
                raise InvalidRunRequestError(
                    f"area {area_id} has no converged reference fit"
                )
            if compositions[area_id] != area.model_composition:
                raise InvalidRunRequestError(
                    f"area {area_id} model composition changed after request creation"
                )
            if revisions and revisions[area_id] != area.revision:
                raise InvalidRunRequestError(
                    f"area {area_id} revision changed after request creation"
                )
            if reference.dataset_source_revision != dataset_identity.source_revision:
                raise InvalidRunRequestError(f"area {area_id} reference uses another source")
            if reference.area_revision != area.revision:
                raise InvalidRunRequestError(f"area {area_id} reference is stale")
            if reference.model_composition != area.model_composition:
                raise InvalidRunRequestError(
                    f"area {area_id} reference uses another model composition"
                )
            if reference.fit_range != request.fit_range:
                raise InvalidRunRequestError(f"area {area_id} reference fit range is stale")
            if reference.method != request.method:
                raise InvalidRunRequestError(
                    f"area {area_id} reference uses another fit method"
                )

    @staticmethod
    def _parameters_from_reference(
        built: BuiltAreaModel,
        reference: ReferenceFitSnapshot,
    ):
        params = built.params.copy()
        snapshots = {str(item["name"]): item for item in reference.params}
        if set(snapshots) != set(params):
            raise InvalidRunRequestError(
                f"area {reference.area_id} reference parameters do not match its model"
            )
        for name, parameter in params.items():
            snapshot = snapshots[name]
            parameter.set(
                value=float(snapshot["value"]),
                min=float(snapshot["min"]),
                max=float(snapshot["max"]),
                vary=bool(snapshot["vary"]),
                expr=snapshot.get("expr"),
                brute_step=snapshot.get("brute_step"),
            )
        return params

    @classmethod
    def _initial_params_for_pixel(
        cls,
        built: BuiltAreaModel,
        reference: ReferenceFitSnapshot,
        rerun_from: Mapping[str, Mapping[str, float]] | None = None,
    ):
        """Return an independent parameter copy for exactly one pixel."""
        params = cls._parameters_from_reference(built, reference)
        if rerun_from is not None:
            raise InvalidRunRequestError("rerun propagation is not part of the first run")
        return params.copy()

    @staticmethod
    def _component_id_map(area: AreaModelSpec) -> dict[str, str]:
        result = {
            str(spec.prefix): str(spec.id) for spec in area.continuum_specs
        }
        if area.model_composition.value == "continuum_plus_elnes":
            result.update(
                {
                    str(spec.prefix): str(spec.id)
                    for spec in area.fine_structure_specs
                    if spec.enabled
                }
            )
        return result

    @staticmethod
    def _selected_coordinates(mask: np.ndarray) -> np.ndarray:
        """Return a deterministic traversal that tests may safely permute."""
        return np.argwhere(np.asarray(mask, dtype=bool))

    def _fit_pixel(
        self,
        built: BuiltAreaModel,
        area: AreaModelSpec,
        reference: ReferenceFitSnapshot,
        signal: np.ndarray,
        eloss: np.ndarray,
        request: NLLSRunRequest,
    ) -> PixelFitSnapshot:
        pixel = np.asarray(signal, dtype=float).reshape(-1)
        x_axis = np.asarray(eloss, dtype=float).reshape(-1)
        finite = (
            np.isfinite(pixel)
            & np.isfinite(x_axis)
            & (x_axis >= request.fit_range.minimum)
            & (x_axis <= request.fit_range.maximum)
        )
        if np.count_nonzero(finite) <= built.n_varying_parameters:
            raise InsufficientReferenceDataError(
                "pixel has too few finite samples for its varying parameters"
            )
        initial = self._initial_params_for_pixel(built, reference)
        result = built.model.fit(
            pixel[finite],
            params=initial,
            x=x_axis[finite],
            method=request.method,
        )
        redchi = float(result.redchi)
        if (
            not result.success
            or not math.isfinite(redchi)
            or any(not np.isfinite(parameter.value) for parameter in result.params.values())
        ):
            raise PixelFitError(str(result.message))
        best_fit = np.asarray(
            built.model.eval(params=result.params, x=x_axis), dtype=float
        )
        evaluated = {
            str(name): np.asarray(values, dtype=float)
            for name, values in built.model.eval_components(
                params=result.params, x=x_axis
            ).items()
        }
        if np.any(~np.isfinite(best_fit)) or any(
            np.any(~np.isfinite(values)) for values in evaluated.values()
        ):
            raise PixelFitError("pixel fit produced non-finite model curves")
        component_ids = self._component_id_map(area)
        components = {
            component_ids.get(name, name.rstrip("_") or "component"): values
            for name, values in evaluated.items()
        }
        parameters = {
            str(name): (
                float(parameter.value),
                (
                    float(parameter.stderr)
                    if parameter.stderr is not None and np.isfinite(parameter.stderr)
                    else None
                ),
            )
            for name, parameter in result.params.items()
        }
        return PixelFitSnapshot(
            redchi=redchi,
            best_fit=best_fit,
            residual=pixel - best_fit,
            components=components,
            parameters=parameters,
        )

    def fit_area_serial(
        self,
        request: NLLSRunRequest,
        area: AreaModelSpec,
        reference: ReferenceFitSnapshot,
        source_cube: np.ndarray,
        eloss: np.ndarray,
        mask: np.ndarray,
        accumulator: NLLSResultsAccumulator,
        *,
        geometry: ExperimentalGeometry,
        built: BuiltAreaModel | None = None,
        cancel_event: Any | None = None,
        on_pixel_done: Callable[[], None] | None = None,
    ) -> None:
        if built is None:
            built = self.model_builder.build(
                area, geometry, eloss, request.fit_range
            )
        # Validate once before entering the hot loop. Every pixel still receives a copy.
        self._parameters_from_reference(built, reference)
        for y, x in self._selected_coordinates(mask):
            if self._is_cancelled(cancel_event):
                return
            try:
                pixel_result = self._fit_pixel(
                    built,
                    area,
                    reference,
                    source_cube[int(y), int(x), :],
                    eloss,
                    request,
                )
                accumulator.store_success(
                    int(y),
                    int(x),
                    redchi=pixel_result.redchi,
                    best_fit=pixel_result.best_fit,
                    residual=pixel_result.residual,
                    components=pixel_result.components,
                    parameters=pixel_result.parameters,
                )
            except InsufficientReferenceDataError:
                accumulator.store_error(
                    int(y), int(x), FitStatus.INSUFFICIENT_DATA
                )
            except Exception:
                accumulator.store_error(int(y), int(x), FitStatus.FIT_ERROR)
            finally:
                if on_pixel_done is not None:
                    on_pixel_done()

    def fit_areas(
        self,
        request: NLLSRunRequest,
        source: xr.Dataset,
        geometry: ExperimentalGeometry,
        dataset_identity: DatasetIdentity,
        areas: Mapping[str, AreaModelSpec],
        reference_fits: Mapping[str, ReferenceFitSnapshot],
        *,
        cancel_event: Any | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> xr.Dataset:
        self._validate_request(
            request, source, dataset_identity, areas, reference_fits
        )
        accumulator = NLLSResultsAccumulator.create(source)
        cube = accumulator.original_data
        eloss = accumulator.eloss
        masks: dict[str, np.ndarray] = {}
        for index, area_id in enumerate(request.selected_areas):
            area = areas[area_id]
            mask = self._area_mask(area, accumulator.spatial_shape)
            masks[area_id] = mask
            label = int(area.clustering_label) if area.clustering_label is not None else index
            accumulator.select_area(area_id, label, mask)

        curve_metadata: list[dict[str, Any]] = []
        built_models: dict[str, BuiltAreaModel] = {}
        for area_id in request.selected_areas:
            area = areas[area_id]
            # Reconstruct exactly once per area, then reuse it for every pixel.
            built = self.model_builder.build(
                area, geometry, eloss, request.fit_range
            )
            built_models[area_id] = built
            for component_id in built.component_ids:
                accumulator.register_component(component_id)
            for parameter in reference_fits[area_id].params:
                accumulator.register_parameter(str(parameter["name"]))
            for component_id, curve in built.curve_snapshots.items():
                curve_metadata.append(
                    {
                        "area_id": area_id,
                        "component_id": component_id,
                        "provider_version": curve.provider_version,
                        "formula_version": curve.formula_version,
                        "table_checksums": tuple(curve.table_checksums),
                    }
                )

        total = sum(int(np.count_nonzero(mask)) for mask in masks.values())
        completed = 0
        last_published = 0
        if progress_callback is not None:
            progress_callback(0, total)

        def on_pixel_done() -> None:
            nonlocal completed, last_published
            completed += 1
            if progress_callback is not None and (
                completed == total
                or completed - last_published >= self.progress_chunk_size
            ):
                last_published = completed
                progress_callback(completed, total)

        for area_id in request.selected_areas:
            if self._is_cancelled(cancel_event):
                break
            area = areas[area_id]
            self.fit_area_serial(
                request,
                area,
                reference_fits[area_id],
                cube,
                eloss,
                masks[area_id],
                accumulator,
                geometry=geometry,
                built=built_models[area_id],
                cancel_event=cancel_event,
                on_pixel_done=on_pixel_done,
            )

        cancelled = self._is_cancelled(cancel_event) and completed < total
        if cancelled:
            accumulator.cancel_pending()
        elif progress_callback is not None and last_published != total:
            progress_callback(total, total)

        statuses, counts = np.unique(accumulator.fit_status, return_counts=True)
        status_counts = {
            str(int(status)): int(count) for status, count in zip(statuses, counts)
        }
        configuration = {
            area_id: {
                "revision": int(areas[area_id].revision),
                "model_composition": areas[area_id].model_composition.value,
                "component_ids": [
                    spec.id for spec in areas[area_id].continuum_specs
                ]
                + [
                    spec.id
                    for spec in areas[area_id].fine_structure_specs
                    if spec.enabled
                ],
                "mask_fingerprint": areas[area_id].mask_fingerprint,
            }
            for area_id in request.selected_areas
        }
        request_payload = {
            **asdict(request),
            "fit_range": asdict(request.fit_range),
            "model_composition_by_area": [
                [area_id, composition.value]
                for area_id, composition in request.model_composition_by_area
            ],
        }
        attrs = {
            "schema_version": int(SCHEMA_VERSION),
            "dataset_identity": json.dumps(asdict(dataset_identity), sort_keys=True),
            "dataset_source_revision": dataset_identity.source_revision,
            "source_kind": dataset_identity.source_kind,
            "geometry": json.dumps(asdict(geometry), sort_keys=True),
            "method": request.method,
            "model_composition_by_area": json.dumps(
                {
                    area_id: composition.value
                    for area_id, composition in request.model_composition_by_area
                },
                sort_keys=True,
            ),
            "background_subtracted": int(dataset_identity.background_subtracted),
            "preprocessing_history": json.dumps(
                dataset_identity.preprocessing_history, sort_keys=True, default=str
            ),
            "chemical_shift_convention": CHEMICAL_SHIFT_CONVENTION,
            "oos_provider_version": OOS_PROVIDER_VERSION,
            "oos_formula_version": OOS_FORMULA_VERSION,
            "oos_curve_metadata": json.dumps(curve_metadata, sort_keys=True),
            "configuration": json.dumps(configuration, sort_keys=True),
            "selected_areas": json.dumps(request.selected_areas),
            "run_request": json.dumps(request_payload, sort_keys=True, default=str),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "complete": int(not cancelled),
            "cancelled": int(cancelled),
            "processed_pixels": int(completed),
            "selected_pixels": int(total),
            "fit_status_counts": json.dumps(status_counts, sort_keys=True),
            "mywhateels_version": _package_version("MyWhatEELS"),
            "lmfit_version": str(lmfit.__version__),
        }
        return NLLSResultsAssembler.assemble(accumulator, attrs)
