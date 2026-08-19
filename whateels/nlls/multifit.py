"""Deterministic serial Elemental NLLS fitting over spectrum images."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
from typing import Any
from uuid import uuid4

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
from .cross_sections import OOSCurveSnapshot
from .errors import (
    InsufficientReferenceDataError,
    InvalidRunRequestError,
    PixelFitError,
)
from .model_builder import BuiltAreaModel, NLLSModelBuilder
from .results import (
    FitStatus,
    NLLSResultsAccumulator,
    NLLSResultsAssembler,
)


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class PixelFitSnapshot:
    redchi: float
    best_fit: np.ndarray
    residual: np.ndarray
    components: dict[str, np.ndarray]
    parameters: dict[str, tuple[float, float | None]]


class _SampledOOSProvider:
    """Worker-local provider backed only by already sampled portable curves."""

    def __init__(self, snapshots: tuple[OOSCurveSnapshot, ...]):
        self._snapshots = {
            (int(snapshot.atomic_number), tuple(snapshot.shells)): snapshot
            for snapshot in snapshots
        }

    def curve(
        self,
        atomic_number,
        shells,
        geometry,
        eloss,
        broadening,
        fit_range,
    ) -> OOSCurveSnapshot:
        try:
            snapshot = self._snapshots[(int(atomic_number), tuple(shells))]
        except KeyError as exc:
            raise InvalidRunRequestError(
                f"parallel worker has no sampled OOS curve for Z={atomic_number}, shells={tuple(shells)}"
            ) from exc
        return snapshot


def _pixel_snapshot_payload(snapshot: PixelFitSnapshot) -> dict[str, Any]:
    return {
        "redchi": float(snapshot.redchi),
        "best_fit": np.asarray(snapshot.best_fit, dtype=float),
        "residual": np.asarray(snapshot.residual, dtype=float),
        "components": {
            str(name): np.asarray(values, dtype=float)
            for name, values in snapshot.components.items()
        },
        "parameters": {
            str(name): (float(value), None if stderr is None else float(stderr))
            for name, (value, stderr) in snapshot.parameters.items()
        },
    }


def fit_chunk_worker(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Spawn-safe worker: rebuild a model and return numeric pixel DTOs only."""
    signals = np.asarray(payload["signals"], dtype=float)
    coordinates = np.asarray(payload["coordinates"], dtype=np.int64)
    eloss = np.asarray(payload["eloss"], dtype=float)
    area: AreaModelSpec = payload["area"]
    geometry: ExperimentalGeometry = payload["geometry"]
    request: NLLSRunRequest = payload["request"]
    reference: ReferenceFitSnapshot | None = payload.get("reference")
    snapshots = tuple(payload["curve_snapshots"])

    builder = NLLSModelBuilder(_SampledOOSProvider(snapshots))
    service = ElementalMultifitService(builder)
    built = builder.build(area, geometry, eloss, request.fit_range)
    output: list[dict[str, Any]] = []
    for (y, x), signal in zip(coordinates, signals):
        try:
            snapshot = service._fit_pixel(
                built,
                area,
                reference,
                signal,
                eloss,
                request,
            )
            output.append(
                {
                    "y": int(y),
                    "x": int(x),
                    "status": int(FitStatus.SUCCESS),
                    "result": _pixel_snapshot_payload(snapshot),
                }
            )
        except InsufficientReferenceDataError:
            output.append(
                {
                    "y": int(y),
                    "x": int(x),
                    "status": int(FitStatus.INSUFFICIENT_DATA),
                    "result": None,
                }
            )
        except Exception:
            output.append(
                {
                    "y": int(y),
                    "x": int(x),
                    "status": int(FitStatus.FIT_ERROR),
                    "result": None,
                }
            )
    return output


def _package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "unknown"


