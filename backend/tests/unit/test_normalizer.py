"""Unit tests for MarkdownNormalizer."""

import pytest
from app.services.text.normalizer import MarkdownNormalizer


@pytest.fixture
def normalizer() -> MarkdownNormalizer:
    return MarkdownNormalizer()


# ------------------------------------------------------------------ #
# Individual syntax rules                                             #
# ------------------------------------------------------------------ #

def test_normalize_inline_link(normalizer):
    """[LangChain](https://langchain.com) → LangChain"""
    result = normalizer.normalize("[LangChain](https://langchain.com)")
    assert result == "LangChain"


def test_normalize_bold(normalizer):
    """**RAG** → RAG"""
    result = normalizer.normalize("**RAG**")
    assert result == "RAG"


def test_normalize_italic(normalizer):
    """*RAG* → RAG and _RAG_ → RAG"""
    assert normalizer.normalize("*RAG*") == "RAG"
    assert normalizer.normalize("_RAG_") == "RAG"


def test_normalize_heading(normalizer):
    """## Arquitetura → Arquitetura, # Intro → Intro"""
    assert normalizer.normalize("## Arquitetura") == "Arquitetura"
    assert normalizer.normalize("# Intro") == "Intro"


def test_normalize_bullet_list(normalizer):
    """- Primeiro passo → Primeiro passo"""
    result = normalizer.normalize("- Primeiro passo")
    assert result == "Primeiro passo"


def test_normalize_numbered_list(normalizer):
    """1. Passo um → Passo um"""
    result = normalizer.normalize("1. Passo um")
    assert result == "Passo um"


def test_normalize_inline_code(normalizer):
    """`código` → código"""
    result = normalizer.normalize("`código`")
    assert result == "código"


def test_normalize_blockquote(normalizer):
    """> Citação → Citação"""
    result = normalizer.normalize("> Citação")
    assert result == "Citação"


def test_normalize_image(normalizer):
    """![alt](url) → '' (empty after strip)"""
    result = normalizer.normalize("![diagrama](https://example.com/img.png)")
    assert result == ""


def test_normalize_horizontal_rule(normalizer):
    """--- on its own line → empty/whitespace-only after strip"""
    result = normalizer.normalize("---")
    assert result.strip() == ""


# ------------------------------------------------------------------ #
# Combined and edge-case tests                                        #
# ------------------------------------------------------------------ #

def test_normalize_combined(normalizer):
    """Multi-line Markdown with headings, bullets, and bold → clean text."""
    raw = (
        "## Arquitetura RAG\n"
        "\n"
        "- Primeiro passo: **ingestão** de documentos\n"
        "- Segundo passo: *recuperação* semântica\n"
    )
    result = normalizer.normalize(raw)

    assert "Arquitetura RAG" in result
    assert "ingestão" in result
    assert "recuperação" in result
    # Markdown syntax must be gone
    assert "##" not in result
    assert "**" not in result
    assert "*" not in result
    assert result.startswith("Arquitetura RAG")


def test_normalize_preserves_plain_text(normalizer):
    """Plain text (no Markdown) should come through essentially unchanged."""
    plain = "Este é um texto simples sem formatação especial."
    result = normalizer.normalize(plain)
    assert result == plain


def test_normalize_multiple_blank_lines(normalizer):
    """Three or more consecutive blank lines are collapsed to one blank line."""
    raw = "Parágrafo um.\n\n\n\nParágrafo dois."
    result = normalizer.normalize(raw)
    # Must not contain 3+ consecutive newlines
    assert "\n\n\n" not in result
    # Both paragraphs must still be present
    assert "Parágrafo um." in result
    assert "Parágrafo dois." in result
