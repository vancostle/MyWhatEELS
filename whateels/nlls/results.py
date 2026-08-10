"""Dense, portable accumulation for Elemental NLLS multipixel results."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping

import numpy as np
import xarray as xr

from .defaults import CHEMICAL_SHIFT_CONVENTION
from .errors import InvalidRunRequestError


class FitStatus(IntEnum):
    NOT_SELECTED = 0
    PENDING = 1
    SUCCESS = 2
    INSUFFICIENT_DATA = 3
    FIT_ERROR = 4
    CANCELLED = 5


FIT_STATUS_LABELS = {int(status): status.name.lower() for status in FitStatus}


@dataclass
class NLLSResultsAccumulator:
    """Accumulate only numeric arrays; never retain ``ModelResult`` objects."""

    original_data: np.ndarray = field(repr=False)
    eloss: np.ndarray = field(repr=False)
    y_coords: np.ndarray = field(repr=False)
    x_coords: np.ndarray = field(repr=False)
    area_label: np.ndarray = field(repr=False)
    fit_status: np.ndarray = field(repr=False)
    reduced_chi_square: np.ndarray = field(repr=False)
    best_fit: np.ndarray = field(repr=False)
    residuals: np.ndarray = field(repr=False)
    components: dict[str, np.ndarray] = field(default_factory=dict, repr=False)
    parameters: dict[str, np.ndarray] = field(default_factory=dict, repr=False)
    parameter_stderr: dict[str, np.ndarray] = field(default_factory=dict, repr=False)
    area_ids_by_label: dict[int, str] = field(default_factory=dict)

    @classmethod
    def create(cls, source: xr.Dataset) -> "NLLSResultsAccumulator":
        if "ElectronCount" not in source or "Eloss" not in source.coords:
            raise InvalidRunRequestError(
                "NLLS source must contain ElectronCount and Eloss"
            )
        cube = np.asarray(source["ElectronCount"].values, dtype=float)
        eloss = np.asarray(source.coords["Eloss"].values, dtype=float).reshape(-1)
        if cube.ndim != 3 or cube.shape[-1] != eloss.size:
            raise InvalidRunRequestError(
                "NLLS source must have dimensions (y, x, Eloss)"
            )
        y_dim, x_dim = source["ElectronCount"].dims[:2]
        y_coords = (
            np.asarray(source.coords[y_dim].values)
            if y_dim in source.coords
            else np.arange(cube.shape[0])
        )
        x_coords = (
            np.asarray(source.coords[x_dim].values)
            if x_dim in source.coords
            else np.arange(cube.shape[1])
        )
        spatial_shape = cube.shape[:2]
        spectral_shape = cube.shape
        return cls(
            original_data=np.array(cube, copy=True, order="C"),
            eloss=np.array(eloss, copy=True),
            y_coords=np.array(y_coords, copy=True),
            x_coords=np.array(x_coords, copy=True),
            area_label=np.full(spatial_shape, -1, dtype=np.int32),
            fit_status=np.full(
                spatial_shape, int(FitStatus.NOT_SELECTED), dtype=np.int8
            ),
            reduced_chi_square=np.full(spatial_shape, np.nan, dtype=float),
            best_fit=np.full(spectral_shape, np.nan, dtype=float),
            residuals=np.full(spectral_shape, np.nan, dtype=float),
        )

    @property
    def spatial_shape(self) -> tuple[int, int]:
        return tuple(int(value) for value in self.original_data.shape[:2])

    def select_area(self, area_id: str, label: int, mask: np.ndarray) -> None:
        area_mask = np.asarray(mask, dtype=bool)
        if area_mask.shape != self.spatial_shape or not np.any(area_mask):
            raise InvalidRunRequestError(
                f"area {area_id} has an empty or incompatible mask"
            )
        if np.any(self.fit_status[area_mask] != int(FitStatus.NOT_SELECTED)):
            raise InvalidRunRequestError("selected NLLS area masks overlap")
        numeric_label = int(label)
        existing_area = self.area_ids_by_label.get(numeric_label)
        if existing_area is not None and existing_area != str(area_id):
            raise InvalidRunRequestError(
                "selected NLLS areas must have unique numeric labels"
            )
        self.area_label[area_mask] = numeric_label
        self.fit_status[area_mask] = int(FitStatus.PENDING)
        self.area_ids_by_label[numeric_label] = str(area_id)

    def _component_array(self, component_id: str) -> np.ndarray:
        key = str(component_id)
        if key not in self.components:
            self.components[key] = np.full(self.original_data.shape, np.nan, dtype=float)
        return self.components[key]

    def register_component(self, component_id: str) -> None:
        """Guarantee a dense component variable even when every pixel fails."""
        self._component_array(component_id)

    def _parameter_array(self, parameter_name: str) -> np.ndarray:
        key = str(parameter_name)
        if key not in self.parameters:
            self.parameters[key] = np.full(self.spatial_shape, np.nan, dtype=float)
            self.parameter_stderr[key] = np.full(self.spatial_shape, np.nan, dtype=float)
        return self.parameters[key]

    def register_parameter(self, parameter_name: str) -> None:
        """Guarantee value/stderr maps before the first pixel is attempted."""
        self._parameter_array(parameter_name)

    def store_success(
        self,
        y: int,
        x: int,
        *,
        redchi: float,
        best_fit: np.ndarray,
        residual: np.ndarray,
        components: Mapping[str, np.ndarray],
        parameters: Mapping[str, tuple[float, float | None]],
    ) -> None:
        best = np.asarray(best_fit, dtype=float).reshape(-1)
        resid = np.asarray(residual, dtype=float).reshape(-1)
        if best.size != self.eloss.size or resid.size != self.eloss.size:
            raise ValueError("pixel result curves must match Eloss")
        self.fit_status[y, x] = int(FitStatus.SUCCESS)
        self.reduced_chi_square[y, x] = float(redchi)
        self.best_fit[y, x, :] = best
        self.residuals[y, x, :] = resid
        for component_id, values in components.items():
            component = np.asarray(values, dtype=float).reshape(-1)
            if component.size != self.eloss.size:
                raise ValueError("pixel component curves must match Eloss")
            self._component_array(component_id)[y, x, :] = component
        for name, (value, stderr) in parameters.items():
            self._parameter_array(name)[y, x] = float(value)
            if stderr is not None and np.isfinite(stderr):
                self.parameter_stderr[str(name)][y, x] = float(stderr)

    def store_error(self, y: int, x: int, status: FitStatus) -> None:
        if status not in {FitStatus.INSUFFICIENT_DATA, FitStatus.FIT_ERROR}:
            raise ValueError("pixel errors require an error FitStatus")
        self.fit_status[y, x] = int(status)

    def cancel_pending(self) -> None:
        self.fit_status[self.fit_status == int(FitStatus.PENDING)] = int(
            FitStatus.CANCELLED
        )

    def to_dataset(self, attrs: Mapping[str, Any] | None = None) -> xr.Dataset:
        variables: dict[str, tuple[tuple[str, ...], np.ndarray]] = {
            "OriginalData": (("y", "x", "Eloss"), self.original_data),
            "AreaLabel": (("y", "x"), self.area_label),
            "FitStatus": (("y", "x"), self.fit_status),
            "ReducedChiSquare": (("y", "x"), self.reduced_chi_square),
            "BestFit": (("y", "x", "Eloss"), self.best_fit),
            "Residuals": (("y", "x", "Eloss"), self.residuals),
        }
        for component_id, values in self.components.items():
            variables[f"{component_id}__component"] = (
                ("y", "x", "Eloss"),
                values,
            )
        for parameter_name, values in self.parameters.items():
            variables[parameter_name] = (("y", "x"), values)
            variables[f"{parameter_name}__stderr"] = (
                ("y", "x"),
                self.parameter_stderr[parameter_name],
            )
        dataset = xr.Dataset(
            variables,
            coords={
                "y": self.y_coords,
                "x": self.x_coords,
                "Eloss": self.eloss,
            },
            attrs=dict(attrs or {}),
        )
        dataset["OriginalData"].attrs["units"] = "electron_count"
        dataset["BestFit"].attrs["units"] = "electron_count"
        dataset["Residuals"].attrs["units"] = "electron_count"
        dataset["ReducedChiSquare"].attrs["description"] = "lmfit reduced chi-square"
        dataset["FitStatus"].attrs["codes"] = json.dumps(FIT_STATUS_LABELS, sort_keys=True)
        dataset["AreaLabel"].attrs["area_ids_by_label"] = json.dumps(
            self.area_ids_by_label, sort_keys=True
        )
        for component_id in self.components:
            dataset[f"{component_id}__component"].attrs["units"] = "electron_count"
        for name in self.parameters:
            if name.endswith("chemical_shift"):
                dataset[name].attrs.update(
                    {
                        "units": "eV",
                        "chemical_shift_convention": CHEMICAL_SHIFT_CONVENTION,
                    }
                )
        return dataset


class NLLSResultsAssembler:
    """Named facade kept separate from the mutable accumulator."""

    @staticmethod
    def assemble(
        accumulator: NLLSResultsAccumulator,
        attrs: Mapping[str, Any],
    ) -> xr.Dataset:
        return accumulator.to_dataset(attrs)
