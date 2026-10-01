"""Unit tests for MP3Exporter.

All tests mock subprocess and the shared _ffmpeg resolver so no real FFmpeg
is required.  The correct patch target is ``app.services.audio._ffmpeg.shutil``
because that is where ``shutil.which`` is now called.
"""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio.exporter import MP3Exporter, MP3ExportError

# Patch target: shutil lives inside the _ffmpeg helper module
_WHICH_TARGET = "app.services.audio._ffmpeg.shutil.which"
_RUN_TARGET = "app.services.audio.exporter.subprocess.run"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 200)
    return path


def _fake_ffmpeg_run(cmd, **kwargs):
    """Simulate a successful FFmpeg run that creates the output file."""
    out = Path(cmd[-1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"ID3" + b"\x00" * 512)  # minimal fake MP3
    return MagicMock(returncode=0, stderr="")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_export_calls_ffmpeg_with_correct_args(tmp_path):
    """export() invokes FFmpeg with -codec:a libmp3lame and the given bitrate."""
    src = _make_wav(tmp_path / "merged.wav")
    dst = tmp_path / "output.mp3"

    with (
        patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"),
        patch(_RUN_TARGET, side_effect=_fake_ffmpeg_run) as mock_run,
    ):
        exporter = MP3Exporter(ffmpeg_path="ffmpeg", bitrate="128k")
        exporter.export(src, dst)

    cmd = mock_run.call_args[0][0]
    assert "-codec:a" in cmd
    assert "libmp3lame" in cmd
    assert "-b:a" in cmd
    assert "128k" in cmd
    assert str(dst) in cmd


def test_export_bitrate_override(tmp_path):
    """Per-call bitrate overrides the instance-level default."""
    src = _make_wav(tmp_path / "merged.wav")
    dst = tmp_path / "output.mp3"

    with (
        patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"),
        patch(_RUN_TARGET, side_effect=_fake_ffmpeg_run) as mock_run,
    ):
        exporter = MP3Exporter(ffmpeg_path="ffmpeg", bitrate="192k")
        exporter.export(src, dst, bitrate="64k")  # override

    cmd = mock_run.call_args[0][0]
    assert "64k" in cmd
    assert "192k" not in cmd


def test_export_ffmpeg_not_found_raises(tmp_path):
    """Missing FFmpeg binary raises MP3ExportError before calling subprocess."""
    src = _make_wav(tmp_path / "merged.wav")

    with patch(_WHICH_TARGET, return_value=None):
        exporter = MP3Exporter(ffmpeg_path="ffmpeg")
        with pytest.raises(MP3ExportError, match="not found"):
            exporter.export(src, tmp_path / "out.mp3")


def test_export_missing_wav_raises(tmp_path):
    """Non-existent source WAV raises MP3ExportError."""
    with patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"):
        exporter = MP3Exporter(ffmpeg_path="ffmpeg")
        with pytest.raises(MP3ExportError, match="not found"):
            exporter.export(tmp_path / "ghost.wav", tmp_path / "out.mp3")


def test_export_ffmpeg_failure_raises(tmp_path):
    """Non-zero FFmpeg exit code raises MP3ExportError."""
    src = _make_wav(tmp_path / "merged.wav")

    with (
        patch(_WHICH_TARGET, return_value="/usr/bin/ffmpeg"),
        patch(_RUN_TARGET) as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stderr="encode error")

        exporter = MP3Exporter(ffmpeg_path="ffmpeg")
        with pytest.raises(MP3ExportError, match="MP3 export failed"):
            exporter.export(src, tmp_path / "out.mp3")
