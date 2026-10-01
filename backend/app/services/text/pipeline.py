"""Text preprocessing pipeline for TTS conversion.

Composes :class:`~app.services.text.normalizer.MarkdownNormalizer` and
:class:`~app.services.text.chunker.TextChunker` into a single entry-point
that accepts raw (possibly Markdown-formatted) text and returns a list of
TTS-ready plain-text chunks.
"""

from app.services.text.normalizer import MarkdownNormalizer
from app.services.text.chunker import TextChunker


class TextPreprocessingPipeline:
    """Normalize then chunk raw input text for TTS consumption.

    Both internal components are injectable via constructor arguments,
    which makes the pipeline easy to unit-test with mock collaborators.

    Args:
        normalizer: An object with a ``normalize(text: str) -> str`` method.
            Defaults to a fresh :class:`MarkdownNormalizer` instance.
        chunker: An object with a ``chunk(text: str) -> list[str]`` method.
            Defaults to a fresh :class:`TextChunker` instance.

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
