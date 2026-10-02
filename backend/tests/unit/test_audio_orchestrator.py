"""Unit tests for AudioOrchestrator.

All collaborators (AudioRenderer, AudioConcatenator, MP3Exporter) are injected
as mocks so these tests run without Piper models or FFmpeg installed.
"""

from __future__ import annotations

import json
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


@dataclass(frozen=True)
class _PreparedFragment:
    index: int
    text: str


@dataclass(frozen=True)
class _PreparedSentence:
    index: int
    text: str
    fragments: tuple[_PreparedFragment, ...]


@dataclass(frozen=True)
class _PreparedChunk:
    index: int
    sentences: tuple[_PreparedSentence, ...]


@dataclass(frozen=True)
class _PreparedDocument:
    chunks: tuple[_PreparedChunk, ...]


def _make_prepared_document() -> _PreparedDocument:
    return _PreparedDocument(
        chunks=(
            _PreparedChunk(
                index=0,
                sentences=(
                    _PreparedSentence(
                        index=0,
                        text="Alpha beta.",
                        fragments=(
                            _PreparedFragment(index=0, text="Alpha"),
                            _PreparedFragment(index=1, text="beta."),
                        ),
                    ),
                    _PreparedSentence(
                        index=1,
                        text="Gamma.",
                        fragments=(
                            _PreparedFragment(index=0, text="Gamma."),
                        ),
                    ),
                ),
            ),
        ),
    )


def _make_synchronized_mock_trio(
    tmp_path: Path,
    wav_builder,
    *,
    merged_frame_count=None,
):
    frame_counts = (7, 11, 13)
    events = []
    rendered_paths = [
        tmp_path / f"fragment_{index}.wav"
        for index in range(len(frame_counts))
    ]

    renderer = MagicMock()

    def _fake_render_fragments(*, fragments, voice, speed, temp_dir):
        del fragments, voice, speed
        events.append("render")
        paths = []
        for path, frame_count in zip(rendered_paths, frame_counts, strict=True):
            paths.append(
                wav_builder(
                    Path(temp_dir) / path.name,
                    frame_count=frame_count,
                )
            )
        return paths

    renderer.render_fragments.side_effect = _fake_render_fragments

    concatenator = MagicMock()

    def _fake_concatenate(wavs, output_path):
        events.append("concatenate")
        assert [path.name for path in wavs] == [path.name for path in rendered_paths]
        return wav_builder(
            output_path,
            frame_count=(
                sum(frame_counts)
                if merged_frame_count is None
                else merged_frame_count
            ),
        )

    concatenator.concatenate.side_effect = _fake_concatenate

    exporter = MagicMock()

    def _fake_export(wav_path, output_path, bitrate=None):
        del wav_path, bitrate
        events.append("export")
        output_path.write_bytes(b"ID3-synchronized")
        return output_path

    exporter.export.side_effect = _fake_export
    return renderer, concatenator, exporter, events


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


def test_generate_synchronized_renders_fragments_in_document_order(
    tmp_path,
    wav_builder,
):
    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    orchestrator.generate_synchronized(
        document=_make_prepared_document(),
        output_path=tmp_path / "lesson.mp3",
    )

    fragments = renderer.render_fragments.call_args.kwargs["fragments"]
    assert [fragment.text for fragment in fragments] == [
        "Alpha",
        "beta.",
        "Gamma.",
    ]
    concatenator.concatenate.assert_called_once()


def test_generate_synchronized_uses_actual_wav_frames_for_sentence_ranges(
    tmp_path,
    wav_builder,
):
    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    result = orchestrator.generate_synchronized(
        document=_make_prepared_document(),
        output_path=tmp_path / "lesson.mp3",
    )

    timeline = json.loads(result.timeline_path.read_text(encoding="utf-8"))
    assert timeline["audio"]["total_samples"] == 31
    assert [
        (sentence["start_sample"], sentence["end_sample"])
        for sentence in timeline["chunks"][0]["sentences"]
    ] == [(0, 18), (18, 31)]


def test_generate_synchronized_rejects_merged_wav_frame_mismatch(
    tmp_path,
    wav_builder,
):
    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
        merged_frame_count=30,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    with pytest.raises(ValueError):
        orchestrator.generate_synchronized(
            document=_make_prepared_document(),
            output_path=tmp_path / "lesson.mp3",
        )

    exporter.export.assert_not_called()


def test_generate_synchronized_rejects_incompatible_fragment_wavs(
    tmp_path,
    wav_builder,
):
    renderer = MagicMock()

    def _fake_render_fragments(*, fragments, voice, speed, temp_dir):
        del fragments, voice, speed
        return [
            wav_builder(Path(temp_dir) / "fragment_0.wav", frame_count=7),
            wav_builder(
                Path(temp_dir) / "fragment_1.wav",
                frame_count=11,
                channels=2,
            ),
            wav_builder(Path(temp_dir) / "fragment_2.wav", frame_count=13),
        ]

    renderer.render_fragments.side_effect = _fake_render_fragments
    concatenator = MagicMock()
    exporter = MagicMock()
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    with pytest.raises(ValueError, match="compatible PCM formats"):
        orchestrator.generate_synchronized(
            document=_make_prepared_document(),
            output_path=tmp_path / "lesson.mp3",
        )

    concatenator.concatenate.assert_not_called()
    exporter.export.assert_not_called()


def test_generate_synchronized_exports_one_mp3_and_returns_timeline_path(
    tmp_path,
    wav_builder,
):
    renderer, concatenator, exporter, events = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )
    output_path = tmp_path / "lesson.mp3"

    result = orchestrator.generate_synchronized(
        document=_make_prepared_document(),
        output_path=output_path,
    )

    exporter.export.assert_called_once()
    merged_wav = concatenator.concatenate.call_args.args[1]
    assert exporter.export.call_args.kwargs["wav_path"] == merged_wav
    assert events == ["render", "concatenate", "export"]
    assert result.timeline_path == (tmp_path / "lesson.timeline.json").resolve()
    assert result.timeline_path.is_file()
