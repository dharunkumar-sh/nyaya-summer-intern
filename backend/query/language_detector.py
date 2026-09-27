"""
Language detector distinguishing Tamil Unicode, ISO 15919 Romanized Transliteration, and English.
"""
import re
from typing import Dict, Any


class LanguageDetector:
    """Classifies input query script and language archetype."""

    TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")
    LATIN_REGEX = re.compile(r"[a-zA-Z]")
    ISO_DIACRITICS = re.compile(r"[āīūṛṝḷḹēōñṅṇṭṟśṣḻĀĪŪṚṜḶḸĒŌÑṄṆṬṞŚṢḺ]")

    @classmethod
    def detect_language(cls, text: str) -> Dict[str, Any]:
        """Detects whether text is Classical Tamil Unicode, Transliteration, English, or Mixed."""
        if not text or not text.strip():
            return {
                "primary_language": "unknown",
                "script": "empty",
                "is_tamil": False,
                "is_english": False,
                "is_mixed": False,
                "confidence": 0.0,
            }

        tamil_chars = len(cls.TAMIL_REGEX.findall(text))
        latin_chars = len(cls.LATIN_REGEX.findall(text))
        iso_chars = len(cls.ISO_DIACRITICS.findall(text))
        total_chars = max(len(text.replace(" ", "")), 1)

        tamil_ratio = tamil_chars / total_chars
        latin_ratio = latin_chars / total_chars
        iso_ratio = iso_chars / total_chars

        if tamil_chars > 0 and latin_chars > 0:
            return {
                "primary_language": "mixed",
                "script": "Mixed (Tamil + English)",
                "is_tamil": True,
                "is_english": True,
                "is_mixed": True,
                "tamil_ratio": round(tamil_ratio, 2),
                "latin_ratio": round(latin_ratio, 2),
                "confidence": 0.95,
            }
        elif tamil_chars > 0:
            return {
                "primary_language": "ta",
                "script": "Tamil Unicode",
                "is_tamil": True,
                "is_english": False,
                "is_mixed": False,
                "tamil_ratio": round(tamil_ratio, 2),
                "confidence": round(min(max(tamil_ratio, 0.7) * 1.2, 1.0), 2),
            }
        elif iso_chars > 0 or any(
            w in text.lower() for w in ["tolkappiyam", "kurinci", "tinai", "porulatikaram", "mutalporul", "karupporul", "uriporul", "mullai", "marutam", "neytal", "palai"]
        ):
            return {
                "primary_language": "iso15919",
                "script": "ISO 15919 Transliteration",
                "is_tamil": False,
                "is_english": True,
                "is_mixed": False,
                "confidence": 0.90,
            }
        else:
            return {
                "primary_language": "en",
                "script": "Latin (English)",
                "is_tamil": False,
                "is_english": True,
                "is_mixed": False,
                "confidence": 0.95,
            }

