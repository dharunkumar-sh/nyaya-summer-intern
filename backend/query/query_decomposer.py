"""
Query decomposer structuring raw input into target locus (Pakṣa), property (Sādhya), and reason (Hetu).
"""
import re
from typing import Dict, Any
from .language_detector import LanguageDetector
from .intent_classifier import IntentClassifier
from .entity_detector import QueryEntityDetector


class QueryDecomposer:
    """Decomposes user input into formal Nyāya constituents."""

    _TINAI_MAP = {
        "mullai": "Mullai",
        "forest": "Mullai",
        "pastoral": "Mullai",
        "முல்லை": "Mullai",
        "காடு": "Mullai",
        "marutam": "Marutam",
        "marutham": "Marutam",
        "agricultural": "Marutam",
        "riverine": "Marutam",
        "plains": "Marutam",
        "மருதம்": "Marutam",
        "வயல்": "Marutam",
        "neytal": "Neytal",
        "neithal": "Neytal",
        "littoral": "Neytal",
        "coastal": "Neytal",
        "sea": "Neytal",
        "ocean": "Neytal",
        "நெய்தல்": "Neytal",
        "கடல்": "Neytal",
        "palai": "Pālai",
        "paalai": "Pālai",
        "arid": "Pālai",
        "desert": "Pālai",
        "wasteland": "Pālai",
        "பாலை": "Pālai",
        "பாலைவனம்": "Pālai",
        "kurinci": "Kuṟiñci",
        "kurinji": "Kuṟiñci",
        "mountain": "Kuṟiñci",
        "montane": "Kuṟiñci",
        "குறிஞ்சி": "Kuṟiñci",
        "மலை": "Kuṟiñci",
    }

    @classmethod
    def decompose(cls, query_text: str, focus: str = "Relationship") -> Dict[str, Any]:
        """Analyzes query text and builds structured question profile."""
        lang_meta = LanguageDetector.detect_language(query_text)
        intent_meta = IntentClassifier.classify_intent(query_text)
        entities = QueryEntityDetector.detect(query_text)

        # Detect primary Tiṇai context from entities first
        detected_tinai = None
        for e in entities:
            if e.get("tinai") and e["tinai"] not in ("General", "Unknown", None):
                detected_tinai = e["tinai"]
                break

        # If not found in entities, scan query text
        if not detected_tinai:
            q_lower = query_text.lower()
            for pattern, tinai_val in cls._TINAI_MAP.items():
                if re.search(r"\b" + re.escape(pattern) + r"\b", q_lower if pattern.isascii() else query_text, re.IGNORECASE):
                    detected_tinai = tinai_val
                    break

        if not detected_tinai:
            # Default to Kuṟiñci (the classical primary archetype of Akam)
            detected_tinai = "Kuṟiñci"

        # Extract primary entity names for thesis personalization
        primary_entity = entities[0]["term"] if entities else detected_tinai

        # Generate default formal thesis (Pakṣa / Sādhya)
        thesis = f"In {detected_tinai} Tiṇai, objective ecological constituents ({primary_entity}) deterministically govern aesthetic mood."
        tamil_thesis = f"{detected_tinai}த் திணை ஒழுக்கத்தில், முதற்பொருளும் கருப்பொருளும் ({primary_entity}) உரிப்பொருளை நிலைநாட்டுகின்றன."

        return {
            "raw_query": query_text,
            "focus_domain": focus,
            "language": lang_meta,
            "intent": intent_meta,
            "entities": entities,
            "detected_tinai": detected_tinai,
            "thesis": thesis,
            "tamil_thesis": tamil_thesis,
            "target_locus_paksa": f"Tolkāppiyam {detected_tinai} Poetics",
        }
