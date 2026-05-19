import subprocess


def open_macos_file_dialog() -> str:
    """Open a native macOS file dialog and return the selected path."""
    applescript = (
        'set selectedFile to choose file with prompt "Select a DigitalMicrograph file" '
        'of type {"dm3", "dm4"} without invisibles and multiple selections allowed false\n'
        'POSIX path of selectedFile'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        print(f"macOS dialog launch failed: {exc}")
        return ""

    if result.returncode == 0:
        return result.stdout.strip()

    stderr = (result.stderr or "").strip()
    # -128 is the standard AppleScript user-cancel code.
    if "-128" in stderr or "User canceled" in stderr:
        return ""

    if stderr:
        print(f"macOS dialog error: {stderr}")
    return ""
