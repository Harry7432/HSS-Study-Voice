"""Unit tests for TextPreprocessingPipeline."""

from unittest.mock import MagicMock
import pytest
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
