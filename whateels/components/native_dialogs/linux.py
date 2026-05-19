import os
import shutil
import subprocess
from typing import Iterable


def _resolve_executable(command: str, absolute_fallbacks: Iterable[str]) -> str | None:
    path = shutil.which(command)
    if path:
        return path

    for candidate in absolute_fallbacks:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def _is_supported_dm_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in {".dm3", ".dm4"}


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


def open_linux_file_dialog() -> str:
    """Open a native Linux file dialog and return the selected path.

    Tries common desktop utilities in order:
    1) zenity
    2) kdialog
    3) yad
    Returns empty string on cancel or if no backend is available.
    """
    zenity = _resolve_executable("zenity", ("/usr/bin/zenity", "/bin/zenity"))
    if zenity:
        selected = _run_dialog([
            zenity,
            "--file-selection",
            "--title=Select a DigitalMicrograph file",
            "--file-filter=DigitalMicrograph files | *.dm3 *.dm4",
            "--file-filter=All files | *",
        ])
        if not selected or _is_supported_dm_file(selected):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}")
        return ""

    kdialog = _resolve_executable("kdialog", ("/usr/bin/kdialog", "/bin/kdialog"))
    if kdialog:
        selected = _run_dialog([
            kdialog,
            "--getopenfilename",
            "",
            "*.dm3 *.dm4|DigitalMicrograph files\n*|All files",
            "--title",
            "Select a DigitalMicrograph file",
        ])
        if not selected or _is_supported_dm_file(selected):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}")
        return ""

    yad = _resolve_executable("yad", ("/usr/bin/yad", "/bin/yad"))
    if yad:
        selected = _run_dialog([
            yad,
            "--file-selection",
            "--title=Select a DigitalMicrograph file",
            "--file-filter=DigitalMicrograph files (*.dm3 *.dm4) | *.dm3 *.dm4",
            "--file-filter=All files (*) | *",
        ])
        if not selected or _is_supported_dm_file(selected):
            return selected
        print(f"Linux dialog selected unsupported file type: {selected}")
        return ""

    print("No supported Linux dialog backend found (zenity, kdialog, or yad).")
    return ""
