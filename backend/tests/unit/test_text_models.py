"""Unit tests for structured text preparation models."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.text.models import (
    PreparedChunk,
    PreparedDocument,
    PreparedSentence,
    SynthesisFragment,
)


def _sentence(*, index=0, text="Primeira frase.", fragments=None):
    return PreparedSentence(
        index=index,
        text=text,
        fragments=fragments or (SynthesisFragment(index=0, text=text),),
    )


def _chunk(*, index=0, sentences=None):
    return PreparedChunk(
        index=index,
        sentences=sentences or (_sentence(),),
    )


def test_prepared_models_are_immutable_and_derive_chunk_text():
    sentence = _sentence(
        text="Alpha beta.",
        fragments=[
            SynthesisFragment(index=0, text="Alpha"),
            SynthesisFragment(index=1, text="beta."),
        ],
    )
    chunk = _chunk(
        sentences=[sentence, _sentence(index=1, text="Gamma.")],
    )
    document = PreparedDocument(chunks=[chunk])

    assert isinstance(document.chunks, tuple)
    assert isinstance(document.chunks[0].sentences, tuple)
    assert isinstance(document.chunks[0].sentences[0].fragments, tuple)
    assert document.chunks[0].text == "Alpha beta. Gamma."
    with pytest.raises(FrozenInstanceError):
        document.chunks = ()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PreparedDocument(chunks=()),
        lambda: PreparedChunk(index=0, sentences=()),
        lambda: PreparedSentence(index=0, text="", fragments=(SynthesisFragment(0, "x"),)),
        lambda: PreparedSentence(index=0, text="   ", fragments=(SynthesisFragment(0, "x"),)),
        lambda: PreparedSentence(index=0, text="Frase.", fragments=()),
        lambda: SynthesisFragment(index=0, text=""),
        lambda: SynthesisFragment(index=0, text="   "),
    ],
)
def test_prepared_models_reject_empty_collections_and_text(factory):
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SynthesisFragment(index=-1, text="Fragmento"),
        lambda: PreparedSentence(index=-1, text="Frase.", fragments=(SynthesisFragment(0, "Frase."),)),
        lambda: PreparedChunk(index=-1, sentences=(_sentence(),)),
        lambda: PreparedSentence(
            index=0,
            text="Frase.",
            fragments=(SynthesisFragment(index=1, text="Frase."),),
        ),
    ],
)
def test_prepared_models_reject_invalid_positional_indices(factory):
    with pytest.raises(ValueError):
        factory()


def test_synthesis_fragment_rejects_text_above_configured_limit():
    with pytest.raises(ValueError):
        SynthesisFragment(
            index=0,
            text="x" * (settings.MAX_CHUNK_CHARS + 1),
        )


def test_synthesis_fragment_accepts_audio_lifecycle_states(tmp_path):
    unrendered = SynthesisFragment(index=0, text="Frase.")
    rendered_unmeasured = SynthesisFragment(
        index=0,
        text="Frase.",
        wav_path=tmp_path / "pending.wav",
    )
    rendered = SynthesisFragment(
        index=0,
        text="Frase.",
        wav_path=tmp_path / "fragment.wav",
        frame_count=10,
    )

    assert unrendered.wav_path is None
    assert unrendered.frame_count is None
    assert rendered_unmeasured.wav_path == Path(tmp_path / "pending.wav")
    assert rendered_unmeasured.frame_count is None
    assert rendered.wav_path == Path(tmp_path / "fragment.wav")
    assert rendered.frame_count == 10


@pytest.mark.parametrize(
    "wav_path, frame_count",
    [
        (None, 10),
        (Path("fragment.wav"), 0),
        (Path("fragment.wav"), -1),
    ],
)
def test_synthesis_fragment_rejects_incomplete_or_non_positive_rendered_state(
    wav_path,
    frame_count,
):
    with pytest.raises(ValueError):
        SynthesisFragment(
            index=0,
            text="Frase.",
            wav_path=wav_path,
            frame_count=frame_count,
        )
