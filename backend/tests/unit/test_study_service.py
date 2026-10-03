"""Unit tests for StudyService, with TextPreprocessingPipeline/AudioOrchestrator doubles."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.core.config import settings
from app.services.audio.orchestrator import AudioResult
from app.services.studies.service import STUDY_ID_PATTERN, StudyService


def _make_service() -> tuple[StudyService, MagicMock, MagicMock, list[AudioResult]]:
    pipeline = MagicMock()
    pipeline.prepare.return_value = "prepared-document"

    orchestrator = MagicMock()
    produced_results: list[AudioResult] = []

    def _fake_generate_synchronized(document, output_path, voice=None, speed=None, bitrate=None):
        output_path = Path(output_path)
        result = AudioResult(
            output_path=output_path,
            chunks_count=2,
            duration_seconds=5.5,
            file_size_bytes=1024,
            processing_time_seconds=0.75,
            timeline_path=output_path.with_suffix(".timeline.json"),
        )
        produced_results.append(result)
        return result

    orchestrator.generate_synchronized.side_effect = _fake_generate_synchronized

    service = StudyService(pipeline=pipeline, orchestrator=orchestrator)
    return service, pipeline, orchestrator, produced_results


def test_create_generates_study_id_matching_pattern():
    service, _, _, _ = _make_service()

    record = service.create(text="Texto de estudo.")

    assert STUDY_ID_PATTERN.match(record.study_id)


def test_create_audio_and_timeline_paths_follow_sibling_convention():
    service, _, _, _ = _make_service()

    record = service.create(text="Texto de estudo.")

    assert record.audio_path.name == f"{record.study_id}.mp3"
    assert record.audio_path == settings.OUTPUT_DIR / f"{record.study_id}.mp3"
    assert record.timeline_path.name == f"{record.study_id}.timeline.json"


def test_create_propagates_audio_result_unchanged():
    service, _, _, produced_results = _make_service()

    record = service.create(text="Texto de estudo.")

    assert record.result is produced_results[0]


def test_create_passes_prepared_document_and_options_to_orchestrator():
    service, pipeline, orchestrator, _ = _make_service()

    service.create(
        text="Texto de estudo.",
        voice="pt_BR-faber-medium",
        speed=1.25,
        bitrate="320k",
    )

    pipeline.prepare.assert_called_once_with("Texto de estudo.")
    call_kwargs = orchestrator.generate_synchronized.call_args.kwargs
    assert call_kwargs["document"] == "prepared-document"
    assert call_kwargs["voice"] == "pt_BR-faber-medium"
    assert call_kwargs["speed"] == 1.25
    assert call_kwargs["bitrate"] == "320k"
    assert isinstance(call_kwargs["output_path"], Path)
