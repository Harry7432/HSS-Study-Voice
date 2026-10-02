"""Sentence-aware text chunker for TTS preprocessing.

Splits normalized plain text into chunks that:
- Respect sentence and paragraph boundaries.
- Never exceed ``settings.MAX_CHUNK_CHARS`` characters.
- Merge fragments shorter than ``settings.MIN_CHUNK_CHARS`` with the next chunk.
"""

import re
from typing import Optional

from app.core.config import settings
from app.services.text.models import PreparedSentence, SynthesisFragment


class TextChunker:
    """Split plain text into TTS-ready chunks of bounded length.

    Configuration is read from :data:`app.core.config.settings` at
    instantiation time so that environment-variable overrides are honoured.

    Args:
        max_chars: Override for ``settings.MAX_CHUNK_CHARS``.
        min_chars: Override for ``settings.MIN_CHUNK_CHARS``.
    """

    # Sentence-ending punctuation followed by a space (or end-of-string)
    _RE_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")

    def __init__(
        self,
        max_chars: Optional[int] = None,
        min_chars: Optional[int] = None,
    ) -> None:
        self._max_chars = max_chars if max_chars is not None else settings.MAX_CHUNK_CHARS
        self._min_chars = min_chars if min_chars is not None else settings.MIN_CHUNK_CHARS

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def chunk(self, text: str) -> list[str]:
        """Split *text* into a list of TTS-ready chunks.

        Algorithm
        ---------
        1. Split by double newline → paragraphs.
        2. For each paragraph split by sentence-ending punctuation.
        3. Accumulate sentences until the next one would exceed
           ``MAX_CHUNK_CHARS``; then flush the current buffer.
        4. If a single sentence exceeds ``MAX_CHUNK_CHARS`` it is
           hard-split on the last space before the limit.
        5. After all sentences are processed, merge any trailing chunk
           shorter than ``MIN_CHUNK_CHARS`` into the previous chunk when
           possible.

        Args:
            text: Normalized plain text (output of :class:`MarkdownNormalizer`).

        Returns:
            List of non-empty, stripped chunk strings.
        """
        if not text or not text.strip():
            return []

        sentences = self.prepare_sentences(text)
        raw_chunks = self._accumulate_chunks(
            [sentence.text for sentence in sentences]
        )
        merged = self._merge_short_chunks(raw_chunks)
        return [c for c in merged if c.strip()]

    def prepare_sentences(self, text: str) -> tuple[PreparedSentence, ...]:
        """Create canonical logical sentences before chunk grouping."""
        if not text or not text.strip():
            return ()

        prepared = []
        fragment_limit = min(
            self._max_chars,
            settings.MAX_CHUNK_CHARS,
        )
        for sentence_index, sentence_text in enumerate(
            self._extract_sentences(text)
        ):
            fragment_texts = (
                self._split_by_word_boundary(
                    sentence_text,
                    max_chars=fragment_limit,
                )
                if len(sentence_text) > fragment_limit
                else [sentence_text]
            )
            fragments = tuple(
                SynthesisFragment(index=index, text=fragment_text)
                for index, fragment_text in enumerate(fragment_texts)
            )
            prepared.append(
                PreparedSentence(
                    index=sentence_index,
                    text=sentence_text,
                    fragments=fragments,
                )
            )
        return tuple(prepared)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_sentences(self, text: str) -> list[str]:
        """Return a flat list of sentence strings from *text*.

        Paragraphs (double newlines) are treated as hard sentence boundaries.
        """
        sentences: list[str] = []
        paragraphs = re.split(r"\n\n+", text.strip())
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # Split paragraph into sentences on punctuation boundaries
            parts = self._RE_SENTENCE_SPLIT.split(para)
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)
        return sentences

    def _accumulate_chunks(self, sentences: list[str]) -> list[str]:
        """Pack sentences into chunks not exceeding ``_max_chars``."""
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for sentence in sentences:
            # If a single sentence exceeds the limit, split it on word boundary
            if len(sentence) > self._max_chars:
                # Flush any accumulated content first
                if current_parts:
                    chunks.append(" ".join(current_parts))
                    current_parts = []
                    current_len = 0
                # Hard-split the oversized sentence
                chunks.extend(self._split_by_word_boundary(sentence))
                continue

            # Length of the chunk if we append this sentence (with a space separator)
            needed = len(sentence) if not current_parts else current_len + 1 + len(sentence)

            if needed > self._max_chars and current_parts:
                # Flush the current chunk and start fresh
                chunks.append(" ".join(current_parts))
                current_parts = [sentence]
                current_len = len(sentence)
            else:
                current_parts.append(sentence)
                current_len = needed

        if current_parts:
            chunks.append(" ".join(current_parts))

        return chunks

    def _split_by_word_boundary(
        self,
        sentence: str,
        max_chars: Optional[int] = None,
    ) -> list[str]:
        """Split an oversized *sentence* into sub-chunks at word boundaries."""
        limit = max_chars if max_chars is not None else self._max_chars
        chunks: list[str] = []
        while len(sentence) > limit:
            # Find the last space within the allowed window
            split_at = sentence.rfind(" ", 0, limit)
            if split_at == -1:
                # No space found — hard-cut at the character limit
                split_at = limit
            chunks.append(sentence[:split_at].strip())
            sentence = sentence[split_at:].strip()
        if sentence:
            chunks.append(sentence)
        return chunks

    def _merge_short_chunks(self, chunks: list[str]) -> list[str]:
        """Merge chunks shorter than ``_min_chars`` with the next chunk."""
        if not chunks:
            return chunks

        merged: list[str] = []
        i = 0
        while i < len(chunks):
            current = chunks[i]
            # If current chunk is short and there is a next chunk that can absorb it
            if len(current) < self._min_chars and i + 1 < len(chunks):
                combined = current + " " + chunks[i + 1]
                # Only merge if the result does not exceed max_chars
                if len(combined) <= self._max_chars:
                    chunks[i + 1] = combined  # replace next chunk; revisit it
                    i += 1
                    continue  # do not append current — it is folded into next
            merged.append(current)
            i += 1

        return merged
