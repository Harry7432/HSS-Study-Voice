"""Unit tests for AudioConcatenator.

Uses mocked subprocess and the shared _ffmpeg resolver so no real FFmpeg
is required.  The correct patch target is ``app.services.audio._ffmpeg.shutil``
because that is where ``shutil.which`` is now called.
"""

from __future__ import annotations

import shutil
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio.concatenator import AudioConcatenator, AudioConcatError

# Patch target: shutil lives inside the _ffmpeg helper module
_WHICH_TARGET = "app.services.audio._ffmpeg.shutil.which"
_RUN_TARGET = "app.services.audio.concatenator.subprocess.run"


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
    """A single WAV is copied directly — no FFmpeg resolution is attempted."""
    src = _make_wav(tmp_path / "chunk_0.wav")
    dst = tmp_path / "merged.wav"

    # No patch needed: single-file path never calls _assert_ffmpeg_available
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
        patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"),
        patch(_RUN_TARGET) as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        dst.write_bytes(b"fake")  # simulate ffmpeg output

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
        patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"),
        patch(_RUN_TARGET) as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stderr="codec error")

        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        with pytest.raises(AudioConcatError, match="FFmpeg concat failed"):
            cat.concatenate(wavs, dst)


def test_concatenate_ffmpeg_not_found_raises(tmp_path):
    """Missing FFmpeg binary raises AudioConcatError before any subprocess."""
    wavs = [_make_wav(tmp_path / f"chunk_{i}.wav") for i in range(2)]

    with patch(_WHICH_TARGET, return_value=None):
        cat = AudioConcatenator(ffmpeg_path="ffmpeg")
        with pytest.raises(AudioConcatError, match="not found"):
            cat.concatenate(wavs, tmp_path / "out.wav")
