import sys


def open_native_file_dialog() -> str:
    """Open a platform-native file dialog and return the selected path.

    Returns an empty string when canceled or when the current platform
    has no implementation yet.
    """
    if sys.platform == "win32":
        from .windows import open_windows_file_dialog

        return open_windows_file_dialog()

    if sys.platform == "darwin":
        from .macos import open_macos_file_dialog

        return open_macos_file_dialog()

    if sys.platform.startswith("linux"):
        from .linux import open_linux_file_dialog

        return open_linux_file_dialog()

    return ""
