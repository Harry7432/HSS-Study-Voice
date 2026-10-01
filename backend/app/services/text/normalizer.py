"""Markdown normalization for TTS preprocessing.

Strips Markdown syntax while preserving all semantic (spoken) content,
producing clean plain text suitable for Text-to-Speech engines.
"""

import re


class MarkdownNormalizer:
    """Convert Markdown-formatted text into TTS-friendly plain text.

    The normalizer removes visual/structural Markdown syntax but retains
    every word that carries meaning.  For example, ``**RAG**`` becomes
    ``RAG`` and ``[LangChain](https://…)`` becomes ``LangChain``.
    """

    # ------------------------------------------------------------------ #
    # Compiled regex patterns (class-level, built once)                   #
    # ------------------------------------------------------------------ #

    # Images: ![alt text](url)  →  remove entirely (no auditory value)
    _RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")

    # Inline links: [text](url)  →  text
    _RE_INLINE_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

    # Reference-style links: [text][ref]  →  text
    _RE_REF_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")

    # Bold: **text** or __text__  →  text
    _RE_BOLD = re.compile(r"\*{2}(.+?)\*{2}|_{2}(.+?)_{2}", re.DOTALL)

    # Italic: *text* or _text_  →  text
    # Must run AFTER bold so that ** is already consumed.
    _RE_ITALIC = re.compile(r"\*(.+?)\*|_(.+?)_", re.DOTALL)

    # Inline code: `code`  →  code
    _RE_INLINE_CODE = re.compile(r"`([^`]+)`")

    # Headings: ## Title  →  Title  (1–6 hashes, optional trailing hashes)
    _RE_HEADING = re.compile(r"^#{1,6}\s+(.*?)(?:\s+#+)?\s*$", re.MULTILINE)

    # Horizontal rules: ---, ***, ___ on their own line  →  empty line
    _RE_HORIZ_RULE = re.compile(r"^\s*(?:[-*_]){3,}\s*$", re.MULTILINE)

    # Blockquotes: > text  →  text  (handles nested >, e.g. >> text)
    _RE_BLOCKQUOTE = re.compile(r"^>+\s?", re.MULTILINE)

    # Unordered list bullets: - item / * item / + item  →  item
    _RE_BULLET = re.compile(r"^[ \t]*[-*+]\s+", re.MULTILINE)

    # Ordered list markers: 1. item  →  item
    _RE_ORDERED = re.compile(r"^[ \t]*\d+\.\s+", re.MULTILINE)

    # Collapse 3+ consecutive blank lines into a single blank line
    _RE_MULTI_BLANK = re.compile(r"\n{3,}")

    def normalize(self, text: str) -> str:
        """Strip Markdown syntax from *text* and return TTS-ready plain text.

        Processing order matters:
        1. Images (before link patterns so ``![…](…)`` is not partially caught)
        2. Inline links / reference links
        3. Bold (before italic so ``**`` is consumed first)
        4. Italic
        5. Inline code
        6. Block-level: headings, horizontal rules, blockquotes, list markers
        7. Per-line whitespace cleanup
        8. Collapse multiple blank lines

        Args:
            text: Raw Markdown (or plain) text.

        Returns:
            Clean text with Markdown syntax removed.
        """
        if not text:
            return text

        # 1. Remove images entirely
        text = self._RE_IMAGE.sub("", text)

        # 2. Unwrap links — keep display text
        text = self._RE_INLINE_LINK.sub(r"\1", text)
        text = self._RE_REF_LINK.sub(r"\1", text)

        # 3. Remove bold markers — keep inner text (group 1 or group 2)
        text = self._RE_BOLD.sub(lambda m: m.group(1) or m.group(2), text)

        # 4. Remove italic markers — keep inner text
        text = self._RE_ITALIC.sub(lambda m: m.group(1) or m.group(2), text)

        # 5. Remove inline code backticks — keep code word
        text = self._RE_INLINE_CODE.sub(r"\1", text)

        # 6a. Replace heading lines with just their text content
        text = self._RE_HEADING.sub(r"\1", text)

        # 6b. Erase horizontal rules (leave a blank line in their place)
        text = self._RE_HORIZ_RULE.sub("", text)

        # 6c. Strip blockquote markers
        text = self._RE_BLOCKQUOTE.sub("", text)

        # 6d. Strip unordered list markers
        text = self._RE_BULLET.sub("", text)

        # 6e. Strip ordered list markers
        text = self._RE_ORDERED.sub("", text)

        # 7. Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)

        # 8. Collapse 3+ blank lines → 1 blank line
        text = self._RE_MULTI_BLANK.sub("\n\n", text)

        return text.strip()
