"""Single source of defaults shared by the Elemental NLLS domain and GUI."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from .contracts import ParameterSpec


SCHEMA_VERSION = 1
OOS_FORMULA_VERSION = "salvat-rpwba-eaxis-v1"
OOS_PROVIDER_VERSION = "FSalvat-OOS/1"
OOS_UNITS = "m^2/eV"

CHEMICAL_SHIFT_CONVENTION = (
    "model(x)=table(x+chemical_shift); positive shifts features to lower energy"
)
CHEMICAL_SHIFT_TOOLTIP = (
    "Positive chemical shift evaluates table(x + shift) and moves the modeled edge "
    "to lower energy. Associated ELNES center intervals move with the same edge."
)

DEFAULT_MODEL_COMPOSITION = "continuum_plus_elnes"
DEFAULT_ELNES_SHAPE = "GaussianModel"
DEFAULT_FLEXIBILITY = "Medium"
DEFAULT_FWHM_EV = 4.8
DEFAULT_SOFTEN = True
DEFAULT_SOFTEN_SIGMA_EV = 1.5

SUPPORTED_ELNES_SHAPES = (
    "GaussianModel",
    "LorentzianModel",
    "PseudoVoigtModel",
    "SplitLorentzianModel",
)

_COUPLED_SHELLS = (("L2", "L3"), ("M4", "M5"))


def stable_component_token(symbol: str, shells: Iterable[str]) -> str:
    """Return a deterministic identifier safe for lmfit parameter prefixes."""
    raw = f"{symbol}_{''.join(shells)}".lower()
    token = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return token or "edge"


def canonical_subshell_groups(
    selected: Iterable[str], available: Iterable[str]
) -> tuple[tuple[str, ...], ...]:
    """Partition selected shells and complete the supported physical doublets.

    Selecting either member of L2/L3 or M4/M5 includes both when both tables are
    available. Other shells remain independent components.
    """
    selected_set = {str(shell) for shell in selected}
    available_order = tuple(dict.fromkeys(str(shell) for shell in available))
    available_set = set(available_order)
    groups: list[tuple[str, ...]] = []
    consumed: set[str] = set()

    for pair in _COUPLED_SHELLS:
        if selected_set.intersection(pair):
            present = tuple(shell for shell in pair if shell in available_set)
            if present:
                groups.append(present)
                consumed.update(pair)

    for shell in available_order:
        if shell in selected_set and shell not in consumed:
            groups.append((shell,))

    return tuple(groups)


def fwhm_from_attrs(attrs: dict) -> float:
    """Resolve an instrumental FWHM from metadata with a finite fallback."""
    try:
        value = float(attrs.get("fwhm_from_0loss", DEFAULT_FWHM_EV))
    except (TypeError, ValueError):
        value = DEFAULT_FWHM_EV
    return value if math.isfinite(value) and value > 0.0 else DEFAULT_FWHM_EV


def continuum_parameter_specs(chemical_shift: float = 0.0) -> tuple[ParameterSpec, ParameterSpec]:
    return (
        ParameterSpec(value=1.0, minimum=0.0, maximum=math.inf, vary=True),
        ParameterSpec(
            value=float(chemical_shift),
            minimum=-20.0,
            maximum=20.0,
            vary=False,
        ),
    )


def fine_structure_parameter_specs(
    fwhm_eV: float,
    center_offset_eV: float = 7.0,
) -> tuple[ParameterSpec, ParameterSpec, ParameterSpec]:
    """Return ELNES offset, width and amplitude defaults.

    The offset is relative to the shell onset: 0 eV is the onset itself and
    14 eV is its initial upper search bound.  Seven eV is the fallback center
    when a local white-line maximum is unavailable.
    """
    sigma = max(0.5, float(fwhm_eV) / 2.354820045)
    center_offset = min(14.0, max(0.0, float(center_offset_eV)))
    return (
        ParameterSpec(
            minimum=0.0,
            value=center_offset,
            maximum=14.0,
            vary=True,
        ),
        ParameterSpec(
            value=sigma,
            minimum=0.5,
            maximum=sigma * 2.25,
            vary=True,
        ),
        ParameterSpec(value=1.0, minimum=0.0, maximum=math.inf, vary=True),
    )
