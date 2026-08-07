"""Public, serializable provenance for Elemental NLLS input sources."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from .errors import InvalidSourceError


BACKGROUND_SUBTRACTED_ATTR = "background_subtracted"
PREPROCESSING_HISTORY_ATTR = "preprocessing_history"
POWER_LAW_OPERATION = "power_law_background_subtraction"


def parse_preprocessing_history(dataset: Any) -> tuple[dict[str, Any], ...]:
    raw = getattr(dataset, "attrs", {}).get(PREPROCESSING_HISTORY_ATTR, ())
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidSourceError("preprocessing_history is not valid JSON") from exc
    if raw in (None, ""):
        return ()
    if not isinstance(raw, (list, tuple)) or not all(isinstance(item, dict) for item in raw):
        raise InvalidSourceError("preprocessing_history must be a JSON list of objects")
    return tuple(dict(item) for item in raw)


def validate_background_subtracted(dataset: Any) -> tuple[dict[str, Any], ...]:
    """Return history only when a power-law subtraction is publicly accredited."""
    if dataset is None:
        raise InvalidSourceError("no active dataset")
    history = parse_preprocessing_history(dataset)
    has_operation = any(item.get("operation") == POWER_LAW_OPERATION for item in history)
    flag = getattr(dataset, "attrs", {}).get(BACKGROUND_SUBTRACTED_ATTR, False)
    if flag is not True or not has_operation:
        raise InvalidSourceError(
            "the active source does not document a power-law pre-edge background subtraction"
        )
    return history


def _source_identity(dataset: Any) -> dict[str, Any]:
    eloss = np.ascontiguousarray(np.asarray(dataset.coords["Eloss"].values, dtype=np.float64))
    return {
        "original_name": str(dataset.attrs.get("original_name", "")),
        "image_name": str(dataset.attrs.get("image_name", "")),
        "shape": [int(value) for value in dataset["ElectronCount"].shape],
        "eloss_sha256": hashlib.sha256(eloss.tobytes()).hexdigest(),
    }


def _array_sha256(values: Any) -> str:
    """Hash an array in bounded first-axis slabs without retaining a giant bytes copy."""
    array = np.asarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii", errors="replace"))
    digest.update(json.dumps([int(value) for value in array.shape]).encode("ascii"))
    if array.ndim == 0:
        digest.update(np.ascontiguousarray(array).tobytes())
    else:
        for index in range(array.shape[0]):
            digest.update(np.ascontiguousarray(array[index]).tobytes())
    return digest.hexdigest()


def publish_power_law_subtracted_dataset(
    base_dataset: Any,
    electron_count: Any,
    *,
    fit_range_eV: tuple[float, float],
    implementation: str = "whateels.helpers.fitting.multifitting.MultiFit",
) -> Any:
    """Return a dataset carrying the fitted data and verifiable provenance attrs."""
    published = base_dataset.assign({"ElectronCount": electron_count})
    try:
        history = list(parse_preprocessing_history(base_dataset))
    except InvalidSourceError:
        history = []
    source_identity = _source_identity(base_dataset)
    revision_payload = {
        "source_identity": source_identity,
        "output_electron_count_sha256": _array_sha256(electron_count),
        "fit_range_eV": [float(fit_range_eV[0]), float(fit_range_eV[1])],
        "implementation": implementation,
    }
    revision = hashlib.sha256(
        json.dumps(revision_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    history.append(
        {
            "operation": POWER_LAW_OPERATION,
            "implementation": implementation,
            "fit_range_eV": revision_payload["fit_range_eV"],
            "source_identity": source_identity,
            "output_electron_count_sha256": revision_payload[
                "output_electron_count_sha256"
            ],
            "revision": revision,
        }
    )
    published.attrs = dict(getattr(published, "attrs", {}))
    published.attrs[BACKGROUND_SUBTRACTED_ATTR] = True
    published.attrs[PREPROCESSING_HISTORY_ATTR] = json.dumps(
        history, sort_keys=True, separators=(",", ":")
    )
    published.attrs["preprocessing_revision"] = revision
    return published
