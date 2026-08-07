"""Reference spectrum extraction and lightweight lmfit snapshots."""

from __future__ import annotations

import hashlib
import math
import warnings
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from .contracts import (
    AreaModelSpec,
    DatasetIdentity,
    ExperimentalGeometry,
    FitRange,
    ReferenceFitBatchResult,
    ReferenceFitFailure,
    ReferenceFitSnapshot,
)
from .errors import InsufficientReferenceDataError, ReferenceFitError
from .model_builder import NLLSModelBuilder


@dataclass(frozen=True)
class ReferenceSpectrumSelection:
    """A reproducible spatial selection and its mean reference spectrum."""

    spectrum: np.ndarray = field(compare=False, repr=False)
    strategy: str
    pixel_count: int
    mask_fingerprint: str

    def __post_init__(self) -> None:
        spectrum = np.array(self.spectrum, dtype=float, copy=True, order="C")
        if spectrum.ndim != 1 or not np.any(np.isfinite(spectrum)):
            raise InsufficientReferenceDataError(
                "reference selection contains no finite spectrum"
            )
        spectrum.setflags(write=False)
        object.__setattr__(self, "spectrum", spectrum)
        object.__setattr__(self, "pixel_count", int(self.pixel_count))


class ReferenceSpectrumService:
    @staticmethod
    def mask_fingerprint(mask: np.ndarray) -> str:
        area_mask = np.ascontiguousarray(np.asarray(mask, dtype=np.uint8))
        digest = hashlib.sha256()
        digest.update(str(tuple(area_mask.shape)).encode("ascii"))
        digest.update(area_mask.tobytes())
        return digest.hexdigest()

    @staticmethod
    def roi_mask(
        spatial_shape: tuple[int, int], pairs: Iterable[tuple[int, int]]
    ) -> np.ndarray:
        mask = np.zeros(tuple(int(value) for value in spatial_shape), dtype=bool)
        for row, column in pairs:
            y = int(row)
            x = int(column)
            if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]:
                mask[y, x] = True
        if not np.any(mask):
            raise InsufficientReferenceDataError(
                "commit a non-empty ROI or choose the central-window reference"
            )
        mask.setflags(write=False)
        return mask

    @staticmethod
    def central_mask(spatial_shape: tuple[int, int]) -> np.ndarray:
        ny, nx = (int(value) for value in spatial_shape)
        if ny <= 0 or nx <= 0:
            raise ValueError("reference source must have a non-empty spatial shape")
        y0, y1 = (2 * ny) // 5, max((3 * ny) // 5, (2 * ny) // 5 + 1)
        x0, x1 = (2 * nx) // 5, max((3 * nx) // 5, (2 * nx) // 5 + 1)
        mask = np.zeros((ny, nx), dtype=bool)
        mask[y0:y1, x0:x1] = True
        mask.setflags(write=False)
        return mask

    @classmethod
    def select_from_mask(
        cls, cube: np.ndarray, mask: np.ndarray, strategy: str
    ) -> ReferenceSpectrumSelection:
        data = np.asarray(cube, dtype=float)
        area_mask = np.asarray(mask, dtype=bool)
        if data.ndim != 3:
            raise ValueError("reference source must have dimensions (y, x, Eloss)")
        if area_mask.shape != data.shape[:2] or not np.any(area_mask):
            raise ValueError("reference mask must match the cube and select at least one pixel")
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", category=RuntimeWarning)
            reference = np.nanmean(data[area_mask, :], axis=0)
        if not np.any(np.isfinite(reference)):
            raise InsufficientReferenceDataError("reference mask contains no finite spectra")
        return ReferenceSpectrumSelection(
            spectrum=reference,
            strategy=str(strategy),
            pixel_count=int(np.count_nonzero(area_mask)),
            mask_fingerprint=cls.mask_fingerprint(area_mask),
        )

    @classmethod
    def from_mask(cls, cube: np.ndarray, mask: np.ndarray) -> np.ndarray:
        return cls.select_from_mask(cube, mask, "mask_mean").spectrum

    @classmethod
    def select_from_roi(
        cls, cube: np.ndarray, pairs: Iterable[tuple[int, int]]
    ) -> ReferenceSpectrumSelection:
        data = np.asarray(cube, dtype=float)
        if data.ndim != 3:
            raise ValueError("reference source must have dimensions (y, x, Eloss)")
        return cls.select_from_mask(
            data, cls.roi_mask(data.shape[:2], pairs), "roi_mean"
        )

    @classmethod
    def from_roi(cls, cube: np.ndarray, pairs: Iterable[tuple[int, int]]) -> np.ndarray:
        return cls.select_from_roi(cube, pairs).spectrum

    @classmethod
    def select_default_central(cls, cube: np.ndarray) -> ReferenceSpectrumSelection:
        data = np.asarray(cube, dtype=float)
        if data.ndim != 3:
            raise ValueError("reference source must have dimensions (y, x, Eloss)")
        return cls.select_from_mask(
            data, cls.central_mask(data.shape[:2]), "central_mean"
        )

    @classmethod
    def default_central(cls, cube: np.ndarray) -> np.ndarray:
        return cls.select_default_central(cube).spectrum


