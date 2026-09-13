"""
Entity extractor for Classical Tamil literary knowledge.

Identifies entities across 8 typed categories using a curated lexicon
of Tolkāppiyam canonical terms.  Each extracted entity carries full provenance
so downstream reasoning can trace every fact back to its source passage.

EntityCategory values
---------------------
PERSON, PLACE, OBJECT, EVENT, CONCEPT, INSTITUTION,
LITERARY_CONCEPT, ETHICAL_CONCEPT
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import (
    EntityCategory,
    ExtractionMethod,
    ExtractedEntity,
    Provenance,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------

# Each entry: Tamil surface form → metadata dict
# Required keys: canonical_form, transliteration, category, tinai
# Optional:      attributes (dict of extra metadata)

_LEXICON: Dict[str, Dict[str, Any]] = {

    # -----------------------------------------------------------------------
    # PERSON  — historical/mythological persons
    # -----------------------------------------------------------------------
    "தொல்காப்பியர்": {
        "canonical_form":  "Tolkāppiyar",
        "transliteration": "Tolkāppiyar",
        "category":        EntityCategory.PERSON,
        "tinai":           "General",
        "attributes":      {"role": "Grammarian", "work": "Tolkāppiyam"},
    },
    "நக்கீரர்": {
        "canonical_form":  "Nakkīrar",
        "transliteration": "Nakkīrar",
        "category":        EntityCategory.PERSON,
        "tinai":           "General",
        "attributes":      {"role": "Commentator"},
    },
    "சேயோன்": {
        "canonical_form":  "Cēyōṉ",
        "transliteration": "Cēyōṉ",
        "category":        EntityCategory.PERSON,
        "tinai":           "Kuṟiñci",
        "attributes":      {"role": "Deity", "epithet": "Murukaṉ"},
    },
    "மாயோன்": {
        "canonical_form":  "Māyōṉ",
        "transliteration": "Māyōṉ",
        "category":        EntityCategory.PERSON,
        "tinai":           "Mullai",
        "attributes":      {"role": "Deity", "epithet": "Tirumaḷ"},
    },
    "வேந்தன்": {
        "canonical_form":  "Vēntan",
        "transliteration": "Vēntan",
        "category":        EntityCategory.PERSON,
        "tinai":           "Marutam",
        "attributes":      {"role": "Deity", "epithet": "Indra"},
    },
    "வருணன்": {
        "canonical_form":  "Varuṇaṉ",
        "transliteration": "Varuṇaṉ",
        "category":        EntityCategory.PERSON,
        "tinai":           "Neytal",
        "attributes":      {"role": "Deity", "epithet": "Sea-god"},
    },
    "கொற்றவை": {
        "canonical_form":  "Koṟṟavai",
        "transliteration": "Koṟṟavai",
        "category":        EntityCategory.PERSON,
        "tinai":           "Pālai",
        "attributes":      {"role": "Deity", "gender": "Female"},
    },

    # -----------------------------------------------------------------------
    # PLACE  — landscapes, terrains, geographical markers
    # -----------------------------------------------------------------------
    "குறிஞ்சி": {
        "canonical_form":  "Kuṟiñci",
        "transliteration": "Kuṟiñci",
        "category":        EntityCategory.PLACE,
        "tinai":           "Kuṟiñci",
        "attributes":      {"terrain": "Mountain"},
    },
    "முல்லை": {
        "canonical_form":  "Mullai",
        "transliteration": "Mullai",
        "category":        EntityCategory.PLACE,
        "tinai":           "Mullai",
        "attributes":      {"terrain": "Forest"},
    },
    "மருதம்": {
        "canonical_form":  "Marutam",
        "transliteration": "Marutam",
        "category":        EntityCategory.PLACE,
        "tinai":           "Marutam",
        "attributes":      {"terrain": "Riverine plains"},
    },
    "நெய்தல்": {
        "canonical_form":  "Neytal",
        "transliteration": "Neytal",
        "category":        EntityCategory.PLACE,
        "tinai":           "Neytal",
        "attributes":      {"terrain": "Littoral coast"},
    },
    "பாலை": {
        "canonical_form":  "Pālai",
        "transliteration": "Pālai",
        "category":        EntityCategory.PLACE,
        "tinai":           "Pālai",
        "attributes":      {"terrain": "Arid wasteland"},
    },
    "மைவரை": {
        "canonical_form":  "Maivarai",
        "transliteration": "Maivarai",
        "category":        EntityCategory.PLACE,
        "tinai":           "Kuṟiñci",
        "attributes":      {"sub_terrain": "Dark mountain range"},
    },
    "காடு": {
        "canonical_form":  "Kāṭu",
        "transliteration": "Kāṭu",
        "category":        EntityCategory.PLACE,
        "tinai":           "Mullai",
        "attributes":      {"sub_terrain": "Forest"},
    },
    "பெருமணல்": {
        "canonical_form":  "Perumaṇal",
        "transliteration": "Perumaṇal",
        "category":        EntityCategory.PLACE,
        "tinai":           "Neytal",
        "attributes":      {"sub_terrain": "Sandy seashore"},
    },
    "தீம்புனல்": {
        "canonical_form":  "Tīmpuṉal",
        "transliteration": "Tīmpuṉal",
        "category":        EntityCategory.PLACE,
        "tinai":           "Marutam",
        "attributes":      {"sub_terrain": "Sweet-water river plains"},
    },

    # -----------------------------------------------------------------------
    # OBJECT  — biotic signifiers, instruments, artefacts
    # -----------------------------------------------------------------------
    "யாழ்": {
        "canonical_form":  "Yāḻ",
        "transliteration": "Yāḻ",
        "category":        EntityCategory.OBJECT,
        "tinai":           "General",
        "attributes":      {"type": "Musical instrument", "class": "Karupporuḷ"},
    },
    "பறை": {
        "canonical_form":  "Paṟai",
        "transliteration": "Paṟai",
        "category":        EntityCategory.OBJECT,
        "tinai":           "General",
        "attributes":      {"type": "Percussion instrument", "class": "Karupporuḷ"},
    },
    "வேங்கை": {
        "canonical_form":  "Vēṅkai",
        "transliteration": "Vēṅkai",
        "category":        EntityCategory.OBJECT,
        "tinai":           "Kuṟiñci",
        "attributes":      {"type": "Flora", "class": "Karupporuḷ"},
    },
    "மயில்": {
        "canonical_form":  "Mayil",
        "transliteration": "Mayil",
        "category":        EntityCategory.OBJECT,
        "tinai":           "Kuṟiñci",
        "attributes":      {"type": "Fauna", "class": "Karupporuḷ"},
    },
    "நிலம்": {
        "canonical_form":  "Nilam",
        "transliteration": "Nilam",
        "category":        EntityCategory.OBJECT,
        "tinai":           "General",
        "attributes":      {"type": "Spatial dimension", "class": "Mutalporuḷ"},
    },
    "பொழுது": {
        "canonical_form":  "Poḻutu",
        "transliteration": "Poḻutu",
        "category":        EntityCategory.OBJECT,
        "tinai":           "General",
        "attributes":      {"type": "Temporal dimension", "class": "Mutalporuḷ"},
    },

    # -----------------------------------------------------------------------
    # EVENT  — affective moods / narrative situations
    # -----------------------------------------------------------------------
    "புணர்தல்": {
        "canonical_form":  "Puṇartal",
        "transliteration": "Puṇartal",
        "category":        EntityCategory.EVENT,
        "tinai":           "Kuṟiñci",
        "attributes":      {"uripporuḷ": "Union", "phase": "Kaḷavu"},
    },
    "பிரிதல்": {
        "canonical_form":  "Pirital",
        "transliteration": "Pirital",
        "category":        EntityCategory.EVENT,
        "tinai":           "Pālai",
        "attributes":      {"uripporuḷ": "Separation", "phase": "Pālai"},
    },
    "இருத்தல்": {
        "canonical_form":  "Iruttal",
        "transliteration": "Iruttal",
        "category":        EntityCategory.EVENT,
        "tinai":           "Mullai",
        "attributes":      {"uripporuḷ": "Patient endurance", "phase": "Kaṟpu"},
    },
    "இரங்கல்": {
        "canonical_form":  "Iraṅkal",
        "transliteration": "Iraṅkal",
        "category":        EntityCategory.EVENT,
        "tinai":           "Neytal",
        "attributes":      {"uripporuḷ": "Anxious pining", "phase": "Kaṟpu"},
    },
    "ஊடல்": {
        "canonical_form":  "Ūṭal",
        "transliteration": "Ūṭal",
        "category":        EntityCategory.EVENT,
        "tinai":           "Marutam",
        "attributes":      {"uripporuḷ": "Feigned sulking", "phase": "Kaṟpu"},
    },

    # -----------------------------------------------------------------------
    # CONCEPT  — tripartite ontological categories
    # -----------------------------------------------------------------------
    "முதற்பொருள்": {
        "canonical_form":  "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "category":        EntityCategory.CONCEPT,
        "tinai":           "General",
        "attributes":      {"ontology": "Primary spatio-temporal ground"},
    },
    "முதல்": {
        "canonical_form":  "Mutal",
        "transliteration": "Mutal",
        "category":        EntityCategory.CONCEPT,
        "tinai":           "General",
        "attributes":      {"ontology": "Abbreviated form of Mutalporuḷ"},
    },
    "கருப்பொருள்": {
        "canonical_form":  "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "category":        EntityCategory.CONCEPT,
        "tinai":           "General",
        "attributes":      {"ontology": "Biotic environmental signifiers"},
    },
    "உரிப்பொருள்": {
        "canonical_form":  "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "category":        EntityCategory.CONCEPT,
        "tinai":           "General",
        "attributes":      {"ontology": "Psychological affective mood"},
    },
    "மெய்ப்பாடு": {
        "canonical_form":  "Meyppāṭu",
        "transliteration": "Meyppāṭu",
        "category":        EntityCategory.CONCEPT,
        "tinai":           "General",
        "attributes":      {"ontology": "Aesthetic emotional manifestation"},
    },

    # -----------------------------------------------------------------------
    # INSTITUTION  — canonical texts, schools, assemblies
    # -----------------------------------------------------------------------
    "தொல்காப்பியம்": {
        "canonical_form":  "Tolkāppiyam",
        "transliteration": "Tolkāppiyam",
        "category":        EntityCategory.INSTITUTION,
        "tinai":           "General",
        "attributes":      {"type": "Grammar treatise", "period": "Classical Sangam"},
    },
    "சங்கம்": {
        "canonical_form":  "Sangam",
        "transliteration": "Saṅkam",
        "category":        EntityCategory.INSTITUTION,
        "tinai":           "General",
        "attributes":      {"type": "Literary academy"},
    },

    # -----------------------------------------------------------------------
    # LITERARY_CONCEPT  — poetic theory terms
    # -----------------------------------------------------------------------
    "திணை": {
        "canonical_form":  "Tiṇai",
        "transliteration": "Tiṇai",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Poetic ecology / convention"},
    },
    "அகம்": {
        "canonical_form":  "Akam",
        "transliteration": "Akam",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Interior / love poetry"},
    },
    "புறம்": {
        "canonical_form":  "Puṟam",
        "transliteration": "Puṟam",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Exterior / heroic poetry"},
    },
    "செய்யுள்": {
        "canonical_form":  "Ceyyuḷ",
        "transliteration": "Ceyyuḷ",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Verse / poetic composition"},
    },
    "பாடல்": {
        "canonical_form":  "Pāṭal",
        "transliteration": "Pāṭal",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Song / lyric"},
    },
    "களவு": {
        "canonical_form":  "Kaḷavu",
        "transliteration": "Kaḷavu",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Clandestine love phase"},
    },
    "கற்பு": {
        "canonical_form":  "Kaṟpu",
        "transliteration": "Kaṟpu",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Chaste conjugal phase"},
    },
    "அணி": {
        "canonical_form":  "Aṇi",
        "transliteration": "Aṇi",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Poetic figure / embellishment"},
    },
    "உவமை": {
        "canonical_form":  "Uvami",
        "transliteration": "Uvami",
        "category":        EntityCategory.LITERARY_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Simile / comparison"},
    },

    # -----------------------------------------------------------------------
    # ETHICAL_CONCEPT  — moral / dharmic concepts
    # -----------------------------------------------------------------------
    "அன்பு": {
        "canonical_form":  "Aṉpu",
        "transliteration": "Aṉpu",
        "category":        EntityCategory.ETHICAL_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Love / compassion"},
    },
    "அறம்": {
        "canonical_form":  "Aram",
        "transliteration": "Aram",
        "category":        EntityCategory.ETHICAL_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Dharma / righteousness"},
    },
    "இன்பம்": {
        "canonical_form":  "Iṉpam",
        "transliteration": "Iṉpam",
        "category":        EntityCategory.ETHICAL_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Pleasure / aesthetic delight"},
    },
    "பொருள்": {
        "canonical_form":  "Poruḷ",
        "transliteration": "Poruḷ",
        "category":        EntityCategory.ETHICAL_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Wealth / material goal"},
    },
    "வீடு": {
        "canonical_form":  "Vīṭu",
        "transliteration": "Vīṭu",
        "category":        EntityCategory.ETHICAL_CONCEPT,
        "tinai":           "General",
        "attributes":      {"domain": "Liberation / moksha"},
    },
}


class EntityExtractor:
    """
    Lexicon-based entity extractor for Classical Tamil literary texts.

    Extraction is purely rule-based (lexicon lookup + substring match),
    making results fully deterministic and provenance-traceable.
    Every extracted entity carries:
      - category: EntityCategory (one of 8 typed values)
      - provenance: source_id, source_text, confidence, extraction_method,
                    validation_status
    """

    LEXICON: Dict[str, Dict[str, Any]] = _LEXICON

    @classmethod
    def extract(
        cls,
        text: str,
        source_id: str = "",
        source_text: str = "",
        supplemental_entities: Optional[List[str]] = None,
    ) -> List[ExtractedEntity]:
        """
        Extracts entities from text using lexicon matching.

        Parameters
        ----------
        text : str
            The normalized passage text to scan.
        source_id : str
            Identifier of the source passage (for provenance).
        source_text : str
            Raw original text (for provenance; may differ from `text`).
        supplemental_entities : list[str], optional
            Additional entity canonical names already known from corpus metadata
            (e.g., sūtra `entities` list).  These are matched against the
            lexicon's canonical_form field.

        Returns
        -------
        List of ExtractedEntity — deduplicated by surface_form.
        """
        results: List[ExtractedEntity] = []
        seen: set = set()

        # 1. Lexicon scan against normalized text
        for surface, meta in cls.LEXICON.items():
            if surface in text and surface not in seen:
                seen.add(surface)
                prov = Provenance(
                    source_id=source_id,
                    source_text=source_text or text[:200],
                    confidence=0.90,
                    extraction_method=ExtractionMethod.LEXICON_MATCH,
                    validation_status=ValidationStatus.UNVERIFIED,
                )
                results.append(
                    ExtractedEntity(
                        surface_form=surface,
                        canonical_form=meta["canonical_form"],
                        transliteration=meta["transliteration"],
                        category=meta["category"],
                        tinai=meta["tinai"],
                        provenance=prov,
                        attributes=dict(meta.get("attributes", {})),
                    )
                )

        # 2. Supplemental entity promotion from corpus metadata
        if supplemental_entities:
            canonical_index = {
                v["canonical_form"]: (k, v)
                for k, v in cls.LEXICON.items()
            }
            for name in supplemental_entities:
                if name in canonical_index and name not in {
                    e.canonical_form for e in results
                }:
                    surface, meta = canonical_index[name]
                    if surface not in seen:
                        seen.add(surface)
                        prov = Provenance(
                            source_id=source_id,
                            source_text=source_text or text[:200],
                            confidence=0.85,
                            extraction_method=ExtractionMethod.LEXICON_MATCH,
                            validation_status=ValidationStatus.UNVERIFIED,
                        )
                        results.append(
                            ExtractedEntity(
                                surface_form=surface,
                                canonical_form=meta["canonical_form"],
                                transliteration=meta["transliteration"],
                                category=meta["category"],
                                tinai=meta["tinai"],
                                provenance=prov,
                                attributes=dict(meta.get("attributes", {})),
                            )
                        )

        return results

    @classmethod
    def get_categories(cls) -> List[Dict[str, str]]:
        """Returns all supported entity categories with descriptions."""
        descriptions = {
            EntityCategory.PERSON:           "Historical, mythological, or fictional persons",
            EntityCategory.PLACE:            "Geographical places, landscapes, or terrain types",
            EntityCategory.OBJECT:           "Physical objects, instruments, flora, fauna",
            EntityCategory.EVENT:            "Events, actions, or poetic situations (affective moods)",
            EntityCategory.CONCEPT:          "Abstract ontological categories (Mutalporuḷ, etc.)",
            EntityCategory.INSTITUTION:      "Texts, academies, schools, assemblies",
            EntityCategory.LITERARY_CONCEPT: "Poetic theory terms (Tiṇai, Akam, Ceyyuḷ, etc.)",
            EntityCategory.ETHICAL_CONCEPT:  "Moral/dharmic values (Aram, Aṉpu, Vīṭu, etc.)",
        }
        return [
            {"category": cat.value, "description": desc}
            for cat, desc in descriptions.items()
        ]
