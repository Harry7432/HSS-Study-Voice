"""Unit tests for AudioOrchestrator.

All collaborators (AudioRenderer, AudioConcatenator, MP3Exporter) are injected
as mocks so these tests run without Piper models or FFmpeg installed.
"""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio.orchestrator import AudioOrchestrator, AudioResult
from app.services.audio.renderer import AudioRenderError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050)  # ~1 second
    return path


def _make_mock_trio(tmp_path: Path):
    """Return (renderer, concatenator, exporter) mocks wired to produce real files."""
    merged_wav = tmp_path / "merged.wav"
    output_mp3 = tmp_path / "output.mp3"

    mock_renderer = MagicMock()
    mock_renderer.render_chunks.return_value = [tmp_path / "chunk_0.wav"]

    mock_cat = MagicMock()

    def _fake_concatenate(wavs, out):
        _make_wav(out)
        return out

    mock_cat.concatenate.side_effect = _fake_concatenate

    mock_exp = MagicMock()

    def _fake_export(wav_path, output_path, bitrate=None):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"ID3" + b"\x00" * 1024)
        return output_path

    mock_exp.export.side_effect = _fake_export

    return mock_renderer, mock_cat, mock_exp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_generate_mp3_returns_audio_result(tmp_path):
    """generate_mp3 returns an AudioResult dataclass."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)
    output = tmp_path / "final.mp3"

    result = orchestrator.generate_mp3(
        chunks=["Primeira frase.", "Segunda frase."],
        output_path=output,
        voice="pt_BR-cadu-medium",
        speed=1.0,
    )

    assert isinstance(result, AudioResult)
    assert result.chunks_count == 2
    assert result.duration_seconds >= 0
    assert result.file_size_bytes > 0
    assert result.processing_time_seconds > 0
    assert result.output_path == output.resolve()


def test_generate_mp3_calls_all_services(tmp_path):
    """All three services are invoked in the correct order."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)

    orchestrator.generate_mp3(
        chunks=["Texto de teste."],
        output_path=tmp_path / "out.mp3",
    )

    renderer.render_chunks.assert_called_once()
    cat.concatenate.assert_called_once()
    exp.export.assert_called_once()


def test_generate_mp3_cleans_up_temp_dir_on_success(tmp_path):
    """Temp directory is removed after a successful run."""
    renderer, cat, exp = _make_mock_trio(tmp_path)

    captured_dirs: list[Path] = []
    original_mkdtemp = __import__("tempfile").mkdtemp

    def _spy_mkdtemp(**kwargs):
        d = original_mkdtemp(**kwargs)
        captured_dirs.append(Path(d))
        return d

    with patch("app.services.audio.orchestrator.tempfile.mkdtemp", side_effect=_spy_mkdtemp):
        orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)
        orchestrator.generate_mp3(chunks=["Teste."], output_path=tmp_path / "out.mp3")

    for d in captured_dirs:
        assert not d.exists(), f"Temp dir was not cleaned up: {d}"


def test_generate_mp3_cleans_up_temp_dir_on_error(tmp_path):
    """Temp directory is removed even when a service raises an exception."""
    renderer = MagicMock()
    renderer.render_chunks.side_effect = AudioRenderError("boom")

    captured_dirs: list[Path] = []
    original_mkdtemp = __import__("tempfile").mkdtemp

    def _spy_mkdtemp(**kwargs):
        d = original_mkdtemp(**kwargs)
        captured_dirs.append(Path(d))
        return d

    with patch("app.services.audio.orchestrator.tempfile.mkdtemp", side_effect=_spy_mkdtemp):
        orchestrator = AudioOrchestrator(renderer=renderer, concatenator=MagicMock(), exporter=MagicMock())
        with pytest.raises(AudioRenderError):
            orchestrator.generate_mp3(chunks=["Texto."], output_path=tmp_path / "out.mp3")

    for d in captured_dirs:
        assert not d.exists(), f"Temp dir leaked after error: {d}"


def test_generate_mp3_passes_voice_and_speed(tmp_path):
    """Custom voice and speed are forwarded to the renderer."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)

    orchestrator.generate_mp3(
        chunks=["Texto."],
        output_path=tmp_path / "out.mp3",
        voice="pt_BR-faber-medium",
        speed=1.25,
    )

    call_kwargs = renderer.render_chunks.call_args.kwargs
    assert call_kwargs["voice"] == "pt_BR-faber-medium"
    assert call_kwargs["speed"] == 1.25
