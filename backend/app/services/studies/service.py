from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.audio.orchestrator import AudioOrchestrator, AudioResult
from app.services.audio.timeline import timeline_path_for
from app.services.text.pipeline import TextPreprocessingPipeline

STUDY_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class StudyRecord:
    """Internal result of StudyService.create(); not a serialized API model."""

    study_id: str
    audio_path: Path
    timeline_path: Path
    result: AudioResult


class StudyService:
    """Orchestrate study creation and lookup over the existing text/audio pipeline."""

    def __init__(
        self,
        pipeline: Optional[TextPreprocessingPipeline] = None,
        orchestrator: Optional[AudioOrchestrator] = None,
    ) -> None:
        self._pipeline = pipeline or TextPreprocessingPipeline()
        self._orchestrator = orchestrator or AudioOrchestrator()

    def _audio_path(self, study_id: str) -> Path:
        return settings.OUTPUT_DIR / f"{study_id}.mp3"

    def get_audio_path(self, study_id: str) -> Optional[Path]:
        audio_path = self._audio_path(study_id)
        return audio_path if audio_path.is_file() else None

    def get_timeline_path(self, study_id: str) -> Optional[Path]:
        timeline_path = timeline_path_for(self._audio_path(study_id))
        return timeline_path if timeline_path.is_file() else None

    def create(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        bitrate: Optional[str] = None,
    ) -> StudyRecord:
        study_id = uuid.uuid4().hex
        audio_path = self._audio_path(study_id)
        document = self._pipeline.prepare(text)
        result = self._orchestrator.generate_synchronized(
            document=document,
            output_path=audio_path,
            voice=voice,
            speed=speed,
            bitrate=bitrate,
        )
        return StudyRecord(
            study_id=study_id,
            audio_path=audio_path,
            timeline_path=result.timeline_path,
            result=result,
        )
