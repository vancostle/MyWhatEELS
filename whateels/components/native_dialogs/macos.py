import os
import subprocess
from collections.abc import Sequence


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


def open_macos_file_dialog(accepted_file_types: Sequence[str] | None = None) -> str:
    """Open a native macOS file dialog and return the selected path."""
    osascript = "/usr/bin/osascript" if os.path.exists("/usr/bin/osascript") else "osascript"
    extensions = _normalize_extensions(accepted_file_types)

    if extensions:
        applescript_extensions = ", ".join(f'"{ext.lstrip(".")}"' for ext in extensions)
        applescript = (
            'set selectedFile to choose file with prompt "Select a file" '
            f'of type {{{applescript_extensions}}} without invisibles and multiple selections allowed false\n'
            'POSIX path of selectedFile'
        )
    else:
        applescript = (
            'set selectedFile to choose file with prompt "Select a file" '
            'without invisibles and multiple selections allowed false\n'
            'POSIX path of selectedFile'
        )

    try:
        result = subprocess.run(
            [osascript, "-e", applescript],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        print(f"macOS dialog launch failed: {exc}")
        return ""

    if result.returncode == 0:
        selected = result.stdout.strip()
        if not selected:
            return ""

        if not extensions:
            return selected

        if os.path.splitext(selected)[1].lower() in set(extensions):
            return selected

        print(f"macOS dialog selected unsupported file type: {selected}. Allowed: {', '.join(extensions)}")
        return ""

    stderr = (result.stderr or "").strip()
    # -128 is the standard AppleScript user-cancel code.
    if "-128" in stderr or "User canceled" in stderr:
        return ""

    if stderr:
        print(f"macOS dialog error: {stderr}")
    return ""
