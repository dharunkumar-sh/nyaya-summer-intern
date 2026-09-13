"""
Query decomposer structuring raw input into target locus (Pakṣa), property (Sādhya), and reason (Hetu).
"""
from typing import Dict, Any
from .language_detector import LanguageDetector
from .intent_classifier import IntentClassifier
from .entity_detector import QueryEntityDetector


class QueryDecomposer:
    """Decomposes user input into formal Nyāya constituents."""

    @classmethod
    def decompose(cls, query_text: str, focus: str = "Relationship") -> Dict[str, Any]:
        """Analyzes query text and builds structured question profile."""
        lang_meta = LanguageDetector.detect_language(query_text)
        intent_meta = IntentClassifier.classify_intent(query_text)
        entities = QueryEntityDetector.detect(query_text)

        # Detect primary Tiṇai context
        detected_tinai = "Kuṟiñci"
        for e in entities:
            if e.get("tinai") and e["tinai"] != "General":
                detected_tinai = e["tinai"]
                break

        # Generate default formal thesis (Pakṣa / Sādhya)
        thesis = f"In {detected_tinai} Tiṇai, objective ecological constituents deterministically govern aesthetic mood."
        tamil_thesis = f"{detected_tinai}த் திணை ஒழுக்கத்தில், முதற்பொருளும் கருப்பொருளும் உரிப்பொருளை நிலைநாட்டுகின்றன."

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
