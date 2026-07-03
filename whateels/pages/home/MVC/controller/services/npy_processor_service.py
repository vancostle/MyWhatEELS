"""
Loads .npy and .npz files and converts the array into an xr.Dataset with the
same structure produced by FileProcessorService / RosettaFileProcessorService.

.npz files (produced by tools/convert_dm.py)
--------------------------------------------
Store the data array alongside calibrated axis arrays so that WhatEELS can
reconstruct the full dataset with real eV coordinates.  Expected keys:

    data          – N-D array
    axis_<name>   – calibrated coordinate array for each axis
    axis_names    – axis names in order
    axis_units    – axis units in order

.npy files
----------
Only the raw array — axis calibration is lost.  Coordinates are synthetic
integer indices.  Supported shapes:

    1D  (energy,)       → single spectrum   (y=1, x=1, Eloss)
    2D  (pos, energy)   → spectrum line      (y=1, x=pos, Eloss)
    3D  (y, x, energy)  → spectrum image     (y, x, Eloss)
"""

from __future__ import annotations

import os
import logging
import numpy as np
import xarray as xr
from .data_processor_service import DataProcessorService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

_log = logging.getLogger(__name__)


class NpyProcessorService:
    """Load a .npy or .npz file and return a list[xr.Dataset] matching the app contract."""

    def __init__(self, model: "HomePageModel"):
        self._model = model
        self._data_processor = DataProcessorService(model)

    # ── Public ──────────────────────────────────────────────────────────────

    def process_upload(self, filename: str, file_path: str) -> list[xr.Dataset]:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".npz":
            ds = self._load_npz(file_path, filename)
        else:
            data = np.load(file_path).astype(np.float64)
            _log.info("[NpyProcessor] Loaded '%s', shape=%s", filename, data.shape)
            ds = self._array_to_dataset(data, filename)

        if ds is None:
            return []

        ds = self._data_processor.clean_dataset(ds)
        is_eels = 'Eloss' in ds.coords
        ds.attrs['dataset_type']      = self._data_processor.determine_dataset_type(ds, is_eels)
        ds.attrs['original_name']     = os.path.basename(file_path)
        ds.attrs['image_name']        = os.path.splitext(os.path.basename(file_path))[0]
        ds.attrs['shape']             = list(ds.ElectronCount.shape)
        ds.attrs.setdefault('beam_energy',       None)
        ds.attrs.setdefault('collection_angle',  None)
        ds.attrs.setdefault('convergence_angle', None)
        return [ds]

    # ── .npz loader ──────────────────────────────────────────────────────────

    def _load_npz(self, file_path: str, filename: str) -> xr.Dataset | None:
        """Reconstruct a calibrated xr.Dataset from an .npz produced by convert_dm.py."""
        archive = np.load(file_path, allow_pickle=False)
        data: np.ndarray = archive['data'].astype(np.float64)

        axis_names: list[str] = list(archive['axis_names'])
        axis_units: list[str] = list(archive['axis_units'])

        _log.info(
            "[NpyProcessor] Loaded .npz '%s', shape=%s, axes=%s",
            filename, data.shape, axis_names,
        )

        # Find the energy/signal axis by unit ("eV") or name.
        energy_idx: int | None = None
        for i, (name, unit) in enumerate(zip(axis_names, axis_units)):
            if 'ev' in unit.lower() or 'energy' in name.lower() or 'loss' in name.lower():
                energy_idx = i
                break

        axes: list[np.ndarray] = [
            archive[f"axis_{name}" if name else f"axis_{i}"]
            for i, name in enumerate(axis_names)
        ]

        ndim = data.ndim

        if ndim == 3 and energy_idx is not None:
            # Ensure layout is (y, x, Eloss).
            if energy_idx == 2:
                pass
            elif energy_idx == 0:
                data = data.transpose(1, 2, 0)
                axes = [axes[1], axes[2], axes[0]]
            y_ax, x_ax, e_ax = axes[0], axes[1], axes[2]
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data)},
                coords={'y': np.arange(data.shape[0]), 'x': np.arange(data.shape[1]), 'Eloss': e_ax},
            )

        if ndim == 2 and energy_idx is not None:
            e_ax = axes[energy_idx]
            nav_ax = axes[1 - energy_idx]
            if energy_idx == 0:
                data = data.T
            data3d = data.reshape(1, data.shape[0], data.shape[1])
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data3d)},
                coords={'y': [0], 'x': np.arange(data3d.shape[1]), 'Eloss': e_ax},
            )

        if ndim == 1:
            e_ax = axes[0] if axes else np.arange(data.shape[0])
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data.reshape(1, 1, -1))},
                coords={'y': [0], 'x': [0], 'Eloss': e_ax},
            )

        # Fallback: no energy axis identified — treat as plain .npy
        return self._array_to_dataset(data, filename)

    # ── .npy loader ──────────────────────────────────────────────────────────

    def _array_to_dataset(self, data: np.ndarray, filename: str) -> xr.Dataset | None:
        """Convert a raw numpy array to an xr.Dataset with synthetic integer axes."""
        ndim = data.ndim

        if ndim == 1:
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data.reshape(1, 1, -1))},
                coords={'y': [0], 'x': [0], 'Eloss': np.arange(data.shape[0])},
            )

        if ndim == 2:
            n_pos, n_energy = data.shape
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data.reshape(1, n_pos, n_energy))},
                coords={'y': [0], 'x': np.arange(n_pos), 'Eloss': np.arange(n_energy)},
            )

        if ndim == 3:
            d0, d1, d2 = data.shape
            if d0 < d1 and d0 < d2:
                data = data.transpose(1, 2, 0)
            ny, nx, ne = data.shape
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data)},
                coords={'y': np.arange(ny), 'x': np.arange(nx), 'Eloss': np.arange(ne)},
            )

        _log.warning("[NpyProcessor] Unsupported ndim=%d for '%s', skipping.", ndim, filename)
        return None
