import json
import logging
import time

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.study import StudyCreateRequest, StudyCreateResponse
from app.services.studies.service import STUDY_ID_PATTERN, StudyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_STR}/studies", tags=["Studies"])
_service = StudyService()


@router.post("", response_model=StudyCreateResponse, status_code=201)
def create_study(payload: StudyCreateRequest) -> StudyCreateResponse:
    start_time = time.perf_counter()
    try:
        record = _service.create(
            text=payload.text,
            voice=payload.voice,
            speed=payload.speed,
            bitrate=payload.bitrate,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        logger.error(
            "Study generation failed: text_length=%d voice=%s elapsed=%.2fs error=%s",
            len(payload.text),
            payload.voice,
            elapsed,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar o estudo em áudio.",
        ) from exc

    return StudyCreateResponse(
        study_id=record.study_id,
        chunks_count=record.result.chunks_count,
        duration_seconds=record.result.duration_seconds,
        file_size_bytes=record.result.file_size_bytes,
        processing_time_seconds=record.result.processing_time_seconds,
    )


@router.get("/{study_id}/audio")
def get_study_audio(
    study_id: str = Path(..., pattern=STUDY_ID_PATTERN.pattern),
) -> FileResponse:
    audio_path = _service.get_audio_path(study_id)
    if audio_path is None:
        raise HTTPException(status_code=404, detail="Estudo não encontrado.")
    return FileResponse(audio_path, media_type="audio/mpeg")


@router.get("/{study_id}/timeline")
def get_study_timeline(
    study_id: str = Path(..., pattern=STUDY_ID_PATTERN.pattern),
) -> dict:
    timeline_path = _service.get_timeline_path(study_id)
    if timeline_path is None:
        raise HTTPException(status_code=404, detail="Estudo não encontrado.")
    return json.loads(timeline_path.read_text(encoding="utf-8"))
