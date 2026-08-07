"""Corrected OOS/FSalvat continuum provider for Elemental NLLS.

The provider evaluates Salvat's RPWBA expression channel by channel on each
table's real energy axis. It never treats the scalar onset as an energy axis and
never extrapolates a cross section outside tabulated support.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.integrate import trapezoid
from scipy.ndimage import gaussian_filter1d

from whateels.helpers.constants import OOS_ROOT

from ..contracts import BroadeningSpec, ExperimentalGeometry, FitRange
from ..defaults import OOS_FORMULA_VERSION, OOS_PROVIDER_VERSION, OOS_UNITS
from ..errors import InvalidOOSDataError, MissingOOSTableError


RYDBERG_EV = 13.6056923
BOHR_RADIUS_M = 5.2917720859e-11
ELECTRON_REST_ENERGY_EV = 510998.9499961642
KEV_TO_EV = 1.0e3
MRAD_TO_RAD = 1.0e-3


@dataclass(frozen=True)
class OOSRawCurve:
    atomic_number: int
    element_name: str
    symbol: str
    shell: str
    energy_eV: np.ndarray
    oscillator_strength: np.ndarray
    onset_eV: float
    table_checksum: str


@dataclass(frozen=True)
class OOSPhysicalCurve:
    energy_eV: np.ndarray
    sigma: np.ndarray
    units: str
    formula_version: str
    onset_eV: float
    table_checksums: tuple[str, ...]


@dataclass(frozen=True)
class OOSCurveSnapshot:
    energy_eV: np.ndarray
    normalized_shape: np.ndarray
    physical_shape: np.ndarray
    normalization_factor: float
    units: str
    formula_version: str
    provider_version: str
    atomic_number: int
    symbol: str
    shells: tuple[str, ...]
    onsets_eV: tuple[float, ...]
    table_checksums: tuple[str, ...]
    broadening_sigma_eV: float
    fit_range: FitRange | None


def _readonly_float_array(values: Any) -> np.ndarray:
    result = np.ascontiguousarray(np.asarray(values, dtype=float))
    result.setflags(write=False)
    return result


def effective_collection_angle_mrad(
    beam_energy_keV: float,
    energy_loss_eV: np.ndarray,
    convergence_angle_mrad: float,
    collection_angle_mrad: float,
) -> np.ndarray:
    """Vectorized Egerton finite-convergence correction in mrad."""
    losses = np.asarray(energy_loss_eV, dtype=float)
    alpha = float(convergence_angle_mrad)
    beta = float(collection_angle_mrad)
    if alpha <= 0.0:
        return np.full(losses.shape, beta, dtype=float)
    if np.any(~np.isfinite(losses)) or np.any(losses <= 0.0):
        raise InvalidOOSDataError("effective-angle losses must be finite and positive")

    e0 = float(beam_energy_keV)
    tgt = e0 * (1.0 + e0 / 1022.0) / (1.0 + e0 / 511.0)
    theta_e = losses / tgt
    a2 = alpha * alpha * 1.0e-6
    b2 = beta * beta * 1.0e-6
    t2 = theta_e * theta_e * 1.0e-6

    with np.errstate(divide="raise", invalid="raise", over="raise"):
        try:
            eta1 = np.sqrt((a2 + b2 + t2) ** 2 - 4.0 * a2 * b2) - a2 - b2 - t2
            eta2 = 2.0 * b2 * np.log(
                0.5
                / t2
                * (np.sqrt((a2 + t2 - b2) ** 2 + 4.0 * b2 * t2) + a2 + t2 - b2)
            )
            eta3 = 2.0 * a2 * np.log(
                0.5
                / t2
                * (np.sqrt((b2 + t2 - a2) ** 2 + 4.0 * a2 * t2) + b2 + t2 - a2)
            )
            f1 = (eta1 + eta2 + eta3) / (2.0 * a2 * np.log1p(b2 / t2))
            f2 = f1 * a2 / b2 if alpha > beta else f1
            beta_star = theta_e * np.sqrt(np.exp(f2 * np.log1p(b2 / t2)) - 1.0)
        except FloatingPointError as exc:
            raise InvalidOOSDataError("finite-convergence angle correction failed") from exc

    if np.any(~np.isfinite(beta_star)) or np.any(beta_star <= 0.0):
        raise InvalidOOSDataError("effective collection angle is not finite and positive")
    return beta_star


class OOSContinuumProvider:
    """Read FSalvat tables and create normalized continuum snapshots."""

    def __init__(self, database_dir: str | Path | None = None):
        self.database_dir = Path(database_dir) if database_dir else OOS_ROOT / "Hartree_Xsections_FSalvat"
        self._payload_cache: dict[int, tuple[str, str, dict[str, Any], str]] = {}

    @staticmethod
    def _validate_atomic_number(atomic_number: int) -> int:
        try:
            value = int(atomic_number)
        except (TypeError, ValueError) as exc:
            raise MissingOOSTableError("atomic number must be an integer from 1 to 99") from exc
        if not 1 <= value <= 99:
            raise MissingOOSTableError("atomic number must be in the range 1..99")
        return value

    def _table_path(self, atomic_number: int) -> Path:
        z = self._validate_atomic_number(atomic_number)
        return self.database_dir / f"OOS{z:02d}.json"

    def _read_payload(self, atomic_number: int) -> tuple[str, str, dict[str, Any], str]:
        z = self._validate_atomic_number(atomic_number)
        if z in self._payload_cache:
            return self._payload_cache[z]
        path = self._table_path(z)
        if not path.is_file():
            raise MissingOOSTableError(f"OOS table not found for Z={z}: {path.name}")
        try:
            raw_bytes = path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidOOSDataError(f"cannot read valid JSON from {path.name}") from exc

        element_name = ""
        symbol = ""
        entries: dict[str, Any] | None = None
        if (
            isinstance(payload, list)
            and len(payload) >= 4
            and isinstance(payload[0], str)
            and isinstance(payload[1], str)
            and isinstance(payload[3], dict)
        ):
            element_name, symbol, entries = payload[0], payload[1], payload[3]
        elif isinstance(payload, list):
            dictionaries = [item for item in payload if isinstance(item, dict)]
            if dictionaries:
                entries = {}
                for item in dictionaries:
                    entries.update(item)
                element_name = str(payload[0]) if payload and isinstance(payload[0], str) else ""
                symbol = str(payload[1]) if len(payload) > 1 and isinstance(payload[1], str) else ""
        if not entries:
            raise InvalidOOSDataError(f"{path.name} does not contain any OOS subshells")

        checksum = hashlib.sha256(raw_bytes).hexdigest()
        parsed = (element_name, symbol, entries, checksum)
        self._payload_cache[z] = parsed
        return parsed

    def available_edges(self, atomic_number: int) -> tuple[str, ...]:
        _, _, entries, _ = self._read_payload(atomic_number)
        return tuple(str(shell) for shell in entries)

    def element_info(self, atomic_number: int) -> tuple[str, str]:
        name, symbol, _, _ = self._read_payload(atomic_number)
        return name, symbol

    def load_raw(self, atomic_number: int, shell: str) -> OOSRawCurve:
        z = self._validate_atomic_number(atomic_number)
        name, symbol, entries, checksum = self._read_payload(z)
        if shell not in entries:
            raise MissingOOSTableError(
                f"subshell {shell!r} is unavailable for Z={z}; available={tuple(entries)}"
            )
        item = entries[shell]
        if not isinstance(item, dict):
            raise InvalidOOSDataError(f"invalid record for Z={z}, shell={shell}")
        try:
            energy = np.asarray(item["eaxis"], dtype=float)
            oscillator = np.asarray(item["counts"], dtype=float)
            onset = float(item["onset"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidOOSDataError(f"incomplete record for Z={z}, shell={shell}") from exc
        if energy.ndim != 1 or oscillator.ndim != 1 or energy.size != oscillator.size:
            raise InvalidOOSDataError("OOS energy/count arrays must be equal-length and one-dimensional")
        if energy.size < 2:
            raise InvalidOOSDataError("an OOS curve needs at least two samples")
        if not math.isfinite(onset) or onset <= 0.0:
            raise InvalidOOSDataError("OOS onset must be finite and positive")
        if np.any(~np.isfinite(energy)) or np.any(~np.isfinite(oscillator)):
            raise InvalidOOSDataError("OOS arrays cannot contain NaN or Inf")
        if np.any(energy <= 0.0) or np.any(oscillator < 0.0):
            raise InvalidOOSDataError("OOS energy must be positive and oscillator strength non-negative")

        order = np.argsort(energy, kind="stable")
        energy = energy[order]
        oscillator = oscillator[order]
        unique_energy, first, counts = np.unique(energy, return_index=True, return_counts=True)
        if np.any(counts > 1):
            oscillator = np.asarray(
                [np.mean(oscillator[start : start + count]) for start, count in zip(first, counts)],
                dtype=float,
            )
            energy = unique_energy
        if energy.size < 2 or np.any(np.diff(energy) <= 0.0):
            raise InvalidOOSDataError("OOS energy axis cannot be made strictly increasing")
        return OOSRawCurve(
            atomic_number=z,
            element_name=name,
            symbol=symbol,
            shell=str(shell),
            energy_eV=_readonly_float_array(energy),
            oscillator_strength=_readonly_float_array(oscillator),
            onset_eV=onset,
            table_checksum=checksum,
        )

    def differential_cross_section(
        self, raw: OOSRawCurve, geometry: ExperimentalGeometry
    ) -> OOSPhysicalCurve:
        """Evaluate Salvat RPWBA on every valid table energy channel."""
        energy = np.asarray(raw.energy_eV, dtype=float)
        oscillator = np.asarray(raw.oscillator_strength, dtype=float)
        kinetic = geometry.beam_energy_keV * KEV_TO_EV
        gamma = 1.0 + kinetic / ELECTRON_REST_ENERGY_EV
        beta_v2 = 1.0 - 1.0 / gamma**2
        valid = (
            np.isfinite(energy)
            & np.isfinite(oscillator)
            & (energy >= raw.onset_eV)
            & (energy > 0.0)
            & (energy < kinetic)
        )
        if np.count_nonzero(valid) < 2:
            raise InvalidOOSDataError(
                f"OOS shell {raw.shell} has fewer than two samples below E0"
            )
        losses = energy[valid]
        if geometry.convergence_angle_mrad > 0.0:
            angle_mrad = effective_collection_angle_mrad(
                geometry.beam_energy_keV,
                losses,
                geometry.convergence_angle_mrad,
                geometry.collection_angle_mrad,
            )
        else:
            angle_mrad = np.full(losses.shape, geometry.collection_angle_mrad)
        theta = angle_mrad * MRAD_TO_RAD

        root_argument = (
            (kinetic * (kinetic + 2.0 * ELECTRON_REST_ENERGY_EV)) ** 3
            * (kinetic - losses)
            * (kinetic - losses + 2.0 * ELECTRON_REST_ENERGY_EV)
        )
        if np.any(~np.isfinite(root_argument)) or np.any(root_argument < 0.0):
            raise InvalidOOSDataError("invalid or overflowing OOS kinematic domain")
        with np.errstate(divide="raise", invalid="raise", over="raise"):
            try:
                y_factor = (
                    1.0
                    + 4.0
                    * np.sqrt(root_argument)
                    * np.sin(theta / 2.0) ** 2
                    / (ELECTRON_REST_ENERGY_EV**2 * losses**2)
                )
                collection_term = np.log(y_factor) - beta_v2 * (1.0 - 1.0 / y_factor)
                prefactor = 8.0 * np.pi * (BOHR_RADIUS_M * RYDBERG_EV) ** 2
                prefactor /= ELECTRON_REST_ENERGY_EV * beta_v2 * losses
                valid_sigma = prefactor * oscillator[valid] * collection_term
            except FloatingPointError as exc:
                raise InvalidOOSDataError("OOS cross-section calculation was not finite") from exc
        if np.any(~np.isfinite(valid_sigma)) or np.any(valid_sigma < 0.0):
            raise InvalidOOSDataError("OOS cross section contains invalid values")
        if not np.any(valid_sigma > 0.0):
            raise InvalidOOSDataError("OOS cross section is completely zero")
        sigma = np.zeros_like(energy)
        sigma[valid] = valid_sigma
        return OOSPhysicalCurve(
            energy_eV=_readonly_float_array(energy),
            sigma=_readonly_float_array(sigma),
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            onset_eV=raw.onset_eV,
            table_checksums=(raw.table_checksum,),
        )

    def curve(
        self,
        atomic_number: int,
        shells: tuple[str, ...],
        geometry: ExperimentalGeometry,
        dataset_eloss: np.ndarray,
        broadening: BroadeningSpec = BroadeningSpec(),
        fit_range: FitRange | None = None,
    ) -> OOSCurveSnapshot:
        if not shells:
            raise MissingOOSTableError("at least one OOS shell is required")
        eloss = np.asarray(dataset_eloss, dtype=float)
        if eloss.ndim != 1 or eloss.size < 2 or np.any(~np.isfinite(eloss)):
            raise InvalidOOSDataError("dataset Eloss must be a finite one-dimensional axis")
        diffs = np.diff(eloss)
        if np.any(diffs <= 0.0):
            raise InvalidOOSDataError("dataset Eloss must be strictly increasing")

        combined = np.zeros(eloss.shape, dtype=float)
        onsets: list[float] = []
        checksums: list[str] = []
        table_minima: list[float] = []
        table_maxima: list[float] = []
        symbol = ""
        for shell in shells:
            raw = self.load_raw(atomic_number, shell)
            physical = self.differential_cross_section(raw, geometry)
            symbol = raw.symbol or symbol
            combined += np.interp(
                eloss,
                physical.energy_eV,
                physical.sigma,
                left=0.0,
                right=0.0,
            )
            onsets.append(raw.onset_eV)
            checksums.append(raw.table_checksum)
            table_minima.append(float(physical.energy_eV[0]))
            table_maxima.append(float(physical.energy_eV[-1]))

        if broadening.enabled and broadening.sigma_eV > 0.0:
            dispersion = float(np.median(np.abs(diffs)))
            if not math.isfinite(dispersion) or dispersion <= 0.0:
                raise InvalidOOSDataError("cannot convert OOS broadening from eV to channels")
            combined = gaussian_filter1d(
                combined,
                sigma=broadening.sigma_eV / dispersion,
                mode="nearest",
            )
        support = (eloss >= min(onsets)) & (eloss >= min(table_minima)) & (
            eloss <= max(table_maxima)
        )
        combined = np.where(support, combined, 0.0)
        if np.any(~np.isfinite(combined)) or np.any(combined < 0.0):
            raise InvalidOOSDataError("interpolated OOS curve contains invalid values")

        fit_mask = np.ones(eloss.shape, dtype=bool)
        if fit_range is not None:
            fit_mask &= (eloss >= fit_range.minimum) & (eloss <= fit_range.maximum)
        if np.count_nonzero(fit_mask) < 2:
            raise InvalidOOSDataError("fit range has fewer than two Eloss samples")
        normalization = float(np.max(np.abs(combined[fit_mask])))
        if not math.isfinite(normalization) or normalization <= 0.0:
            raise InvalidOOSDataError("OOS curve is zero inside the fit range")
        normalized = combined / normalization
        return OOSCurveSnapshot(
            energy_eV=_readonly_float_array(eloss),
            normalized_shape=_readonly_float_array(normalized),
            physical_shape=_readonly_float_array(combined),
            normalization_factor=normalization,
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            provider_version=OOS_PROVIDER_VERSION,
            atomic_number=int(atomic_number),
            symbol=symbol,
            shells=tuple(shells),
            onsets_eV=tuple(onsets),
            table_checksums=tuple(checksums),
            broadening_sigma_eV=broadening.sigma_eV if broadening.enabled else 0.0,
            fit_range=fit_range,
        )

    def integrate(
        self, curve: OOSPhysicalCurve, energy_min: float, energy_max: float
    ) -> float:
        lower, upper = sorted((float(energy_min), float(energy_max)))
        mask = (curve.energy_eV >= lower) & (curve.energy_eV <= upper)
        if np.count_nonzero(mask) < 2:
            raise InvalidOOSDataError("integration window has fewer than two curve samples")
        value = float(trapezoid(curve.sigma[mask], x=curve.energy_eV[mask]))
        if not math.isfinite(value) or value < 0.0:
            raise InvalidOOSDataError("integrated OOS cross section is invalid")
        return value

    def database_info(self) -> dict[str, object]:
        files = tuple(sorted(self.database_dir.glob("OOS[0-9][0-9].json")))
        return {
            "provider_version": OOS_PROVIDER_VERSION,
            "formula_version": OOS_FORMULA_VERSION,
            "source": "F. Salvat Hartree optical oscillator strengths",
            "database_dir": self.database_dir.name,
            "table_count": len(files),
        }
