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
    beam_energy, collection_angle, convergence_angle – optional (from convert_dm)

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
from whateels.errors.npy.data import NpyFileUploadError
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

        c = self._model.constants
        if ext == ".npy":
            ds.attrs[c.ELOSS_CALIBRATED_ATTR] = False
            ds.attrs[c.ELOSS_AXIS_LABEL_ATTR] = c.ELOSS_AXIS_LABEL_CHANNEL
        else:
            ds.attrs[c.ELOSS_CALIBRATED_ATTR] = True
            ds.attrs[c.ELOSS_AXIS_LABEL_ATTR] = c.ELOSS_AXIS_LABEL_EV

        ds = self._data_processor.clean_dataset(ds)
        is_eels = 'Eloss' in ds.coords
        ds.attrs['dataset_type']      = self._data_processor.determine_dataset_type(ds, is_eels)
        ds.attrs['original_name']     = os.path.basename(file_path)
        if 'image_name' not in ds.attrs:
            ds.attrs['image_name']    = os.path.splitext(os.path.basename(file_path))[0]
        ds.attrs['shape']             = list(ds.ElectronCount.shape)
        ds.attrs.setdefault('beam_energy',       None)
        ds.attrs.setdefault('collection_angle',  None)
        ds.attrs.setdefault('convergence_angle', None)

        self._store_metadata(self._build_file_metadata(ds, filename, file_path, ext))
        return [ds]

    def _build_file_metadata(
        self,
        ds: xr.Dataset,
        filename: str,
        file_path: str,
        ext: str,
    ) -> dict:
        """Build a JSON-serializable metadata dict from the processed dataset."""
        c = self._model.constants
        return {
            'source_format': ext.lstrip('.'),
            'filename': filename,
            'original_name': ds.attrs.get('original_name', os.path.basename(file_path)),
            'image_name': ds.attrs.get('image_name'),
            'dataset_type': ds.attrs.get('dataset_type'),
            'shape': ds.attrs.get('shape'),
            'beam_energy': ds.attrs.get('beam_energy'),
            'collection_angle': ds.attrs.get('collection_angle'),
            'convergence_angle': ds.attrs.get('convergence_angle'),
            'eloss_calibrated': ds.attrs.get(c.ELOSS_CALIBRATED_ATTR),
            'eloss_axis_label': ds.attrs.get(c.ELOSS_AXIS_LABEL_ATTR),
        }

    def _store_metadata(self, infoDict: dict | None = None) -> None:
        """Store metadata in app state (same contract as FileProcessorService)."""
        if not infoDict:
            raise NpyFileUploadError("Expected an information dictionary from npy/npz parser.")
        try:
            self._model.app_state.metadata = infoDict
        except Exception as exc:
            raise NpyFileUploadError(exc)

    # ── .npz loader ──────────────────────────────────────────────────────────

    def _load_npz(self, file_path: str, filename: str) -> xr.Dataset | None:
        """Reconstruct a calibrated xr.Dataset from an .npz produced by convert_dm.py."""
        archive = np.load(file_path, allow_pickle=True)
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
        ds: xr.Dataset | None = None

        if ndim == 3 and energy_idx is not None:
            if energy_idx == 2:
                pass
            elif energy_idx == 0:
                data = data.transpose(1, 2, 0)
                axes = [axes[1], axes[2], axes[0]]
            _, _, e_ax = axes[0], axes[1], axes[2]
            ds = xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data)},
                coords={'y': np.arange(data.shape[0]), 'x': np.arange(data.shape[1]), 'Eloss': e_ax},
            )

        elif ndim == 2 and energy_idx is not None:
            if energy_idx == 0:
                data = data.T
            data3d = data.reshape(1, data.shape[0], data.shape[1])
            ds = xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data3d)},
                coords={'y': [0], 'x': np.arange(data3d.shape[1]), 'Eloss': axes[energy_idx]},
            )

        elif ndim == 1:
            e_ax = axes[0] if axes else np.arange(data.shape[0])
            ds = xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data.reshape(1, 1, -1))},
                coords={'y': [0], 'x': [0], 'Eloss': e_ax},
            )

        else:
            ds = self._array_to_dataset(data, filename)

        if ds is not None:
            for key in ('beam_energy', 'collection_angle', 'convergence_angle'):
                if key in archive.files:
                    ds.attrs[key] = float(np.asarray(archive[key]).item())
            if 'image_name' in archive.files:
                ds.attrs['image_name'] = str(np.asarray(archive['image_name']).item())

        return ds

    # ── .npy loader ──────────────────────────────────────────────────────────

    @staticmethod
    def _orient_to_y_x_eloss(data: np.ndarray) -> np.ndarray:
        """Return array as (y, x, Eloss).

        HyperSpy / convert_dm store navigation axes first and the signal (energy)
        axis last, e.g. (70, 100, 2048).  For EELS the energy dimension is typically
        the largest — never the smallest.
        """
        if data.ndim != 3:
            return data

        d0, d1, d2 = data.shape
        # Energy axis = largest dimension (typical EELS: 2048 >> 70, 100).
        energy_idx = int(np.argmax(data.shape))

        if energy_idx == 2:
            return data
        if energy_idx == 0:
            return data.transpose(1, 2, 0)   # (E, y, x) → (y, x, E)
        # energy_idx == 1
        return data.transpose(0, 2, 1)       # (y, E, x) → (y, x, E)

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
            data = self._orient_to_y_x_eloss(data)
            ny, nx, ne = data.shape
            return xr.Dataset(
                {'ElectronCount': (['y', 'x', 'Eloss'], data)},
                coords={'y': np.arange(ny), 'x': np.arange(nx), 'Eloss': np.arange(ne)},
            )

        _log.warning("[NpyProcessor] Unsupported ndim=%d for '%s', skipping.", ndim, filename)
        return None
