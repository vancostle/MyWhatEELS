import ctypes
from ctypes import wintypes


class _OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", wintypes.LPCWSTR),
        ("lpstrCustomFilter", wintypes.LPWSTR),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", wintypes.LPWSTR),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", wintypes.LPWSTR),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", wintypes.LPCWSTR),
        ("lpstrTitle", wintypes.LPCWSTR),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", wintypes.LPCWSTR),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", wintypes.LPVOID),
        ("lpTemplateName", wintypes.LPCWSTR),
        ("pvReserved", wintypes.LPVOID),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


def open_windows_file_dialog() -> str:
    ofn_file_must_exist = 0x00001000
    ofn_path_must_exist = 0x00000800
    ofn_explorer = 0x00080000
    ofn_hide_readonly = 0x00000004

    file_buffer = ctypes.create_unicode_buffer(65536)
    filter_value = "DigitalMicrograph (*.dm3;*.dm4)\0*.dm3;*.dm4\0All files (*.*)\0*.*\0\0"

    ofn = _OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(_OPENFILENAMEW)
    ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    ofn.lpstrFilter = filter_value
    ofn.nFilterIndex = 1
    ofn.lpstrFile = ctypes.cast(file_buffer, wintypes.LPWSTR)
    ofn.nMaxFile = len(file_buffer)
    ofn.lpstrTitle = "Select a DigitalMicrograph file"
    ofn.Flags = ofn_explorer | ofn_file_must_exist | ofn_path_must_exist | ofn_hide_readonly

    selected = ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
    if selected:
        return file_buffer.value.strip()

    error_code = ctypes.windll.comdlg32.CommDlgExtendedError()
    if error_code != 0:
        print(f"Win32 dialog error code: {error_code}")
    return ""
