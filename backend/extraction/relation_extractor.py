"""
Relation extractor for Classical Tamil literary knowledge.

Enforces a strictly controlled relation vocabulary:
- All emitted relations use RelationType enum values only
- Free-text predicate strings are rejected via RelationType.from_raw()
- Corpus-embedded triples are promoted with validation_status=CORPUS_VALIDATED
- Rule-inferred relations carry validation_status=UNVERIFIED

Extraction strategies (in order of confidence)
-----------------------------------------------
1. Corpus triple promotion    (conf=0.95, corpus_validated)
2. Entity co-occurrence rules (conf=0.80, unverified)
3. Textual pattern rules      (conf=0.70, unverified)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    ExtractionMethod,
    ExtractedRelation,
    Provenance,
    RelationType,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Textual pattern rules
# Each tuple: (Tamil marker regex, RelationType, role)
# role: "subj_obj" means (token before marker) rel (token after marker)
# ---------------------------------------------------------------------------

_PATTERN_RULES: List[Tuple[str, RelationType]] = [
    # "X உடைய Y" → X POSSESSES Y
    (r"(\S+)\s+உடைய\s+(\S+)", RelationType.POSSESSES),
    # "X ஆல் Y" → X CAUSES Y
    (r"(\S+)\s+ஆல்\s+(\S+)", RelationType.CAUSES),
    # "X இல் Y" → X LOCATED_IN Y
    (r"(\S+)\s+இல்\s+(\S+)", RelationType.LOCATED_IN),
    # "X ஒடு Y" / "X உடன் Y" → X SUPPORTS Y  (sociative = mutual support)
    (r"(\S+)\s+(?:ஒடு|உடன்)\s+(\S+)", RelationType.SUPPORTS),
    # "X எனப்படுவது Y" → X CLASSIFIED_AS Y
    (r"(\S+)\s+(?:எனப்படுவது|என்று\s+சொல்லப்படும்)\s+(\S+)", RelationType.CLASSIFIED_AS),
    # "X என்னும் Y" → X PART_OF Y
    (r"(\S+)\s+என்னும்\s+(\S+)", RelationType.PART_OF),
    # "X கணவன் Y" → X HUSBAND_OF Y
    (r"(\S+)\s+கணவன்\s+(\S+)", RelationType.HUSBAND_OF),
]

# ---------------------------------------------------------------------------
# Entity-pair co-occurrence rules
# tuple: (entity_a canonical, entity_b canonical) → RelationType
# ---------------------------------------------------------------------------

_COOCCUR_RULES: Dict[Tuple[str, str], RelationType] = {
    ("Cēyōṉ",      "Kuṟiñci"):    RelationType.PRESIDES_OVER,
    ("Māyōṉ",      "Mullai"):     RelationType.PRESIDES_OVER,
    ("Vēntan",     "Marutam"):    RelationType.PRESIDES_OVER,
    ("Varuṇaṉ",    "Neytal"):     RelationType.PRESIDES_OVER,
    ("Koṟṟavai",   "Pālai"):      RelationType.PRESIDES_OVER,
    ("Kuṟiñci",    "Maivarai"):   RelationType.HAS_HABITAT,
    ("Mullai",     "Kāṭu"):       RelationType.HAS_HABITAT,
    ("Marutam",    "Tīmpuṉal"):   RelationType.HAS_HABITAT,
    ("Neytal",     "Perumaṇal"): RelationType.HAS_HABITAT,
    ("Kuṟiñci",    "Puṇartal"):   RelationType.HAS_AFFECTIVE_MOOD,
    ("Pālai",      "Pirital"):    RelationType.HAS_AFFECTIVE_MOOD,
    ("Mullai",     "Iruttal"):    RelationType.HAS_AFFECTIVE_MOOD,
    ("Neytal",     "Iraṅkal"):    RelationType.HAS_AFFECTIVE_MOOD,
    ("Marutam",    "Ūṭal"):       RelationType.HAS_AFFECTIVE_MOOD,
    ("Mutalporuḷ", "Nilam"):      RelationType.CONSISTS_OF,
    ("Mutalporuḷ", "Poḻutu"):     RelationType.CONSISTS_OF,
    ("Akattiṇai",  "Mutalporuḷ"): RelationType.CONTAINS,
    ("Akattiṇai",  "Karupporuḷ"): RelationType.CONTAINS,
    ("Akattiṇai",  "Uripporuḷ"):  RelationType.CONTAINS,
    ("Mutalporuḷ", "Uripporuḷ"):  RelationType.GROUNDS_IN,
    ("Karupporuḷ", "Uripporuḷ"):  RelationType.MANIFESTS_AS,
    ("Karupporuḷ", "Vēṅkai"):     RelationType.INCLUDES_COMPONENT,
    ("Karupporuḷ", "Yāḻ"):        RelationType.INCLUDES_COMPONENT,
    ("Karupporuḷ", "Paṟai"):      RelationType.INCLUDES_COMPONENT,
    ("Uripporuḷ",  "Meyppāṭu"):   RelationType.MANIFESTS_AS,
}

# Reverse-index: canonical_form → surface_form (for co-occurrence matching)
_CANONICAL_TO_SURFACE: Dict[str, str] = {
    "Cēyōṉ": "சேயோன்", "Māyōṉ": "மாயோன்", "Vēntan": "வேந்தன்",
    "Varuṇaṉ": "வருணன்", "Koṟṟavai": "கொற்றவை",
    "Kuṟiñci": "குறிஞ்சி", "Mullai": "முல்லை",
    "Marutam": "மருதம்", "Neytal": "நெய்தல்", "Pālai": "பாலை",
    "Maivarai": "மைவரை", "Kāṭu": "காடு", "Tīmpuṉal": "தீம்புனல்",
    "Perumaṇal": "பெருமணல்",
    "Puṇartal": "புணர்தல்", "Pirital": "பிரிதல்", "Iruttal": "இருத்தல்",
    "Iraṅkal": "இரங்கல்", "Ūṭal": "ஊடல்",
    "Mutalporuḷ": "முதற்பொருள்", "Karupporuḷ": "கருப்பொருள்",
    "Uripporuḷ": "உரிப்பொருள்", "Nilam": "நிலம்", "Poḻutu": "பொழுது",
    "Meyppāṭu": "மெய்ப்பாடு",
    "Vēṅkai": "வேங்கை", "Yāḻ": "யாழ்", "Paṟai": "பறை",
    "Tolkāppiyam": "தொல்காப்பியம்",
}


class RelationExtractor:
    """
    Controlled-vocabulary relation extractor.

    All emitted relations use a RelationType enum value.
    Predicates not in the vocabulary are silently discarded.
    """

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @classmethod
    def extract(
        cls,
        text: str,
        entities: List[Dict[str, Any]],
        corpus_triples: Optional[List[Dict[str, str]]] = None,
        source_id: str = "",
        source_text: str = "",
    ) -> List[ExtractedRelation]:
        """
        Extracts relations using three strategies in priority order:
        1. Corpus triple promotion (highest confidence, corpus_validated)
        2. Entity co-occurrence rules (medium confidence, unverified)
        3. Textual pattern rules (lower confidence, unverified)

        Parameters
        ----------
        text : str
            Normalized passage text.
        entities : list[dict]
            Previously extracted entities (from EntityExtractor.extract()).
        corpus_triples : list[dict], optional
            Raw triples from the canonical sūtra dict
            (keys: subject, predicate, object).
        source_id, source_text : str
            Provenance fields.
        """
        results: List[ExtractedRelation] = []
        seen_keys: set = set()

        # Strategy 1: Corpus triple promotion
        if corpus_triples:
            for triple in corpus_triples:
                rel_type = RelationType.from_raw(triple.get("predicate", ""))
                if rel_type is None:
                    continue  # discard unmapped predicates
                key = (triple["subject"], rel_type, triple["object"])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                prov = Provenance(
                    source_id=source_id,
                    source_text=source_text or text[:200],
                    confidence=0.95,
                    extraction_method=ExtractionMethod.CORPUS_TRIPLE,
                    validation_status=ValidationStatus.CORPUS_VALIDATED,
                )
                results.append(
                    ExtractedRelation(
                        subject=triple["subject"],
                        predicate=rel_type,
                        object=triple["object"],
                        provenance=prov,
                    )
                )

        # Strategy 2: Entity co-occurrence rules
        entity_canonicals = {e.get("canonical_form", "") for e in entities}
        for (canon_a, canon_b), rel_type in _COOCCUR_RULES.items():
            if canon_a in entity_canonicals and canon_b in entity_canonicals:
                key = (canon_a, rel_type, canon_b)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                prov = Provenance(
                    source_id=source_id,
                    source_text=source_text or text[:200],
                    confidence=0.80,
                    extraction_method=ExtractionMethod.ENTITY_COOCCUR,
                    validation_status=ValidationStatus.UNVERIFIED,
                )
                results.append(
                    ExtractedRelation(
                        subject=canon_a,
                        predicate=rel_type,
                        object=canon_b,
                        provenance=prov,
                    )
                )

        # Strategy 3: Textual pattern rules
        for pattern, rel_type in _PATTERN_RULES:
            for match in re.finditer(pattern, text):
                subj = match.group(1)
                obj  = match.group(2)
                key  = (subj, rel_type, obj)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                prov = Provenance(
                    source_id=source_id,
                    source_text=source_text or text[:200],
                    confidence=0.70,
                    extraction_method=ExtractionMethod.PATTERN_RULE,
                    validation_status=ValidationStatus.UNVERIFIED,
                )
                results.append(
                    ExtractedRelation(
                        subject=subj,
                        predicate=rel_type,
                        object=obj,
                        provenance=prov,
                    )
                )

        return results

    @classmethod
    def get_relation_types(cls) -> List[Dict[str, str]]:
        """Returns the full controlled relation vocabulary."""
        descriptions = {
            RelationType.ACCUSED_OF:         "X is accused of Y",
            RelationType.JUDGED:             "X is judged by / as Y",
            RelationType.PRESENTED:          "X is presented to Y",
            RelationType.CONTAINS:           "X contains Y as a constituent",
            RelationType.HUSBAND_OF:         "X is husband of Y",
            RelationType.POSSESSES:          "X possesses / owns Y",
            RelationType.LOCATED_IN:         "X is located in / at Y",
            RelationType.CAUSES:             "X causes Y",
            RelationType.CONTRADICTS:        "X contradicts Y",
            RelationType.SUPPORTS:           "X supports / corroborates Y",
            RelationType.PART_OF:            "X is a part of Y",
            RelationType.CLASSIFIED_AS:      "X is classified as Y",
            RelationType.PRESIDES_OVER:      "Deity X presides over landscape Y",
            RelationType.HAS_HABITAT:        "Landscape X has habitat marker Y",
            RelationType.HAS_AFFECTIVE_MOOD: "Tiṇai X has Uripporuḷ (affective mood) Y",
            RelationType.CONSISTS_OF:        "Category X consists of component Y",
            RelationType.MANIFESTS_AS:       "Concept X manifests as / in Y",
            RelationType.EVOKES_AFFECT:      "Signifier X evokes affective response Y",
            RelationType.GROUNDS_IN:         "Concept X is ontologically grounded in Y",
            RelationType.INCLUDES_COMPONENT: "Category X includes biotic component Y",
        }
        return [
            {"relation": rt.value, "description": desc}
            for rt, desc in descriptions.items()
        ]