class ElementalMultifitService:
    """Fit selected masks serially, isolating every pixel failure."""

    def __init__(
        self,
        model_builder: NLLSModelBuilder,
        *,
        progress_chunk_size: int = 16,
        parallel_chunk_size: int | None = None,
    ):
        self.model_builder = model_builder
        self.progress_chunk_size = max(1, int(progress_chunk_size))
        self.parallel_chunk_size = (
            None
            if parallel_chunk_size is None
            else max(1, int(parallel_chunk_size))
        )

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
            if compositions[area_id] != area.model_composition:
                raise InvalidRunRequestError(
                    f"area {area_id} model composition changed after request creation"
                )
            if revisions and revisions[area_id] != area.revision:
                raise InvalidRunRequestError(
                    f"area {area_id} revision changed after request creation"
                )
            reference = reference_fits.get(area_id)
            if reference is None or not reference.success:
                raise InvalidRunRequestError(
                    f"area {area_id} has no converged reference fit"
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
    ):
        """Return an independent parameter copy for exactly one pixel."""
        params = cls._parameters_from_reference(built, reference)
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

    def _parallel_plan(
        self,
        pixel_count: int,
        requested_workers: int,
    ) -> tuple[int, int, int]:
        pixels = max(0, int(pixel_count))
        workers = min(max(1, int(requested_workers)), max(1, pixels))
        if self.parallel_chunk_size is None:
            chunk_size = max(
                8,
                min(128, int(math.ceil(pixels / max(1, workers * 4)))),
            )
        else:
            chunk_size = self.parallel_chunk_size
        chunks = int(math.ceil(pixels / chunk_size)) if pixels else 0
        return min(workers, max(1, chunks)), int(chunk_size), chunks

    def _fit_pixel(
        self,
        built: BuiltAreaModel,
        area: AreaModelSpec,
        reference: ReferenceFitSnapshot | None,
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
        if reference is None:
            raise InvalidRunRequestError("an area reference is required")
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
        reference: ReferenceFitSnapshot | None,
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
        if reference is None:
            raise InvalidRunRequestError("an area reference is required")
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

    @staticmethod
    def _store_parallel_pixel(
        accumulator: NLLSResultsAccumulator,
        payload: Mapping[str, Any],
    ) -> None:
        y, x = int(payload["y"]), int(payload["x"])
        status = FitStatus(int(payload["status"]))
        if status is not FitStatus.SUCCESS:
            accumulator.store_error(y, x, status)
            return
        result = payload.get("result")
        if not isinstance(result, Mapping):
            accumulator.store_error(y, x, FitStatus.FIT_ERROR)
            return
        accumulator.store_success(
            y,
            x,
            redchi=float(result["redchi"]),
            best_fit=np.asarray(result["best_fit"], dtype=float),
            residual=np.asarray(result["residual"], dtype=float),
            components={
                str(name): np.asarray(values, dtype=float)
                for name, values in result["components"].items()
            },
            parameters={
                str(name): (
                    float(values[0]),
                    None if values[1] is None else float(values[1]),
                )
                for name, values in result["parameters"].items()
            },
        )

    def fit_area_parallel(
        self,
        request: NLLSRunRequest,
        area: AreaModelSpec,
        reference: ReferenceFitSnapshot | None,
        source_cube: np.ndarray,
        eloss: np.ndarray,
        mask: np.ndarray,
        accumulator: NLLSResultsAccumulator,
        *,
        geometry: ExperimentalGeometry,
        built: BuiltAreaModel,
        cancel_event: Any | None = None,
        on_pixel_done: Callable[[], None] | None = None,
    ) -> None:
        """Fit bounded chunks in spawn-safe processes and merge numeric DTOs."""
        coordinates = self._selected_coordinates(mask)
        if coordinates.size == 0:
            return
        worker_count, chunk_size, _ = self._parallel_plan(
            int(coordinates.shape[0]), request.workers
        )
        if worker_count <= 1:
            self.fit_area_serial(
                request,
                area,
                reference,
                source_cube,
                eloss,
                mask,
                accumulator,
                geometry=geometry,
                built=built,
                cancel_event=cancel_event,
                on_pixel_done=on_pixel_done,
            )
            return

        chunks = tuple(
            coordinates[start : start + chunk_size]
            for start in range(0, coordinates.shape[0], chunk_size)
        )

        def payload_for(chunk: np.ndarray) -> dict[str, Any]:
            signals = np.asarray(
                [source_cube[int(y), int(x), :] for y, x in chunk],
                dtype=float,
            )
            return {
                "signals": signals,
                "coordinates": np.asarray(chunk, dtype=np.int64),
                "eloss": np.asarray(eloss, dtype=float),
                "area": area,
                "geometry": geometry,
                "request": request,
                "reference": reference,
                "curve_snapshots": tuple(built.curve_snapshots.values()),
            }

        executor = ProcessPoolExecutor(max_workers=worker_count)
        pending: dict[Any, np.ndarray] = {}
        next_chunk = 0
        try:
            while next_chunk < len(chunks) and len(pending) < worker_count:
                chunk = chunks[next_chunk]
                pending[executor.submit(fit_chunk_worker, payload_for(chunk))] = chunk
                next_chunk += 1

            while pending:
                completed_futures, _ = wait(
                    tuple(pending), return_when=FIRST_COMPLETED
                )
                for future in completed_futures:
                    chunk = pending.pop(future)
                    if self._is_cancelled(cancel_event):
                        continue
                    try:
                        pixel_payloads = future.result()
                        if len(pixel_payloads) != len(chunk):
                            raise PixelFitError("parallel worker returned a short chunk")
                        for pixel_payload in pixel_payloads:
                            self._store_parallel_pixel(accumulator, pixel_payload)
                            if on_pixel_done is not None:
                                on_pixel_done()
                    except Exception:
                        for y, x in chunk:
                            accumulator.store_error(
                                int(y), int(x), FitStatus.FIT_ERROR
                            )
                            if on_pixel_done is not None:
                                on_pixel_done()

                if self._is_cancelled(cancel_event):
                    for future in pending:
                        future.cancel()
                    break
                while next_chunk < len(chunks) and len(pending) < worker_count:
                    chunk = chunks[next_chunk]
                    pending[executor.submit(fit_chunk_worker, payload_for(chunk))] = chunk
                    next_chunk += 1
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

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
            request,
            source,
            dataset_identity,
            areas,
            reference_fits,
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
            for parameter_name in built.params:
                accumulator.register_parameter(str(parameter_name))
            for component_id, curve in built.curve_snapshots.items():
                continuum_spec = next(
                    spec
                    for spec in area.continuum_specs
                    if spec.id == component_id
                )
                curve_metadata.append(
                    {
                        "area_id": area_id,
                        "component_id": component_id,
                        "provider_version": curve.provider_version,
                        "formula_version": curve.formula_version,
                        "table_checksums": tuple(curve.table_checksums),
                        "atomic_number": int(curve.atomic_number),
                        "symbol": str(curve.symbol),
                        "shells": tuple(curve.shells),
                        "onsets_eV": tuple(float(value) for value in curve.onsets_eV),
                        "normalization_factor": float(curve.normalization_factor),
                        "units": str(curve.units),
                        "edge_id": str(continuum_spec.edge_id),
                        "elnes_component_ids": tuple(
                            fine.id
                            for fine in area.fine_structure_specs
                            if fine.enabled
                            and fine.edge_id == continuum_spec.edge_id
                            and area.model_composition.value
                            == "continuum_plus_elnes"
                        ),
                    }
                )

        parallel_plan: dict[str, dict[str, int]] = {}
        if request.parallel:
            for area_id in request.selected_areas:
                pixel_count = int(np.count_nonzero(masks[area_id]))
                effective_workers, chunk_size, chunk_count = self._parallel_plan(
                    pixel_count, request.workers
                )
                bytes_per_pixel = int(eloss.size * np.dtype(float).itemsize)
                bytes_per_pixel += 2 * np.dtype(np.int64).itemsize
                parallel_plan[area_id] = {
                    "pixels": pixel_count,
                    "workers": effective_workers,
                    "chunk_size": chunk_size,
                    "chunks": chunk_count,
                    "estimated_inflight_payload_bytes": int(
                        effective_workers
                        * min(chunk_size, max(1, pixel_count))
                        * bytes_per_pixel
                    ),
                }

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
            fit_method = (
                self.fit_area_parallel if request.parallel else self.fit_area_serial
            )
            fit_method(
                request,
                area,
                reference_fits.get(area_id),
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
        parameter_schema = {
            area_id: [
                {
                    "name": str(name),
                    "value": float(parameter.value),
                    "min": float(parameter.min),
                    "max": float(parameter.max),
                    "vary": bool(parameter.vary),
                    "expr": parameter.expr,
                    "brute_step": parameter.brute_step,
                }
                for name, parameter in built_models[area_id].params.items()
            ]
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
            "execution_mode": "parallel" if request.parallel else "serial",
            "workers": int(request.workers if request.parallel else 1),
            "effective_workers": int(
                max(
                    (plan["workers"] for plan in parallel_plan.values()),
                    default=1,
                )
            ),
            "parallel_chunk_size": int(self.parallel_chunk_size or 0),
            "parallel_plan": json.dumps(parallel_plan, sort_keys=True),
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
            "parameter_schema_by_area": json.dumps(
                parameter_schema, sort_keys=True, default=str
            ),
            "selected_areas": json.dumps(request.selected_areas),
            "run_request": json.dumps(request_payload, sort_keys=True, default=str),
            "run_id": uuid4().hex,
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
