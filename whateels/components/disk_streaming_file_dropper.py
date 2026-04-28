import os
import tempfile
from typing import IO, Any

import panel as pn


class DiskStreamingFileDropper(pn.widgets.FileDropper):
    """
    A FileDropper that streams upload chunks directly to a temp file on disk
    instead of accumulating them all in RAM and joining at the end.

    Panel's default FileDropper does:
        file_buffer: bytes = b''.join(all_chunks)   # <-- single contiguous alloc

    For large files (multi-GB) that single allocation causes MemoryError.
    This subclass overrides _process_event to write each chunk to a
    NamedTemporaryFile as it arrives, then stores the file *path* (str)
    as the widget value instead of the raw bytes.

    Downstream code that receives the value must handle both cases:
      - bytes  → small file, classic in-memory upload (Panel default path)
      - str    → large file, path to the temp file on disk
    The temp file is the caller's responsibility to delete after use.
    """

    def __init__(self, **params):
        super().__init__(**params)
        # {filename: open NamedTemporaryFile handle}
        self._stream_handles: dict[str, IO[bytes]] = {}

    def _process_event(self, event: Any) -> None:  # type: ignore[override]
        data: dict[str, Any] = event.data
        name: str = data["name"]

        # ── delete_event ──────────────────────────────────────────────────────
        if event.event_name == "delete_event":
            mime: dict = self.mime_type  # type: ignore[assignment]
            val: dict = self.value       # type: ignore[assignment]
            if name in mime:
                del mime[name]
            if name in val:
                del val[name]
            self.param.trigger("mime_type", "value")
            # Clean up any in-progress temp file for this name
            handle = self._stream_handles.pop(name, None)
            if handle is not None:
                try:
                    handle.close()
                    os.unlink(handle.name)
                except OSError:
                    pass
            return

        # ── upload_event ──────────────────────────────────────────────────────
        chunk_data: bytes = data["data"]

        if data["chunk"] == 1:
            # First chunk: open a new temp file
            suffix = os.path.splitext(name)[1]
            tmp: IO[bytes] = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            self._stream_handles[name] = tmp
            tmp.write(chunk_data)
        else:
            handle = self._stream_handles.get(name)
            if handle is not None:
                handle.write(chunk_data)

        if data["chunk"] != data["total_chunks"]:
            return

        # Last chunk: close the file and hand the path to the value dict
        handle = self._stream_handles.pop(name, None)
        temp_path: str | None = None
        if handle is not None:
            handle.close()
            temp_path = handle.name  # type: ignore[attr-defined]

        if temp_path is not None:
            val = self.value   # type: ignore[assignment]
            val[name] = temp_path  # str path, not bytes
        mime = self.mime_type  # type: ignore[assignment]
        mime[name] = data["type"]
        self.param.trigger("mime_type", "value")
