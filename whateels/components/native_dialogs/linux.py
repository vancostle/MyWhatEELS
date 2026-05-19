import shutil
import subprocess


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
    if shutil.which("zenity"):
        return _run_dialog([
            "zenity",
            "--file-selection",
            "--title=Select a DigitalMicrograph file",
            "--file-filter=DigitalMicrograph files | *.dm3 *.dm4",
            "--file-filter=All files | *",
        ])

    if shutil.which("kdialog"):
        return _run_dialog([
            "kdialog",
            "--getopenfilename",
            "",
            "*.dm3 *.dm4|DigitalMicrograph files\n*|All files",
            "--title",
            "Select a DigitalMicrograph file",
        ])

    if shutil.which("yad"):
        return _run_dialog([
            "yad",
            "--file-selection",
            "--title=Select a DigitalMicrograph file",
            "--file-filter=DigitalMicrograph files (*.dm3 *.dm4) | *.dm3 *.dm4",
            "--file-filter=All files (*) | *",
        ])

    print("No supported Linux dialog backend found (zenity, kdialog, or yad).")
    return ""
