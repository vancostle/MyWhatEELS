import logging
import os
import struct
import tempfile
from typing import IO, Any

import panel as pn

_log = logging.getLogger(__name__)


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
        # {filename: total bytes written so far}
        self._bytes_written: dict[str, int] = {}
        # {filename: set of received chunk numbers}
        self._received_chunks: dict[str, set[int]] = {}

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
            handle = self._stream_handles.pop(name, None)
            if handle is not None:
                try:
                    handle.close()
                    os.unlink(handle.name)
                except OSError:
                    pass
            self._received_chunks.pop(name, None)
            self._bytes_written.pop(name, None)
            return

        # ── upload_event ──────────────────────────────────────────────────────
        chunk_data: bytes = data["data"]
        chunk_number: int = data.get("chunk", -1)
        total_chunks: int = data.get("total_chunks", -1)

        if chunk_number == 1:
            # First chunk: discard any stale handle for this name (e.g. aborted upload)
            stale = self._stream_handles.pop(name, None)
            if stale is not None:
                try:
                    stale.close()
                    os.unlink(stale.name)
                except OSError:
                    pass
            self._bytes_written[name] = 0
            self._received_chunks[name] = set()
            suffix = os.path.splitext(name)[1]
            tmp: IO[bytes] = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            self._stream_handles[name] = tmp
            _log.info("[DiskStreamer] Started streaming '%s' → %s  total_chunks=%d", name, tmp.name, total_chunks)

        handle: IO[bytes] | None = self._stream_handles.get(name)
        if handle is not None:
            n = handle.write(chunk_data)
            self._bytes_written[name] = self._bytes_written.get(name, 0) + (
                n if n is not None else len(chunk_data)
            )
        else:
            _log.error("[DiskStreamer] No open handle for '%s' at chunk %d – chunk lost!", name, chunk_number)

        self._received_chunks.setdefault(name, set()).add(chunk_number)

        _log.debug(
            "[DiskStreamer] chunk %d/%d  size=%d  file='%s'",
            chunk_number, total_chunks, len(chunk_data), name,
        )

        if chunk_number != total_chunks:
            return

        # ── Last chunk: finalise ──────────────────────────────────────────────
        handle = self._stream_handles.pop(name, None)
        temp_path: str | None = None
        if handle is not None:
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            temp_path = handle.name  # type: ignore[attr-defined]

        # Verify all chunks arrived
        received = self._received_chunks.pop(name, set())
        missing = set(range(1, total_chunks + 1)) - received
        if missing:
            _log.error("[DiskStreamer] '%s' missing chunks: %s", name, sorted(missing))
        else:
            _log.info("[DiskStreamer] '%s' all %d chunks received", name, total_chunks)

        if temp_path is not None:
            expected = self._bytes_written.pop(name, None)
            on_disk = os.path.getsize(temp_path)
            _log.info(
                "[DiskStreamer] %s → temp=%s  bytes_written=%s  on_disk=%s  match=%s",
                name, temp_path, expected, on_disk,
                (expected is None or expected == on_disk),
            )
            # DM header sanity log (bytes 4-11 = file_length = total_size - 16)
            if os.path.splitext(name)[1].lower() in {".dm3", ".dm4"}:
                try:
                    with open(temp_path, "rb") as fh:
                        raw = fh.read(12)
                    if len(raw) >= 12:
                        dm_version = struct.unpack(">I", raw[0:4])[0]
                        if dm_version == 3:
                            dm_body = struct.unpack(">I", raw[4:8])[0]
                        elif dm_version == 4:
                            dm_body = struct.unpack(">Q", raw[4:12])[0]
                        else:
                            dm_body = None
                        if dm_body is not None:
                            dm_total = dm_body + 16  # header field excludes first 16 bytes
                            _log.info(
                                "[DiskStreamer] DM%d header: body_field=%d  total_expected=%d  on_disk=%d  delta=%d",
                                dm_version, dm_body, dm_total, on_disk, on_disk - dm_total,
                            )
                except Exception as exc:
                    _log.warning("[DiskStreamer] header check failed: %s", exc)

            val = self.value   # type: ignore[assignment]
            val[name] = temp_path  # str path, not bytes
        mime = self.mime_type  # type: ignore[assignment]
        mime[name] = data["type"]
        self.param.trigger("mime_type", "value")
