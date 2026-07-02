"""
Convert a DM3/DM4 file to .hspy (HyperSpy) and .npy (NumPy) formats.

Usage
-----
    python tools/convert_dm.py path/to/file.dm3
    python tools/convert_dm.py path/to/file.dm4 --out path/to/output_dir
    python tools/convert_dm.py path/to/file.dm3 --fmt hspy       # only .hspy
    python tools/convert_dm.py path/to/file.dm3 --fmt npy        # only .npy
    python tools/convert_dm.py path/to/file.dm3 --fmt hspy npy   # both (default)

Each signal inside the DM file becomes a separate output file:
    <stem>_signal0.hspy  /  <stem>_signal0.npy
    <stem>_signal1.hspy  /  <stem>_signal1.npy
    ...

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


def _save_hspy(signal, stem: Path) -> None:
    out = stem.with_suffix(".hspy")
    # HyperSpy writes metadata as strings; on Windows the default 'charmap' codec
    # chokes on non-ASCII characters (e.g. → in the title).  Sanitise before saving.
    try:
        original_title = signal.metadata.General.title
        signal.metadata.General.title = original_title.encode("ascii", errors="replace").decode("ascii")
    except Exception:
        pass
    signal.save(str(out), overwrite=True)
    print(f"[convert_dm]   → {out}")


def _save_npy(signal, stem: Path) -> None:
    import numpy as np
    out = stem.with_suffix(".npy")
    np.save(str(out), signal.data)
    print(f"[convert_dm]   → {out}  (shape={signal.data.shape}, dtype={signal.data.dtype})")


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
        choices=["hspy", "npy"],
        default=["hspy", "npy"],
        metavar="FORMAT",
        help="Output format(s): hspy, npy, or both (default: both).",
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
        try:
            if "hspy" in formats:
                _save_hspy(signal, stem)
            if "npy" in formats:
                _save_npy(signal, stem)
        except Exception as exc:
            print(f"[convert_dm] ERROR saving signal {i}: {exc}", file=sys.stderr)
            return 1

    print("[convert_dm] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
