"""Structural protocol for a reconstructible Elemental NLLS continuum backend."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ..contracts import BroadeningSpec, ExperimentalGeometry, FitRange


class CrossSectionProvider(Protocol):
    def available_edges(self, atomic_number: int) -> tuple[str, ...]: ...

    def curve(
        self,
        atomic_number: int,
        shells: tuple[str, ...],
        geometry: ExperimentalGeometry,
        dataset_eloss: np.ndarray,
        broadening: BroadeningSpec,
        fit_range: FitRange | None,
    ): ...

    def database_info(self) -> dict[str, object]: ...