class ReferenceFitService:
    def __init__(self, model_builder: NLLSModelBuilder):
        self.model_builder = model_builder

    @staticmethod
    def _parameter_snapshot(params) -> tuple[dict[str, object], ...]:
        snapshots: list[dict[str, object]] = []
        for name, parameter in params.items():
            snapshots.append(
                {
                    "name": str(name),
                    "value": float(parameter.value),
                    "min": float(parameter.min),
                    "max": float(parameter.max),
                    "vary": bool(parameter.vary),
                    "expr": parameter.expr,
                    "brute_step": parameter.brute_step,
                    "stderr": (
                        float(parameter.stderr)
                        if parameter.stderr is not None and math.isfinite(parameter.stderr)
                        else None
                    ),
                }
            )
        return tuple(snapshots)

    def fit_area(
        self,
        area: AreaModelSpec,
        geometry: ExperimentalGeometry,
        dataset_identity: DatasetIdentity,
        reference: np.ndarray | ReferenceSpectrumSelection,
        eloss: np.ndarray,
        fit_range: FitRange,
        method: str = "leastsq",
    ) -> ReferenceFitSnapshot:
        x = np.asarray(eloss, dtype=float)
        if isinstance(reference, ReferenceSpectrumSelection):
            selection = reference
        else:
            selection = ReferenceSpectrumSelection(
                spectrum=reference,
                strategy=area.reference_strategy,
                pixel_count=0,
                mask_fingerprint="",
            )
        signal = np.asarray(selection.spectrum, dtype=float)
        if x.ndim != 1 or signal.ndim != 1 or x.size != signal.size:
            raise InsufficientReferenceDataError("reference and Eloss must be equal-length vectors")
        built = self.model_builder.build(area, geometry, x, fit_range)
        mask = (
            np.isfinite(x)
            & np.isfinite(signal)
            & (x >= fit_range.minimum)
            & (x <= fit_range.maximum)
        )
        if np.count_nonzero(mask) <= built.n_varying_parameters:
            raise InsufficientReferenceDataError(
                "reference fit range has too few finite samples for the varying parameters"
            )
        result = built.model.fit(
            signal[mask],
            params=built.params.copy(),
            x=x[mask],
            method=method,
        )
        finite_params = all(np.isfinite(parameter.value) for parameter in result.params.values())
        if not result.success or not finite_params or not math.isfinite(float(result.redchi)):
            raise ReferenceFitError(str(result.message))
        full_best_fit = np.asarray(built.model.eval(params=result.params, x=x), dtype=float)
        if np.any(~np.isfinite(full_best_fit)):
            raise ReferenceFitError("reference best fit contains NaN or Inf")
        components = {
            str(name): np.asarray(values, dtype=float)
            for name, values in built.model.eval_components(params=result.params, x=x).items()
        }
        if any(np.any(~np.isfinite(values)) for values in components.values()):
            raise ReferenceFitError("reference components contain NaN or Inf")
        return ReferenceFitSnapshot(
            area_id=area.area_id,
            success=True,
            message=str(result.message),
            method=method,
            params=self._parameter_snapshot(result.params),
            redchi=float(result.redchi),
            reference_spectrum=signal,
            reference_strategy=selection.strategy,
            reference_pixel_count=selection.pixel_count,
            reference_mask_fingerprint=selection.mask_fingerprint,
            best_fit=full_best_fit,
            residual=signal - full_best_fit,
            components=components,
            dataset_source_revision=dataset_identity.source_revision,
            area_revision=area.revision,
            model_composition=area.model_composition,
            fit_range=fit_range,
        )

    def fit_many(
        self,
        areas: Iterable[AreaModelSpec],
        geometry: ExperimentalGeometry,
        dataset_identity: DatasetIdentity,
        references: dict[str, ReferenceSpectrumSelection],
        eloss: np.ndarray,
        fit_range: FitRange,
        method: str = "leastsq",
    ) -> ReferenceFitBatchResult:
        """Fit every requested area, isolating failures without hiding their cause."""
        snapshots: list[ReferenceFitSnapshot] = []
        failures: list[ReferenceFitFailure] = []
        for area in areas:
            try:
                reference = references[area.area_id]
                snapshots.append(
                    self.fit_area(
                        area,
                        geometry,
                        dataset_identity,
                        reference,
                        eloss,
                        fit_range,
                        method=method,
                    )
                )
            except Exception as exc:
                failures.append(
                    ReferenceFitFailure(
                        area_id=area.area_id,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
        return ReferenceFitBatchResult(tuple(snapshots), tuple(failures))
