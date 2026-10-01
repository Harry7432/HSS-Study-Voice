"""WAV → MP3 exporter using FFmpeg.

Converts a WAV file to MP3 with the ``libmp3lame`` codec at a configurable
bitrate.  Verifies FFmpeg availability before attempting conversion.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.audio._ffmpeg import FFmpegNotFoundError, resolve_ffmpeg

logger = logging.getLogger(__name__)


class MP3ExportError(Exception):
    """Raised when WAV → MP3 conversion fails."""


class MP3Exporter:
    """Convert a WAV file to MP3 using FFmpeg's ``libmp3lame`` encoder.

    Args:
        ffmpeg_path: Explicit path or name of the ``ffmpeg`` executable.
            Overrides :data:`settings.FFMPEG_PATH` and auto-detection.
            Pass ``None`` (default) to use the standard resolution order:
            ``settings.FFMPEG_PATH`` → ``shutil.which("ffmpeg")``.
        bitrate: MP3 bitrate string (e.g. ``"192k"``).  Defaults to
            :data:`settings.MP3_BITRATE`.
    """

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        bitrate: Optional[str] = None,
    ) -> None:
        self._ffmpeg_override = ffmpeg_path  # None = use settings + auto-detect
        self._bitrate = bitrate or settings.MP3_BITRATE

    # ------------------------------------------------------------------ #

    def export(
        self,
        wav_path: Path,
        output_path: Path,
        bitrate: Optional[str] = None,
    ) -> Path:
        """Convert *wav_path* to an MP3 file at *output_path*.

        Args:
            wav_path: Source WAV file (must exist).
            output_path: Destination ``.mp3`` file path.
            bitrate: Override the instance-level bitrate for this call only.

        Returns:
            *output_path* after the MP3 has been written.

        Raises:
            MP3ExportError: If FFmpeg is unavailable, the source file is
                missing, or conversion fails.
        """
        wav_path = Path(wav_path)
        output_path = Path(output_path)
        effective_bitrate = bitrate or self._bitrate

        # Resolve FFmpeg binary (raises MP3ExportError if not found)
        try:
            override = self._ffmpeg_override if self._ffmpeg_override is not None else settings.FFMPEG_PATH
            ffmpeg = resolve_ffmpeg(override)
        except FFmpegNotFoundError as exc:
            raise MP3ExportError(str(exc)) from exc

        if not wav_path.exists():
            raise MP3ExportError(f"Source WAV not found: {wav_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg,
            "-y",
            "-i", str(wav_path),
            "-codec:a", "libmp3lame",
            "-b:a", effective_bitrate,
            str(output_path),
        ]
        logger.debug("Running: %s", shlex.join(cmd))

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise MP3ExportError(
                f"FFmpeg MP3 export failed (exit {result.returncode}):\n"
                f"{result.stderr[-2000:]}"
            )

        size_kb = output_path.stat().st_size / 1024
        logger.info(
            "Exported MP3: %s  [%s, %.1f KB]",
            output_path.name,
            effective_bitrate,
            size_kb,
        )
        return output_path

