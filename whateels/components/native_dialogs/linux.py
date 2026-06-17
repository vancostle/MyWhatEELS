import os
import shutil
import subprocess
from collections.abc import Sequence
from typing import Iterable


def _resolve_executable(command: str, absolute_fallbacks: Iterable[str]) -> str | None:
    path = shutil.which(command)
    if path:
        return path

    for candidate in absolute_fallbacks:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def _normalize_extensions(accepted_file_types: Sequence[str] | None) -> list[str]:
    if not accepted_file_types:
        return []

    normalized: list[str] = []
    for ext in accepted_file_types:
        candidate = str(ext).strip().lower()
        if not candidate:
            continue
        if not candidate.startswith("."):
            candidate = f".{candidate}"
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _run_dialog(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        print(f"Linux dialog launch failed: {exc}")
        return ""

    if result.returncode == 0:
        return (result.stdout or "").strip()

    # Standard cancel code for these tools.
    if result.returncode == 1:
        return ""

    stderr = (result.stderr or "").strip()
    if stderr:
        print(f"Linux dialog error: {stderr}")
    return ""


def open_linux_file_dialog(accepted_file_types: Sequence[str] | None = None) -> str:
    """Open a native Linux file dialog and return the selected path.

    Tries common desktop utilities in order:
    1) zenity
    2) kdialog
    3) yad
    Returns empty string on cancel or if no backend is available.
    """
    extensions = _normalize_extensions(accepted_file_types)
    extension_globs = " ".join(f"*{ext}" for ext in extensions) if extensions else "*"
    extension_human = ", ".join(extensions) if extensions else "*"

    zenity = _resolve_executable("zenity", ("/usr/bin/zenity", "/bin/zenity"))
    if zenity:
        selected = _run_dialog([
            zenity,
            "--file-selection",
            "--title=Select a file",
            f"--file-filter=Supported files ({extension_human}) | {extension_globs}",
            "--file-filter=All files | *",
        ])
        if not selected:
            return selected
        if not extensions or os.path.splitext(selected)[1].lower() in set(extensions):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}. Allowed: {', '.join(extensions)}")
        return ""

    kdialog = _resolve_executable("kdialog", ("/usr/bin/kdialog", "/bin/kdialog"))
    if kdialog:
        selected = _run_dialog([
            kdialog,
            "--getopenfilename",
            "",
            f"{extension_globs}|Supported files ({extension_human})\n*|All files",
            "--title",
            "Select a file",
        ])
        if not selected:
            return selected
        if not extensions or os.path.splitext(selected)[1].lower() in set(extensions):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}. Allowed: {', '.join(extensions)}")
        return ""

    yad = _resolve_executable("yad", ("/usr/bin/yad", "/bin/yad"))
    if yad:
        selected = _run_dialog([
            yad,
            "--file-selection",
            "--title=Select a file",
            f"--file-filter=Supported files ({extension_human}) | {extension_globs}",
            "--file-filter=All files (*) | *",
        ])
        if not selected:
            return selected
        if not extensions or os.path.splitext(selected)[1].lower() in set(extensions):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}. Allowed: {', '.join(extensions)}")
        return ""

    print("No supported Linux dialog backend found (zenity, kdialog, or yad).")
    return ""
