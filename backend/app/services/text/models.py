"""Immutable models for sentence-aware text preparation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


def _validate_index(index: int, field_name: str) -> None:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _validate_text(text: str, field_name: str) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{field_name} must be non-empty text")


@dataclass(frozen=True)
class SynthesisFragment:
    """A bounded piece of one logical sentence rendered as one WAV."""

    index: int
    text: str
    wav_path: Path | None = None
    frame_count: int | None = None

    def __post_init__(self) -> None:
        _validate_index(self.index, "SynthesisFragment.index")
        _validate_text(self.text, "SynthesisFragment.text")
        if len(self.text) > settings.MAX_CHUNK_CHARS:
            raise ValueError(
                "SynthesisFragment.text must not exceed "
                f"{settings.MAX_CHUNK_CHARS} characters"
            )

        if self.wav_path is None:
            if self.frame_count is not None:
                raise ValueError(
                    "SynthesisFragment.frame_count requires a wav_path"
                )
            return
        try:
            object.__setattr__(self, "wav_path", Path(self.wav_path))
        except TypeError as exc:
            raise ValueError("SynthesisFragment.wav_path must be a path") from exc
        if self.frame_count is not None and (
            isinstance(self.frame_count, bool)
            or not isinstance(self.frame_count, int)
            or self.frame_count <= 0
        ):
            raise ValueError("SynthesisFragment.frame_count must be a positive integer")


@dataclass(frozen=True)
class PreparedSentence:
    """A logical sentence whose identity survives internal fragmentation."""

    index: int
    text: str
    fragments: tuple[SynthesisFragment, ...]

    def __post_init__(self) -> None:
        _validate_index(self.index, "PreparedSentence.index")
        _validate_text(self.text, "PreparedSentence.text")
        fragments = tuple(self.fragments)
        if not fragments:
            raise ValueError("PreparedSentence.fragments must be non-empty")
        for position, fragment in enumerate(fragments):
            if not isinstance(fragment, SynthesisFragment):
                raise TypeError(
                    "PreparedSentence.fragments must contain SynthesisFragment values"
                )
            if fragment.index != position:
                raise ValueError(
                    "SynthesisFragment.index must equal its collection position"
                )
        object.__setattr__(self, "fragments", fragments)


@dataclass(frozen=True)
class PreparedChunk:
    """An ordered parent grouping of prepared logical sentences."""

    index: int
    sentences: tuple[PreparedSentence, ...]

    def __post_init__(self) -> None:
        _validate_index(self.index, "PreparedChunk.index")
        sentences = tuple(self.sentences)
        if not sentences:
            raise ValueError("PreparedChunk.sentences must be non-empty")
        for position, sentence in enumerate(sentences):
            if not isinstance(sentence, PreparedSentence):
                raise TypeError(
                    "PreparedChunk.sentences must contain PreparedSentence values"
                )
            if sentence.index != position:
                raise ValueError(
                    "PreparedSentence.index must equal its collection position"
                )
        object.__setattr__(self, "sentences", sentences)

    @property
    def text(self) -> str:
        """Return sentence text joined in spoken order."""
        return " ".join(sentence.text for sentence in self.sentences)


@dataclass(frozen=True)
class PreparedDocument:
    """A non-empty ordered collection of chunks prepared for audio."""

    chunks: tuple[PreparedChunk, ...]

    def __post_init__(self) -> None:
        chunks = tuple(self.chunks)
        if not chunks:
            raise ValueError("PreparedDocument.chunks must be non-empty")
        for position, chunk in enumerate(chunks):
            if not isinstance(chunk, PreparedChunk):
                raise TypeError(
                    "PreparedDocument.chunks must contain PreparedChunk values"
                )
            if chunk.index != position:
                raise ValueError(
                    "PreparedChunk.index must equal its collection position"
                )
        object.__setattr__(self, "chunks", chunks)
