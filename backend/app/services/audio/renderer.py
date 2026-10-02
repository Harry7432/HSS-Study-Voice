"""WAV segment renderer for TTS audio pipeline.

Renders each text chunk into a numbered WAV file using :class:`PiperProvider`,
storing all segments in a caller-supplied temporary directory.
"""

from __future__ import annotations

import logging
import wave
from dataclasses import replace
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.providers.tts.base import TTSSynthesisError
from app.providers.tts.piper_provider import PiperProvider
from app.services.text.models import SynthesisFragment

logger = logging.getLogger(__name__)


class AudioRenderError(TTSSynthesisError):
    """Raised when one or more chunks fail to render as WAV audio."""


class AudioRenderer:
    """Synthesize a list of text chunks into individual WAV segment files.

    Args:
        provider: A :class:`PiperProvider` instance.  Defaults to a fresh
            instance using :data:`settings.VOICES_DIR`.
        cleanup_on_error: When ``True`` (default), already-rendered WAV files
            are deleted if any chunk fails so the caller receives a clean state.
    """

    def __init__(
        self,
        provider: Optional[PiperProvider] = None,
        cleanup_on_error: bool = True,
    ) -> None:
        self._provider = provider or PiperProvider()
        self._cleanup_on_error = cleanup_on_error

    def render_chunks(
        self,
        chunks: list[str],
        voice: str,
        speed: float,
        temp_dir: Path,
    ) -> list[Path]:
        """Render each text chunk to a zero-padded WAV file in *temp_dir*.

        Files are named ``chunk_0000.wav``, ``chunk_0001.wav``, … so that
        alphabetical and numeric ordering are identical.

        Args:
            chunks: Non-empty plain-text strings (output of the text pipeline).
            voice: Piper voice model identifier (e.g. ``"pt_BR-cadu-medium"``).
            speed: Speech speed multiplier (1.0 = normal).
            temp_dir: Existing directory where WAV segments are written.

        Returns:
            Ordered list of :class:`~pathlib.Path` objects pointing to the
            generated WAV files.

        Raises:
            AudioRenderError: If *chunks* is empty or any segment fails to
                synthesize.
        """
        if not chunks:
            raise AudioRenderError("Cannot render audio: chunk list is empty.")

        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        width = len(str(len(chunks) - 1))  # zero-pad width
        rendered: list[Path] = []

        try:
            for idx, chunk in enumerate(chunks):
                wav_name = f"chunk_{idx:0{width}d}.wav"
                wav_path = temp_dir / wav_name
                logger.debug("Rendering chunk %d/%d → %s", idx + 1, len(chunks), wav_name)
                self._provider.synthesize(
                    text=chunk,
                    output_path=wav_path,
                    voice=voice,
                    speed=speed,
                )
                rendered.append(wav_path)
        except TTSSynthesisError as exc:
            if self._cleanup_on_error:
                for wav in rendered:
                    wav.unlink(missing_ok=True)
            raise AudioRenderError(
                f"Failed to render chunk {idx + 1}/{len(chunks)}: {exc}"
            ) from exc

        logger.info("Rendered %d WAV segments to %s", len(rendered), temp_dir)
        return rendered

    def render_fragments(
        self,
        fragments: list[SynthesisFragment],
        voice: str,
        speed: float,
        temp_dir: Path,
    ) -> list[SynthesisFragment]:
        """Render and measure synthesis fragments in their input order."""
        if not fragments:
            raise AudioRenderError("Cannot render audio: fragment list is empty.")

        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        width = len(str(len(fragments) - 1))
        rendered: list[SynthesisFragment] = []
        generated_paths: list[Path] = []

        try:
            for idx, fragment in enumerate(fragments):
                wav_path = temp_dir / f"fragment_{idx:0{width}d}.wav"
                generated_paths.append(wav_path)
                self._provider.synthesize(
                    text=fragment.text,
                    output_path=wav_path,
                    voice=voice,
                    speed=speed,
                )
                with wave.open(str(wav_path), "rb") as wav_file:
                    frame_count = wav_file.getnframes()
                if frame_count <= 0:
                    raise wave.Error("Rendered WAV contains no frames")
                rendered.append(
                    replace(
                        fragment,
                        wav_path=wav_path,
                        frame_count=frame_count,
                    )
                )
        except (TTSSynthesisError, OSError, EOFError, wave.Error) as exc:
            if self._cleanup_on_error:
                for wav_path in generated_paths:
                    wav_path.unlink(missing_ok=True)
            raise AudioRenderError(
                f"Failed to render fragment {idx + 1}/{len(fragments)}: {exc}"
            ) from exc

        logger.info("Rendered %d WAV fragments to %s", len(rendered), temp_dir)
        return rendered
