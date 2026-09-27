"""
Language Detection and Epistemic Terminology Preservation Utilities for Hybrid RAG.

Provides server-side Unicode-aware language detection, explicit user language
override resolution, and classical Tamil terminology preservation for LLM answer synthesis.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Union

# Curated Classical Tamil literary & Nyāya philosophical tokens
CANONICAL_LITERARY_TERMS: List[Dict[str, str]] = [
    {"term": "tolkappiyam", "tamil": "தொல்காப்பியம்", "transliteration": "Tolkāppiyam"},
    {"term": "porulatikaram", "tamil": "பொருளதிகாரம்", "transliteration": "Poruḷatikāram"},
    {"term": "akattinaiyiyal", "tamil": "அகத்திணையியல்", "transliteration": "Akattiṇaiyiyal"},
    {"term": "purattinaiyiyal", "tamil": "புறத்திணையியல்", "transliteration": "Puṟattiṇaiyiyal"},
    {"term": "mutalporul", "tamil": "முதற்பொருள்", "transliteration": "Mutalporuḷ"},
    {"term": "karupporul", "tamil": "கருப்பொருள்", "transliteration": "Karupporuḷ"},
    {"term": "uripporul", "tamil": "உரிப்பொருள்", "transliteration": "Uripporuḷ"},
    {"term": "kurinci", "tamil": "குறிஞ்சி", "transliteration": "Kuṟiñci"},
    {"term": "kurinji", "tamil": "குறிஞ்சி", "transliteration": "Kuṟiñci"},
    {"term": "mullai", "tamil": "முல்லை", "transliteration": "Mullai"},
    {"term": "marutam", "tamil": "மருதம்", "transliteration": "Marutam"},
    {"term": "marutham", "tamil": "மருதம்", "transliteration": "Marutam"},
    {"term": "neytal", "tamil": "நெய்தல்", "transliteration": "Neytal"},
    {"term": "neythal", "tamil": "நெய்தல்", "transliteration": "Neytal"},
    {"term": "palai", "tamil": "பாலை", "transliteration": "Pālai"},
    {"term": "tinai", "tamil": "திணை", "transliteration": "Tiṇai"},
    {"term": "thinai", "tamil": "திணை", "transliteration": "Tiṇai"},
    {"term": "punartal", "tamil": "புணர்தல்", "transliteration": "Puṇartal"},
    {"term": "iruttal", "tamil": "இருத்தல்", "transliteration": "Iruttal"},
    {"term": "utal", "tamil": "ஊடல்", "transliteration": "Ūṭal"},
    {"term": "oodal", "tamil": "ஊடல்", "transliteration": "Ūṭal"},
    {"term": "irankal", "tamil": "இரங்கல்", "transliteration": "Iraṅkal"},
    {"term": "pirital", "tamil": "பிரிதல்", "transliteration": "Pirital"},
    {"term": "mayon", "tamil": "மாயோன்", "transliteration": "Māyōṉ"},
    {"term": "ceyon", "tamil": "சேயோன்", "transliteration": "Cēyōṉ"},
    {"term": "varunan", "tamil": "வருணன்", "transliteration": "Varuṇaṉ"},
    {"term": "vendan", "tamil": "வேந்தன்", "transliteration": "Vēntaṉ"},
    {"term": "kotravai", "tamil": "கொற்றவை", "transliteration": "Koṟṟavai"},
    {"term": "vyapti", "tamil": "வியாப்தி", "transliteration": "Vyāpti"},
    {"term": "pratijna", "tamil": "பிரதிஞ்ஞா", "transliteration": "Pratijñā"},
    {"term": "hetu", "tamil": "ஹேது", "transliteration": "Hetu"},
    {"term": "udaharana", "tamil": "உதாரணம்", "transliteration": "Udāharaṇa"},
    {"term": "upanaya", "tamil": "உபநயம்", "transliteration": "Upanaya"},
    {"term": "nigamana", "tamil": "நிகமனம்", "transliteration": "Nigamana"},
    {"term": "hetvabhasa", "tamil": "ஹேத்வாபாசம்", "transliteration": "Hetvābhāsa"},
    {"term": "pramana", "tamil": "பிரமாணம்", "transliteration": "Pramāṇa"},
]

# Explicit user language override patterns
EXPLICIT_TAMIL_PATTERNS = [
    r"\banswer in tamil\b",
    r"\bin tamil\b",
    r"\btamil please\b",
    r"\brespond in tamil\b",
    r"தமிழில்\s*(விடை|பதில்|எழுதவும்)",
    r"தமிழில்\s*கூறவும்",
    r"தமிழில்",
]

EXPLICIT_ENGLISH_PATTERNS = [
    r"\banswer in english\b",
    r"\bin english\b",
    r"\benglish please\b",
    r"\brespond in english\b",
    r"ஆங்கிலத்தில்\s*(விடை|பதில்|எழுதவும்)",
    r"ஆங்கிலத்தில்",
]


def strip_diacritics(text: str) -> str:
    """Normalizes Unicode text and strips Romanized Tamil diacritics for resilient token matching."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    replacements = {
        "ṟ": "r", "ñ": "n", "ṅ": "n", "ḷ": "l", "ḻ": "l",
        "ō": "o", "ē": "e", "ṭ": "t", "ṯ": "t", "ṇ": "n",
        "ā": "a", "ī": "i", "ū": "u",
    }
    lowered = stripped.lower()
    for src, tgt in replacements.items():
        lowered = lowered.replace(src, tgt)
    return lowered


