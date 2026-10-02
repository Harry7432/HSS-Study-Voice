"""End-to-end audio orchestrator for the TTS pipeline.

Coordinates :class:`~app.services.audio.renderer.AudioRenderer`,
:class:`~app.services.audio.concatenator.AudioConcatenator`, and
:class:`~app.services.audio.exporter.MP3Exporter` into a single callable
that accepts pre-processed text chunks and returns a final MP3 file with
accompanying metadata.

Temporary WAV segments are always cleaned up, even when errors occur.
"""

from __future__ import annotations

import hashlib
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
from app.services.audio.timeline import (
    SAMPLE_RATE_HZ,
    TimelineAudio,
    TimelineChunk,
    TimelineDocument,
    TimelineSentence,
    timeline_path_for,
)
from app.services.text.models import PreparedDocument

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
        timeline_path: Sibling timeline for synchronized generation, otherwise ``None``.
    """

    output_path: Path
    chunks_count: int
    duration_seconds: float
    file_size_bytes: int
    processing_time_seconds: float
    timeline_path: Path | None = None


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

    def generate_synchronized(
        self,
        document: PreparedDocument,
        output_path: Path,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        bitrate: Optional[str] = None,
    ) -> AudioResult:
        """Generate one MP3 and its exact sentence timeline for one prepared chunk."""
        if len(document.chunks) != 1:
            raise ValueError(
                "Synchronized generation currently requires exactly one prepared chunk"
            )

        effective_voice = voice or settings.DEFAULT_VOICE
        effective_speed = speed if speed is not None else settings.DEFAULT_SPEED
        effective_bitrate = bitrate or settings.MP3_BITRATE
        output_path = Path(output_path)
        timeline_path = timeline_path_for(output_path)
        start_time = time.perf_counter()
        prepared_chunk = document.chunks[0]
        fragments = [
            fragment
            for sentence in prepared_chunk.sentences
            for fragment in sentence.fragments
        ]

        tmp_dir = Path(tempfile.mkdtemp(prefix="tts_phase3_"))
        try:
            rendered_fragments = self._renderer.render_fragments(
                fragments=fragments,
                voice=effective_voice,
                speed=effective_speed,
                temp_dir=tmp_dir,
            )
            wav_paths = [
                Path(
                    rendered.wav_path
                    if getattr(rendered, "wav_path", None) is not None
                    else rendered
                )
                for rendered in rendered_fragments
            ]
            if len(wav_paths) != len(fragments):
                raise ValueError(
                    "Rendered fragment count must equal prepared fragment count"
                )

            frame_counts: list[int] = []
            pcm_format: tuple[int, int, int, str] | None = None
            for wav_path in wav_paths:
                with wave.open(str(wav_path), "rb") as wav_file:
                    current_format = (
                        wav_file.getnchannels(),
                        wav_file.getsampwidth(),
                        wav_file.getframerate(),
                        wav_file.getcomptype(),
                    )
                    if current_format[2] != SAMPLE_RATE_HZ:
                        raise ValueError(
                            f"Rendered WAV sample rate must be {SAMPLE_RATE_HZ} Hz"
                        )
                    if pcm_format is None:
                        pcm_format = current_format
                    elif current_format != pcm_format:
                        raise ValueError(
                            "Rendered WAV segments must use compatible PCM formats"
                        )
                    frame_counts.append(wav_file.getnframes())

            merged_wav = tmp_dir / "merged.wav"
            self._concatenator.concatenate(wav_paths, merged_wav)
            with wave.open(str(merged_wav), "rb") as wav_file:
                merged_format = (
                    wav_file.getnchannels(),
                    wav_file.getsampwidth(),
                    wav_file.getframerate(),
                    wav_file.getcomptype(),
                )
                merged_frame_count = wav_file.getnframes()

            if merged_format != pcm_format:
                raise ValueError("Merged WAV must preserve the segment PCM format")
            if merged_frame_count != sum(frame_counts):
                raise ValueError(
                    "Merged WAV frame count must equal the sum of rendered segments"
                )

            self._exporter.export(
                wav_path=merged_wav,
                output_path=output_path,
                bitrate=effective_bitrate,
            )
            with output_path.open("rb") as mp3_file:
                mp3_sha256 = hashlib.file_digest(mp3_file, "sha256").hexdigest()

            offset = 0
            frame_position = 0
            timeline_sentences: list[TimelineSentence] = []
            for sentence in prepared_chunk.sentences:
                sentence_start = offset
                for _ in sentence.fragments:
                    offset += frame_counts[frame_position]
                    frame_position += 1
                timeline_sentences.append(
                    TimelineSentence(
                        index=sentence.index,
                        text=sentence.text,
                        start_sample=sentence_start,
                        end_sample=offset,
                    )
                )

            timeline = TimelineDocument(
                schema_version=1,
                audio=TimelineAudio(
                    filename=output_path.name,
                    sha256=mp3_sha256,
                    sample_rate_hz=SAMPLE_RATE_HZ,
                    total_samples=merged_frame_count,
                ),
                chunks=(
                    TimelineChunk(
                        index=prepared_chunk.index,
                        start_sample=0,
                        end_sample=merged_frame_count,
                        sentences=tuple(timeline_sentences),
                    ),
                ),
            )
            timeline.write(
                timeline_path,
                merged_frame_count=merged_frame_count,
            )
        finally:
            self._cleanup_temp_dir(tmp_dir)

        elapsed = time.perf_counter() - start_time
        return AudioResult(
            output_path=output_path.resolve(),
            chunks_count=len(document.chunks),
            duration_seconds=round(merged_frame_count / SAMPLE_RATE_HZ, 3),
            file_size_bytes=output_path.stat().st_size,
            processing_time_seconds=round(elapsed, 3),
            timeline_path=timeline_path.resolve(),
        )

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
