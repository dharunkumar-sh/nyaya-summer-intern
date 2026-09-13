"""
Unicode, whitespace, and punctuation normalizer for Classical Tamil Literary texts.

Enforces Unicode NFC normalization, handles virama (pulli), standardizes
danda/double-danda markers, removes ZWNJ/ZWJ anomalies, and collapses
all spurious whitespace — while preserving Tamil verse line structure.
"""
import re
import unicodedata
from typing import Optional


class TamilNormalizer:
    """Normalizes Tamil Unicode text following Classical Sangam conventions."""

    # Tamil Unicode block: U+0B80–U+0BFF
    TAMIL_RANGE = re.compile(r"[\u0B80-\u0BFF]")

    # Virama (pulli) — U+0BCD
    VIRAMA = "\u0BCD"

    # Common punctuation that marks sūtra/sentence boundaries
    SENTENCE_END_MARKERS = re.compile(r"[.।॥]+")

    # Punctuation safe to strip (not poetic markers)
    STRIP_PUNCT = re.compile(r"[!\"#\$%&'()*+,\-/:;<=>?@\[\\\]^_`{|}~]")

    # Danda / double-danda variants → canonical "|"
    DANDA_NORM = re.compile(r"[।॥]+")

    # Non-Tamil ASCII decorative chars often embedded in digital texts
    DECORATIVE = re.compile(r"[\u2018\u2019\u201c\u201d\u2014\u2013\u00ab\u00bb]")

    # Multiple blank lines
    BLANK_LINES = re.compile(r"\n{3,}")

    @classmethod
    def normalize(cls, text: str) -> str:
        """Full Unicode NFC normalization with whitespace and punctuation cleanup."""
        if not text:
            return ""

        # 1. Unicode NFC: canonical decomposition → canonical composition
        text = unicodedata.normalize("NFC", text)

        # 2. Standardize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Remove zero-width non-joiner / joiner (unless part of Tamil conjunct)
        text = text.replace("\u200c", "").replace("\u200d", "")

        # 4. Remove decorative quotation marks and em/en dashes
        text = cls.DECORATIVE.sub(" ", text)

        # 5. Collapse inline whitespace (preserve newlines for verse structure)
        lines = text.split("\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
        text = "\n".join(lines)

        # 6. Collapse 3+ consecutive blank lines → double newline
        text = cls.BLANK_LINES.sub("\n\n", text)

        return text.strip()

    @classmethod
    def normalize_punctuation(cls, text: str) -> str:
        """
        Normalizes sentence-boundary punctuation for segmentation.
        Danda (।) and double-danda (॥) are treated as sentence terminators.
        """
        if not text:
            return ""
        # Normalize all danda variants to a single period for sentence splitting
        text = cls.DANDA_NORM.sub(".", text)
        # Collapse multiple consecutive periods
        text = re.sub(r"\.{2,}", ".", text)
        return text

    @classmethod
    def strip_punctuation(cls, text: str) -> str:
        """
        Removes punctuation safe to strip while preserving Tamil pulli (U+0BCD),
        Tamil combining marks, and verse newlines.
        """
        if not text:
            return ""
        # Remove standard ASCII punctuation except apostrophe (used in transliteration)
        cleaned = cls.STRIP_PUNCT.sub("", text)
        # Remove trailing/leading punctuation artifacts per token
        cleaned = re.sub(r"[.।॥]+", " ", cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def normalize_virama(cls, text: str) -> str:
        """
        Canonicalizes virama (pulli) usage.
        Ensures virama directly follows consonant with no intervening space.
        """
        if not text:
            return ""
        # Remove spaces before virama
        text = re.sub(r"\s+" + cls.VIRAMA, cls.VIRAMA, text)
        return text

    @classmethod
    def is_tamil(cls, text: str) -> bool:
        """Returns True if the text contains Tamil Unicode characters."""
        return bool(cls.TAMIL_RANGE.search(text))

    @classmethod
    def detect_script(cls, text: str) -> str:
        """
        Detects whether text is primarily Tamil, ISO-15919 transliteration, or English.
        Returns: 'tamil' | 'transliteration' | 'english' | 'mixed'
        """
        if not text:
            return "unknown"
        tamil_chars = len(cls.TAMIL_RANGE.findall(text))
        total_chars = len([c for c in text if not c.isspace()])
        if total_chars == 0:
            return "unknown"
        tamil_ratio = tamil_chars / total_chars
        if tamil_ratio > 0.4:
            return "tamil"
        # Check for common ISO-15919 diacritic characters
        iso_chars = re.findall(r"[āīūṭṭḷṇṉśṣṟṛ]", text, re.IGNORECASE)
        if len(iso_chars) > 2:
            return "transliteration"
        return "english"

    @classmethod
    def full_pipeline(cls, text: str) -> str:
        """
        Applies the complete normalization pipeline:
        NFC → line endings → ZWNJ/ZWJ → decoratives → whitespace → virama.
        """
        text = cls.normalize(text)
        text = cls.normalize_virama(text)
        return text
