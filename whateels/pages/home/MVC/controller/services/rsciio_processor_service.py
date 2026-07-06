"""
Loads DM3/DM4 files via RosettaSciIO and converts each signal into an
xr.Dataset with the same structure produced by FileProcessorService.
"""

import os
import logging
import numpy as np
import xarray as xr
from .data_processor_service import DataProcessorService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

_log = logging.getLogger(__name__)


class RosettaFileProcessorService:
    """
    Drop-in replacement for FileProcessorService using RosettaSciIO as the
    DM3/DM4 parser. Produces the same list[xr.Dataset] contract so the rest
    of the app (plots, AppState, UI) needs no changes.
    """

    def __init__(self, model: "HomePageModel"):
        self._model = model
        self._data_processor = DataProcessorService(model)

    # ── Public ──────────────────────────────────────────────────────────────

    _READERS: dict[str, str] = {
        ".dm3":  "rsciio.digitalmicrograph",
        ".dm4":  "rsciio.digitalmicrograph",
        ".hspy": "rsciio.hspy",
    }

    def process_upload(self, filename: str, file_path: str) -> list[xr.Dataset]:
        """
        Read *file_path* with rsciio and return a list of cleaned xr.Datasets.
        Also stores the first signal's metadata in AppState.
        """
        import importlib

        ext = os.path.splitext(filename)[1].lower()
        reader_module = self._READERS.get(ext)
        if reader_module is None:
            raise ValueError(f"Unsupported file extension '{ext}'. Supported: {list(self._READERS)}")

        file_reader = importlib.import_module(reader_module).file_reader
        signals: list[dict] = file_reader(file_path)
        if not signals:
            return []

        self._model.app_state.metadata = signals[0].get('metadata', {})

        all_datasets: list[xr.Dataset] = []
        for signal in signals:
            ds = self._signal_to_dataset(signal, file_path)
            if ds is not None:
                all_datasets.append(ds)

        return all_datasets

    # ── Private ─────────────────────────────────────────────────────────────

    def _signal_to_dataset(self, signal: dict, file_path: str) -> xr.Dataset | None:
        data: np.ndarray = np.array(signal['data'], dtype=np.float64)
        # DM reader provides 'index_in_array'; hspy reader does not (axes already ordered).
        axes: list[dict] = sorted(
            signal['axes'],
            key=lambda a: a.get('index_in_array', signal['axes'].index(a)),
        )
        meta: dict = signal['metadata']
        orig: dict = signal.get('original_metadata', {})

        is_eels = meta.get('Signal', {}).get('signal_type', '') == 'EELS'
        energy_ax_idx = self._find_energy_axis_idx(axes)
        if energy_ax_idx is not None:
            is_eels = True

        try:
            if is_eels and energy_ax_idx is not None:
                ds = self._build_eels_dataset(data, axes, energy_ax_idx)
            elif data.ndim == 3:
                # 3D signal without a recognised energy axis — assume (y, x, signal)
                # and treat the last axis as Eloss using whatever axis metadata exists.
                _log.info(
                    "3D non-EELS signal in '%s' — treating last axis as energy channel.",
                    file_path,
                )
                inferred_energy_idx = len(axes) - 1
                is_eels = True  # treat as spectrum image so the correct plot is chosen
                ds = self._build_eels_dataset(data, axes, inferred_energy_idx)
            else:
                ds = self._build_image_dataset(data)

            if ds is None:
                return None

            ds = self._data_processor.clean_dataset(ds)
            ds.attrs['dataset_type'] = self._data_processor.determine_dataset_type(ds, is_eels)
            self._attach_attrs(ds, meta, orig, file_path)
            return ds

        except Exception:
            _log.warning("Failed to convert signal to dataset for '%s'", file_path, exc_info=True)
            return None

    def _build_eels_dataset(
        self,
        data: np.ndarray,
        axes: list[dict],
        energy_ax_idx: int,
    ) -> xr.Dataset | None:
        """Build (y, x, Eloss) dataset from rsciio EELS signal."""

        energy_coords = self._axis_to_array(axes[energy_ax_idx])

        if data.ndim == 1:
            # Single spectrum (energy,) → (y=1, x=1, energy)
            data_3d = data.reshape(1, 1, -1)
            y_coords = np.array([0], dtype=np.int32)
            x_coords = np.array([0], dtype=np.int32)

        elif data.ndim == 2:
            # Spectrum line — rsciio/HyperSpy: (nav, signal) i.e. (x, energy).
            # Guard against (energy, x) just in case.
            if energy_ax_idx == 0:
                data = data.T          # (energy, x) → (x, energy)
            n_pos = data.shape[0]
            data_3d = data.reshape(1, n_pos, -1)   # → (y=1, x, energy)
            y_coords = np.array([0], dtype=np.int32)
            x_coords = np.arange(n_pos, dtype=np.int32)

        elif data.ndim == 3:
            # Spectrum image — rsciio/HyperSpy: (y, x, energy) i.e. energy last.
            # Guard against (energy, y, x) from older files.
            if energy_ax_idx == 2:
                data_3d = data
            elif energy_ax_idx == 0:
                data_3d = data.transpose(1, 2, 0)  # (energy, y, x) → (y, x, energy)
            else:
                _log.warning("Unexpected energy axis index %d for 3D EELS data", energy_ax_idx)
                return None
            y_coords = np.arange(data_3d.shape[0], dtype=np.int32)
            x_coords = np.arange(data_3d.shape[1], dtype=np.int32)

        else:
            _log.warning("Unsupported data ndim=%d for EELS signal", data.ndim)
            return None

        return xr.Dataset(
            {'ElectronCount': (['y', 'x', 'Eloss'], data_3d)},
            coords={'y': y_coords, 'x': x_coords, 'Eloss': energy_coords},
        )

    def _build_image_dataset(self, data: np.ndarray) -> xr.Dataset | None:
        """Build (y, x) dataset from a non-EELS 2D image signal."""
        if data.ndim != 2:
            _log.warning("Non-EELS signal has unexpected ndim=%d, skipping", data.ndim)
            return None
        y_coords = np.arange(data.shape[0], dtype=np.int32)
        x_coords = np.arange(data.shape[1], dtype=np.int32)
        return xr.Dataset(
            {'ElectronCount': (['y', 'x'], data)},
            coords={'y': y_coords, 'x': x_coords},
        )

    def _attach_attrs(self, ds: xr.Dataset, meta: dict, orig: dict, file_path: str) -> None:
        """Populate dataset.attrs to match the FileProcessorService contract.

        Tries the HyperSpy-normalised ``metadata`` dict first, then falls back
        to ``original_metadata`` (raw DM ImageTags), which mirrors the structure
        the own parser reads directly.

        Note: rsciio's ``original_metadata['ImageList']`` uses keys like
        ``TagGroup0``, ``TagGroup1`` … (not numeric strings like the own parser's
        infoDict).  We iterate over all entries to find the one with the relevant
        ImageTags instead of hardcoding a key.
        """
        acq       = meta.get('Acquisition_instrument', {}).get('TEM', {})
        eels_meta = acq.get('EELS', {})
        general   = meta.get('General', {})

        image_tags = self._find_image_tags(orig)

        # ── beam energy ──────────────────────────────────────────────────────
        # rsciio stores it in kV; own parser reads V and divides by 1000.
        beam_energy = acq.get('beam_energy', None)
        if beam_energy is None and image_tags:
            try:
                v = image_tags['Microscope Info']['Voltage']
                beam_energy = v / 1000.0
            except (KeyError, TypeError):
                pass

        # ── collection angle ─────────────────────────────────────────────────
        collection_angle = eels_meta.get('collection_angle', None)
        if collection_angle is None:
            detector = acq.get('Detector', {})
            if isinstance(detector, dict):
                collection_angle = detector.get('EELS', {}).get('collection_angle', None)
        if collection_angle is None and image_tags:
            try:
                collection_angle = (
                    image_tags['EELS']['Experimental Conditions']
                               ['Collection semi-angle (mrad)']
                )
            except (KeyError, TypeError):
                pass

        # ── convergence angle ────────────────────────────────────────────────
        # rsciio key is 'convergence_angle', NOT 'convergence_semiangle_rad'.
        convergence_angle = acq.get('convergence_angle', None)
        if convergence_angle is None and image_tags:
            try:
                convergence_angle = (
                    image_tags['EELS']['Experimental Conditions']
                               ['Convergence semi-angle (mrad)']
                )
            except (KeyError, TypeError):
                pass

        ds.attrs['original_name']     = os.path.basename(file_path)
        ds.attrs['image_name']        = general.get('title', os.path.basename(file_path))
        ds.attrs['beam_energy']       = beam_energy
        ds.attrs['collection_angle']  = collection_angle
        ds.attrs['convergence_angle'] = convergence_angle
        ds.attrs['shape']             = list(ds.ElectronCount.shape)

    @staticmethod
    def _find_image_tags(orig: dict) -> dict | None:
        """Return the first ImageTags dict that contains useful microscope metadata.

        rsciio stores ``original_metadata['ImageList']`` with keys like
        ``TagGroup0``, ``TagGroup1``, … rather than the numeric strings used by
        the own parser.  We iterate over all entries and return the ImageTags of
        the first one that has more than just a GMS Version entry.
        """
        image_list = orig.get('ImageList', {})
        best: dict | None = None
        for entry in image_list.values():
            if not isinstance(entry, dict):
                continue
            tags = entry.get('ImageTags')
            if not isinstance(tags, dict) or not tags:
                continue
            if best is None:
                best = tags
            # Prefer the entry with the most keys (richer metadata).
            if len(tags) > len(best):
                best = tags
        return best

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _axis_to_array(axis: dict) -> np.ndarray:
        # hspy reader stores 'size' as a string; DM reader stores it as int.
        return axis['offset'] + axis['scale'] * np.arange(int(axis['size']))

    @staticmethod
    def _find_energy_axis_idx(axes: list[dict]) -> int | None:
        """Return the index of the energy (signal) axis, or None."""
        for i, ax in enumerate(axes):
            name  = ax.get('name',  '').lower()
            units = ax.get('units', '').lower()
            if 'energy' in name or 'loss' in name or units == 'ev':
                return i
        return None
