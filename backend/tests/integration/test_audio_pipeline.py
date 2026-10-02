"""Integration test for the full audio pipeline (Phase 3).

Requires:
- Piper voice model ``pt_BR-cadu-medium`` present in VOICES_DIR
- FFmpeg installed and accessible on PATH (or via FFMPEG_PATH env var)

Both guards are applied via ``pytest.mark.skipif`` so this test is silently
skipped in CI environments that lack these dependencies.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import wave
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.audio._ffmpeg import FFmpegNotFoundError, resolve_ffmpeg
from app.services.audio.concatenator import AudioConcatenator
from app.services.audio.orchestrator import AudioOrchestrator
from app.services.text.pipeline import TextPreprocessingPipeline


# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------

try:
    resolve_ffmpeg(settings.FFMPEG_PATH)
    FFMPEG_AVAILABLE = True
except FFmpegNotFoundError:
    FFMPEG_AVAILABLE = False
VOICE_AVAILABLE = (
    (settings.VOICES_DIR / f"{settings.DEFAULT_VOICE}.onnx").exists()
    and (settings.VOICES_DIR / f"{settings.DEFAULT_VOICE}.onnx.json").exists()
)

pytestmark = [
    pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg not installed"),
    pytest.mark.skipif(not VOICE_AVAILABLE, reason=f"Voice model '{settings.DEFAULT_VOICE}' not downloaded"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def orchestrator() -> AudioOrchestrator:
    return AudioOrchestrator()


@pytest.fixture(scope="module")
def pipeline() -> TextPreprocessingPipeline:
    return TextPreprocessingPipeline()


class _RecordingConcatenator(AudioConcatenator):
    """Run real concatenation while retaining PCM facts for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.segment_names: list[str] = []
        self.segment_frame_counts: list[int] = []
        self.merged_frame_count = 0

    def concatenate(self, wav_paths: list[Path], output_path: Path) -> Path:
        self.segment_names = [path.name for path in wav_paths]
        self.segment_frame_counts = []
        for wav_path in wav_paths:
            with wave.open(str(wav_path), "rb") as wav_file:
                self.segment_frame_counts.append(wav_file.getnframes())

        result = super().concatenate(wav_paths, output_path)
        with wave.open(str(result), "rb") as wav_file:
            self.merged_frame_count = wav_file.getnframes()
        return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "## Introdução ao RAG\n\n"
    "O **Retrieval-Augmented Generation** é uma técnica que combina busca semântica "
    "com geração de texto por modelos de linguagem.\n\n"
    "- Primeiro, documentos são indexados em um banco vetorial.\n"
    "- Depois, consultas recuperam os trechos mais relevantes.\n"
    "- Por fim, o modelo gera uma resposta fundamentada.\n\n"
    "Essa abordagem melhora a precisão e reduz alucinações."
)


def test_full_pipeline_produces_mp3(tmp_path, orchestrator, pipeline):
    """End-to-end: Markdown text → normalized chunks → WAV segments → MP3."""
    output_mp3 = tmp_path / "test_output.mp3"

    chunks = pipeline.process(SAMPLE_TEXT)
    assert len(chunks) > 0, "Pipeline produced no chunks"

    result = orchestrator.generate_mp3(
        chunks=chunks,
        output_path=output_mp3,
        voice=settings.DEFAULT_VOICE,
        speed=1.0,
    )

    assert output_mp3.exists(), "MP3 file was not created"
    assert result.file_size_bytes > 0, "MP3 file is empty"
    assert result.duration_seconds > 0, "Duration must be positive"
    assert result.chunks_count == len(chunks)
    assert result.processing_time_seconds > 0


def test_mp3_is_valid_audio(tmp_path, orchestrator, pipeline):
    """FFprobe confirms the generated MP3 is valid audio."""
    output_mp3 = tmp_path / "valid_audio.mp3"
    chunks = pipeline.process("Este é um teste de áudio simples para validação.")

    orchestrator.generate_mp3(chunks=chunks, output_path=output_mp3)

    # Use ffprobe to inspect the file
    import subprocess
    from pathlib import Path as _Path
    ffmpeg_bin = _Path(settings.FFMPEG_PATH)
    ffprobe_candidate = ffmpeg_bin.parent / ("ffprobe" + ffmpeg_bin.suffix)
    ffprobe_path = str(ffprobe_candidate) if ffprobe_candidate.exists() else (shutil.which("ffprobe") or "ffprobe")
    probe_result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries",
         "format=duration,size,bit_rate", "-of", "default=noprint_wrappers=1",
         str(output_mp3)],
        capture_output=True,
        text=True,
    )
    assert probe_result.returncode == 0, f"ffprobe failed: {probe_result.stderr}"
    assert "duration" in probe_result.stdout


def test_temp_dir_is_cleaned_up(tmp_path, orchestrator, pipeline):
    """No temporary WAV files remain in the temp directory after generation."""
    import tempfile
    import os

    chunks = pipeline.process("Verificando limpeza de temporários.")
    output_mp3 = tmp_path / "cleanup_test.mp3"

    # Count tmp dirs before
    tmp_base = Path(tempfile.gettempdir())
    before = set(p.name for p in tmp_base.iterdir() if p.is_dir() and p.name.startswith("tts_phase3_"))

    orchestrator.generate_mp3(chunks=chunks, output_path=output_mp3)

    after = set(p.name for p in tmp_base.iterdir() if p.is_dir() and p.name.startswith("tts_phase3_"))
    leaked = after - before
    assert not leaked, f"Temp directories leaked: {leaked}"


