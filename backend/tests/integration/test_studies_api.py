"""Real end-to-end tests for the Studies API using Piper and FFmpeg."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes import studies
from app.core.config import settings
from app.main import app
from app.services.audio._ffmpeg import FFmpegNotFoundError, resolve_ffmpeg
from app.services.studies.service import StudyService

try:
    resolve_ffmpeg(settings.FFMPEG_PATH)
    FFMPEG_AVAILABLE = True
except FFmpegNotFoundError:
    FFMPEG_AVAILABLE = False

VOICE_AVAILABLE = (
    (settings.VOICES_DIR / f"{settings.DEFAULT_VOICE}.onnx").is_file()
    and (settings.VOICES_DIR / f"{settings.DEFAULT_VOICE}.onnx.json").is_file()
)

pytestmark = [
    pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg not installed"),
    pytest.mark.skipif(
        not VOICE_AVAILABLE,
        reason=f"Voice model '{settings.DEFAULT_VOICE}' not downloaded",
    ),
]


def _temp_processing_dirs() -> set[Path]:
    roots = {Path(tempfile.gettempdir()), settings.TEMP_DIR}
    return {
        path.resolve()
        for root in roots
        if root.is_dir()
        for path in root.glob("tts_phase3_*")
        if path.is_dir()
    }


@pytest.fixture
def real_client(tmp_path, monkeypatch):
    original_service = studies._service
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)
    studies._service = StudyService()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        studies._service = original_service


def test_create_and_fetch_real_study_without_temp_residue(real_client):
    before = _temp_processing_dirs()

    create_response = real_client.post(
        f"{settings.API_V1_STR}/studies",
        json={
            "text": "## Teste real\n\nPrimeira frase de áudio. Segunda frase da timeline."
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    study_id = created["study_id"]
    assert len(study_id) == 32
    assert all(character in "0123456789abcdef" for character in study_id)
    assert created["chunks_count"] > 0
    assert created["duration_seconds"] > 0
    assert created["file_size_bytes"] > 0

    audio_response = real_client.get(
        f"{settings.API_V1_STR}/studies/{study_id}/audio"
    )
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/mpeg"
    assert audio_response.content.startswith(b"ID3")

    timeline_response = real_client.get(
        f"{settings.API_V1_STR}/studies/{study_id}/timeline"
    )
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert timeline["schema_version"] == 1
    assert timeline["audio"]["filename"] == f"{study_id}.mp3"
    assert timeline["audio"]["total_samples"] > 0
    assert [
        sentence["text"]
        for chunk in timeline["chunks"]
        for sentence in chunk["sentences"]
    ] == [
        "Teste real\nPrimeira frase de áudio.",
        "Segunda frase da timeline.",
    ]
    assert _temp_processing_dirs() == before


def test_failed_real_study_creation_leaves_no_temp_residue(real_client):
    before = _temp_processing_dirs()

    response = real_client.post(
        f"{settings.API_V1_STR}/studies",
        json={"text": "Falha real controlada.", "voice": "voz-inexistente"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Falha ao gerar o estudo em áudio."}
    assert _temp_processing_dirs() == before