def detect_query_language(
    query: str,
    client_language: Optional[Union[Dict[str, Any], str]] = None,
) -> Dict[str, Any]:
    """
    Detects the user inquiry language (Tamil, English, or Bilingual) and any explicit user language request.

    Returns:
        Dict containing language code ('ta', 'en', 'bilingual'), target response language,
        detected classical terms, and strict LLM instruction guidelines.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return {
            "code": "empty",
            "primary_language": "english",
            "target_response_language": "english",
            "label": "Awaiting Query",
            "is_tamil": False,
            "is_english": True,
            "is_bilingual": False,
            "has_classical_terms": False,
            "detected_terms": [],
            "instruction_note": "Awaiting query. Defaulting to English with Classical Tamil terminology preservation.",
        }

    # 1. Check for explicit user language overrides in query text
    lower_query = clean_query.lower()
    explicit_target = None
    for pattern in EXPLICIT_TAMIL_PATTERNS:
        if re.search(pattern, lower_query, re.IGNORECASE):
            explicit_target = "tamil"
            break

    if not explicit_target:
        for pattern in EXPLICIT_ENGLISH_PATTERNS:
            if re.search(pattern, lower_query, re.IGNORECASE):
                explicit_target = "english"
                break

    # 2. Count character frequencies
    # Tamil Unicode block: U+0B80 to U+0BFF
    tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", clean_query))
    latin_chars = len(re.findall(r"[a-zA-Z]", clean_query))
    total_letters = tamil_chars + latin_chars

    # 3. Detect embedded Classical Tamil terms
    norm_query = strip_diacritics(clean_query)
    detected_terms: List[Dict[str, str]] = []
    for entry in CANONICAL_LITERARY_TERMS:
        if entry["tamil"] in clean_query:
            detected_terms.append(entry)
            continue
        term_norm = strip_diacritics(entry["term"])
        # Word boundary matching
        if re.search(rf"(^|[^a-zA-Z0-9]){term_norm}([^a-zA-Z0-9]|$)", norm_query, re.IGNORECASE):
            detected_terms.append(entry)

    tamil_ratio = (tamil_chars / total_letters) if total_letters > 0 else 0.0
    latin_ratio = (latin_chars / total_letters) if total_letters > 0 else 0.0

    # 4. Resolve client hint if provided
    client_code = ""
    if isinstance(client_language, dict):
        client_code = str(client_language.get("code") or "").lower()
    elif isinstance(client_language, str):
        client_code = client_language.strip().lower()

    # 5. Determine base detected language
    if tamil_chars > 0 and (latin_chars == 0 or tamil_ratio >= 0.70):
        code = "ta"
        primary = "tamil"
        label = "தமிழ் (Tamil)"
        is_tamil = True
        is_english = False
        is_bilingual = False
    elif tamil_chars > 0 and latin_chars > 0:
        code = "bilingual"
        primary = "bilingual"
        label = "Bilingual (தமிழ் / English)"
        is_tamil = True
        is_english = True
        is_bilingual = True
    else:
        code = "en"
        primary = "english"
        label = "English (with Classical Terms)" if detected_terms else "English"
        is_tamil = False
        is_english = True
        is_bilingual = False

    # Respect explicit user request if present, otherwise default to primary query language
    target_lang = explicit_target or (primary if primary in ("tamil", "english") else "tamil" if client_code == "ta" else "english")

    instruction_note = (
        f"User query is primarily in {label}. "
        f"Respond with the primary verdict and justification in {target_lang.upper()}, "
        "while providing both authentic Tamil and scholarly English synthesis. "
        "Strictly preserve all Classical Tamil terminology, proper names, and sūtra citations without translation distortion."
    )

    return {
        "code": code,
        "primary_language": primary,
        "target_response_language": target_lang,
        "label": label,
        "is_tamil": is_tamil,
        "is_english": is_english,
        "is_bilingual": is_bilingual,
        "has_classical_terms": bool(detected_terms),
        "detected_terms": [t["transliteration"] for t in detected_terms],
        "tamil_ratio": round(tamil_ratio, 2),
        "latin_ratio": round(latin_ratio, 2),
        "explicit_override": explicit_target,
        "instruction_note": instruction_note,
    }


def format_insufficient_evidence_response(
    lang_info: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    """
    Constructs an explicit, non-speculative insufficient evidence response
    aligned with the user's inquiry language. Guarantees zero fabricated answers or citations.
    """
    is_tamil = lang_info.get("primary_language") == "tamil" or lang_info.get("code") == "ta"

    if is_tamil:
        tamil_answer = "தீர்மானிக்கப் போதுமான தொல்காப்பிய மூலச் சான்றுகள் கிடைக்கவில்லை."
        english_answer = "Insufficient canonical evidence retrieved to answer query without speculation."
        verdict_status = "போதிய மூலச் சான்றுகள் இல்லை (Insufficient Evidence)"
        justification_ta = (
            f"தொல்காப்பிய மூல நூல்களில் வினவப்பட்ட கருதுகோளுக்குப் போதிய பொருத்தமான சூத்திரங்கள் மீட்கப்படவில்லை ({reason}). "
            "சான்றுகளற்ற ஊக விடைகள் தடுத்து நிறுத்தப்பட்டன."
        )
        justification_en = (
            f"Retrieved canonical evidence fell below required relevance and count criteria ({reason}). "
            "Speculative answer generation was strictly blocked in accordance with Nyāya epistemic boundaries."
        )
        subtitle = f"மூலச் சான்றுப் பற்றாக்குறை: {reason}"
    else:
        tamil_answer = "தீர்மானிக்கப் போதுமான தொல்காப்பியச் சான்றுகள் கிடைக்கவில்லை."
        english_answer = "Insufficient canonical evidence retrieved to answer query without speculation."
        verdict_status = "Insufficient Canonical Evidence (போதிய சான்றுகள் இல்லை)"
        justification_ta = (
            f"வினாவிற்குரிய தொல்காப்பியச் சான்றுகளின் பொருத்தம் அல்லது எண்ணிக்கை போதாமையால் முடிவு நிறுவப்படவில்லை ({reason})."
        )
        justification_en = (
            f"Retrieved canonical passages did not satisfy the minimum relevance or verification threshold ({reason}). "
            "Speculative extrapolation without source evidence is strictly prohibited."
        )
        subtitle = f"Evidence threshold unmet: {reason}"

    return {
        "tamilAnswer": tamil_answer,
        "englishAnswer": english_answer,
        "subtitle": subtitle,
        "confidenceScore": 0.0,
        "starsCount": 0.0,
        "verdictStatus": verdict_status,
        "justificationTamil": normalize_tamil_justification(
            justification_ta,
            fallback="போதிய மூலச் சான்றுகள் இல்லாததால் முடிவு நிறுவப்படவில்லை.",
        ),
        "justificationEnglish": justification_en,
        "keySources": [],
    }


_TAMIL_TINAI_NAMES = {
    "Kuṟiñci": "குறிஞ்சி",
    "Kurinji": "குறிஞ்சி",
    "Mullai": "முல்லை",
    "Marutam": "மருதம்",
    "Neytal": "நெய்தல்",
    "Pālai": "பாலை",
    "Palai": "பாலை",
}


def normalize_tamil_justification(text: Optional[str], fallback: str = "") -> str:
    """
    Keeps Tamil justification prose free of Latin words and inline source IDs.

    Source identifiers remain available in the structured keySources field, so
    removing them here does not lose citation data.
    """
    value = str(text or "").strip()
    for source_name, tamil_name in _TAMIL_TINAI_NAMES.items():
        value = value.replace(source_name, tamil_name)

    # Remove parenthesized Latin citations such as (tol-porul-akam-005).
    value = re.sub(r"\([^()]*[A-Za-z][^()]*\)", "", value)
    # Remove remaining Latin words, including source IDs and transliterations.
    value = re.sub(r"\b[A-Za-z][A-Za-z0-9_.-]*\b", "", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"\(\s*\)|\[\s*\]", "", value)
    value = value.strip(" \t,;:-")

    return value or fallback
