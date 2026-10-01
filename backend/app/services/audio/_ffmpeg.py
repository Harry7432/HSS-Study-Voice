"""Shared FFmpeg binary resolution utility.

Resolution order:
1. If *path_override* is a non-empty string:
   a. Treat it as an absolute path — if the file exists, use it directly.
   b. Otherwise search PATH with ``shutil.which(path_override)``.
   c. If still not found, raise :class:`FFmpegNotFoundError` with the
      configured value in the message so the user knows what was tried.
2. If *path_override* is empty, search PATH for ``"ffmpeg"`` automatically.
3. If nothing is found, raise :class:`FFmpegNotFoundError` with clear
   instructions.

This means:
* New machines — just install FFmpeg and put it on PATH; no config needed.
* Machines with FFmpeg in a non-PATH location — set ``FFMPEG_PATH`` in ``.env``.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class FFmpegNotFoundError(Exception):
    """Raised when the FFmpeg binary cannot be located."""


def resolve_ffmpeg(path_override: str = "") -> str:
    """Return the absolute path to the ``ffmpeg`` executable.

    Args:
        path_override: Value of ``settings.FFMPEG_PATH``.  Empty string
            triggers automatic PATH search.

    Returns:
        Absolute path string to the FFmpeg binary.

    Raises:
        FFmpegNotFoundError: If the binary cannot be found by any means.
    """
    if path_override:
        # 1a. Absolute path that exists on disk — use it directly.
        candidate = Path(path_override)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)

        # 1b. Named binary or relative path — search PATH.
        found = shutil.which(path_override)
        if found:
            return found

        raise FFmpegNotFoundError(
            f"FFmpeg not found at configured path '{path_override}'. "
            "Check the FFMPEG_PATH setting in your .env file."
        )

    # 2. Auto-detect: search PATH for 'ffmpeg'.
    found = shutil.which("ffmpeg")
    if found:
        return found

    raise FFmpegNotFoundError(
        "FFmpeg executable not found on PATH. "
        "Install FFmpeg (https://ffmpeg.org/download.html) and ensure it is "
        "accessible via your system PATH, or set FFMPEG_PATH in .env to "
        "point to the binary directly."
    )
