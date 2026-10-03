"""Unit tests for StudyCreateRequest/StudyCreateResponse validation rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.study import StudyCreateRequest, StudyCreateResponse


def test_text_empty_is_rejected():
    with pytest.raises(ValidationError):
        StudyCreateRequest(text="")


def test_text_only_whitespace_is_rejected():
    with pytest.raises(ValidationError):
        StudyCreateRequest(text="    \n\t  ")


def test_text_above_max_chars_is_rejected():
    too_long = "a" * (settings.MAX_REQUEST_TEXT_CHARS + 1)
    with pytest.raises(ValidationError):
        StudyCreateRequest(text=too_long)


def test_text_at_max_chars_is_accepted():
    exactly_max = "a" * settings.MAX_REQUEST_TEXT_CHARS
    request = StudyCreateRequest(text=exactly_max)
    assert request.text == exactly_max


def test_valid_text_is_accepted():
    request = StudyCreateRequest(text="Texto válido de estudo.")
    assert request.text == "Texto válido de estudo."


def test_voice_speed_bitrate_default_to_none():
    request = StudyCreateRequest(text="Texto.")
    assert request.voice is None
    assert request.speed is None
    assert request.bitrate is None


def test_speed_zero_is_rejected():
    with pytest.raises(ValidationError):
        StudyCreateRequest(text="Texto.", speed=0)


def test_speed_negative_is_rejected():
    with pytest.raises(ValidationError):
        StudyCreateRequest(text="Texto.", speed=-1.0)


def test_speed_positive_is_accepted():
    request = StudyCreateRequest(text="Texto.", speed=1.5)
    assert request.speed == 1.5


def test_voice_and_bitrate_are_passed_through():
    request = StudyCreateRequest(
        text="Texto.",
        voice="pt_BR-faber-medium",
        bitrate="320k",
    )
    assert request.voice == "pt_BR-faber-medium"
    assert request.bitrate == "320k"


def test_response_fields():
    response = StudyCreateResponse(
        study_id="a" * 32,
        chunks_count=3,
        duration_seconds=12.5,
        file_size_bytes=2048,
        processing_time_seconds=1.2,
    )
    assert response.study_id == "a" * 32
    assert response.chunks_count == 3
    assert response.duration_seconds == 12.5
    assert response.file_size_bytes == 2048
    assert response.processing_time_seconds == 1.2
