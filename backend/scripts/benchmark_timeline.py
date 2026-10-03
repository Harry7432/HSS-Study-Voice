"""Baseline-versus-timeline performance benchmark (SC-005 / T027).

Compares the legacy ``AudioOrchestrator.generate_mp3()`` flow against the
synchronized ``AudioOrchestrator.generate_synchronized()`` flow on the same
machine, voice, speed and bitrate, and reports the percentage overhead that
timeline preparation adds to the total pipeline time.

The benchmark excludes voice-model download time: it fails fast if the
requested voice is not already present in ``settings.VOICES_DIR`` (run once
manually beforehand to download it; downloading is a one-time setup cost,
not a per-run cost, so it must not be counted in either measurement) and it
performs one untimed warm-up synthesis to load the model into memory before
timing either flow, so that model load time is excluded identically from
both.

The input fixture is a single generated paragraph of representative prose,
repeated until its estimated spoken duration reaches ``--minutes`` (60 by
default, matching the representative scenario in spec.md SC-005). Fixture
sizing uses a fixed chars-per-second calibration measured once against the
configured voice/speed; the actual resulting audio duration is measured and
reported alongside the overhead, so the report stays honest even if sizing
is imprecise.

Usage (run from ``backend/``; ``PYTHONPATH=.`` is required, matching
``scripts/compare_voices.py``)::

    PYTHONPATH=. uv run python scripts/benchmark_timeline.py
    PYTHONPATH=. uv run python scripts/benchmark_timeline.py --minutes 5 --voice pt_BR-cadu-medium
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.audio.concatenator import AudioConcatenator
from app.services.audio.exporter import MP3Exporter
from app.services.audio.orchestrator import AudioOrchestrator
from app.services.audio.renderer import AudioRenderer
from app.services.text.pipeline import TextPreprocessingPipeline

_BASE_PARAGRAPH = (
    "Retrieval-Augmented Generation, também conhecido como RAG, combina busca "
    "semântica com geração de texto por modelos de linguagem. Documentos são "
    "indexados em um banco vetorial e consultas recuperam os trechos mais "
    "relevantes antes da geração da resposta. Essa abordagem melhora a precisão "
    "das respostas e reduz alucinações em cenários de estudo e consulta."
)

# Calibrated from a representative local measurement with pt_BR-cadu-medium at
# speed 1.0 (see research.md). Only used to size the fixture text; the real
# resulting duration is always measured and reported, never assumed.
_CHARS_PER_SECOND_OF_AUDIO = 16.1


@dataclass
class _RunResult:
    label: str
    processing_time_seconds: float
    audio_duration_seconds: float
    output_path: Path


def _build_fixture_text(target_minutes: float) -> str:
    target_seconds = target_minutes * 60
    target_chars = int(target_seconds * _CHARS_PER_SECOND_OF_AUDIO)
    paragraphs = max(1, round(target_chars / len(_BASE_PARAGRAPH)))
    return "\n\n".join(_BASE_PARAGRAPH for _ in range(paragraphs))


def _wav_duration_seconds(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def _require_voice_present(voice: str) -> None:
    onnx = settings.VOICES_DIR / f"{voice}.onnx"
    config = settings.VOICES_DIR / f"{voice}.onnx.json"
    if not onnx.exists() or not config.exists():
        raise SystemExit(
            f"Voice '{voice}' is not downloaded in {settings.VOICES_DIR}. "
            "Download it once beforehand (voice download time is excluded "
            "from this benchmark on purpose; it is a one-time setup cost)."
        )


def _warm_up(renderer: AudioRenderer, voice: str, speed: float, tmp_dir: Path) -> None:
    """Untimed synthesis so model-load cost is excluded from both runs."""
    renderer.render_chunks(
        chunks=["Aquecimento do modelo antes da medição."],
        voice=voice,
        speed=speed,
        temp_dir=tmp_dir,
    )


def run_baseline(
    *,
    renderer: AudioRenderer,
    text: str,
    voice: str,
    speed: float,
    bitrate: str,
    output_dir: Path,
) -> _RunResult:
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=AudioConcatenator(),
        exporter=MP3Exporter(),
    )
    chunks = TextPreprocessingPipeline().process(text)
    output_path = output_dir / "baseline.mp3"

    result = orchestrator.generate_mp3(
        chunks=chunks,
        output_path=output_path,
        voice=voice,
        speed=speed,
        bitrate=bitrate,
    )
    return _RunResult(
        label="baseline (generate_mp3)",
        processing_time_seconds=result.processing_time_seconds,
        audio_duration_seconds=result.duration_seconds,
        output_path=result.output_path,
    )


def run_synchronized(
    *,
    renderer: AudioRenderer,
    text: str,
    voice: str,
    speed: float,
    bitrate: str,
    output_dir: Path,
) -> _RunResult:
    orchestrator = AudioOrchestrator(
        renderer=renderer,
        concatenator=AudioConcatenator(),
        exporter=MP3Exporter(),
    )
    document = TextPreprocessingPipeline().prepare(text)
    output_path = output_dir / "synchronized.mp3"

    result = orchestrator.generate_synchronized(
        document=document,
        output_path=output_path,
        voice=voice,
        speed=speed,
        bitrate=bitrate,
    )
    return _RunResult(
        label="synchronized (generate_synchronized)",
        processing_time_seconds=result.processing_time_seconds,
        audio_duration_seconds=result.duration_seconds,
        output_path=result.output_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--minutes",
        type=float,
        default=60.0,
        help="Target fixture audio duration in minutes (default: 60, per SC-005).",
    )
    parser.add_argument("--voice", default=settings.DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=settings.DEFAULT_SPEED)
    parser.add_argument("--bitrate", default=settings.MP3_BITRATE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the two generated MP3/timeline artifacts (default: a temp dir).",
    )
    args = parser.parse_args(argv)

    _require_voice_present(args.voice)

    cleanup_output_dir = args.output_dir is None
    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="benchmark_timeline_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    text = _build_fixture_text(args.minutes)
    print(f"Fixture size: {len(text)} characters (target ~{args.minutes:.1f} min of audio)")

    warmup_dir = Path(tempfile.mkdtemp(prefix="benchmark_timeline_warmup_"))
    renderer = AudioRenderer()
    try:
        print("Warming up voice model (untimed, excluded from both runs)...")
        _warm_up(renderer, args.voice, args.speed, warmup_dir)

        print(f"Running baseline with voice={args.voice} speed={args.speed} bitrate={args.bitrate} ...")
        baseline = run_baseline(
            renderer=renderer,
            text=text,
            voice=args.voice,
            speed=args.speed,
            bitrate=args.bitrate,
            output_dir=output_dir,
        )
        print(
            f"  baseline: processing={baseline.processing_time_seconds:.3f}s "
            f"audio={baseline.audio_duration_seconds:.1f}s"
        )

        print("Running synchronized flow...")
        synchronized = run_synchronized(
            renderer=renderer,
            text=text,
            voice=args.voice,
            speed=args.speed,
            bitrate=args.bitrate,
            output_dir=output_dir,
        )
        print(
            f"  synchronized: processing={synchronized.processing_time_seconds:.3f}s "
            f"audio={synchronized.audio_duration_seconds:.1f}s"
        )
    finally:
        shutil.rmtree(warmup_dir, ignore_errors=True)
        if cleanup_output_dir:
            shutil.rmtree(output_dir, ignore_errors=True)

    overhead_seconds = synchronized.processing_time_seconds - baseline.processing_time_seconds
    overhead_pct = (
        (overhead_seconds / baseline.processing_time_seconds) * 100
        if baseline.processing_time_seconds > 0
        else float("inf")
    )

    print("\n" + "=" * 70)
    print("SC-005 benchmark result")
    print("=" * 70)
    print(f"Voice:                {args.voice}  speed={args.speed}  bitrate={args.bitrate}")
    print(f"Fixture audio length: {baseline.audio_duration_seconds / 60:.2f} min")
    print(f"Baseline time:        {baseline.processing_time_seconds:.3f}s")
    print(f"Synchronized time:    {synchronized.processing_time_seconds:.3f}s")
    print(f"Overhead:             {overhead_seconds:+.3f}s ({overhead_pct:+.2f}%)")
    print(f"SC-005 gate (<= 5%):  {'PASS' if overhead_pct <= 5.0 else 'FAIL'}")

    return 0 if overhead_pct <= 5.0 else 1


if __name__ == "__main__":
    sys.exit(main())
