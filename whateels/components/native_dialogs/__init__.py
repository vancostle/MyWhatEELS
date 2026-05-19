import sys

from .linux import open_linux_file_dialog
from .macos import open_macos_file_dialog
from .windows import open_windows_file_dialog


def open_native_file_dialog() -> str:
    """Open a platform-native file dialog and return the selected path.

    Returns an empty string when canceled or when the current platform
    has no implementation yet.
    """
    if sys.platform == "win32":
        return open_windows_file_dialog()

    if sys.platform == "darwin":
        return open_macos_file_dialog()

    if sys.platform.startswith("linux"):
        return open_linux_file_dialog()

    return ""
