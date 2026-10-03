"""Unit tests for AudioOrchestrator.

All collaborators (AudioRenderer, AudioConcatenator, MP3Exporter) are injected
as mocks so these tests run without Piper models or FFmpeg installed.
"""

from __future__ import annotations

import inspect
import json
import wave
from dataclasses import dataclass, fields
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
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


# ---------------------------------------------------------------------------
# T026: Regression tests — legacy generate_mp3()/AudioResult contract
# ---------------------------------------------------------------------------

def test_generate_mp3_signature_unchanged():
    """The legacy generate_mp3() parameter names, order and defaults are untouched."""
    params = inspect.signature(AudioOrchestrator.generate_mp3).parameters
    assert list(params) == [
        "self",
        "chunks",
        "output_path",
        "voice",
        "speed",
        "bitrate",
    ]
    assert params["voice"].default is None
    assert params["speed"].default is None
    assert params["bitrate"].default is None


def test_audio_result_preserves_existing_fields_and_adds_optional_timeline_path():
    """AudioResult keeps every pre-existing field and only adds an optional one."""
    field_names = [f.name for f in fields(AudioResult)]
    assert field_names == [
        "output_path",
        "chunks_count",
        "duration_seconds",
        "file_size_bytes",
        "processing_time_seconds",
        "timeline_path",
    ]
    timeline_field = next(f for f in fields(AudioResult) if f.name == "timeline_path")
    assert timeline_field.default is None


def test_generate_mp3_result_has_no_timeline_path_for_legacy_flow(tmp_path):
    """generate_mp3() (the non-synchronized flow) never populates timeline_path."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)

    result = orchestrator.generate_mp3(
        chunks=["Texto de teste."],
        output_path=tmp_path / "out.mp3",
    )

    assert result.timeline_path is None


def test_generate_mp3_forwards_bitrate_to_exporter(tmp_path):
    """A custom bitrate argument is forwarded to the exporter unchanged."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)

    orchestrator.generate_mp3(
        chunks=["Texto."],
        output_path=tmp_path / "out.mp3",
        bitrate="320k",
    )

    call_kwargs = exp.export.call_args.kwargs
    assert call_kwargs["bitrate"] == "320k"


def test_generate_mp3_uses_settings_defaults_when_voice_speed_bitrate_omitted(tmp_path):
    """Omitted voice/speed/bitrate fall back to the existing settings defaults."""
    renderer, cat, exp = _make_mock_trio(tmp_path)
    orchestrator = AudioOrchestrator(renderer=renderer, concatenator=cat, exporter=exp)

    orchestrator.generate_mp3(
        chunks=["Texto."],
        output_path=tmp_path / "out.mp3",
    )

    render_kwargs = renderer.render_chunks.call_args.kwargs
    assert render_kwargs["voice"] == settings.DEFAULT_VOICE
    assert render_kwargs["speed"] == settings.DEFAULT_SPEED
    export_kwargs = exp.export.call_args.kwargs
    assert export_kwargs["bitrate"] == settings.MP3_BITRATE


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


