"""Text preprocessing pipeline for TTS conversion.

Composes :class:`~app.services.text.normalizer.MarkdownNormalizer` and
:class:`~app.services.text.chunker.TextChunker` into entry points for legacy
plain-text chunks and structured sentence-aware preparation.
"""

from app.services.text.normalizer import MarkdownNormalizer
from app.services.text.chunker import TextChunker
from app.services.text.models import PreparedChunk, PreparedDocument


class TextPreprocessingPipeline:
    """Normalize then chunk raw input text for TTS consumption.

    Both internal components are injectable via constructor arguments,
    which makes the pipeline easy to unit-test with mock collaborators.

    Args:
        normalizer: An object with a ``normalize(text: str) -> str`` method.
            Defaults to a fresh :class:`MarkdownNormalizer` instance.
        chunker: An object with ``chunk(text: str) -> list[str]`` and
            ``prepare_sentences(text: str)`` methods. Defaults to a fresh
            :class:`TextChunker` instance.

    Example::

        pipeline = TextPreprocessingPipeline()
        chunks = pipeline.process("## Hello\\n\\nThis is **bold** text.")
        # → ['Hello', 'This is bold text.']
    """

    def __init__(self, normalizer=None, chunker=None) -> None:
        self.normalizer: MarkdownNormalizer = normalizer or MarkdownNormalizer()
        self.chunker: TextChunker = chunker or TextChunker()

    def process(self, raw_text: str) -> list[str]:
        """Normalize then chunk raw input text.

        Args:
            raw_text: Arbitrary input that may contain Markdown formatting.

        Returns:
            List of TTS-ready plain-text chunk strings.  Empty list when
            *raw_text* is empty or contains only whitespace / syntax noise.
        """
        normalized = self.normalizer.normalize(raw_text)
        return self.chunker.chunk(normalized)

    def prepare(self, raw_text: str) -> PreparedDocument:
        """Normalize text and preserve its canonical sentence structure."""
        normalized = self.normalizer.normalize(raw_text)
        chunks = self.chunker.prepare_chunks(normalized)
        return PreparedDocument(chunks=chunks)
