import re
from typing import Dict, Any


class IntentClassifier:
    """Classifies user's epistemic inquiry goal."""

    # Pre-compiled regex patterns for accurate bilingual classification
    _WHY_PATTERNS = [
        r"\bwhy\b", r"\bjustify\b", r"\breason\b", r"\brationale\b", r"\bsignificance\b",
        r"ஏன்", r"எற்றுக்கு", r"காரணம்", r"எதனால்", r"விளக்குக", r"ஏது"
    ]
    _HOW_PATTERNS = [
        r"\bhow\b", r"\bprocess\b", r"\brelation(ship)?\b", r"\binteract(ion)?\b",
        r"\bconnect(ion)?\b", r"\bgovern(s)?\b", r"\binfluence(s)?\b", r"\bmechanism\b",
        r"எவ்வாறு", r"எங்ஙனம்", r"முறைமை", r"தொடர்பு", r"எப்படி", r"இயைபு", r"இணைப்பு"
    ]
    _WHO_PATTERNS = [
        r"\bwho\b", r"\bwhom\b", r"\bwhose\b", r"\bdeity\b", r"\bgod\b", r"\bgoddess\b",
        r"\bprotagonist\b", r"\bhero\b", r"\bheroine\b", r"\bcompanion\b",
        r"யார்", r"எவர்", r"பாத்திரம்", r"தெய்வம்", r"கடவுள்", r"தலைவன்", r"தலைவி", r"தோழி"
    ]
    _WHAT_PATTERNS = [
        r"\bwhat\b", r"\bwhich\b", r"\bdefine\b", r"\bdefinition\b", r"\bdescribe\b",
        r"\blist\b", r"\bidentify\b",
        r"என்ன", r"எது", r"எவை", r"யாது", r"பொருள்", r"இலக்கணம்", r"கூறுக"
    ]

    @classmethod
    def classify_intent(cls, query: str) -> Dict[str, Any]:
        """Classifies intent using Tamil interrogatives and English keywords."""
        q_lower = query.lower()

        # Check in priority order: Why -> How -> Who -> What (default)
        if any(re.search(p, q_lower if p.isascii() else query, re.IGNORECASE) for p in cls._WHY_PATTERNS):
            return {
                "intent": "Why / Justification",
                "tamil_label": "ஏது / காரணம்",
                "primary_nyaya_focus": "Hetu (Inferential Ground)",
            }
        elif any(re.search(p, q_lower if p.isascii() else query, re.IGNORECASE) for p in cls._HOW_PATTERNS):
            return {
                "intent": "How / Process",
                "tamil_label": "செய்கை / முறைமை",
                "primary_nyaya_focus": "Vyāpti (Universal Concomitance & Application)",
            }
        elif any(re.search(p, q_lower if p.isascii() else query, re.IGNORECASE) for p in cls._WHO_PATTERNS):
            return {
                "intent": "Who / Entity",
                "tamil_label": "பாத்திரம் / தெய்வம்",
                "primary_nyaya_focus": "Pakṣa (Locus Characterization)",
            }
        else:
            return {
                "intent": "What / Fact",
                "tamil_label": "பொருள் / உண்மை",
                "primary_nyaya_focus": "Pratijñā (Target Proposition)",
            }
