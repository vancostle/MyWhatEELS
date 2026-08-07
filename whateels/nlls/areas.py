"""Validated conversion of Clustering outputs into NLLS area masks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .contracts import DatasetIdentity
from .errors import InvalidClusteringError


_MISSING_IDENTITIES = {"", "none", "null", "no file uploaded"}


def _usable_identity(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return None if normalized.casefold() in _MISSING_IDENTITIES else normalized


def _mask_fingerprint(mask: np.ndarray, label_value: int) -> str:
    contiguous = np.ascontiguousarray(mask, dtype=np.uint8)
    digest = hashlib.sha256()
    digest.update(f"{contiguous.shape}:{label_value}:".encode("ascii"))
    digest.update(contiguous.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class AreaDefinition:
    """Spatial definition produced from one unique clustering label."""

    area_id: str
    label: str
    label_value: int
    mask: np.ndarray = field(compare=False, repr=False)
    mask_fingerprint: str = ""
    source_kind: str = "current_clustering"
    clustering_type: str = "unknown"

    def __post_init__(self) -> None:
        area_mask = np.array(self.mask, dtype=bool, copy=True, order="C")
        if area_mask.ndim != 2 or not np.any(area_mask):
            raise InvalidClusteringError(
                "each clustering area must be a non-empty two-dimensional mask"
            )
        area_mask.setflags(write=False)
        object.__setattr__(self, "mask", area_mask)
        object.__setattr__(self, "label_value", int(self.label_value))
        if not self.mask_fingerprint:
            object.__setattr__(
                self,
                "mask_fingerprint",
                _mask_fingerprint(area_mask, int(self.label_value)),
            )


class ClusteringAreaAdapter:
    """Create stable, mutually exclusive NLLS areas from ``outputs.labels``."""

    @staticmethod
    def _validate_identity(clustering: dict[str, Any], identity: DatasetIdentity) -> None:
        clustering_file = _usable_identity(clustering.get("file"))
        dataset_file = _usable_identity(identity.original_name)
        if clustering_file and dataset_file:
            if Path(clustering_file).name.casefold() != Path(dataset_file).name.casefold():
                raise InvalidClusteringError(
                    "clustering file does not match the active dataset"
                )

        clustering_image = _usable_identity(clustering.get("spectrum_image"))
        dataset_image = _usable_identity(identity.image_name)
        if clustering_image and dataset_image:
            if clustering_image.casefold() != dataset_image.casefold():
                raise InvalidClusteringError(
                    "clustering spectrum image does not match the active dataset"
                )

    @classmethod
    def from_result(
        cls,
        result: Any,
        dataset_identity: DatasetIdentity,
        spatial_shape: tuple[int, int],
    ) -> tuple[AreaDefinition, ...]:
        if not isinstance(result, dict) or not isinstance(result.get("clustering"), dict):
            raise InvalidClusteringError("current clustering result is missing")
        clustering = result["clustering"]
        outputs = clustering.get("outputs")
        if not isinstance(outputs, dict) or outputs.get("labels") is None:
            raise InvalidClusteringError("clustering outputs.labels is missing")

        cls._validate_identity(clustering, dataset_identity)
        raw_labels = np.asarray(outputs["labels"])
        if raw_labels.ndim != 2 or tuple(raw_labels.shape) != tuple(spatial_shape):
            raise InvalidClusteringError(
                "clustering label shape does not match the active spectrum image"
            )
        if np.issubdtype(raw_labels.dtype, np.bool_):
            raise InvalidClusteringError("clustering labels must be integer identifiers")
        try:
            numeric_labels = np.asarray(raw_labels, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise InvalidClusteringError("clustering labels must be numeric") from exc
        if not np.all(np.isfinite(numeric_labels)):
            raise InvalidClusteringError("clustering labels contain NaN or Inf")
        rounded = np.rint(numeric_labels)
        if not np.array_equal(numeric_labels, rounded):
            raise InvalidClusteringError("clustering labels must be integer-valued")
        if np.any(rounded < 0) or np.any(rounded > np.iinfo(np.int64).max):
            raise InvalidClusteringError("clustering labels must be non-negative integers")

        labels = rounded.astype(np.int64)
        unique_labels = np.unique(labels)
        declared_clusters = clustering.get("inputs", {}).get("n_clusters") if isinstance(
            clustering.get("inputs"), dict
        ) else None
        if declared_clusters is not None:
            try:
                declared_clusters = int(declared_clusters)
            except (TypeError, ValueError) as exc:
                raise InvalidClusteringError("clustering n_clusters is invalid") from exc
            if declared_clusters != int(unique_labels.size):
                raise InvalidClusteringError(
                    "clustering n_clusters does not match the unique labels"
                )

        clustering_type = str(clustering.get("type") or "unknown")
        areas = tuple(
            AreaDefinition(
                area_id=f"cluster_{int(label_value)}",
                label=f"Cluster {int(label_value)}",
                label_value=int(label_value),
                mask=labels == label_value,
                clustering_type=clustering_type,
            )
            for label_value in unique_labels
        )
        if not areas:
            raise InvalidClusteringError("clustering contains no areas")

        coverage = np.sum(
            np.stack([area.mask for area in areas], axis=0), axis=0, dtype=np.uint16
        )
        if not np.all(coverage == 1):
            raise InvalidClusteringError(
                "clustering masks must be mutually exclusive and cover every pixel"
            )
        return areas
