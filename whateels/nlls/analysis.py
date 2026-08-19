"""Portable Center Analysis and White Lines for dense Elemental NLLS results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import numpy as np
import xarray as xr
from scipy.integrate import simpson

from .results import FitStatus


def _validate_results(results: xr.Dataset) -> None:
    required = {"FitStatus", "AreaLabel", "OriginalData"}
    missing = required.difference(results.data_vars)
    if missing:
        raise ValueError("NLLS analysis is missing: " + ", ".join(sorted(missing)))
    if results["OriginalData"].dims != ("y", "x", "Eloss"):
        raise ValueError("NLLS analysis requires y, x, Eloss dimensions")


def _parent_attrs(results: xr.Dataset, analysis_type: str) -> dict[str, object]:
    return {
        "analysis_type": analysis_type,
        "source_run_id": str(results.attrs.get("run_id", "")),
        "dataset_source_revision": str(results.attrs.get("dataset_source_revision", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _derived_dataset(
    results: xr.Dataset,
    variables: dict,
    *,
    attrs: dict[str, object],
) -> xr.Dataset:
    variables.update(
        {
            "FitStatus": (
                ("y", "x"),
                np.asarray(results["FitStatus"].values, dtype=np.int8),
            ),
            "AreaLabel": (
                ("y", "x"),
                np.asarray(results["AreaLabel"].values, dtype=np.int32),
            ),
        }
    )
    dataset = xr.Dataset(
        variables,
        coords={"y": results.coords["y"], "x": results.coords["x"]},
        attrs=attrs,
    )
    dataset["FitStatus"].attrs.update(results["FitStatus"].attrs)
    dataset["AreaLabel"].attrs.update(results["AreaLabel"].attrs)
    return dataset


class CenterAnalysisService:
    """Compute absolute distances between two fitted ELNES center maps."""

    @staticmethod
    def available_centers(results: xr.Dataset) -> tuple[str, ...]:
        _validate_results(results)
        return tuple(
            name
            for name, variable in results.data_vars.items()
            if variable.dims == ("y", "x")
            and name.endswith("center")
            and not name.endswith("__stderr")
        )

    def compute(self, results: xr.Dataset, center_a: str, center_b: str) -> xr.Dataset:
        available = set(self.available_centers(results))
        if center_a == center_b or center_a not in available or center_b not in available:
            raise ValueError("center analysis requires two different fitted center maps")
        values_a = np.asarray(results[center_a].values, dtype=float)
        values_b = np.asarray(results[center_b].values, dtype=float)
        status = np.asarray(results["FitStatus"].values, dtype=np.int8)
        valid = (
            (status == int(FitStatus.SUCCESS))
            & np.isfinite(values_a)
            & np.isfinite(values_b)
        )
        distances = np.where(valid, np.abs(values_a - values_b), np.nan)
        dataset = _derived_dataset(
            results,
            {"Distances": (("y", "x"), distances)},
            attrs={
                **_parent_attrs(results, "center_distance"),
                "center_a": center_a,
                "center_b": center_b,
                "units": "eV",
            },
        )
        dataset["Distances"].attrs.update(
            units="eV", description="absolute fitted-center distance"
        )
        return dataset


@dataclass(frozen=True)
class WhiteLineRequest:
    component_a: str
    component_b: str
    source: str = "fitted"
    window_mode: str = "auto"
    window_a: tuple[float, float] | None = None
    window_b: tuple[float, float] | None = None
    subtract_components: tuple[str, ...] = ()
    invert_ratio: bool = False

    def __post_init__(self) -> None:
        if self.component_a == self.component_b:
            raise ValueError("white-line components must be different")
        if self.source not in {"fitted", "raw"}:
            raise ValueError("white-line source must be fitted or raw")
        if self.window_mode not in {"auto", "manual"}:
            raise ValueError("white-line window mode must be auto or manual")
        if self.window_mode == "manual" and (
            self.window_a is None or self.window_b is None
        ):
            raise ValueError("manual white-line mode requires both windows")


class WhiteLineService:
    """Integrate two fitted/raw white-line regions with SciPy Simpson."""

    AUTO_FWHM_FACTOR = 2.5625

    @staticmethod
    def available_components(results: xr.Dataset) -> tuple[str, ...]:
        _validate_results(results)
        return tuple(
            name.removesuffix("__component")
            for name, variable in results.data_vars.items()
            if variable.dims == ("y", "x", "Eloss")
            and name.endswith("__component")
            and "elnes" in name.lower()
        )

    @staticmethod
    def _variable_name(results: xr.Dataset, component: str) -> str:
        name = component if component.endswith("__component") else f"{component}__component"
        if name not in results or results[name].dims != ("y", "x", "Eloss"):
            raise ValueError(f"unknown fitted component: {component}")
        return name

    @staticmethod
    def _curve_fwhm(energy: np.ndarray, curve: np.ndarray) -> float:
        finite = np.isfinite(energy) & np.isfinite(curve)
        if np.count_nonzero(finite) < 3:
            return np.nan
        x, y = energy[finite], curve[finite]
        peak = float(np.max(y))
        if not np.isfinite(peak) or peak <= 0.0:
            return np.nan
        indices = np.flatnonzero(y >= peak / 2.0)
        return (
            float(x[indices[-1]] - x[indices[0]])
            if indices.size >= 2
            else np.nan
        )

    def _auto_width(
        self,
        energy: np.ndarray,
        component_a: np.ndarray,
        component_b: np.ndarray,
        valid: np.ndarray,
    ) -> float:
        widths = np.asarray(
            [
                self._curve_fwhm(energy, cube[row, column, :])
                for cube in (component_a, component_b)
                for row, column in np.argwhere(valid)
            ],
            dtype=float,
        )
        widths = widths[np.isfinite(widths) & (widths > 0.0)]
        if widths.size == 0:
            raise ValueError("white-line auto mode could not determine a finite FWHM")
        return self.AUTO_FWHM_FACTOR * float(np.max(widths))

    @staticmethod
    def _integrate(
        energy: np.ndarray,
        curve: np.ndarray,
        window: np.ndarray,
    ) -> float:
        lower, upper = sorted((float(window[0]), float(window[1])))
        mask = (
            np.isfinite(energy)
            & np.isfinite(curve)
            & (energy >= lower)
            & (energy <= upper)
        )
        return (
            float(simpson(curve[mask], x=energy[mask]))
            if np.count_nonzero(mask) >= 2
            else np.nan
        )

    def compute(self, results: xr.Dataset, request: WhiteLineRequest) -> xr.Dataset:
        _validate_results(results)
        energy = np.asarray(results.coords["Eloss"].values, dtype=float)
        component_a = np.asarray(
            results[self._variable_name(results, request.component_a)].values,
            dtype=float,
        )
        component_b = np.asarray(
            results[self._variable_name(results, request.component_b)].values,
            dtype=float,
        )
        status = np.asarray(results["FitStatus"].values, dtype=np.int8)
        valid = (
            (status == int(FitStatus.SUCCESS))
            & np.any(np.isfinite(component_a), axis=-1)
            & np.any(np.isfinite(component_b), axis=-1)
        )
        if request.source == "raw":
            base = np.asarray(results["OriginalData"].values, dtype=float).copy()
            for component in request.subtract_components:
                variable = self._variable_name(results, component)
                base -= np.nan_to_num(results[variable].values, nan=0.0)
            curves_a = curves_b = np.clip(base, 0.0, None)
        else:
            curves_a, curves_b = component_a, component_b

        if request.window_mode == "auto":
            half_width = self._auto_width(energy, component_a, component_b, valid) / 2.0
            windows_a = np.full((*valid.shape, 2), np.nan, dtype=float)
            windows_b = np.full((*valid.shape, 2), np.nan, dtype=float)
            for row, column in np.argwhere(valid):
                center_a = energy[int(np.nanargmax(component_a[row, column, :]))]
                center_b = energy[int(np.nanargmax(component_b[row, column, :]))]
                windows_a[row, column] = (center_a - half_width, center_a + half_width)
                windows_b[row, column] = (center_b - half_width, center_b + half_width)
        else:
            windows_a = np.broadcast_to(
                np.asarray(sorted(request.window_a), dtype=float), (*valid.shape, 2)
            ).copy()
            windows_b = np.broadcast_to(
                np.asarray(sorted(request.window_b), dtype=float), (*valid.shape, 2)
            ).copy()

        intensity_a = np.full(valid.shape, np.nan, dtype=float)
        intensity_b = np.full(valid.shape, np.nan, dtype=float)
        for row, column in np.argwhere(valid):
            intensity_a[row, column] = self._integrate(
                energy, curves_a[row, column, :], windows_a[row, column]
            )
            intensity_b[row, column] = self._integrate(
                energy, curves_b[row, column, :], windows_b[row, column]
            )
        numerator, denominator = (
            (intensity_b, intensity_a)
            if request.invert_ratio
            else (intensity_a, intensity_b)
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = numerator / denominator
        ratio[~np.isfinite(ratio)] = np.nan
        dataset = _derived_dataset(
            results,
            {
                "IntensityA": (("y", "x"), intensity_a),
                "IntensityB": (("y", "x"), intensity_b),
                "Ratio": (("y", "x"), ratio),
                "WindowMinA": (("y", "x"), windows_a[..., 0]),
                "WindowMaxA": (("y", "x"), windows_a[..., 1]),
                "WindowMinB": (("y", "x"), windows_b[..., 0]),
                "WindowMaxB": (("y", "x"), windows_b[..., 1]),
            },
            attrs={
                **_parent_attrs(results, "white_lines"),
                "request": json.dumps(asdict(request), sort_keys=True),
                "integration": "scipy.integrate.simpson",
                "auto_fwhm_factor": self.AUTO_FWHM_FACTOR,
            },
        )
        dataset["IntensityA"].attrs["units"] = "electron_count_eV"
        dataset["IntensityB"].attrs["units"] = "electron_count_eV"
        dataset["Ratio"].attrs["units"] = "dimensionless"
        return dataset
