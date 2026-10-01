"""End-to-end audio orchestrator for the TTS pipeline.

Coordinates :class:`~app.services.audio.renderer.AudioRenderer`,
:class:`~app.services.audio.concatenator.AudioConcatenator`, and
:class:`~app.services.audio.exporter.MP3Exporter` into a single callable
that accepts pre-processed text chunks and returns a final MP3 file with
accompanying metadata.

Temporary WAV segments are always cleaned up, even when errors occur.
"""

from __future__ import annotations

import logging
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.audio.concatenator import AudioConcatenator
from app.services.audio.exporter import MP3Exporter
from app.services.audio.renderer import AudioRenderer

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Metadata returned by :meth:`AudioOrchestrator.generate_mp3`.

    Attributes:
        output_path: Absolute path to the generated MP3 file.
        chunks_count: Number of text chunks that were synthesised.
        duration_seconds: Total audio duration in seconds (from the merged WAV).
        file_size_bytes: Size of the final MP3 file in bytes.
        processing_time_seconds: Wall-clock time for the full pipeline.
    """

    output_path: Path
    chunks_count: int
    duration_seconds: float
    file_size_bytes: int
    processing_time_seconds: float


class AudioOrchestrator:
    """Coordinate the full audio pipeline: chunks → WAV segments → MP3.

    All three internal services are injectable via the constructor so the
    orchestrator is straightforward to unit-test with mocks.

    Args:
        renderer: Converts text chunks to WAV files.
        concatenator: Merges WAV segments into a single WAV.
        exporter: Converts the merged WAV to MP3.
    """

    def __init__(
        self,
        renderer: Optional[AudioRenderer] = None,
        concatenator: Optional[AudioConcatenator] = None,
        exporter: Optional[MP3Exporter] = None,
    ) -> None:
        self._renderer = renderer or AudioRenderer()
        self._concatenator = concatenator or AudioConcatenator()
        self._exporter = exporter or MP3Exporter()

    # ------------------------------------------------------------------ #

    def generate_mp3(
        self,
        chunks: list[str],
        output_path: Path,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        bitrate: Optional[str] = None,
    ) -> AudioResult:
        """Run the full pipeline and produce an MP3 file.

        Args:
            chunks: Pre-processed plain-text chunks (output of
                :class:`~app.services.text.pipeline.TextPreprocessingPipeline`).
            output_path: Destination path for the final ``.mp3`` file.
            voice: Piper voice model identifier.  Defaults to
                :data:`settings.DEFAULT_VOICE`.
            speed: Speech speed multiplier.  Defaults to
                :data:`settings.DEFAULT_SPEED`.
            bitrate: MP3 bitrate string.  Defaults to
                :data:`settings.MP3_BITRATE`.

        Returns:
            :class:`AudioResult` with path, duration, size and timing.

        Raises:
            AudioRenderError: If any chunk cannot be synthesised.
            AudioConcatError: If WAV concatenation fails.
            MP3ExportError: If WAV → MP3 conversion fails.
        """
        effective_voice = voice or settings.DEFAULT_VOICE
        effective_speed = speed if speed is not None else settings.DEFAULT_SPEED
        effective_bitrate = bitrate or settings.MP3_BITRATE

        output_path = Path(output_path)
        start_time = time.perf_counter()

        tmp_dir = Path(tempfile.mkdtemp(prefix="tts_phase3_"))
        try:
            # 1. Render chunks → WAV segments
            logger.info(
                "Rendering %d chunk(s) with voice=%s speed=%.2f",
                len(chunks),
                effective_voice,
                effective_speed,
            )
            wav_segments = self._renderer.render_chunks(
                chunks=chunks,
                voice=effective_voice,
                speed=effective_speed,
                temp_dir=tmp_dir,
            )

            # 2. Concatenate WAV segments → merged WAV
            merged_wav = tmp_dir / "merged.wav"
            self._concatenator.concatenate(wav_segments, merged_wav)

            # 3. Read WAV duration before export
            duration = self._get_wav_duration(merged_wav)

            # 4. Export merged WAV → MP3
            self._exporter.export(
                wav_path=merged_wav,
                output_path=output_path,
                bitrate=effective_bitrate,
            )

        finally:
            # Always clean up temporary directory
            self._cleanup_temp_dir(tmp_dir)

        elapsed = time.perf_counter() - start_time
        result = AudioResult(
            output_path=output_path.resolve(),
            chunks_count=len(chunks),
            duration_seconds=round(duration, 3),
            file_size_bytes=output_path.stat().st_size,
            processing_time_seconds=round(elapsed, 3),
        )
        logger.info(
            "MP3 generated: %s | duration=%.1fs size=%d bytes elapsed=%.2fs",
            output_path.name,
            result.duration_seconds,
            result.file_size_bytes,
            result.processing_time_seconds,
        )
        return result

    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_wav_duration(wav_path: Path) -> float:
        """Return the duration of a WAV file in seconds."""
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate if rate > 0 else 0.0

    @staticmethod
    def _cleanup_temp_dir(tmp_dir: Path) -> None:
        """Remove *tmp_dir* and all its contents, ignoring errors."""
        import shutil as _shutil
        try:
            _shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.debug("Cleaned up temp dir: %s", tmp_dir)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to clean up %s: %s", tmp_dir, exc)
