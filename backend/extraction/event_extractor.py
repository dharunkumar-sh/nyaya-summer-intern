"""
Event extractor for Classical Tamil literary knowledge.

Produces fully structured Event objects with all 8 core fields:
  actor, action, object, location, time, condition, source

plus a nested EventContext:
  speaker, situation, location, genre, preceding_event, season, time_of_day

Every event carries full provenance.  Events are never auto-validated.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import (
    Event,
    EventContext,
    ExtractionMethod,
    Provenance,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Poetic situation detection tables
# ---------------------------------------------------------------------------

_KALAVU_MARKERS = {
    "புணர்தல்", "இரவுக்குறி", "பகற்குறி", "களவு",
    "இயற்கைப் புணர்ச்சி", "களவொழுக்கம்",
}

_KARPU_MARKERS = {
    "கற்பு", "இல்லறம்", "கிழத்தி", "மனைவி", "ஊடல்",
    "கற்பொழுக்கம்",
}

_PURAM_MARKERS = {
    "வெட்சி", "கரந்தை", "வஞ்சி", "காஞ்சி", "உழிஞை",
    "நொச்சி", "தும்பை", "வாகை", "பாடான்", "போர்", "அரசன்",
}

# Tinai → canonical actor (speaker role in interior poetry)
_TINAI_SPEAKER: Dict[str, str] = {
    "Kuṟiñci": "Heroine (mountain)",
    "Mullai":  "Heroine (forest)",
    "Marutam": "Hero / Heroine (riverine)",
    "Neytal":  "Heroine (coastal)",
    "Pālai":   "Hero / Heroine (wasteland)",
    "General": "Poet / Commentator",
}

# Tinai → poetic situation
_TINAI_SITUATION: Dict[str, str] = {
    "Kuṟiñci": "Clandestine union (Kaḷavu phase)",
    "Mullai":  "Patient endurance during hero's absence",
    "Marutam": "Lovers' feigned sulking (Ūṭal)",
    "Neytal":  "Anxious pining at the seashore",
    "Pālai":   "Separation and travail in the wasteland",
    "General": "General poetic / grammatical exposition",
}

# Uripporuḷ (affective mood) → canonical Event action
_AFFECT_ACTION: Dict[str, str] = {
    "புணர்தல்": "Union (Puṇartal) — clandestine meeting",
    "பிரிதல்":  "Separation (Pirital) — hero's departure",
    "இருத்தல்": "Patient endurance (Iruttal) — awaiting return",
    "இரங்கல்":  "Anxious pining (Iraṅkal) — lamenting absence",
    "ஊடல்":    "Feigned estrangement (Ūṭal) — lovers' quarrel",
}

# Seasons
_SEASON_MAP: Dict[str, str] = {
    "கார்": "Kār (Monsoon)",
    "கூதிர்": "Kūtir (Chilly winter)",
    "முன்பனி": "Muṉpaṉi (Early frost)",
    "பின்பனி": "Piṉpaṉi (Late frost)",
    "இளவேனில்": "Iḷavēṉil (Spring)",
    "முதுவேனில்": "Mutuvēṉil (Summer)",
}

# Times of day
_YAMAM_MAP: Dict[str, str] = {
    "மாலை": "Mālai (Evening)",
    "யாமம்": "Yāmam (Midnight)",
    "வைகறை": "Vaikaṟai (Dawn)",
    "காலை": "Kālai (Morning)",
    "நண்பகல்": "Naṇpakal (Noon)",
    "எற்பாடு": "Eṟpāṭu (Sunset)",
}


class EventExtractor:
    """
    Structured event extractor for Classical Tamil verse.

    Detects poetic situations (Kaḷavu / Kaṟpu / Puṟam) and constructs
    full Event objects with actor, action, object, location, time,
    condition, source, and a complete EventContext.
    """

    @classmethod
    def extract(
        cls,
        text: str,
        tinai: str = "General",
        source_id: str = "",
        source_text: str = "",
        preceding_event: Optional[str] = None,
    ) -> List[Event]:
        """
        Extracts structured events from a passage.

        Returns a list of Event objects.  For most classical sūtras this
        yields one primary event (the poetic situation); multi-clause
        sūtras may yield more.
        """
        events: List[Event] = []

        # ---- detect poetic situation ----
        is_kalavu = any(m in text for m in _KALAVU_MARKERS)
        is_karpu  = any(m in text for m in _KARPU_MARKERS)
        is_puram  = any(m in text for m in _PURAM_MARKERS)

        # ---- detect temporal markers ----
        season     = next((v for k, v in _SEASON_MAP.items() if k in text), None)
        time_of_day = next((v for k, v in _YAMAM_MAP.items() if k in text), None)

        # ---- detect explicit affect action ----
        affect_action = next(
            (v for k, v in _AFFECT_ACTION.items() if k in text), None
        )

        # ---- determine genre ----
        genre = "Puṟam (Heroic / Societal)" if is_puram else "Akam (Interior / Aesthetic)"

        # ---- infer actor from tinai ----
        actor = _TINAI_SPEAKER.get(tinai, _TINAI_SPEAKER["General"])

        # ---- infer situation ----
        if is_kalavu:
            situation = "Clandestine union (Kaḷavu phase)"
        elif is_karpu:
            situation = "Chaste conjugal phase (Kaṟpu)"
        elif is_puram:
            situation = "Heroic / societal event (Puṟam)"
        else:
            situation = _TINAI_SITUATION.get(tinai, "General poetic exposition")

        # ---- detect landscape / location from tinai ----
        _tinai_location: Dict[str, str] = {
            "Kuṟiñci": "Mountain landscape (Maivarai)",
            "Mullai":  "Forest landscape (Kāṭu)",
            "Marutam": "River-plain landscape (Tīmpuṉal)",
            "Neytal":  "Coastal landscape (Perumaṇal)",
            "Pālai":   "Arid wasteland (Pālai terrain)",
        }
        location = _tinai_location.get(tinai)

        # ---- detect source authority from text ----
        source_authority: Optional[str] = None
        if "தொல்காப்பியம்" in text or "தொல்காப்பியர்" in text:
            source_authority = "Tolkāppiyam"
        elif "சங்கம்" in text:
            source_authority = "Sangam"

        # ---- build EventContext ----
        ctx = EventContext(
            speaker=actor,
            situation=situation,
            location=location,
            genre=genre,
            preceding_event=preceding_event,
            season=season,
            time_of_day=time_of_day,
        )

        # ---- build primary Event ----
        action = affect_action or situation
        prov = Provenance(
            source_id=source_id,
            source_text=source_text or text[:200],
            confidence=0.75,
            extraction_method=ExtractionMethod.HEURISTIC,
            validation_status=ValidationStatus.UNVERIFIED,
        )

        events.append(
            Event(
                actor=actor,
                action=action,
                object=tinai if tinai != "General" else None,
                location=location,
                time=time_of_day or season,
                condition=f"Tiṇai convention: {tinai}" if tinai != "General" else None,
                source=source_authority,
                context=ctx,
                provenance=prov,
            )
        )

        return events
