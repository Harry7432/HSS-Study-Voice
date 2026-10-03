from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class ErrorResponse(BaseModel):
    detail: str


class StudyCreateRequest(BaseModel):
    text: str = Field(..., max_length=settings.MAX_REQUEST_TEXT_CHARS)
    voice: str | None = None
    speed: float | None = Field(default=None, gt=0)
    bitrate: str | None = None

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return value


class StudyCreateResponse(BaseModel):
    study_id: str
    chunks_count: int
    duration_seconds: float
    file_size_bytes: int
    processing_time_seconds: float
