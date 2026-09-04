"""Reconstruct lmfit models from serializable Elemental NLLS area specs."""

from __future__ import annotations

import functools
import operator
from dataclasses import dataclass
from typing import Any

import numpy as np
from lmfit import Model, Parameters
from lmfit.models import (
    GaussianModel,
    LorentzianModel,
    PseudoVoigtModel,
    SplitLorentzianModel,
)

from .contracts import (
    AreaModelSpec,
    DatasetIdentity,
    ExperimentalGeometry,
    FineStructureSpec,
    FitRange,
    ModelBuildSnapshot,
    ModelComposition,
    ParameterSpec,
)
from .cross_sections import OOSContinuumProvider, OOSCurveSnapshot
from .errors import EmptyModelError, UnsupportedModelCompositionError


@dataclass(frozen=True)
class BuiltAreaModel:
    model: Any
    params: Parameters
    curve_snapshots: dict[str, OOSCurveSnapshot]
    component_ids: tuple[str, ...]

    @property
    def n_varying_parameters(self) -> int:
        return sum(bool(parameter.vary) for parameter in self.params.values())


class NLLSModelBuilder:
    """Build either supported composition from an obligatory list of OOS continua."""

    _ELNES_MODELS = {
        "GaussianModel": GaussianModel,
        "LorentzianModel": LorentzianModel,
        "PseudoVoigtModel": PseudoVoigtModel,
        "SplitLorentzianModel": SplitLorentzianModel,
    }

    def __init__(self, oos_provider: OOSContinuumProvider):
        self.oos_provider = oos_provider

    @staticmethod
    def _make_oos_component(snapshot: OOSCurveSnapshot, prefix: str) -> Model:
        """Create ``A * table(x + chemical_shift)`` from a portable snapshot.

        Positive ``chemical_shift`` moves the tabulated feature toward lower
        energy loss. This sign is intentionally opposite to an ELNES ``center``.
        """
        energy = np.asarray(snapshot.energy_eV, dtype=float)
        shape = np.asarray(snapshot.normalized_shape, dtype=float)

        def oos_continuum(x, A=1.0, chemical_shift=0.0):
            sample_x = np.asarray(x, dtype=float) + chemical_shift
            return A * np.interp(sample_x, energy, shape, left=0.0, right=0.0)

        model = Model(
            oos_continuum,
            independent_vars=["x"],
            prefix=prefix,
            nan_policy="omit",
        )
        model.set_param_hint("A", value=1.0, min=0.0, vary=True)
        model.set_param_hint(
            "chemical_shift",
            value=0.0,
            min=-20.0,
            max=20.0,
            vary=False,
        )
        return model

    def _make_elnes_component(self, spec: FineStructureSpec):
        try:
            model_type = self._ELNES_MODELS[spec.shape]
        except KeyError as exc:
            raise ValueError(f"unsupported ELNES shape: {spec.shape}") from exc
        return model_type(prefix=spec.prefix, nan_policy="omit")

    @staticmethod
    def _apply_parameter_spec(parameter, spec: ParameterSpec) -> None:
        parameter.set(
            value=spec.value,
            min=spec.minimum,
            max=spec.maximum,
            vary=spec.vary,
            expr=spec.expr,
            brute_step=spec.brute_step,
        )

    def _apply_parameter_specs(self, params: Parameters, area: AreaModelSpec) -> None:
        for continuum in area.continuum_specs:
            self._apply_parameter_spec(params[f"{continuum.prefix}A"], continuum.amplitude)
            self._apply_parameter_spec(
                params[f"{continuum.prefix}chemical_shift"], continuum.chemical_shift
            )

        if area.model_composition is not ModelComposition.CONTINUUM_PLUS_ELNES:
            return
        for fine in area.fine_structure_specs:
            if not fine.enabled:
                continue
            self._apply_parameter_spec(params[f"{fine.prefix}center"], fine.center)
            self._apply_parameter_spec(params[f"{fine.prefix}sigma"], fine.sigma)
            self._apply_parameter_spec(params[f"{fine.prefix}amplitude"], fine.amplitude)
            sigma_r = params.get(f"{fine.prefix}sigma_r")
            if sigma_r is not None:
                self._apply_parameter_spec(sigma_r, fine.sigma)

    def evaluate_fine_structure(
        self,
        spec: FineStructureSpec,
        eloss: np.ndarray,
        *,
        amplitude: float | None = None,
    ) -> np.ndarray:
        """Evaluate one ELNES spec with the exact model semantics used by Build.

        ``amplitude`` is a display-only override used to derive a stable visual
        scale. It does not mutate the immutable spec or relax its saved bounds.
        """
        model = self._make_elnes_component(spec)
        params = model.make_params()
        self._apply_parameter_spec(params[f"{spec.prefix}center"], spec.center)
        self._apply_parameter_spec(params[f"{spec.prefix}sigma"], spec.sigma)
        self._apply_parameter_spec(params[f"{spec.prefix}amplitude"], spec.amplitude)
        sigma_r = params.get(f"{spec.prefix}sigma_r")
        if sigma_r is not None:
            self._apply_parameter_spec(sigma_r, spec.sigma)
        if amplitude is not None:
            params[f"{spec.prefix}amplitude"].set(
                value=float(amplitude),
                min=-np.inf,
                max=np.inf,
                vary=False,
                expr=None,
            )
        values = np.asarray(
            model.eval(params=params, x=np.asarray(eloss, dtype=float)),
            dtype=float,
        )
        if np.any(~np.isfinite(values)):
            raise ValueError("fine-structure preview contains NaN or Inf")
        return values

    def build(
        self,
        area: AreaModelSpec,
        geometry: ExperimentalGeometry,
        eloss: np.ndarray,
        fit_range: FitRange | None = None,
    ) -> BuiltAreaModel:
        parts: list[Any] = []
        snapshots: dict[str, OOSCurveSnapshot] = {}
        component_ids: list[str] = []

        for continuum in area.continuum_specs:
            snapshot = self.oos_provider.curve(
                continuum.atomic_number,
                continuum.shells,
                geometry,
                np.asarray(eloss, dtype=float),
                continuum.broadening,
                fit_range,
            )
            snapshots[continuum.id] = snapshot
            parts.append(self._make_oos_component(snapshot, continuum.prefix))
            component_ids.append(continuum.id)

        if not parts:
            raise EmptyModelError("area has no valid OOS continuum components")

        if area.model_composition is ModelComposition.CONTINUUM_PLUS_ELNES:
            for fine in area.fine_structure_specs:
                if fine.enabled:
                    parts.append(self._make_elnes_component(fine))
                    component_ids.append(fine.id)
        elif area.model_composition is not ModelComposition.CONTINUUM_ONLY:
            raise UnsupportedModelCompositionError(str(area.model_composition))

        composite = functools.reduce(operator.add, parts)
        params = composite.make_params()
        self._apply_parameter_specs(params, area)
        return BuiltAreaModel(
            model=composite,
            params=params,
            curve_snapshots=snapshots,
            component_ids=tuple(component_ids),
        )

    @staticmethod
    def snapshot(
        built: BuiltAreaModel,
        area: AreaModelSpec,
        dataset_identity: DatasetIdentity,
        eloss: np.ndarray,
    ) -> ModelBuildSnapshot:
        """Materialize a portable preview without retaining live lmfit objects."""
        x = np.asarray(eloss, dtype=float)
        preview = np.asarray(built.model.eval(params=built.params, x=x), dtype=float)
        components = {
            str(name): np.asarray(values, dtype=float)
            for name, values in built.model.eval_components(params=built.params, x=x).items()
        }
        if np.any(~np.isfinite(preview)) or any(
            np.any(~np.isfinite(values)) for values in components.values()
        ):
            raise ValueError("elemental model preview contains NaN or Inf")

        params = tuple(
            {
                "name": str(name),
                "value": float(parameter.value),
                "min": float(parameter.min),
                "max": float(parameter.max),
                "vary": bool(parameter.vary),
                "expr": parameter.expr,
                "brute_step": parameter.brute_step,
            }
            for name, parameter in built.params.items()
        )
        curve_metadata = tuple(
            {
                "component_id": component_id,
                "provider_version": curve.provider_version,
                "formula_version": curve.formula_version,
                "units": curve.units,
                "normalization_factor": float(curve.normalization_factor),
                "atomic_number": int(curve.atomic_number),
                "symbol": curve.symbol,
                "shells": tuple(curve.shells),
                "onsets_eV": tuple(float(value) for value in curve.onsets_eV),
                "table_checksums": tuple(curve.table_checksums),
                "broadening_sigma_eV": float(curve.broadening_sigma_eV),
            }
            for component_id, curve in built.curve_snapshots.items()
        )
        return ModelBuildSnapshot(
            area_id=area.area_id,
            area_revision=area.revision,
            dataset_source_revision=dataset_identity.source_revision,
            model_composition=area.model_composition,
            component_ids=built.component_ids,
            params=params,
            preview=preview,
            components=components,
            curve_metadata=curve_metadata,
        )
