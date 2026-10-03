"""Unit tests for TextPreprocessingPipeline."""

import inspect
from unittest.mock import MagicMock
import pytest
from app.services.text.chunker import TextChunker
from app.services.text.normalizer import MarkdownNormalizer
from app.services.text.pipeline import TextPreprocessingPipeline


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_pipeline_process_returns_list():
    """process() must always return a list."""
    pipeline = TextPreprocessingPipeline()
    result = pipeline.process("Texto simples.")
    assert isinstance(result, list)


def test_pipeline_process_normalizes_markdown():
    """Markdown input is stripped; output chunks contain only plain text."""
    pipeline = TextPreprocessingPipeline()
    md_text = (
        "## Introdução\n"
        "\n"
        "Este é um texto com **negrito** e *itálico*.\n"
        "Veja [LangChain](https://langchain.com) para mais detalhes.\n"
    )
    result = pipeline.process(md_text)

    assert isinstance(result, list)
    assert len(result) > 0

    full_text = " ".join(result)
    # Markdown syntax must be absent
    assert "##" not in full_text
    assert "**" not in full_text
    assert "https://" not in full_text
    # Semantic content must be present
    assert "Introdução" in full_text
    assert "negrito" in full_text
    assert "LangChain" in full_text


def test_pipeline_process_empty_input():
    """Empty string input returns an empty list."""
    pipeline = TextPreprocessingPipeline()
    assert pipeline.process("") == []


def test_pipeline_uses_custom_normalizer_and_chunker():
    """Constructor accepts and uses injected normalizer and chunker."""
    mock_normalizer = MagicMock()
    mock_normalizer.normalize.return_value = "Texto normalizado."

    mock_chunker = MagicMock()
    mock_chunker.chunk.return_value = ["Texto normalizado."]

    pipeline = TextPreprocessingPipeline(
        normalizer=mock_normalizer,
        chunker=mock_chunker,
    )
    result = pipeline.process("Entrada qualquer.")

    # Verify collaborators were called with correct arguments
    mock_normalizer.normalize.assert_called_once_with("Entrada qualquer.")
    mock_chunker.chunk.assert_called_once_with("Texto normalizado.")
    assert result == ["Texto normalizado."]


def test_pipeline_prepare_returns_normalized_structured_document():
    pipeline = TextPreprocessingPipeline(
        chunker=TextChunker(max_chars=100, min_chars=5),
    )

    document = pipeline.prepare("1. Primeira frase.\n2. Segunda frase?")

    assert len(document.chunks) == 1
    chunk = document.chunks[0]
    assert (chunk.index, chunk.text) == (
        0,
        "Primeira frase. Segunda frase?",
    )
    assert [
        (sentence.index, sentence.text)
        for sentence in chunk.sentences
    ] == [
        (0, "Primeira frase."),
        (1, "Segunda frase?"),
    ]
    assert [
        [(fragment.index, fragment.text) for fragment in sentence.fragments]
        for sentence in chunk.sentences
    ] == [
        [(0, "Primeira frase.")],
        [(0, "Segunda frase?")],
    ]


def test_pipeline_process_keeps_legacy_list_contract():
    pipeline = TextPreprocessingPipeline(
        chunker=TextChunker(max_chars=100, min_chars=5),
    )

    result = pipeline.process("Primeira **frase**. Segunda frase?")

    assert result == ["Primeira frase. Segunda frase?"]
    assert all(isinstance(chunk, str) for chunk in result)


# ------------------------------------------------------------------ #
# T015: Multi-chunk packing and sentence identity tests (US2)        #
# ------------------------------------------------------------------ #

def test_pipeline_prepare_packs_multiple_chunks_from_markdown_paragraphs():
    pipeline = TextPreprocessingPipeline(
        chunker=TextChunker(max_chars=100, min_chars=5),
    )
    raw_text = (
        "## Seção 1\n\n"
        "Primeira frase do primeiro bloco com **destaque**.\n\n"
        "## Seção 2\n\n"
        "Segunda frase do segundo bloco com *ênfase*."
    )
    document = pipeline.prepare(raw_text)

    assert len(document.chunks) > 1
    for position, chunk in enumerate(document.chunks):
        assert chunk.index == position
        assert len(chunk.sentences) > 0
        for s_pos, sentence in enumerate(chunk.sentences):
            assert sentence.index == s_pos
        assert "##" not in chunk.text
        assert "**" not in chunk.text
        assert "*" not in chunk.text


def test_pipeline_prepare_retains_sentence_identity_across_internal_fragments():
    pipeline = TextPreprocessingPipeline(
        chunker=TextChunker(max_chars=35, min_chars=5),
    )
    long_sentence = (
        "Esta é uma frase longa suficiente para ser fragmentada internamente pela síntese."
    )
    raw_text = f"Curta.\n\n{long_sentence}\n\nOutra curta."
    document = pipeline.prepare(raw_text)

    assert len(document.chunks) >= 2
    all_sentences = [s for c in document.chunks for s in c.sentences]
    matching = [s for s in all_sentences if s.text == long_sentence]
    assert len(matching) == 1
    target_sentence = matching[0]
    assert len(target_sentence.fragments) > 1
    assert [f.index for f in target_sentence.fragments] == list(
        range(len(target_sentence.fragments))
    )
    assert target_sentence.index == 0


