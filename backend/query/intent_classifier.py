"""
Query intent classifier mapping inquiry to Nyāya epistemic goals.
Classifies query into: Why / Justification, What / Fact, How / Process, Who / Entity.
"""
from typing import Dict, Any


class IntentClassifier:
    """Classifies user's epistemic inquiry goal."""

    @classmethod
    def classify_intent(cls, query: str) -> Dict[str, Any]:
        """Classifies intent using Tamil interrogatives and English keywords."""
        q_lower = query.lower()

        if any(w in query for w in ["ஏன்", "எற்றுக்கு", "காரணம்", "எதனால்"]) or "why" in q_lower or "justify" in q_lower:
            return {
                "intent": "Why / Justification",
                "tamil_label": "ஏது / காரணம்",
                "primary_nyaya_focus": "Hetu (Inferential Ground)",
            }
        elif any(w in query for w in ["எவ்வாறு", "எங்ஙனம்", "முறைமை", "தொடர்பு"]) or "how" in q_lower or "process" in q_lower:
            return {
                "intent": "How / Process",
                "tamil_label": "செய்கை / முறைமை",
                "primary_nyaya_focus": "Vyāpti (Universal Concomitance & Application)",
            }
        elif any(w in query for w in ["யார்", "எவர்", "பாத்திரம்", "தெய்வம்"]) or "who" in q_lower or "deity" in q_lower:
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