def test_multi_chunk_text_produces_longer_audio(tmp_path, orchestrator, pipeline):
    """Longer input text (more chunks) produces a longer audio file than short text."""
    short_text = "Frase curta."
    long_text = SAMPLE_TEXT  # many sentences → more chunks

    short_chunks = pipeline.process(short_text)
    long_chunks = pipeline.process(long_text)

    short_mp3 = tmp_path / "short.mp3"
    long_mp3 = tmp_path / "long.mp3"

    short_result = orchestrator.generate_mp3(chunks=short_chunks, output_path=short_mp3)
    long_result = orchestrator.generate_mp3(chunks=long_chunks, output_path=long_mp3)

    assert long_result.duration_seconds > short_result.duration_seconds, (
        f"Expected long text ({long_result.duration_seconds:.1f}s) to be longer "
        f"than short text ({short_result.duration_seconds:.1f}s)"
    )


def test_single_chunk_bypass_produces_valid_mp3(tmp_path, orchestrator):
    """Single-chunk input (concatenator fast-path) still produces a valid MP3."""
    chunks = ["Esta é uma única frase simples."]
    output_mp3 = tmp_path / "single_chunk.mp3"

    result = orchestrator.generate_mp3(
        chunks=chunks,
        output_path=output_mp3,
        voice=settings.DEFAULT_VOICE,
    )

    assert output_mp3.exists()
    assert result.chunks_count == 1
    assert result.file_size_bytes > 0


def test_synchronized_pipeline_produces_exact_sentence_timeline(
    tmp_path,
    pipeline,
):
    """Real Piper/FFmpeg flow binds ordered sentence ranges to the final MP3."""
    raw_text = (
        "Primeira frase de integração. "
        "Segunda frase com áudio. "
        "Terceira frase final."
    )
    document = pipeline.prepare(raw_text)
    prepared_sentences = document.chunks[0].sentences
    prepared_fragments = [
        fragment
        for sentence in prepared_sentences
        for fragment in sentence.fragments
    ]
    recording_concatenator = _RecordingConcatenator()
    synchronized_orchestrator = AudioOrchestrator(
        concatenator=recording_concatenator,
    )
    output_mp3 = tmp_path / "sentence_timeline.mp3"

    result = synchronized_orchestrator.generate_synchronized(
        document=document,
        output_path=output_mp3,
        voice=settings.DEFAULT_VOICE,
        speed=1.0,
    )

    expected_timeline_path = tmp_path / "sentence_timeline.timeline.json"
    assert result.output_path == output_mp3.resolve()
    assert result.timeline_path == expected_timeline_path.resolve()
    assert output_mp3.is_file()
    assert expected_timeline_path.is_file()

    timeline = json.loads(expected_timeline_path.read_text(encoding="utf-8"))
    assert set(timeline) == {"schema_version", "audio", "chunks"}
    assert timeline["schema_version"] == 1
    assert set(timeline["audio"]) == {
        "filename",
        "sha256",
        "sample_rate_hz",
        "total_samples",
    }
    assert timeline["audio"]["filename"] == output_mp3.name
    assert timeline["audio"]["sample_rate_hz"] == 22050
    with output_mp3.open("rb") as mp3_file:
        assert timeline["audio"]["sha256"] == hashlib.file_digest(
            mp3_file,
            "sha256",
        ).hexdigest()

    assert recording_concatenator.segment_names == [
        f"fragment_{index}.wav" for index in range(len(prepared_fragments))
    ]
    assert recording_concatenator.merged_frame_count == sum(
        recording_concatenator.segment_frame_counts
    )
    assert timeline["audio"]["total_samples"] == (
        recording_concatenator.merged_frame_count
    )

    assert len(timeline["chunks"]) == 1
    timeline_chunk = timeline["chunks"][0]
    assert set(timeline_chunk) == {
        "index",
        "start_sample",
        "end_sample",
        "sentences",
    }
    assert timeline_chunk["index"] == 0
    timeline_sentences = timeline_chunk["sentences"]
    assert all(
        set(sentence) == {"index", "text", "start_sample", "end_sample"}
        for sentence in timeline_sentences
    )
    assert [sentence["index"] for sentence in timeline_sentences] == list(
        range(len(prepared_sentences))
    )
    assert [sentence["text"] for sentence in timeline_sentences] == [
        sentence.text for sentence in prepared_sentences
    ]
    assert timeline_sentences[0]["start_sample"] == 0
    assert all(
        current["end_sample"] == following["start_sample"]
        for current, following in zip(
            timeline_sentences,
            timeline_sentences[1:],
        )
    )
    assert all(
        sentence["end_sample"] > sentence["start_sample"]
        for sentence in timeline_sentences
    )
    assert all(len(sentence.fragments) == 1 for sentence in prepared_sentences)
    assert [
        sentence["end_sample"] - sentence["start_sample"]
        for sentence in timeline_sentences
    ] == recording_concatenator.segment_frame_counts
    assert timeline_sentences[-1]["end_sample"] == (
        recording_concatenator.merged_frame_count
    )
    assert timeline_chunk["start_sample"] == 0
    assert timeline_chunk["end_sample"] == recording_concatenator.merged_frame_count
