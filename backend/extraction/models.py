"""
Shared data models for the Semantic Knowledge Extraction pipeline.

All types are defined here to serve as the single source of truth
for entities, relations, events, contexts, and extraction provenance.

Design constraints
------------------
- EntityCategory is a typed Enum — no free-text categories allowed
- RelationType is a typed Enum — no free-text predicates allowed
- Every extracted fact carries full provenance (source_id, source_text,
  confidence, extraction_method, validation_status)
- LLM-generated facts are NEVER automatically set to 'validated'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


# ---------------------------------------------------------------------------
# Entity Category
# ---------------------------------------------------------------------------

class EntityCategory(str, Enum):
    """Typed entity categories for Classical Tamil literary knowledge."""
    PERSON           = "PERSON"
    PLACE            = "PLACE"
    OBJECT           = "OBJECT"
    EVENT            = "EVENT"
    CONCEPT          = "CONCEPT"
    INSTITUTION      = "INSTITUTION"
    LITERARY_CONCEPT = "LITERARY_CONCEPT"
    ETHICAL_CONCEPT  = "ETHICAL_CONCEPT"


# ---------------------------------------------------------------------------
# Relation Type  —  controlled vocabulary, no free-text predicates
# ---------------------------------------------------------------------------

class RelationType(str, Enum):
    """
    Controlled relation vocabulary for Tamil literary knowledge extraction.
    Every relation emitted by the pipeline MUST use one of these values.
    Free-text or LLM-generated predicate strings are rejected at the type level.
    """
    # General cross-domain
    ACCUSED_OF        = "accused_of"
    JUDGED            = "judged"
    PRESENTED         = "presented"
    CONTAINS          = "contains"
    HUSBAND_OF        = "husband_of"
    POSSESSES         = "possesses"
    LOCATED_IN        = "located_in"
    CAUSES            = "causes"
    CONTRADICTS       = "contradicts"
    SUPPORTS          = "supports"
    PART_OF           = "part_of"
    CLASSIFIED_AS     = "classified_as"

    # Tolkāppiyam-specific (canonical semiotic predicates)
    PRESIDES_OVER     = "presides_over"
    HAS_HABITAT       = "has_habitat"
    HAS_AFFECTIVE_MOOD = "has_affective_mood"
    CONSISTS_OF       = "consists_of"
    MANIFESTS_AS      = "manifests_as"
    EVOKES_AFFECT     = "evokes_affect"
    GROUNDS_IN        = "grounds_in"
    INCLUDES_COMPONENT = "includes_component"

    @classmethod
    def from_raw(cls, raw: str) -> Optional["RelationType"]:
        """
        Maps a raw predicate string (from corpus triples or rules) to a
        controlled RelationType.  Returns None if the predicate is not
        in the vocabulary — callers must handle None and discard the relation.
        """
        _MAP: Dict[str, RelationType] = {
            # Corpus canonical predicates
            "presidesOver":             cls.PRESIDES_OVER,
            "presides_over":            cls.PRESIDES_OVER,
            "hasHabitat":               cls.HAS_HABITAT,
            "has_habitat":              cls.HAS_HABITAT,
            "hasUripporuḷ":             cls.HAS_AFFECTIVE_MOOD,
            "hasAffectiveMood":         cls.HAS_AFFECTIVE_MOOD,
            "has_affective_mood":       cls.HAS_AFFECTIVE_MOOD,
            "consistsOf":               cls.CONSISTS_OF,
            "consists_of":              cls.CONSISTS_OF,
            "manifestsSignifierFor":    cls.MANIFESTS_AS,
            "manifests_as":             cls.MANIFESTS_AS,
            "deterministicallyGrounds": cls.GROUNDS_IN,
            "grounds_in":               cls.GROUNDS_IN,
            "includesComponent":        cls.INCLUDES_COMPONENT,
            "includes_component":       cls.INCLUDES_COMPONENT,
            "evokesAffect":             cls.EVOKES_AFFECT,
            "evokes_affect":            cls.EVOKES_AFFECT,
            # General predicates
            "accused_of":               cls.ACCUSED_OF,
            "judged":                   cls.JUDGED,
            "presented":                cls.PRESENTED,
            "contains":                 cls.CONTAINS,
            "husband_of":               cls.HUSBAND_OF,
            "possesses":                cls.POSSESSES,
            "located_in":               cls.LOCATED_IN,
            "isSpaceDimensionOf":       cls.LOCATED_IN,
            "causes":                   cls.CAUSES,
            "contradicts":              cls.CONTRADICTS,
            "supports":                 cls.SUPPORTS,
            "hasConstituent":           cls.CONTAINS,
            "part_of":                  cls.PART_OF,
            "classified_as":            cls.CLASSIFIED_AS,
            "isTimeDimensionOf":        cls.CLASSIFIED_AS,
            "formulates":               cls.CONTAINS,
            "manifestsAs":              cls.MANIFESTS_AS,
        }
        return _MAP.get(raw)


# ---------------------------------------------------------------------------
# Validation status
# ---------------------------------------------------------------------------

class ValidationStatus(str, Enum):
    """
    Trust level of an extracted fact.
    Facts are NEVER auto-validated on extraction — they start as UNVERIFIED.
    Only facts sourced directly from scholarly-curated corpus triples may be
    promoted to CORPUS_VALIDATED.  LLM-generated facts remain UNVERIFIED.
    """
    UNVERIFIED        = "unverified"
    CORPUS_VALIDATED  = "corpus_validated"
    MANUALLY_VERIFIED = "manually_verified"
    REJECTED          = "rejected"


# ---------------------------------------------------------------------------
# Extraction method
# ---------------------------------------------------------------------------

class ExtractionMethod(str, Enum):
    LEXICON_MATCH   = "lexicon_match"
    PATTERN_RULE    = "pattern_rule"
    CORPUS_TRIPLE   = "corpus_triple"
    ENTITY_COOCCUR  = "entity_cooccurrence"
    HEURISTIC       = "heuristic"


# ---------------------------------------------------------------------------
# Provenance mixin
# ---------------------------------------------------------------------------

@dataclass
class Provenance:
    """
    Source traceability for every extracted fact.
    Attached to every Entity, Relation, and Event.
    """
    source_id:         str
    source_text:       str
    confidence:        float          # 0.0 – 1.0
    extraction_method: ExtractionMethod
    validation_status: ValidationStatus = ValidationStatus.UNVERIFIED
    extracted_at:      str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id":         self.source_id,
            "source_text":       self.source_text,
            "confidence":        self.confidence,
            "extraction_method": self.extraction_method.value,
            "validation_status": self.validation_status.value,
            "extracted_at":      self.extracted_at,
        }


# ---------------------------------------------------------------------------
# Extracted Entity
# ---------------------------------------------------------------------------

@dataclass
class ExtractedEntity:
    surface_form:    str
    canonical_form:  str
    transliteration: str
    category:        EntityCategory
    tinai:           str
    provenance:      Provenance
    id:              str = field(default_factory=lambda: f"ent-{uuid.uuid4().hex[:8]}")
    attributes:      Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":              self.id,
            "surface_form":    self.surface_form,
            "canonical_form":  self.canonical_form,
            "transliteration": self.transliteration,
            "category":        self.category.value,
            "tinai":           self.tinai,
            "attributes":      self.attributes,
            **self.provenance.to_dict(),
        }


# ---------------------------------------------------------------------------
# Extracted Relation
# ---------------------------------------------------------------------------

@dataclass
class ExtractedRelation:
    subject:    str
    predicate:  RelationType           # MUST be a controlled RelationType
    object:     str
    provenance: Provenance
    id:         str = field(default_factory=lambda: f"rel-{uuid.uuid4().hex[:8]}")
    qualifiers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":         self.id,
            "subject":    self.subject,
            "predicate":  self.predicate.value,
            "object":     self.object,
            "qualifiers": self.qualifiers,
            **self.provenance.to_dict(),
        }


# ---------------------------------------------------------------------------
# Event Context
# ---------------------------------------------------------------------------

@dataclass
class EventContext:
    """
    Discourse-level context surrounding an extracted event.
    All fields are optional — only populate what the text supports.
    """
    speaker:        Optional[str] = None
    situation:      Optional[str] = None
    location:       Optional[str] = None
    genre:          Optional[str] = None   # Akam / Puṟam
    preceding_event: Optional[str] = None
    season:         Optional[str] = None
    time_of_day:    Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker":        self.speaker,
            "situation":      self.situation,
            "location":       self.location,
            "genre":          self.genre,
            "preceding_event": self.preceding_event,
            "season":         self.season,
            "time_of_day":    self.time_of_day,
        }


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """
    Structured event representation with all 8 core fields plus context.
    Every field except actor/action may be None when the text is silent.
    """
    actor:      Optional[str]
    action:     str
    object:     Optional[str]
    location:   Optional[str]
    time:       Optional[str]
    condition:  Optional[str]
    source:     Optional[str]        # narrative source / authority cited
    context:    EventContext
    provenance: Provenance
    id:         str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":        self.id,
            "actor":     self.actor,
            "action":    self.action,
            "object":    self.object,
            "location":  self.location,
            "time":      self.time,
            "condition": self.condition,
            "source":    self.source,
            "context":   self.context.to_dict(),
            **self.provenance.to_dict(),
        }


# ---------------------------------------------------------------------------
# Full Extraction Result
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    Complete output of the SemanticExtractionPipeline for one passage.
    """
    passage_id:   str
    source_text:  str
    entities:     List[ExtractedEntity]
    relations:    List[ExtractedRelation]
    events:       List[Event]
    context:      Dict[str, Any]
    extraction_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        summary = {
            "entity_count":   len(self.entities),
            "relation_count": len(self.relations),
            "event_count":    len(self.events),
            "entity_categories": list({e.category.value for e in self.entities}),
            "relation_types":    list({r.predicate.value for r in self.relations}),
        }
        return {
            "passage_id":         self.passage_id,
            "source_text":        self.source_text,
            "entities":           [e.to_dict() for e in self.entities],
            "relations":          [r.to_dict() for r in self.relations],
            "events":             [ev.to_dict() for ev in self.events],
            "context":            self.context,
            "extraction_summary": summary,
        }
