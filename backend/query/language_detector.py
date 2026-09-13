"""
Language detector distinguishing Tamil Unicode, ISO 15919 Romanized Transliteration, and English.
"""
import re
from typing import Dict, Any


class LanguageDetector:
    """Classifies input query script and language archetype."""

    TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")
    ISO_DIACRITICS = re.compile(r"[āīūṛṝḷḹēōñṅṇṭṟśṣḥṁṉ]")

    @classmethod
    def detect_language(cls, text: str) -> Dict[str, Any]:
        """Detects whether text is Classical Tamil Unicode, Transliteration, or English."""
        if not text or not text.strip():
            return {"primary_language": "unknown", "script": "empty", "confidence": 0.0}

        tamil_chars = len(cls.TAMIL_REGEX.findall(text))
        iso_chars = len(cls.ISO_DIACRITICS.findall(text))
        total_chars = max(len(text.replace(" ", "")), 1)

        tamil_ratio = tamil_chars / total_chars
        iso_ratio = iso_chars / total_chars

        if tamil_ratio > 0.25:
            return {
                "primary_language": "ta",
                "script": "Tamil Unicode",
                "is_tamil": True,
                "confidence": round(min(tamil_ratio * 1.5, 1.0), 2),
            }
        elif iso_ratio > 0.03 or any(
            w in text.lower() for w in ["tolkappiyam", "kurinci", "tinai", "porulatikaram"]
        ):
            return {
                "primary_language": "iso15919",
                "script": "ISO 15919 Transliteration",
                "is_tamil": False,
                "confidence": 0.88,
            }
        else:
            return {
                "primary_language": "en",
                "script": "Latin (English)",
                "is_tamil": False,
                "confidence": 0.95,
            }
