"""Unit tests for TextChunker."""

import pytest
from app.services.text.chunker import TextChunker


# ------------------------------------------------------------------ #
# Helpers / fixtures                                                  #
# ------------------------------------------------------------------ #

def make_chunker(max_chars=500, min_chars=20) -> TextChunker:
    """Return a TextChunker with explicit limits to keep tests deterministic."""
    return TextChunker(max_chars=max_chars, min_chars=min_chars)


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_chunk_empty_string():
    """Empty / whitespace-only input returns an empty list."""
    chunker = make_chunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   ") == []
    assert chunker.chunk("\n\n\n") == []


def test_chunk_short_text_single_chunk():
    """Text shorter than MAX_CHUNK_CHARS is returned as a single chunk."""
    chunker = make_chunker(max_chars=500)
    text = "Esta é uma frase curta."
    result = chunker.chunk(text)
    assert len(result) == 1
    assert result[0] == text


def test_chunk_long_text_multiple_chunks():
    """Every chunk produced must be <= MAX_CHUNK_CHARS characters."""
    max_chars = 100
    chunker = make_chunker(max_chars=max_chars, min_chars=5)
    # Build text with many short sentences that together exceed 100 chars
    text = " ".join([f"Frase número {i}." for i in range(1, 20)])
    result = chunker.chunk(text)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= max_chars, f"Chunk too long ({len(chunk)}): {chunk!r}"


def test_chunk_respects_sentence_boundaries():
    """Chunks should end at sentence-ending punctuation when possible."""
    max_chars = 60
    chunker = make_chunker(max_chars=max_chars, min_chars=5)
    text = "Primeira frase completa. Segunda frase completa. Terceira frase."
    result = chunker.chunk(text)
    # All chunks together must recover the full text content
    rejoined = " ".join(result)
    for sentence in ["Primeira frase completa.", "Segunda frase completa.", "Terceira frase."]:
        assert sentence in rejoined
    # No chunk may exceed the limit
    for chunk in result:
        assert len(chunk) <= max_chars


def test_chunk_min_chars_merging():
    """A chunk shorter than MIN_CHUNK_CHARS is merged with the following chunk."""
    # With max=200 and min=50, a short 10-char fragment must not appear alone
    chunker = make_chunker(max_chars=200, min_chars=50)
    # "Ok." is only 3 chars — it should be merged with the next sentence
    text = "Ok. Esta é uma frase longa o suficiente para passar o limite mínimo de caracteres."
    result = chunker.chunk(text)
    # "Ok." alone must not be a standalone chunk
    assert not any(c.strip() == "Ok." for c in result)
    # Content must still be present
    full = " ".join(result)
    assert "Ok." in full


def test_chunk_oversized_sentence_split():
    """A single sentence longer than MAX_CHUNK_CHARS is split at a word boundary."""
    max_chars = 50
    chunker = make_chunker(max_chars=max_chars, min_chars=5)
    # Build a sentence that is definitely > 50 chars with no natural splits
    long_sentence = "Esta é uma frase muito longa que certamente ultrapassa o limite máximo de caracteres permitido."
    result = chunker.chunk(long_sentence)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= max_chars, f"Chunk too long: {chunk!r}"


def test_chunk_paragraphs_separated():
    """Paragraph breaks (double newline) act as chunk boundaries."""
    max_chars = 500
    chunker = make_chunker(max_chars=max_chars, min_chars=5)
    para1 = "Primeiro parágrafo com conteúdo suficiente."
    para2 = "Segundo parágrafo com conteúdo diferente."
    text = f"{para1}\n\n{para2}"
    result = chunker.chunk(text)
    # Both paragraphs must be represented somewhere in the output
    full = " ".join(result)
    assert "Primeiro parágrafo" in full
    assert "Segundo parágrafo" in full


def test_prepare_sentences_extracts_canonical_sentences_before_grouping():
    chunker = make_chunker(max_chars=100, min_chars=5)

    sentences = chunker.prepare_sentences("Primeira frase. Segunda frase?")

    assert [sentence.text for sentence in sentences] == [
        "Primeira frase.",
        "Segunda frase?",
    ]


def test_prepare_sentences_preserves_repeated_text_identity_by_position():
    chunker = make_chunker(max_chars=100, min_chars=5)

    sentences = chunker.prepare_sentences("Repita. Repita.")

    assert [(sentence.index, sentence.text) for sentence in sentences] == [
        (0, "Repita."),
        (1, "Repita."),
    ]
    assert sentences[0] is not sentences[1]


def test_prepare_sentences_keeps_oversized_sentence_as_multiple_fragments():
    chunker = make_chunker(max_chars=12, min_chars=5)

    sentences = chunker.prepare_sentences("alpha beta gamma delta")

    assert len(sentences) == 1
    assert sentences[0].text == "alpha beta gamma delta"
    assert [
        (fragment.index, fragment.text)
        for fragment in sentences[0].fragments
    ] == [
        (0, "alpha beta"),
        (1, "gamma delta"),
    ]
