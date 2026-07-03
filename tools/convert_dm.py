"""
Convert a DM3/DM4 file to .hspy, .npz and/or .npy formats.

Usage
-----
    python tools/convert_dm.py path/to/file.dm3
    python tools/convert_dm.py path/to/file.dm4 --out path/to/output_dir
    python tools/convert_dm.py path/to/file.dm3 --fmt hspy npz npy   # all three (default)
    python tools/convert_dm.py path/to/file.dm3 --fmt hspy            # only .hspy

Each signal inside the DM file becomes a separate output file:
    <stem>_signal0.hspy / <stem>_signal0.npz / <stem>_signal0.npy
    ...

Format notes
------------
.hspy   HyperSpy HDF5 — full axes + metadata
.npz    NumPy zip archive — data + calibrated axis arrays (WhatEELS preferred)
.npy    Raw NumPy array — data only, axis calibration is lost

Dependencies: hyperspy, numpy  (both present in the project venv)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Force UTF-8 I/O on Windows so HyperSpy can handle non-ASCII characters in
# DM metadata (e.g. the → arrow in some Gatan file titles).
os.environ.setdefault("PYTHONUTF8", "1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_signals(dm_path: Path) -> list:
    """Load all signals from a DM3/DM4 file via HyperSpy."""
    import hyperspy.api as hs  # type: ignore
    print(f"[convert_dm] Reading  {dm_path}")
    signals = hs.load(str(dm_path), lazy=False)
    if not isinstance(signals, list):
        signals = [signals]
    print(f"[convert_dm] Found {len(signals)} signal(s).")
    return signals


def _output_stem(dm_path: Path, out_dir: Path, index: int, total: int) -> Path:
    """Build the output file stem (without extension)."""
    suffix = f"_signal{index}" if total > 1 else ""
    return out_dir / (dm_path.stem + suffix)


def _sanitise_title(signal) -> None:
    """Replace non-ASCII characters in the signal title (Windows charmap workaround)."""
    try:
        t = signal.metadata.General.title
        signal.metadata.General.title = t.encode("ascii", errors="replace").decode("ascii")
    except Exception:
        pass


def _save_hspy(signal, stem: Path) -> None:
    out = stem.with_suffix(".hspy")
    _sanitise_title(signal)
    signal.save(str(out), overwrite=True)
    print(f"[convert_dm]   → {out}")



def _save_npy(signal, stem: Path) -> None:
    import numpy as np
    out = stem.with_suffix(".npy")
    np.save(str(out), signal.data)
    print(f"[convert_dm]   → {out}  (shape={signal.data.shape}, dtype={signal.data.dtype})")


def _save_npz(signal, stem: Path) -> None:
    """Save data + calibrated axis arrays into a single .npz archive.

    The archive contains:
        data          – the raw N-D array
        axis_<name>   – one array per axis with calibrated coordinates
        axis_names    – axis names in order (e.g. ['y', 'x', 'Energy loss'])
        axis_units    – axis units in order (e.g. ['', '', 'eV'])
    """
    import numpy as np

    out = stem.with_suffix(".npz")
    arrays: dict[str, np.ndarray] = {"data": signal.data}

    axis_names: list[str] = []
    axis_units: list[str] = []
    for ax in signal.axes_manager.navigation_axes[::-1] + signal.axes_manager.signal_axes[::-1]:
        key = f"axis_{ax.name}" if ax.name else f"axis_{ax.index_in_array}"
        arrays[key] = ax.axis          # calibrated coordinate array
        axis_names.append(ax.name or "")
        axis_units.append(ax.units or "")

    arrays["axis_names"] = np.array(axis_names)
    arrays["axis_units"] = np.array(axis_units)

    np.savez(str(out), **arrays)
    print(f"[convert_dm]   → {out}  (shape={signal.data.shape}, axes={axis_names})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a DM3/DM4 file to .hspy and/or .npy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the source .dm3 or .dm4 file.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="DIR",
        help="Output directory (defaults to the same directory as the input file).",
    )
    parser.add_argument(
        "--fmt",
        nargs="+",
        choices=["hspy", "npz", "npy"],
        default=["hspy", "npz", "npy"],
        metavar="FORMAT",
        help="Output format(s): hspy, npz, npy (default: all three).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    dm_path: Path = args.input.resolve()
    if not dm_path.is_file():
        print(f"[convert_dm] ERROR: file not found: {dm_path}", file=sys.stderr)
        return 1

    out_dir: Path = args.out.resolve() if args.out else dm_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    formats: set[str] = set(args.fmt)

    try:
        signals = _load_signals(dm_path)
    except Exception as exc:
        print(f"[convert_dm] ERROR loading file: {exc}", file=sys.stderr)
        return 1

    for i, signal in enumerate(signals):
        stem = _output_stem(dm_path, out_dir, i, len(signals))
        print(f"[convert_dm] Signal {i}: {signal}")
        failed = False
        for fmt, saver in [
            ("hspy", _save_hspy),
            ("npz",  _save_npz),
            ("npy",  _save_npy),
        ]:
            if fmt not in formats:
                continue
            try:
                saver(signal, stem)
            except Exception as exc:
                print(f"[convert_dm] ERROR saving signal {i} as .{fmt}: {exc}", file=sys.stderr)
                failed = True
        if failed:
            return 1

    print("[convert_dm] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