def _make_multi_chunk_prepared_document() -> _PreparedDocument:
    return _PreparedDocument(
        chunks=(
            _PreparedChunk(
                index=0,
                sentences=(
                    _PreparedSentence(
                        index=0,
                        text="Primeiro chunk primeira frase.",
                        fragments=(
                            _PreparedFragment(index=0, text="Primeiro chunk"),
                            _PreparedFragment(index=1, text="primeira frase."),
                        ),
                    ),
                    _PreparedSentence(
                        index=1,
                        text="Primeiro chunk segunda frase.",
                        fragments=(
                            _PreparedFragment(index=0, text="Primeiro chunk segunda frase."),
                        ),
                    ),
                ),
            ),
            _PreparedChunk(
                index=1,
                sentences=(
                    _PreparedSentence(
                        index=0,
                        text="Segundo chunk frase unica.",
                        fragments=(
                            _PreparedFragment(index=0, text="Segundo chunk frase unica."),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_generate_synchronized_supports_multiple_chunks_and_fragmented_sentences(
    tmp_path,
    wav_builder,
):
    frame_counts = (7, 11, 13, 17)
    rendered_paths = [
        tmp_path / f"fragment_{index}.wav"
        for index in range(len(frame_counts))
    ]

    renderer = MagicMock()

    def _fake_render_fragments(*, fragments, voice, speed, temp_dir):
        del fragments, voice, speed
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
        assert [path.name for path in wavs] == [path.name for path in rendered_paths]
        return wav_builder(
            output_path,
            frame_count=sum(frame_counts),
        )

    concatenator.concatenate.side_effect = _fake_concatenate

    exporter = MagicMock()

    def _fake_export(wav_path, output_path, bitrate=None):
        del wav_path, bitrate
        output_path.write_bytes(b"ID3-multi-chunk")
        return output_path

    exporter.export.side_effect = _fake_export

    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )
    doc = _make_multi_chunk_prepared_document()
    output_path = tmp_path / "multi_chunk_lesson.mp3"

    result = orchestrator.generate_synchronized(
        document=doc,
        output_path=output_path,
    )

    assert result.chunks_count == 2
    assert result.timeline_path == (tmp_path / "multi_chunk_lesson.timeline.json").resolve()
    assert result.timeline_path.is_file()

    timeline = json.loads(result.timeline_path.read_text(encoding="utf-8"))
    assert timeline["audio"]["total_samples"] == 48
    assert len(timeline["chunks"]) == 2

    chunk_0 = timeline["chunks"][0]
    assert chunk_0["index"] == 0
    assert chunk_0["start_sample"] == 0
    assert chunk_0["end_sample"] == 31
    assert [
        (s["index"], s["start_sample"], s["end_sample"])
        for s in chunk_0["sentences"]
    ] == [(0, 0, 18), (1, 18, 31)]

    chunk_1 = timeline["chunks"][1]
    assert chunk_1["index"] == 1
    assert chunk_1["start_sample"] == 31
    assert chunk_1["end_sample"] == 48
    assert [
        (s["index"], s["start_sample"], s["end_sample"])
        for s in chunk_1["sentences"]
    ] == [(0, 31, 48)]


def test_generate_synchronized_pre_commit_failure_preserves_prior_state(
    tmp_path,
    wav_builder,
):
    output_mp3 = tmp_path / "lesson.mp3"
    output_timeline = tmp_path / "lesson.timeline.json"
    output_mp3.write_bytes(b"prior_mp3_content")
    output_timeline.write_bytes(b"prior_timeline_content")

    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    exporter.export.side_effect = RuntimeError("Export failed in pre-commit")

    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    with pytest.raises(RuntimeError, match="Export failed"):
        orchestrator.generate_synchronized(
            document=_make_prepared_document(),
            output_path=output_mp3,
        )

    assert output_mp3.read_bytes() == b"prior_mp3_content"
    assert output_timeline.read_bytes() == b"prior_timeline_content"
    remaining_files = [p.name for p in tmp_path.iterdir() if p.name.startswith(".")]
    assert not remaining_files, f"Staging or backup files leaked: {remaining_files}"


def test_generate_synchronized_first_replace_failure_rolls_back_prior_state(
    tmp_path,
    wav_builder,
):
    output_mp3 = tmp_path / "lesson.mp3"
    output_timeline = tmp_path / "lesson.timeline.json"
    output_mp3.write_bytes(b"prior_mp3_content")
    output_timeline.write_bytes(b"prior_timeline_content")

    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    original_replace = Path.replace

    def _failing_replace(self_path, target_path):
        src = Path(self_path)
        if Path(target_path) == output_mp3 and ".tmp" in src.name:
            raise OSError("First replace (MP3) failed")
        return original_replace(self_path, target_path)

    with patch.object(Path, "replace", autospec=True, side_effect=_failing_replace):
        with pytest.raises(OSError, match="First replace"):
            orchestrator.generate_synchronized(
                document=_make_prepared_document(),
                output_path=output_mp3,
            )

    assert output_mp3.read_bytes() == b"prior_mp3_content"
    assert output_timeline.read_bytes() == b"prior_timeline_content"


def test_generate_synchronized_second_replace_failure_compensating_rollback_restores_prior_state(
    tmp_path,
    wav_builder,
):
    output_mp3 = tmp_path / "lesson.mp3"
    output_timeline = tmp_path / "lesson.timeline.json"
    output_mp3.write_bytes(b"prior_mp3_content")
    output_timeline.write_bytes(b"prior_timeline_content")

    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    original_replace = Path.replace

    def _failing_second_replace(self_path, target_path):
        src = Path(self_path)
        if Path(target_path) == output_timeline and ".tmp" in src.name:
            raise OSError("Second replace (Timeline) failed")
        return original_replace(self_path, target_path)


    with patch.object(Path, "replace", autospec=True, side_effect=_failing_second_replace):
        with pytest.raises(OSError, match="Second replace"):
            orchestrator.generate_synchronized(
                document=_make_prepared_document(),
                output_path=output_mp3,
            )

    assert output_mp3.read_bytes() == b"prior_mp3_content"
    assert output_timeline.read_bytes() == b"prior_timeline_content"


def test_generate_synchronized_second_replace_failure_without_prior_state_removes_partial_mp3(
    tmp_path,
    wav_builder,
):
    output_mp3 = tmp_path / "lesson.mp3"
    output_timeline = tmp_path / "lesson.timeline.json"

    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    original_replace = Path.replace

    def _failing_second_replace(self_path, target_path):
        if Path(target_path) == output_timeline:
            raise OSError("Second replace (Timeline) failed without prior state")
        return original_replace(self_path, target_path)

    with patch.object(Path, "replace", autospec=True, side_effect=_failing_second_replace):
        with pytest.raises(OSError, match="Second replace"):
            orchestrator.generate_synchronized(
                document=_make_prepared_document(),
                output_path=output_mp3,
            )

    assert not output_mp3.exists()
    assert not output_timeline.exists()


def test_generate_synchronized_rollback_failure_retains_recovery_backups(
    tmp_path,
    wav_builder,
):
    from app.services.audio.orchestrator import AudioRollbackError

    output_mp3 = tmp_path / "lesson.mp3"
    output_timeline = tmp_path / "lesson.timeline.json"
    output_mp3.write_bytes(b"prior_mp3_content")
    output_timeline.write_bytes(b"prior_timeline_content")

    renderer, concatenator, exporter, _ = _make_synchronized_mock_trio(
        tmp_path,
        wav_builder,
    )
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=concatenator,
        exporter=exporter,
    )

    original_replace = Path.replace

    def _triple_failing_replace(self_path, target_path):
        target = Path(target_path)
        src = Path(self_path)
        if target == output_timeline and not ".bak" in src.name:
            raise OSError("Second replace (Timeline) failed")
        if target == output_mp3 and ".bak" in src.name:
            raise OSError("Rollback replace failed")
        return original_replace(self_path, target_path)


    with patch.object(Path, "replace", autospec=True, side_effect=_triple_failing_replace):
        with pytest.raises(AudioRollbackError) as exc_info:
            orchestrator.generate_synchronized(
                document=_make_prepared_document(),
                output_path=output_mp3,
            )

    assert "rollback" in str(exc_info.value).lower()
    retained_backups = [p for p in tmp_path.iterdir() if ".bak" in p.name]
    assert len(retained_backups) > 0, "Backups should be retained when rollback fails"


