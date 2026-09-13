"""
Context extractor for Classical Tamil literary passages.

Produces a complete context dict with all requested fields:
  speaker, situation, location, genre, preceding_event,
  season, time_of_day

plus existing temporal markers (season, hour).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Lexical tables (duplicated from event_extractor to keep module independent)
# ---------------------------------------------------------------------------

_SEASONS: Dict[str, str] = {
    "கார்":         "Kār (Monsoon)",
    "கூதிர்":       "Kūtir (Chilly winter)",
    "முன்பனி":      "Muṉpaṉi (Early frost)",
    "பின்பனி":      "Piṉpaṉi (Late frost)",
    "இளவேனில்":     "Iḷavēṉil (Spring)",
    "முதுவேனில்":    "Mutuvēṉil (Summer)",
}

_YAMAMS: Dict[str, str] = {
    "மாலை":    "Mālai (Evening)",
    "யாமம்":   "Yāmam (Midnight)",
    "வைகறை":  "Vaikaṟai (Dawn)",
    "காலை":    "Kālai (Morning)",
    "நண்பகல்": "Naṇpakal (Noon)",
    "எற்பாடு": "Eṟpāṭu (Sunset)",
}

_PURAM_MARKERS = {
    "வெட்சி", "கரந்தை", "வஞ்சி", "காஞ்சி", "உழிஞை",
    "நொச்சி", "தும்பை", "வாகை", "பாடான்", "போர்", "அரசன்",
}

_KALAVU_MARKERS = {
    "புணர்தல்", "இரவுக்குறி", "பகற்குறி", "களவு",
    "இயற்கைப் புணர்ச்சி", "களவொழுக்கம்",
}
_KARPU_MARKERS = {
    "கற்பு", "இல்லறம்", "கிழத்தி", "மனைவி", "ஊடல்",
    "கற்பொழுக்கம்",
}

_TINAI_LOCATION: Dict[str, str] = {
    "Kuṟiñci": "Mountain landscape (Maivarai)",
    "Mullai":  "Forest landscape (Kāṭu)",
    "Marutam": "River-plain landscape (Tīmpuṉal)",
    "Neytal":  "Coastal landscape (Perumaṇal)",
    "Pālai":   "Arid wasteland (Pālai terrain)",
}

_TINAI_SPEAKER: Dict[str, str] = {
    "Kuṟiñci": "Heroine (mountain)",
    "Mullai":  "Heroine (forest)",
    "Marutam": "Hero / Heroine (riverine)",
    "Neytal":  "Heroine (coastal)",
    "Pālai":   "Hero / Heroine (wasteland)",
    "General": "Poet / Commentator",
}

_TINAI_SITUATION: Dict[str, str] = {
    "Kuṟiñci": "Clandestine union (Kaḷavu phase)",
    "Mullai":  "Patient endurance during hero's absence",
    "Marutam": "Lovers' feigned sulking (Ūṭal)",
    "Neytal":  "Anxious pining at the seashore",
    "Pālai":   "Separation and travail in the wasteland",
    "General": "General poetic / grammatical exposition",
}


class ContextExtractor:
    """
    Extracts macro-epistemic and discourse context from a Classical Tamil passage.

    Populates:
      - genre         (Akam / Puṟam)
      - speaker       (inferred from tinai)
      - situation     (poetic phase / dramatic situation)
      - location      (landscape from tinai)
      - preceding_event  (passed in from pipeline)
      - season        (from text temporal markers)
      - time_of_day   (from text temporal markers)
      - has_temporal_marker (bool convenience flag)
    """

    @classmethod
    def extract_context(
        cls,
        text: str,
        tinai: str = "General",
        preceding_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns a complete context dict for one passage.

        Parameters
        ----------
        text : str
            Normalized passage text.
        tinai : str
            Ecological Tiṇai of the passage (from corpus metadata).
        preceding_event : str, optional
            Description of the preceding sūtra's event (for narrative chaining).
        """
        # Genre
        is_puram = any(m in text for m in _PURAM_MARKERS)
        genre = "Puṟam (Heroic / Societal)" if is_puram else "Akam (Interior / Aesthetic)"

        # Poetic phase
        is_kalavu = any(m in text for m in _KALAVU_MARKERS)
        is_karpu  = any(m in text for m in _KARPU_MARKERS)
        if is_kalavu:
            situation = "Clandestine union (Kaḷavu phase)"
        elif is_karpu:
            situation = "Chaste conjugal phase (Kaṟpu)"
        elif is_puram:
            situation = "Heroic / societal event (Puṟam)"
        else:
            situation = _TINAI_SITUATION.get(tinai, "General poetic exposition")

        # Temporal markers
        season      = next((v for k, v in _SEASONS.items() if k in text), None)
        time_of_day = next((v for k, v in _YAMAMS.items() if k in text), None)

        # Speaker & location from tinai
        speaker  = _TINAI_SPEAKER.get(tinai, _TINAI_SPEAKER["General"])
        location = _TINAI_LOCATION.get(tinai)

        return {
            "genre":            genre,
            "speaker":          speaker,
            "situation":        situation,
            "location":         location,
            "preceding_event":  preceding_event,
            "season":           season,
            "time_of_day":      time_of_day,
            "has_temporal_marker": bool(season or time_of_day),
            "is_clandestine":   is_kalavu,
            "is_conjugal":      is_karpu,
            "is_heroic":        is_puram,
            "tinai":            tinai,
        }
