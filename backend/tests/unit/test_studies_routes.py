"""Integration tests for the Studies API router, via TestClient.

StudyService (and its collaborators) are replaced by doubles for most tests so no
real Piper/FFmpeg synthesis happens. One test (Markdown stripping, SC-004) wires a
real TextPreprocessingPipeline through StudyService while only the AudioOrchestrator
is a capturing double, per tasks.md T009.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.routes import studies
from app.core.config import settings
from app.main import app
from app.services.audio.orchestrator import AudioResult
from app.services.audio.renderer import AudioRenderError
from app.services.audio.timeline import (
    SAMPLE_RATE_HZ,
    TimelineAudio,
    TimelineChunk,
    TimelineDocument,
    TimelineSentence,
)
from app.services.studies.service import StudyRecord, StudyService

client = TestClient(app)


@pytest.fixture(autouse=True)
def _restore_service():
    """Each test swaps the module-level _service; restore it afterwards."""
    original = studies._service
    yield
    studies._service = original


def _make_record(study_id: str = "0" * 32) -> StudyRecord:
    audio_path = settings.OUTPUT_DIR / f"{study_id}.mp3"
    timeline_path = settings.OUTPUT_DIR / f"{study_id}.timeline.json"
    result = AudioResult(
        output_path=audio_path,
        chunks_count=2,
        duration_seconds=5.5,
        file_size_bytes=1024,
        processing_time_seconds=0.75,
        timeline_path=timeline_path,
    )
    return StudyRecord(
        study_id=study_id,
        audio_path=audio_path,
        timeline_path=timeline_path,
        result=result,
    )


def test_create_study_returns_201_with_contract_fields():
    fake_service = MagicMock()
    fake_service.create.return_value = _make_record("1" * 32)
    studies._service = fake_service

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "Um texto de estudo válido com duas frases. Segunda frase aqui."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "study_id": "1" * 32,
        "chunks_count": 2,
        "duration_seconds": 5.5,
        "file_size_bytes": 1024,
        "processing_time_seconds": 0.75,
    }


def test_create_study_forwards_voice_speed_bitrate_to_service():
    fake_service = MagicMock()
    fake_service.create.return_value = _make_record("2" * 32)
    studies._service = fake_service

    client.post(
        f"{settings.API_V1_STR}/studies",
        json={
            "text": "Texto de estudo.",
            "voice": "pt_BR-faber-medium",
            "speed": 1.25,
            "bitrate": "320k",
        },
    )

    call_kwargs = fake_service.create.call_args.kwargs
    assert call_kwargs["voice"] == "pt_BR-faber-medium"
    assert call_kwargs["speed"] == 1.25
    assert call_kwargs["bitrate"] == "320k"


def test_create_study_rejects_empty_text():
    studies._service = MagicMock()

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": ""},
    )

    assert response.status_code == 422


def test_create_study_rejects_whitespace_only_text():
    studies._service = MagicMock()

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "    \n\t  "},
    )

    assert response.status_code == 422


def test_create_study_rejects_text_above_max_chars():
    studies._service = MagicMock()

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "a" * (settings.MAX_REQUEST_TEXT_CHARS + 1)},
    )

    assert response.status_code == 422


def test_create_study_returns_500_with_generic_detail_on_generation_failure():
    fake_service = MagicMock()
    fake_service.create.side_effect = AudioRenderError("falha interna de síntese")
    studies._service = fake_service

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "Texto de estudo."},
    )

    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "Falha ao gerar o estudo em áudio."}
    assert "falha interna de síntese" not in response.text


def test_create_study_returns_500_with_generic_detail_on_unexpected_exception():
    fake_service = MagicMock()
    fake_service.create.side_effect = RuntimeError("boom")
    studies._service = fake_service

    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "Texto de estudo."},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Falha ao gerar o estudo em áudio."}


def test_get_audio_returns_exact_bytes_of_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)
    study_id = "3" * 32
    audio_bytes = b"ID3-fixture-mp3-bytes"
    (tmp_path / f"{study_id}.mp3").write_bytes(audio_bytes)
    studies._service = StudyService()

    response = client.get(f"{settings.API_V1_STR}/studies/{study_id}/audio")

    assert response.status_code == 200
    assert response.content == audio_bytes
    assert response.headers["content-type"] == "audio/mpeg"


def test_get_audio_returns_404_for_wellformed_but_missing_id(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)
    studies._service = StudyService()

    response = client.get(f"{settings.API_V1_STR}/studies/{'4' * 32}/audio")

    assert response.status_code == 404
    assert response.json() == {"detail": "Estudo não encontrado."}


def test_get_audio_returns_422_for_malformed_study_id():
    studies._service = MagicMock()

    response = client.get(f"{settings.API_V1_STR}/studies/not-a-valid-id/audio")

    assert response.status_code == 422


def _write_fixture_timeline(path: Path) -> dict:
    document = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename=path.with_suffix("").with_suffix(".mp3").name,
            sha256="a" * 64,
            sample_rate_hz=SAMPLE_RATE_HZ,
            total_samples=10,
        ),
        chunks=(
            TimelineChunk(
                index=0,
                start_sample=0,
                end_sample=10,
                sentences=(
                    TimelineSentence(
                        index=0,
                        text="Frase única de fixture.",
                        start_sample=0,
                        end_sample=10,
                    ),
                ),
            ),
        ),
    )
    document.write(path, merged_frame_count=10)
    return document.to_dict()


def test_get_timeline_returns_fixture_json_matching_contract_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)
    study_id = "5" * 32
    timeline_path = tmp_path / f"{study_id}.timeline.json"
    expected = _write_fixture_timeline(timeline_path)
    studies._service = StudyService()

    response = client.get(f"{settings.API_V1_STR}/studies/{study_id}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body == expected
    assert set(body) == {"schema_version", "audio", "chunks"}
    assert set(body["audio"]) == {"filename", "sha256", "sample_rate_hz", "total_samples"}
    for chunk in body["chunks"]:
        assert set(chunk) == {"index", "start_sample", "end_sample", "sentences"}
        for sentence in chunk["sentences"]:
            assert set(sentence) == {"index", "text", "start_sample", "end_sample"}


def test_get_timeline_returns_404_for_wellformed_but_missing_id(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)
    studies._service = StudyService()

    response = client.get(f"{settings.API_V1_STR}/studies/{'6' * 32}/timeline")

    assert response.status_code == 404
    assert response.json() == {"detail": "Estudo não encontrado."}


def test_get_timeline_returns_422_for_malformed_study_id():
    studies._service = MagicMock()

    response = client.get(f"{settings.API_V1_STR}/studies/not-a-valid-id/timeline")

    assert response.status_code == 422


def test_create_study_markdown_is_not_forwarded_to_synthesis():
    """Real TextPreprocessingPipeline inside StudyService; only orchestrator is a double."""
    captured_documents = []

    class _CapturingOrchestrator:
        def generate_synchronized(self, document, output_path, voice=None, speed=None, bitrate=None):
            captured_documents.append(document)
            return AudioResult(
                output_path=Path(output_path),
                chunks_count=len(document.chunks),
                duration_seconds=1.0,
                file_size_bytes=10,
                processing_time_seconds=0.1,
                timeline_path=Path(output_path).with_suffix(".timeline.json"),
            )

    studies._service = StudyService(orchestrator=_CapturingOrchestrator())

    markdown_text = (
        "## Título\n\n"
        "Este é um texto em **negrito** com uma frase.\n\n"
        "- Item de lista um\n"
        "- Item de lista dois\n\n"
        "Segunda frase de verdade."
    )
    response = client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": markdown_text},
    )

    assert response.status_code == 201
    assert len(captured_documents) == 1
    document = captured_documents[0]
    markdown_markers = ("#", "**", "- ")
    for chunk in document.chunks:
        for sentence in chunk.sentences:
            for marker in markdown_markers:
                assert marker not in sentence.text, (
                    f"Markdown marker {marker!r} leaked into synthesis text: {sentence.text!r}"
                )
