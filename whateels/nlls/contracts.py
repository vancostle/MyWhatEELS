"""Serializable domain contracts for Elemental NLLS."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .errors import InvalidGeometryError, UnsupportedModelCompositionError


class ModelComposition(str, Enum):
    CONTINUUM_ONLY = "continuum_only"
    CONTINUUM_PLUS_ELNES = "continuum_plus_elnes"

    @classmethod
    def parse(cls, value: "ModelComposition | str") -> "ModelComposition":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            raise UnsupportedModelCompositionError(str(value)) from exc


@dataclass(frozen=True)
class FitRange:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        minimum = float(self.minimum)
        maximum = float(self.maximum)
        if not (math.isfinite(minimum) and math.isfinite(maximum) and minimum < maximum):
            raise ValueError("fit range must contain two finite, increasing values")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)


@dataclass(frozen=True)
class BroadeningSpec:
    enabled: bool = True
    sigma_eV: float = 1.5

    def __post_init__(self) -> None:
        sigma = float(self.sigma_eV)
        if not math.isfinite(sigma) or sigma < 0.0:
            raise ValueError("broadening sigma_eV must be finite and non-negative")
        object.__setattr__(self, "sigma_eV", sigma)


@dataclass(frozen=True)
class ParameterSpec:
    value: float
    minimum: float = -math.inf
    maximum: float = math.inf
    vary: bool = True
    expr: str | None = None
    brute_step: float | None = None

    def __post_init__(self) -> None:
        value = float(self.value)
        minimum = float(self.minimum)
        maximum = float(self.maximum)
        if math.isnan(value) or math.isnan(minimum) or math.isnan(maximum):
            raise ValueError("parameter value and bounds cannot be NaN")
        if minimum > maximum or value < minimum or value > maximum:
            raise ValueError("parameter value must lie inside its bounds")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)


@dataclass(frozen=True)
class ExperimentalGeometry:
    beam_energy_keV: float
    collection_angle_mrad: float
    convergence_angle_mrad: float = 0.0
    provenance: str = "dataset.attrs"

    def __post_init__(self) -> None:
        e0 = float(self.beam_energy_keV)
        beta = float(self.collection_angle_mrad)
        alpha = float(self.convergence_angle_mrad)
        if not all(math.isfinite(value) for value in (e0, beta, alpha)):
            raise InvalidGeometryError("E0, beta and alpha must be finite")
        if e0 <= 0.0:
            raise InvalidGeometryError("beam_energy must be greater than 0 keV")
        if beta <= 0.0:
            raise InvalidGeometryError("collection_angle must be greater than 0 mrad")
        if alpha < 0.0:
            raise InvalidGeometryError("convergence_angle cannot be negative")
        object.__setattr__(self, "beam_energy_keV", e0)
        object.__setattr__(self, "collection_angle_mrad", beta)
        object.__setattr__(self, "convergence_angle_mrad", alpha)

    @classmethod
    def from_dataset(cls, dataset: Any) -> "ExperimentalGeometry":
        attrs = getattr(dataset, "attrs", {})
        return cls(
            beam_energy_keV=attrs.get("beam_energy", 0.0),
            collection_angle_mrad=attrs.get("collection_angle", 0.0),
            convergence_angle_mrad=attrs.get("convergence_angle", 0.0),
        )


def _eloss_hash(dataset: Any) -> str:
    values = np.ascontiguousarray(np.asarray(dataset.coords["Eloss"].values, dtype=np.float64))
    return hashlib.sha256(values.tobytes()).hexdigest()


@dataclass(frozen=True)
class DatasetIdentity:
    tab_index: int
    original_name: str
    image_name: str
    shape: tuple[int, ...]
    eloss_hash: str
    source_kind: str
    source_revision: str
    preprocessing_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    background_subtracted: bool = False

    @classmethod
    def from_dataset(
        cls,
        dataset: Any,
        *,
        tab_index: int,
        source_kind: str,
        preprocessing_history: tuple[dict[str, Any], ...] = (),
        background_subtracted: bool = False,
    ) -> "DatasetIdentity":
        attrs = getattr(dataset, "attrs", {})
        shape = tuple(int(value) for value in dataset["ElectronCount"].shape)
        revision_payload = {
            "eloss_hash": _eloss_hash(dataset),
            "shape": shape,
            "source_kind": source_kind,
            "history": preprocessing_history,
        }
        revision = hashlib.sha256(
            json.dumps(revision_payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return cls(
            tab_index=int(tab_index),
            original_name=str(attrs.get("original_name", "")),
            image_name=str(attrs.get("image_name", "")),
            shape=shape,
            eloss_hash=revision_payload["eloss_hash"],
            source_kind=str(source_kind),
            source_revision=revision,
            preprocessing_history=preprocessing_history,
            background_subtracted=bool(background_subtracted),
        )


@dataclass(frozen=True)
class EdgeSpec:
    id: str
    atomic_number: int
    symbol: str
    shells: tuple[str, ...]
    onset_eV: float


@dataclass(frozen=True)
class ContinuumSpec:
    id: str
    edge_id: str
    atomic_number: int
    symbol: str
    shells: tuple[str, ...]
    prefix: str
    onset_eV: float
    broadening: BroadeningSpec
    amplitude: ParameterSpec
    chemical_shift: ParameterSpec
    provider_version: str
    chemical_shift_convention: str


@dataclass(frozen=True)
class FineStructureSpec:
    id: str
    edge_id: str
    shell: str
    prefix: str
    shape: str
    center: ParameterSpec
    sigma: ParameterSpec
    amplitude: ParameterSpec
    enabled: bool = True


@dataclass(frozen=True)
class AreaModelSpec:
    area_id: str
    label: str
    model_composition: ModelComposition = ModelComposition.CONTINUUM_PLUS_ELNES
    edges: tuple[EdgeSpec, ...] = ()
    continuum_specs: tuple[ContinuumSpec, ...] = ()
    fine_structure_specs: tuple[FineStructureSpec, ...] = ()
    mask: np.ndarray | None = field(default=None, compare=False, repr=False)
    mask_fingerprint: str = ""
    clustering_label: int | None = None
    revision: int = 0
    built_revision: int | None = None
    reference_strategy: str = "roi_mean"

    @property
    def is_built(self) -> bool:
        return self.built_revision == self.revision and bool(self.continuum_specs)


def _readonly_array(values: Any) -> np.ndarray:
    result = np.array(values, dtype=float, copy=True, order="C")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class ModelBuildSnapshot:
    area_id: str
    area_revision: int
    dataset_source_revision: str
    model_composition: ModelComposition
    component_ids: tuple[str, ...]
    params: tuple[dict[str, Any], ...]
    preview: np.ndarray = field(compare=False, repr=False)
    components: dict[str, np.ndarray] = field(compare=False, repr=False)
    curve_metadata: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", _readonly_array(self.preview))
        object.__setattr__(
            self,
            "components",
            {name: _readonly_array(values) for name, values in self.components.items()},
        )


@dataclass(frozen=True)
class ReferenceFitSnapshot:
    area_id: str
    success: bool
    message: str
    method: str
    params: tuple[dict[str, Any], ...]
    redchi: float
    reference_spectrum: np.ndarray = field(compare=False, repr=False)
    reference_strategy: str
    reference_pixel_count: int
    reference_mask_fingerprint: str
    best_fit: np.ndarray = field(compare=False, repr=False)
    residual: np.ndarray = field(compare=False, repr=False)
    components: dict[str, np.ndarray] = field(compare=False, repr=False)
    dataset_source_revision: str
    area_revision: int
    model_composition: ModelComposition
    fit_range: FitRange

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reference_spectrum", _readonly_array(self.reference_spectrum)
        )
        object.__setattr__(self, "best_fit", _readonly_array(self.best_fit))
        object.__setattr__(self, "residual", _readonly_array(self.residual))
        object.__setattr__(
            self,
            "components",
            {name: _readonly_array(values) for name, values in self.components.items()},
        )


@dataclass(frozen=True)
class ReferenceFitFailure:
    area_id: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ReferenceFitBatchResult:
    snapshots: tuple[ReferenceFitSnapshot, ...]
    failures: tuple[ReferenceFitFailure, ...]

    @property
    def successful_area_ids(self) -> tuple[str, ...]:
        return tuple(snapshot.area_id for snapshot in self.snapshots)

    @property
    def failed_area_ids(self) -> tuple[str, ...]:
        return tuple(failure.area_id for failure in self.failures)


@dataclass(frozen=True)
class NLLSRunRequest:
    selected_areas: tuple[str, ...]
    fit_range: FitRange
    method: str
    model_composition_by_area: tuple[tuple[str, ModelComposition], ...]
    parallel: bool = False
    workers: int = 1
    rerun_from: str | None = None
