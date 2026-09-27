"""
Classical Tamil Unicode and Text Processing Utilities.
Handles canonical Unicode normalization (NFC/NFD), Tamil script detection,
and linguistic tokenization for Sangam / Tolkāppiyam texts.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List

# Unicode ranges for Tamil script: U+0B80 to U+0BFF
TAMIL_UNICODE_PATTERN = re.compile(r"[\u0B80-\u0BFF]")
PUNCTUATION_PATTERN = re.compile(r"[^\w\s\u0B80-\u0BFF]", flags=re.UNICODE)


def normalize_tamil_text(text: str, form: str = "NFC") -> str:
    """
    Applies Unicode canonical normalization (NFC by default) and cleans whitespace.
    Classical Tamil compound characters (consonant + vowel signs) must be in standard NFC
    form to prevent duplicate representation mismatches.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize(form, text)
    # Normalize multiple newlines and spaces
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def is_tamil_text(text: str) -> bool:
    """Returns True if the text contains Tamil Unicode characters."""
    if not text:
        return False
    return bool(TAMIL_UNICODE_PATTERN.search(text))


def clean_tamil_tokens(text: str) -> str:
    """Removes special punctuation while preserving Tamil glyphs and alphanumeric characters."""
    if not text:
        return ""
    normalized = normalize_tamil_text(text)
    return PUNCTUATION_PATTERN.sub(" ", normalized).strip()


def tokenize_tamil_words(text: str) -> List[str]:
    """Tokenizes text into individual words, respecting Tamil Unicode boundaries."""
    cleaned = clean_tamil_tokens(text)
    if not cleaned:
        return []
    return [word for word in cleaned.split() if word]
