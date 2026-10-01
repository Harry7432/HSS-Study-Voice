"""WAV segment concatenator using FFmpeg.

Merges an ordered list of WAV files into a single WAV using the FFmpeg
``concat`` demuxer, which avoids re-encoding and is lossless for same-format
inputs.
"""

from __future__ import annotations

import logging
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioConcatError(Exception):
    """Raised when WAV concatenation fails."""


class AudioConcatenator:
    """Concatenate multiple WAV files into one using FFmpeg's concat demuxer.

    Args:
        ffmpeg_path: Path or name of the ``ffmpeg`` executable.  Defaults to
            :data:`settings.FFMPEG_PATH` (``"ffmpeg"``).
    """

    def __init__(self, ffmpeg_path: Optional[str] = None) -> None:
        self._ffmpeg = ffmpeg_path or settings.FFMPEG_PATH

    # ------------------------------------------------------------------ #

    def concatenate(self, wav_paths: list[Path], output_path: Path) -> Path:
        """Merge *wav_paths* into a single WAV at *output_path*.

        When *wav_paths* contains exactly one file the source is copied
        directly, avoiding an unnecessary FFmpeg invocation.

        Args:
            wav_paths: Ordered list of WAV segment paths to merge.
            output_path: Destination path for the merged WAV file.

        Returns:
            *output_path* after the merged file has been written.

        Raises:
            AudioConcatError: If the list is empty, FFmpeg is unavailable, or
                the FFmpeg subprocess exits with a non-zero code.
        """
        if not wav_paths:
            raise AudioConcatError("Cannot concatenate: wav_paths list is empty.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Fast path: single file → plain copy, no FFmpeg needed.
        if len(wav_paths) == 1:
            logger.debug("Single segment — copying directly to %s", output_path)
            shutil.copy2(wav_paths[0], output_path)
            return output_path

        self._assert_ffmpeg_available()

        # Build the concat list in a temporary text file.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as fh:
            concat_list_path = Path(fh.name)
            for wav in wav_paths:
                # FFmpeg concat format requires escaped single-quotes.
                escaped = str(wav.resolve()).replace("'", "'\\''")
                fh.write(f"file '{escaped}'\n")

        try:
            cmd = [
                self._ffmpeg,
                "-y",                        # overwrite without asking
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
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
                raise AudioConcatError(
                    f"FFmpeg concat failed (exit {result.returncode}):\n"
                    f"{result.stderr[-2000:]}"
                )
        finally:
            concat_list_path.unlink(missing_ok=True)

        logger.info(
            "Concatenated %d WAV segments → %s (%.1f KB)",
            len(wav_paths),
            output_path.name,
            output_path.stat().st_size / 1024,
        )
        return output_path

    # ------------------------------------------------------------------ #

    def _assert_ffmpeg_available(self) -> None:
        if not shutil.which(self._ffmpeg):
            raise AudioConcatError(
                f"FFmpeg executable not found: '{self._ffmpeg}'. "
                "Install FFmpeg or set the FFMPEG_PATH environment variable."
            )
