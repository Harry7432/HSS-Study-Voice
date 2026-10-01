"""Unit tests for AudioRenderer.

All tests use mocked PiperProvider so no real voice model is required.
"""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.providers.tts.base import TTSSynthesisError
from app.services.audio.renderer import AudioRenderer, AudioRenderError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_wav(path: Path) -> None:
    """Write a minimal valid WAV file at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 100)


def _make_mock_provider(tmp_path: Path) -> MagicMock:
    """Return a mock PiperProvider whose synthesize() creates real WAV files."""
    mock = MagicMock()

    def _fake_synthesize(text, output_path, voice, speed):
        _make_fake_wav(output_path)
        return output_path

    mock.synthesize.side_effect = _fake_synthesize
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_render_chunks_returns_ordered_paths(tmp_path):
    """render_chunks returns one WAV path per chunk, in order."""
    provider = _make_mock_provider(tmp_path)
    renderer = AudioRenderer(provider=provider)
    chunks = ["Primeiro.", "Segundo.", "Terceiro."]

    result = renderer.render_chunks(
        chunks=chunks,
        voice="pt_BR-cadu-medium",
        speed=1.0,
        temp_dir=tmp_path / "segs",
    )

    assert len(result) == 3
    for path in result:
        assert path.exists()
        assert path.suffix == ".wav"


def test_render_chunks_zero_padded_names(tmp_path):
    """WAV files are named with zero-padded indices matching chunk count."""
    provider = _make_mock_provider(tmp_path)
    renderer = AudioRenderer(provider=provider)
    chunks = [f"Chunk {i}." for i in range(12)]

    result = renderer.render_chunks(
        chunks=chunks,
        voice="pt_BR-cadu-medium",
        speed=1.0,
        temp_dir=tmp_path / "segs",
    )

    names = [p.name for p in result]
    assert names[0] == "chunk_00.wav"
    assert names[9] == "chunk_09.wav"
    assert names[11] == "chunk_11.wav"


def test_render_chunks_empty_list_raises(tmp_path):
    """Empty chunk list raises AudioRenderError immediately."""
    renderer = AudioRenderer(provider=MagicMock())
    with pytest.raises(AudioRenderError, match="empty"):
        renderer.render_chunks([], voice="pt_BR-cadu-medium", speed=1.0, temp_dir=tmp_path)


def test_render_chunks_cleans_up_on_error(tmp_path):
    """When a chunk fails, already-rendered WAVs are removed (cleanup_on_error=True)."""
    call_count = 0
    seg_dir = tmp_path / "segs"

    def _failing_synthesize(text, output_path, voice, speed):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            _make_fake_wav(output_path)
            return output_path
        raise TTSSynthesisError("Simulated failure on chunk 2")

    mock_provider = MagicMock()
    mock_provider.synthesize.side_effect = _failing_synthesize

    renderer = AudioRenderer(provider=mock_provider, cleanup_on_error=True)

    with pytest.raises(AudioRenderError):
        renderer.render_chunks(
            chunks=["Primeiro.", "Segundo."],
            voice="pt_BR-cadu-medium",
            speed=1.0,
            temp_dir=seg_dir,
        )

    # The first (successful) WAV must have been deleted
    remaining = list(seg_dir.glob("*.wav")) if seg_dir.exists() else []
    assert remaining == [], f"Expected no WAVs after cleanup, found: {remaining}"


def test_render_chunks_no_cleanup_on_error_keeps_files(tmp_path):
    """When cleanup_on_error=False, partial WAVs are preserved after failure."""
    call_count = 0
    seg_dir = tmp_path / "segs"

    def _failing_synthesize(text, output_path, voice, speed):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            _make_fake_wav(output_path)
            return output_path
        raise TTSSynthesisError("Simulated failure")

    mock_provider = MagicMock()
    mock_provider.synthesize.side_effect = _failing_synthesize

    renderer = AudioRenderer(provider=mock_provider, cleanup_on_error=False)

    with pytest.raises(AudioRenderError):
        renderer.render_chunks(
            chunks=["Primeiro.", "Segundo."],
            voice="pt_BR-cadu-medium",
            speed=1.0,
            temp_dir=seg_dir,
        )

    remaining = list(seg_dir.glob("*.wav"))
    assert len(remaining) == 1, "Expected the first WAV to be preserved"
