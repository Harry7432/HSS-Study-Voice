"""Unit tests for AudioConcatenator.

Uses mocked subprocess and shutil so no real FFmpeg is required.
"""

from __future__ import annotations

import shutil
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio.concatenator import AudioConcatenator, AudioConcatError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 100)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_concatenate_empty_list_raises(tmp_path):
    """Empty wav_paths list raises AudioConcatError."""
    cat = AudioConcatenator(ffmpeg_path="ffmpeg")
    with pytest.raises(AudioConcatError, match="empty"):
        cat.concatenate([], tmp_path / "out.wav")


def test_concatenate_single_file_copies_without_ffmpeg(tmp_path):
    """A single WAV is copied directly, no FFmpeg subprocess is spawned."""
    src = _make_wav(tmp_path / "chunk_0.wav")
    dst = tmp_path / "merged.wav"

    # Patch shutil.which so ffmpeg appears missing — single-file path must not call it
    with patch("app.services.audio.concatenator.shutil.which", return_value=None):
        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        result = cat.concatenate([src], dst)

    assert result == dst
    assert dst.exists()
    assert dst.stat().st_size == src.stat().st_size


def test_concatenate_multiple_files_calls_ffmpeg(tmp_path):
    """Multiple WAVs trigger an FFmpeg subprocess call."""
    wavs = [_make_wav(tmp_path / f"chunk_{i}.wav") for i in range(3)]
    dst = tmp_path / "merged.wav"

    with (
        patch("app.services.audio.concatenator.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("app.services.audio.concatenator.subprocess.run") as mock_run,
    ):
        # Simulate ffmpeg creating the output file
        mock_run.return_value = MagicMock(returncode=0)
        dst.write_bytes(b"fake")  # make it appear created

        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        result = cat.concatenate(wavs, dst)

    mock_run.assert_called_once()
    cmd_args = mock_run.call_args[0][0]
    assert "-f" in cmd_args
    assert "concat" in cmd_args
    assert str(dst) in cmd_args


def test_concatenate_ffmpeg_failure_raises(tmp_path):
    """Non-zero FFmpeg exit code raises AudioConcatError."""
    wavs = [_make_wav(tmp_path / f"chunk_{i}.wav") for i in range(2)]
    dst = tmp_path / "merged.wav"

    with (
        patch("app.services.audio.concatenator.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("app.services.audio.concatenator.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stderr="codec error")

        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        with pytest.raises(AudioConcatError, match="FFmpeg concat failed"):
            cat.concatenate(wavs, dst)


def test_concatenate_ffmpeg_not_found_raises(tmp_path):
    """Missing FFmpeg binary raises AudioConcatError before any subprocess."""
    wavs = [_make_wav(tmp_path / f"chunk_{i}.wav") for i in range(2)]

    with patch("app.services.audio.concatenator.shutil.which", return_value=None):
        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        with pytest.raises(AudioConcatError, match="not found"):
            cat.concatenate(wavs, tmp_path / "out.wav")
