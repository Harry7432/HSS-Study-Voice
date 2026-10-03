"""Version 1 domain model and serialization for text-audio timelines."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SAMPLE_RATE_HZ = 22050
MAX_SAFE_INTEGER = 9007199254740991

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def compute_sha256(path: Path) -> str:
    """Calculate and return the lowercase SHA-256 hex digest of a file."""
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_mp3_sha256(mp3_path: Path, expected_sha256: str) -> bool:
    """Return True if mp3_path exists and its SHA-256 matches expected_sha256."""
    p = Path(mp3_path)
    if not p.is_file():
        return False
    digest = compute_sha256(p)
    return digest == expected_sha256.lower()


def _validate_integer(value: object, field_name: str, *, minimum: int = 0) -> None:

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > MAX_SAFE_INTEGER
    ):
        raise ValueError(
            f"{field_name} must be an integer between {minimum} and "
            f"{MAX_SAFE_INTEGER}"
        )


def _validate_index(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def timeline_path_for(audio_path: Path) -> Path:
    """Return the sibling timeline path for a lowercase ``.mp3`` path."""
    audio_path = Path(audio_path)
    if audio_path.suffix != ".mp3" or not audio_path.stem:
        raise ValueError("audio_path must have a lowercase .mp3 suffix")
    return audio_path.with_suffix(".timeline.json")


@dataclass(frozen=True)
class TimelineAudio:
    """Identity and PCM properties of the final audio artifact."""

    filename: str
    sha256: str
    sample_rate_hz: int
    total_samples: int

    def validate(self) -> None:
        if (
            not isinstance(self.filename, str)
            or len(self.filename) < 5
            or Path(self.filename).name != self.filename
            or "/" in self.filename
            or "\\" in self.filename
            or not self.filename.endswith(".mp3")
        ):
            raise ValueError(
                "TimelineAudio.filename must be a basename with a lowercase .mp3 suffix"
            )
        if not isinstance(self.sha256, str) or _SHA256_PATTERN.fullmatch(
            self.sha256
        ) is None:
            raise ValueError(
                "TimelineAudio.sha256 must contain 64 lowercase hexadecimal characters"
            )
        if (
            isinstance(self.sample_rate_hz, bool)
            or not isinstance(self.sample_rate_hz, int)
            or self.sample_rate_hz != SAMPLE_RATE_HZ
        ):
            raise ValueError(
                f"TimelineAudio.sample_rate_hz must be {SAMPLE_RATE_HZ}"
            )
        _validate_integer(
            self.total_samples,
            "TimelineAudio.total_samples",
            minimum=1,
        )


@dataclass(frozen=True)
class TimelineSentence:
    """One normalized logical sentence and its half-open PCM interval."""

    index: int
    text: str
    start_sample: int
    end_sample: int

    def validate(self, *, expected_index: int) -> None:
        _validate_index(self.index, "TimelineSentence.index")
        if self.index != expected_index:
            raise ValueError(
                "TimelineSentence.index must equal its collection position"
            )
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("TimelineSentence.text must be non-empty")
        _validate_integer(self.start_sample, "TimelineSentence.start_sample")
        _validate_integer(self.end_sample, "TimelineSentence.end_sample")
        if self.end_sample <= self.start_sample:
            raise ValueError(
                "TimelineSentence interval must be non-empty and half-open"
            )


@dataclass(frozen=True)
class TimelineChunk:
    """An ordered parent range containing timeline sentences."""

    index: int
    start_sample: int
    end_sample: int
    sentences: tuple[TimelineSentence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sentences", tuple(self.sentences))

    def validate(self, *, expected_index: int, expected_start: int) -> int:
        _validate_index(self.index, "TimelineChunk.index")
        if self.index != expected_index:
            raise ValueError("TimelineChunk.index must equal its collection position")
        _validate_integer(self.start_sample, "TimelineChunk.start_sample")
        _validate_integer(self.end_sample, "TimelineChunk.end_sample")
        if not self.sentences:
            raise ValueError("TimelineChunk.sentences must be non-empty")
        if self.start_sample != expected_start:
            raise ValueError("Timeline chunks must form contiguous ranges")
        if self.start_sample != self.sentences[0].start_sample:
            raise ValueError(
                "TimelineChunk.start_sample must equal its first sentence start"
            )

        next_start = self.start_sample
        for position, sentence in enumerate(self.sentences):
            if not isinstance(sentence, TimelineSentence):
                raise TypeError(
                    "TimelineChunk.sentences must contain TimelineSentence values"
                )
            sentence.validate(expected_index=position)
            if sentence.start_sample != next_start:
                raise ValueError("Timeline sentences must form contiguous ranges")
            next_start = sentence.end_sample

        if self.end_sample != next_start:
            raise ValueError(
                "TimelineChunk.end_sample must equal its last sentence end"
            )
        return self.end_sample


@dataclass(frozen=True)
class TimelineDocument:
    """Canonical version 1 timeline for one completed MP3 artifact."""

    schema_version: int
    audio: TimelineAudio
    chunks: tuple[TimelineChunk, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunks", tuple(self.chunks))

    def validate(self, *, merged_frame_count: int) -> None:
        """Validate the contract and exact merged-WAV frame total."""
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        if not isinstance(self.audio, TimelineAudio):
            raise TypeError("TimelineDocument.audio must be a TimelineAudio")
        self.audio.validate()
        _validate_integer(merged_frame_count, "merged_frame_count", minimum=1)
        if merged_frame_count != self.audio.total_samples:
            raise ValueError(
                "merged_frame_count must equal TimelineAudio.total_samples"
            )
        if not self.chunks:
            raise ValueError("TimelineDocument.chunks must be non-empty")

        next_start = 0
        for position, chunk in enumerate(self.chunks):
            if not isinstance(chunk, TimelineChunk):
                raise TypeError(
                    "TimelineDocument.chunks must contain TimelineChunk values"
                )
            next_start = chunk.validate(
                expected_index=position,
                expected_start=next_start,
            )

        if next_start != self.audio.total_samples:
            raise ValueError(
                "The last timeline interval must end at audio.total_samples"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return data containing exactly the public version 1 fields."""
        return {
            "schema_version": self.schema_version,
            "audio": {
                "filename": self.audio.filename,
                "sha256": self.audio.sha256,
                "sample_rate_hz": self.audio.sample_rate_hz,
                "total_samples": self.audio.total_samples,
            },
            "chunks": [
                {
                    "index": chunk.index,
                    "start_sample": chunk.start_sample,
                    "end_sample": chunk.end_sample,
                    "sentences": [
                        {
                            "index": sentence.index,
                            "text": sentence.text,
                            "start_sample": sentence.start_sample,
                            "end_sample": sentence.end_sample,
                        }
                        for sentence in chunk.sentences
                    ],
                }
                for chunk in self.chunks
            ],
        }

    def write(self, path: Path, *, merged_frame_count: int) -> Path:
        """Validate and serialize the timeline as canonical UTF-8 JSON."""
        self.validate(merged_frame_count=merged_frame_count)
        path = Path(path)
        path.write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
                separators=(",", ": "),
            )
            + "\n",
            encoding="utf-8",
        )
        return path