def test_pipeline_prepare_preserves_repeated_sentences_distinct_by_positional_hierarchy():
    pipeline = TextPreprocessingPipeline(
        chunker=TextChunker(max_chars=200, min_chars=5),
    )
    raw_text = "Definição importante.\n\nDefinição importante."
    document = pipeline.prepare(raw_text)

    assert len(document.chunks) == 2
    assert document.chunks[0].index == 0
    assert document.chunks[1].index == 1
    s0 = document.chunks[0].sentences[0]
    s1 = document.chunks[1].sentences[0]
    assert s0.text == s1.text == "Definição importante."
    assert s0.index == 0
    assert s1.index == 0
    assert s0 is not s1


def test_pipeline_delegates_chunk_packing_to_injected_chunker():
    from app.services.text.models import (
        PreparedChunk,
        PreparedSentence,
        SynthesisFragment,
    )

    mock_normalizer = MagicMock()
    mock_normalizer.normalize.return_value = "Texto normalizado."

    mock_chunker = MagicMock()
    sentence_0 = PreparedSentence(
        index=0,
        text="Frase 0.",
        fragments=(SynthesisFragment(index=0, text="Frase 0."),),
    )
    sentence_1 = PreparedSentence(
        index=0,
        text="Frase 1.",
        fragments=(SynthesisFragment(index=0, text="Frase 1."),),
    )
    expected_chunks = (
        PreparedChunk(index=0, sentences=(sentence_0,)),
        PreparedChunk(index=1, sentences=(sentence_1,)),
    )
    mock_chunker.prepare_chunks.return_value = expected_chunks

    pipeline = TextPreprocessingPipeline(
        normalizer=mock_normalizer,
        chunker=mock_chunker,
    )
    document = pipeline.prepare("Entrada bruta.")

    mock_normalizer.normalize.assert_called_once_with("Entrada bruta.")
    mock_chunker.prepare_chunks.assert_called_once_with("Texto normalizado.")
    assert document.chunks == expected_chunks


# ------------------------------------------------------------------ #
# T026: Regression tests — legacy chunk()/process() contract         #
# ------------------------------------------------------------------ #

def test_chunk_and_process_signatures_unchanged():
    """Adding prepare()/prepare_chunks() must not alter the legacy signatures."""
    chunk_params = list(inspect.signature(TextChunker.chunk).parameters)
    assert chunk_params == ["self", "text"]

    process_params = list(inspect.signature(TextPreprocessingPipeline.process).parameters)
    assert process_params == ["self", "raw_text"]

    init_params = list(inspect.signature(TextPreprocessingPipeline.__init__).parameters)
    assert init_params == ["self", "normalizer", "chunker"]


@pytest.mark.parametrize(
    "raw_text",
    [
        "## Introdução\n\nTexto com **negrito** e [link](https://exemplo.com).",
        "Primeira frase. Segunda frase! Terceira frase?",
        "",
        "Frase única sem separadores especiais",
    ],
)
def test_process_output_matches_plain_normalize_then_chunk_delegation(raw_text):
    """process() must keep delegating to normalize() then chunk(), unchanged."""
    pipeline = TextPreprocessingPipeline()
    normalizer = MarkdownNormalizer()
    chunker = TextChunker()

    expected = chunker.chunk(normalizer.normalize(raw_text))
    assert pipeline.process(raw_text) == expected


@pytest.mark.parametrize(
    "raw_text",
    [
        "1. Primeira frase.\n2. Segunda frase?\n3. Terceira frase!",
        "Frase curta. Outra frase curta. Mais uma frase curta.",
    ],
)
def test_prepare_chunk_text_matches_legacy_process_output_within_one_paragraph(raw_text):
    """Within a single paragraph, prepare() chunk text matches the legacy list output."""
    chunker = TextChunker(max_chars=100, min_chars=5)
    pipeline = TextPreprocessingPipeline(chunker=chunker)

    legacy_chunks = pipeline.process(raw_text)
    structured_chunks = [chunk.text for chunk in pipeline.prepare(raw_text).chunks]

    assert structured_chunks == legacy_chunks


def test_prepare_chunks_treats_paragraphs_as_hard_boundaries_unlike_legacy_chunk():
    """prepare_chunks() keeps each paragraph as its own chunk; chunk() may merge
    short adjacent paragraphs into one chunk instead. This divergence is an
    intentional US2 guarantee (FR-012) and must not regress to silent merging."""
    chunker = TextChunker(max_chars=100, min_chars=5)
    pipeline = TextPreprocessingPipeline(chunker=chunker)
    raw_text = (
        "## Seção 1\n\nFrase do primeiro bloco.\n\n## Seção 2\n\nFrase do segundo bloco."
    )

    legacy_chunks = pipeline.process(raw_text)
    structured_chunks = [chunk.text for chunk in pipeline.prepare(raw_text).chunks]

    assert legacy_chunks == ["Seção 1\nFrase do primeiro bloco. Seção 2\nFrase do segundo bloco."]
    assert structured_chunks == ["Seção 1\nFrase do primeiro bloco.", "Seção 2\nFrase do segundo bloco."]

