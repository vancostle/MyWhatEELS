import os
import subprocess


def _is_supported_dm_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in {".dm3", ".dm4"}


def open_macos_file_dialog() -> str:
    """Open a native macOS file dialog and return the selected path."""
    osascript = "/usr/bin/osascript" if os.path.exists("/usr/bin/osascript") else "osascript"

    applescript = (
        'set selectedFile to choose file with prompt "Select a DigitalMicrograph file" '
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

        if _is_supported_dm_file(selected):
            return selected

        print(f"macOS dialog selected unsupported file type: {selected}")
        return ""

    stderr = (result.stderr or "").strip()
    # -128 is the standard AppleScript user-cancel code.
    if "-128" in stderr or "User canceled" in stderr:
        return ""

    if stderr:
        print(f"macOS dialog error: {stderr}")
    return ""
