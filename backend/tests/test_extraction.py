"""
Comprehensive tests for the Semantic Knowledge Extraction module.

Tests are deterministic: same input always produces same output.

Test classes
------------
TestEntityCategory        — all 8 EntityCategory enum values
TestRelationType          — controlled vocabulary + from_raw()
TestValidationStatus      — status values and their semantics
TestProvenance            — provenance schema and to_dict()
TestExtractedEntity       — entity schema, category, provenance
TestExtractedRelation     — relation schema, controlled predicate
TestEvent                 — Event all-8-fields + EventContext
TestExtractionResult      — full result schema + to_dict()
TestEntityExtractor       — lexicon extraction, categories
TestRelationExtractor     — 3 strategies, corpus validation, free-text rejection
TestEventExtractor        — poetic situation, all event fields
TestContextExtractor      — all context fields present
TestExtractionPipeline    — single, batch, sutra_id modes
TestExtractionApiEndpoints — 4 API endpoints
"""
import pytest

from app import create_app
from extraction.models import (
    EntityCategory,
    RelationType,
    ValidationStatus,
    ExtractionMethod,
    Provenance,
    ExtractedEntity,
    ExtractedRelation,
    EventContext,
    Event,
    ExtractionResult,
)
from extraction.entity_extractor import EntityExtractor
from extraction.relation_extractor import RelationExtractor
from extraction.event_extractor import EventExtractor
from extraction.context_extractor import ContextExtractor
from extraction.pipeline import SemanticExtractionPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KURINCHI_SUTRA = {
    "id":                "tol-porul-akam-005",
    "sutra_number":      5,
    "atikaram":          "Poruḷatikāram",
    "iyal":              "Akattiṇaiyiyal",
    "tamil_text": (
        "மாயோன் மேய காடுறை உலகமும்\n"
        "சேயோன் மேய மைவரை உலகமும்\n"
        "வேந்தன் மேய தீம்புனல் உலகமும்\n"
        "வருணன் மேய பெருமணல் உலகமும்\n"
        "முல்லை குறிஞ்சி மருதம் நெய்தல்எனச்\n"
        "சொல்லிய முறையால் சொல்லவும் படுமே."
    ),
    "transliteration":   "māyōṉ mēya kāṭuṟai ulakamum ...",
    "english_translation": "The forested realm overseen by Māyōṉ (Mullai)...",
    "category":          "Ecological Deity & Habitat Concordance",
    "tinai":             "Kuṟiñci",
    "entities":          ["Cēyōṉ", "Kuṟiñci", "Maivarai", "Māyōṉ", "Mullai"],
    "triples": [
        {"subject": "Cēyōṉ",    "predicate": "presidesOver", "object": "Kuṟiñci"},
        {"subject": "Kuṟiñci",  "predicate": "hasHabitat",   "object": "Maivarai (Mountain)"},
        {"subject": "Māyōṉ",    "predicate": "presidesOver", "object": "Mullai"},
        {"subject": "Mullai",   "predicate": "hasHabitat",   "object": "Kāṭu (Forest)"},
        {"subject": "Vēntan",   "predicate": "presidesOver", "object": "Marutam"},
        {"subject": "Varuṇaṉ",  "predicate": "presidesOver", "object": "Neytal"},
    ],
    "nyaya_mapping": {"member": "Udāharaṇa", "pramana": "Upamāna + Pratyakṣa"},
}

AKAM_SUTRA = {
    "id":           "tol-porul-akam-003",
    "sutra_number": 3,
    "atikaram":     "Poruḷatikāram",
    "iyal":         "Akattiṇaiyiyal",
    "tamil_text": (
        "முதல்கரு உரிப்பொருள் என்ற மூன்றே\n"
        "நுவலும் காலை முறைசிறந் தனவே\n"
        "பாடலுட் பயின்றவை நாடும் காலை."
    ),
    "tinai":    "General",
    "entities": ["Mutalporuḷ", "Karupporuḷ", "Uripporuḷ"],
    "triples":  [
        {"subject": "Akattiṇai", "predicate": "hasConstituent", "object": "Mutalporuḷ"},
        {"subject": "Akattiṇai", "predicate": "hasConstituent", "object": "Karupporuḷ"},
        {"subject": "Mutalporuḷ", "predicate": "deterministicallyGrounds", "object": "Uripporuḷ"},
    ],
}

PROV = Provenance(
    source_id="test-001",
    source_text="test text",
    confidence=0.9,
    extraction_method=ExtractionMethod.LEXICON_MATCH,
    validation_status=ValidationStatus.UNVERIFIED,
)


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


@pytest.fixture
def pipeline():
    return SemanticExtractionPipeline()


# ===========================================================================
# 1. EntityCategory enum
# ===========================================================================

class TestEntityCategory:

    def test_all_8_categories_exist(self):
        expected = {
            "PERSON", "PLACE", "OBJECT", "EVENT",
            "CONCEPT", "INSTITUTION", "LITERARY_CONCEPT", "ETHICAL_CONCEPT",
        }
        actual = {cat.value for cat in EntityCategory}
        assert expected == actual

    def test_person_value(self):
        assert EntityCategory.PERSON.value == "PERSON"

    def test_place_value(self):
        assert EntityCategory.PLACE.value == "PLACE"

    def test_object_value(self):
        assert EntityCategory.OBJECT.value == "OBJECT"

    def test_event_value(self):
        assert EntityCategory.EVENT.value == "EVENT"

    def test_concept_value(self):
        assert EntityCategory.CONCEPT.value == "CONCEPT"

    def test_institution_value(self):
        assert EntityCategory.INSTITUTION.value == "INSTITUTION"

    def test_literary_concept_value(self):
        assert EntityCategory.LITERARY_CONCEPT.value == "LITERARY_CONCEPT"

    def test_ethical_concept_value(self):
        assert EntityCategory.ETHICAL_CONCEPT.value == "ETHICAL_CONCEPT"


# ===========================================================================
# 2. RelationType enum
# ===========================================================================

class TestRelationType:

    REQUIRED_RELATIONS = {
        "accused_of", "judged", "presented", "contains",
        "husband_of", "possesses", "located_in", "causes",
        "contradicts", "supports", "part_of", "classified_as",
        "presides_over", "has_habitat", "has_affective_mood",
        "consists_of", "manifests_as", "evokes_affect",
        "grounds_in", "includes_component",
    }

    def test_all_required_relations_exist(self):
        actual = {rt.value for rt in RelationType}
        assert self.REQUIRED_RELATIONS.issubset(actual)

    def test_from_raw_corpus_predicate(self):
        assert RelationType.from_raw("presidesOver") == RelationType.PRESIDES_OVER

    def test_from_raw_has_habitat(self):
        assert RelationType.from_raw("hasHabitat") == RelationType.HAS_HABITAT

    def test_from_raw_uripporuḷ(self):
        assert RelationType.from_raw("hasUripporuḷ") == RelationType.HAS_AFFECTIVE_MOOD

    def test_from_raw_deterministically_grounds(self):
        assert RelationType.from_raw("deterministicallyGrounds") == RelationType.GROUNDS_IN

    def test_from_raw_unknown_returns_none(self):
        """Free-text predicates not in vocabulary return None — callers must discard."""
        assert RelationType.from_raw("someFreeTextPredicate") is None

    def test_from_raw_llm_predicate_rejected(self):
        assert RelationType.from_raw("expressesFeelingOfLonging") is None

    def test_from_raw_empty_string_returns_none(self):
        assert RelationType.from_raw("") is None

    def test_from_raw_has_constituent(self):
        assert RelationType.from_raw("hasConstituent") == RelationType.CONTAINS


# ===========================================================================
# 3. ValidationStatus
# ===========================================================================

class TestValidationStatus:

    def test_unverified_value(self):
        assert ValidationStatus.UNVERIFIED.value == "unverified"

    def test_corpus_validated_value(self):
        assert ValidationStatus.CORPUS_VALIDATED.value == "corpus_validated"

    def test_manually_verified_value(self):
        assert ValidationStatus.MANUALLY_VERIFIED.value == "manually_verified"

    def test_rejected_value(self):
        assert ValidationStatus.REJECTED.value == "rejected"


# ===========================================================================
# 4. Provenance
# ===========================================================================

class TestProvenance:

    def test_to_dict_schema(self):
        d = PROV.to_dict()
        required = {
            "source_id", "source_text", "confidence",
            "extraction_method", "validation_status", "extracted_at",
        }
        assert required.issubset(d.keys())

    def test_default_unverified(self):
        p = Provenance(
            source_id="x", source_text="y", confidence=0.8,
            extraction_method=ExtractionMethod.LEXICON_MATCH,
        )
        assert p.validation_status == ValidationStatus.UNVERIFIED

    def test_corpus_triple_can_be_corpus_validated(self):
        p = Provenance(
            source_id="x", source_text="y", confidence=0.95,
            extraction_method=ExtractionMethod.CORPUS_TRIPLE,
            validation_status=ValidationStatus.CORPUS_VALIDATED,
        )
        assert p.validation_status == ValidationStatus.CORPUS_VALIDATED


# ===========================================================================
# 5. ExtractedEntity
# ===========================================================================

class TestExtractedEntity:

    ENTITY = ExtractedEntity(
        surface_form="சேயோன்",
        canonical_form="Cēyōṉ",
        transliteration="Cēyōṉ",
        category=EntityCategory.PERSON,
        tinai="Kuṟiñci",
        provenance=PROV,
    )

    def test_entity_to_dict_schema(self):
        d = self.ENTITY.to_dict()
        required = {
            "id", "surface_form", "canonical_form", "transliteration",
            "category", "tinai", "source_id", "source_text",
            "confidence", "extraction_method", "validation_status",
        }
        assert required.issubset(d.keys())

    def test_category_is_string_in_dict(self):
        d = self.ENTITY.to_dict()
        assert isinstance(d["category"], str)
        assert d["category"] == "PERSON"

    def test_id_auto_assigned(self):
        assert self.ENTITY.id.startswith("ent-")

    def test_unique_ids(self):
        e2 = ExtractedEntity(
            surface_form="மாயோன்",
            canonical_form="Māyōṉ",
            transliteration="Māyōṉ",
            category=EntityCategory.PERSON,
            tinai="Mullai",
            provenance=PROV,
        )
        assert self.ENTITY.id != e2.id


# ===========================================================================
# 6. ExtractedRelation
# ===========================================================================

class TestExtractedRelation:

    REL = ExtractedRelation(
        subject="Cēyōṉ",
        predicate=RelationType.PRESIDES_OVER,
        object="Kuṟiñci",
        provenance=PROV,
    )

    def test_relation_to_dict_schema(self):
        d = self.REL.to_dict()
        required = {
            "id", "subject", "predicate", "object",
            "source_id", "source_text", "confidence",
            "extraction_method", "validation_status",
        }
        assert required.issubset(d.keys())

    def test_predicate_is_string_in_dict(self):
        d = self.REL.to_dict()
        assert isinstance(d["predicate"], str)
        assert d["predicate"] == "presides_over"

    def test_predicate_must_be_relation_type(self):
        """Verify type-level enforcement — RelationType is required."""
        with pytest.raises((TypeError, AttributeError, ValueError)):
            _ = ExtractedRelation(
                subject="X",
                predicate="some_free_text",   # wrong type
                object="Y",
                provenance=PROV,
            ).to_dict()["predicate"]  # will fail at enum .value access


# ===========================================================================
# 7. Event and EventContext
# ===========================================================================

class TestEvent:

    CTX = EventContext(
        speaker="Heroine (mountain)",
        situation="Clandestine union (Kaḷavu phase)",
        location="Mountain landscape (Maivarai)",
        genre="Akam (Interior / Aesthetic)",
        preceding_event=None,
        season="Kār (Monsoon)",
        time_of_day="Mālai (Evening)",
    )

    EVT = Event(
        actor="Heroine (mountain)",
        action="Union (Puṇartal) — clandestine meeting",
        object="Kuṟiñci",
        location="Mountain landscape (Maivarai)",
        time="Mālai (Evening)",
        condition="Tiṇai convention: Kuṟiñci",
        source="Tolkāppiyam",
        context=CTX,
        provenance=PROV,
    )

    def test_event_all_8_core_fields_present(self):
        d = self.EVT.to_dict()
        for field in ("actor", "action", "object", "location", "time", "condition", "source"):
            assert field in d, f"Missing field: {field}"

    def test_event_context_present(self):
        d = self.EVT.to_dict()
        assert "context" in d

    def test_event_context_all_fields(self):
        ctx = self.EVT.to_dict()["context"]
        for field in ("speaker", "situation", "location", "genre",
                      "preceding_event", "season", "time_of_day"):
            assert field in ctx, f"Missing context field: {field}"

    def test_event_id_auto_assigned(self):
        assert self.EVT.id.startswith("evt-")

    def test_event_provenance_in_dict(self):
        d = self.EVT.to_dict()
        assert "source_id" in d
        assert "validation_status" in d

    def test_event_context_to_dict(self):
        ctx_dict = self.CTX.to_dict()
        assert ctx_dict["speaker"]   == "Heroine (mountain)"
        assert ctx_dict["genre"]     == "Akam (Interior / Aesthetic)"
        assert ctx_dict["season"]    == "Kār (Monsoon)"
        assert ctx_dict["time_of_day"] == "Mālai (Evening)"


# ===========================================================================
# 8. ExtractionResult
# ===========================================================================

class TestExtractionResult:

    RESULT = ExtractionResult(
        passage_id="test-001",
        source_text="sample text",
        entities=[TestEvent.EVT.__class__.__mro__[0]],   # placeholder; real test below
        relations=[],
        events=[],
        context={},
    )

    def test_result_to_dict_schema(self):
        e = ExtractedEntity(
            surface_form="சேயோன்", canonical_form="Cēyōṉ",
            transliteration="Cēyōṉ", category=EntityCategory.PERSON,
            tinai="Kuṟiñci", provenance=PROV,
        )
        r = ExtractedRelation(
            subject="Cēyōṉ", predicate=RelationType.PRESIDES_OVER,
            object="Kuṟiñci", provenance=PROV,
        )
        result = ExtractionResult(
            passage_id="p1", source_text="text",
            entities=[e], relations=[r], events=[], context={"genre": "Akam"},
        )
        d = result.to_dict()
        required = {
            "passage_id", "source_text", "entities", "relations",
            "events", "context", "extraction_summary",
        }
        assert required.issubset(d.keys())

    def test_extraction_summary_counts(self):
        e = ExtractedEntity(
            surface_form="சேயோன்", canonical_form="Cēyōṉ",
            transliteration="Cēyōṉ", category=EntityCategory.PERSON,
            tinai="Kuṟiñci", provenance=PROV,
        )
        r = ExtractedRelation(
            subject="Cēyōṉ", predicate=RelationType.PRESIDES_OVER,
            object="Kuṟiñci", provenance=PROV,
        )
        result = ExtractionResult(
            passage_id="p1", source_text="text",
            entities=[e], relations=[r], events=[], context={},
        )
        summary = result.to_dict()["extraction_summary"]
        assert summary["entity_count"]   == 1
        assert summary["relation_count"] == 1
        assert summary["event_count"]    == 0


# ===========================================================================
# 9. EntityExtractor
# ===========================================================================

class TestEntityExtractor:

    def test_extracts_deity(self):
        entities = EntityExtractor.extract(
            "சேயோன் மேய மைவரை உலகமும்", source_id="t1"
        )
        canonicals = [e.canonical_form for e in entities]
        assert "Cēyōṉ" in canonicals

    def test_extracts_place(self):
        entities = EntityExtractor.extract("குறிஞ்சி நிலம்", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.PLACE in cats

    def test_extracts_literary_concept(self):
        entities = EntityExtractor.extract("திணை நெறி பற்றி", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.LITERARY_CONCEPT in cats

    def test_extracts_ethical_concept(self):
        entities = EntityExtractor.extract("அறம் மற்றும் இன்பம்", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.ETHICAL_CONCEPT in cats

    def test_extracts_institution(self):
        entities = EntityExtractor.extract("தொல்காப்பியம் கூறுவது", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.INSTITUTION in cats

    def test_extracts_concept(self):
        entities = EntityExtractor.extract("உரிப்பொருள் முதற்பொருள் கருப்பொருள்", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.CONCEPT in cats

    def test_extracts_object(self):
        entities = EntityExtractor.extract("யாழ் இசை பறை", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.OBJECT in cats

    def test_extracts_event_category(self):
        entities = EntityExtractor.extract("புணர்தல் மற்றும் பிரிதல்", source_id="t1")
        cats = [e.category for e in entities]
        assert EntityCategory.EVENT in cats

    def test_all_entities_have_provenance(self):
        entities = EntityExtractor.extract(
            KURINCHI_SUTRA["tamil_text"], source_id="t1", source_text="raw"
        )
        for e in entities:
            assert e.provenance.source_id == "t1"
            assert e.provenance.validation_status == ValidationStatus.UNVERIFIED

    def test_no_duplicates_in_output(self):
        entities = EntityExtractor.extract(
            "சேயோன் சேயோன் குறிஞ்சி", source_id="t1"
        )
        surface_forms = [e.surface_form for e in entities]
        assert len(surface_forms) == len(set(surface_forms))

    def test_get_categories_returns_8(self):
        cats = EntityExtractor.get_categories()
        assert len(cats) == 8

    def test_get_categories_schema(self):
        for c in EntityExtractor.get_categories():
            assert "category" in c and "description" in c

    def test_deterministic_output(self):
        text = KURINCHI_SUTRA["tamil_text"]
        r1 = [e.canonical_form for e in EntityExtractor.extract(text, source_id="t")]
        r2 = [e.canonical_form for e in EntityExtractor.extract(text, source_id="t")]
        assert sorted(r1) == sorted(r2)


# ===========================================================================
# 10. RelationExtractor
# ===========================================================================

class TestRelationExtractor:

    def test_corpus_triple_promoted_as_corpus_validated(self):
        rels = RelationExtractor.extract(
            text="", entities=[],
            corpus_triples=[
                {"subject": "Cēyōṉ", "predicate": "presidesOver", "object": "Kuṟiñci"}
            ],
            source_id="t1",
        )
        assert len(rels) == 1
        assert rels[0].provenance.validation_status == ValidationStatus.CORPUS_VALIDATED

    def test_corpus_triple_extraction_method(self):
        rels = RelationExtractor.extract(
            text="", entities=[],
            corpus_triples=[
                {"subject": "Cēyōṉ", "predicate": "presidesOver", "object": "Kuṟiñci"}
            ],
            source_id="t1",
        )
        assert rels[0].provenance.extraction_method == ExtractionMethod.CORPUS_TRIPLE

    def test_corpus_triple_confidence_high(self):
        rels = RelationExtractor.extract(
            text="", entities=[],
            corpus_triples=[
                {"subject": "Cēyōṉ", "predicate": "presidesOver", "object": "Kuṟiñci"}
            ],
            source_id="t1",
        )
        assert rels[0].provenance.confidence >= 0.90

    def test_free_text_predicate_rejected(self):
        """Predicates not in vocabulary must be silently discarded."""
        rels = RelationExtractor.extract(
            text="", entities=[],
            corpus_triples=[
                {"subject": "X", "predicate": "expressesFeelingOfLonging", "object": "Y"}
            ],
            source_id="t1",
        )
        assert len(rels) == 0

    def test_llm_generated_predicate_rejected(self):
        rels = RelationExtractor.extract(
            text="", entities=[],
            corpus_triples=[
                {"subject": "A", "predicate": "someLLMGeneratedRelation", "object": "B"}
            ],
            source_id="t1",
        )
        assert len(rels) == 0

    def test_entity_cooccurrence_strategy(self):
        entity_dicts = [
            {"canonical_form": "Cēyōṉ"},
            {"canonical_form": "Kuṟiñci"},
        ]
        rels = RelationExtractor.extract(
            text="", entities=entity_dicts,
            source_id="t1",
        )
        assert any(r.predicate == RelationType.PRESIDES_OVER for r in rels)

    def test_cooccurrence_strategy_unverified(self):
        entity_dicts = [
            {"canonical_form": "Cēyōṉ"},
            {"canonical_form": "Kuṟiñci"},
        ]
        rels = RelationExtractor.extract(
            text="", entities=entity_dicts,
            source_id="t1",
        )
        cooccur_rels = [
            r for r in rels
            if r.provenance.extraction_method == ExtractionMethod.ENTITY_COOCCUR
        ]
        for r in cooccur_rels:
            assert r.provenance.validation_status == ValidationStatus.UNVERIFIED

    def test_all_predicates_are_relation_type_enum(self):
        rels = RelationExtractor.extract(
            text=KURINCHI_SUTRA["tamil_text"],
            entities=[{"canonical_form": "Cēyōṉ"}, {"canonical_form": "Kuṟiñci"}],
            corpus_triples=KURINCHI_SUTRA["triples"],
            source_id="t1",
        )
        for r in rels:
            assert isinstance(r.predicate, RelationType)

    def test_no_duplicate_relations(self):
        rels = RelationExtractor.extract(
            text="",
            entities=[{"canonical_form": "Cēyōṉ"}, {"canonical_form": "Kuṟiñci"}],
            corpus_triples=[
                {"subject": "Cēyōṉ", "predicate": "presidesOver", "object": "Kuṟiñci"},
                {"subject": "Cēyōṉ", "predicate": "presidesOver", "object": "Kuṟiñci"},
            ],
            source_id="t1",
        )
        triple_rels = [
            (r.subject, r.predicate, r.object) for r in rels
            if r.provenance.extraction_method == ExtractionMethod.CORPUS_TRIPLE
        ]
        assert len(triple_rels) == len(set(triple_rels))

    def test_get_relation_types_count(self):
        rts = RelationExtractor.get_relation_types()
        assert len(rts) >= 20

    def test_get_relation_types_schema(self):
        for rt in RelationExtractor.get_relation_types():
            assert "relation" in rt and "description" in rt


# ===========================================================================
# 11. EventExtractor
# ===========================================================================

class TestEventExtractor:

    def test_extracts_at_least_one_event(self):
        events = EventExtractor.extract(
            KURINCHI_SUTRA["tamil_text"], tinai="Kuṟiñci", source_id="t1"
        )
        assert len(events) >= 1

    def test_event_has_all_8_core_fields(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        e = events[0].to_dict()
        for field in ("actor", "action", "object", "location", "time", "condition", "source"):
            assert field in e

    def test_event_has_context(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        assert "context" in events[0].to_dict()

    def test_event_context_has_all_fields(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        ctx = events[0].to_dict()["context"]
        for field in ("speaker", "situation", "location", "genre",
                      "preceding_event", "season", "time_of_day"):
            assert field in ctx

    def test_kalavu_detected(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        ctx = events[0].to_dict()["context"]
        assert "Kaḷavu" in ctx["situation"] or "union" in ctx["situation"].lower()

    def test_season_detected(self):
        events = EventExtractor.extract(
            "கார்காலம் மலையில்", tinai="Kuṟiñci", source_id="t1"
        )
        ctx = events[0].to_dict()["context"]
        assert ctx["season"] is not None

    def test_time_of_day_detected(self):
        events = EventExtractor.extract(
            "மாலை வேளையில் காதலன்", tinai="Kuṟiñci", source_id="t1"
        )
        ctx = events[0].to_dict()["context"]
        assert ctx["time_of_day"] is not None

    def test_event_unverified(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        for e in events:
            assert e.provenance.validation_status == ValidationStatus.UNVERIFIED

    def test_event_genre_akam_for_interior(self):
        events = EventExtractor.extract("புணர்தல்", tinai="Kuṟiñci", source_id="t1")
        ctx = events[0].to_dict()["context"]
        assert "Akam" in ctx["genre"]

    def test_event_genre_puram_detected(self):
        events = EventExtractor.extract("போர் வெட்சி", tinai="General", source_id="t1")
        ctx = events[0].to_dict()["context"]
        assert "Puṟam" in ctx["genre"]


# ===========================================================================
# 12. ContextExtractor
# ===========================================================================

class TestContextExtractor:

    REQUIRED_KEYS = {
        "genre", "speaker", "situation", "location", "preceding_event",
        "season", "time_of_day", "has_temporal_marker",
    }

    def test_all_context_keys_present(self):
        ctx = ContextExtractor.extract_context(
            KURINCHI_SUTRA["tamil_text"], tinai="Kuṟiñci"
        )
        assert self.REQUIRED_KEYS.issubset(ctx.keys())

    def test_genre_akam_for_interior(self):
        ctx = ContextExtractor.extract_context("புணர்தல்", tinai="Kuṟiñci")
        assert "Akam" in ctx["genre"]

    def test_genre_puram_detected(self):
        ctx = ContextExtractor.extract_context("போர் வெட்சி", tinai="General")
        assert "Puṟam" in ctx["genre"]

    def test_speaker_from_tinai(self):
        ctx = ContextExtractor.extract_context("", tinai="Kuṟiñci")
        assert ctx["speaker"] is not None

    def test_location_from_tinai(self):
        ctx = ContextExtractor.extract_context("", tinai="Kuṟiñci")
        assert ctx["location"] is not None

    def test_season_detected_kar(self):
        ctx = ContextExtractor.extract_context("கார் மழை", tinai="Mullai")
        assert ctx["season"] == "Kār (Monsoon)"
        assert ctx["has_temporal_marker"] is True

    def test_time_of_day_malai(self):
        ctx = ContextExtractor.extract_context("மாலை வேளை", tinai="Kuṟiñci")
        assert ctx["time_of_day"] == "Mālai (Evening)"

    def test_preceding_event_passed_through(self):
        ctx = ContextExtractor.extract_context(
            "", tinai="General", preceding_event="Previous union event"
        )
        assert ctx["preceding_event"] == "Previous union event"

    def test_no_temporal_marker_flag_false(self):
        ctx = ContextExtractor.extract_context("plain text without markers")
        assert ctx["has_temporal_marker"] is False

    def test_deterministic(self):
        a = ContextExtractor.extract_context(KURINCHI_SUTRA["tamil_text"], tinai="Kuṟiñci")
        b = ContextExtractor.extract_context(KURINCHI_SUTRA["tamil_text"], tinai="Kuṟiñci")
        assert a == b


# ===========================================================================
# 13. SemanticExtractionPipeline
# ===========================================================================

class TestExtractionPipeline:

    REQUIRED_RESULT_KEYS = {
        "passage_id", "source_text", "entities", "relations",
        "events", "context", "extraction_summary",
    }

    def test_extract_single_schema(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        assert self.REQUIRED_RESULT_KEYS.issubset(result.keys())

    def test_extract_entities_list(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        assert isinstance(result["entities"], list)
        assert len(result["entities"]) > 0

    def test_extract_relations_list(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        assert isinstance(result["relations"], list)

    def test_extract_events_list(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        assert isinstance(result["events"], list)
        assert len(result["events"]) > 0

    def test_corpus_triples_promoted(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA)
        corpus_rels = [
            r for r in result.relations
            if r.provenance.extraction_method == ExtractionMethod.CORPUS_TRIPLE
        ]
        assert len(corpus_rels) > 0

    def test_corpus_relations_corpus_validated(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA)
        for r in result.relations:
            if r.provenance.extraction_method == ExtractionMethod.CORPUS_TRIPLE:
                assert r.provenance.validation_status == ValidationStatus.CORPUS_VALIDATED

    def test_rule_inferred_relations_unverified(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA)
        for r in result.relations:
            if r.provenance.extraction_method != ExtractionMethod.CORPUS_TRIPLE:
                assert r.provenance.validation_status == ValidationStatus.UNVERIFIED

    def test_passage_id_preserved(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        assert result["passage_id"] == "tol-porul-akam-005"

    def test_extraction_summary_schema(self, pipeline):
        result = pipeline.extract(KURINCHI_SUTRA).to_dict()
        summary = result["extraction_summary"]
        assert "entity_count" in summary
        assert "relation_count" in summary
        assert "event_count" in summary

    def test_extract_batch_returns_list(self, pipeline):
        results = pipeline.extract_batch([KURINCHI_SUTRA, AKAM_SUTRA])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_extract_from_sutra_id(self, pipeline):
        result = pipeline.extract_from_sutra_id("tol-porul-akam-005")
        assert result is not None
        assert result["passage_id"] == "tol-porul-akam-005"

    def test_extract_from_invalid_sutra_id_returns_none(self, pipeline):
        assert pipeline.extract_from_sutra_id("does-not-exist") is None

    def test_deterministic_extraction(self, pipeline):
        r1 = pipeline.extract(AKAM_SUTRA).to_dict()
        r2 = pipeline.extract(AKAM_SUTRA).to_dict()
        assert sorted(e["canonical_form"] for e in r1["entities"]) == \
               sorted(e["canonical_form"] for e in r2["entities"])


# ===========================================================================
# 14. API Endpoints
# ===========================================================================

class TestExtractionApiEndpoints:

    def test_extract_by_sutra_id(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"sutra_id": "tol-porul-akam-005"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["passage_id"] == "tol-porul-akam-005"

    def test_extract_result_has_entities(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"sutra_id": "tol-porul-akam-005"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data["entities"], list)
        assert len(data["entities"]) > 0

    def test_extract_result_has_relations(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"sutra_id": "tol-porul-akam-005"},
        )
        data = resp.get_json()["data"]
        assert isinstance(data["relations"], list)

    def test_extract_result_has_events(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"sutra_id": "tol-porul-akam-005"},
        )
        data = resp.get_json()["data"]
        assert isinstance(data["events"], list)

    def test_extract_invalid_sutra_returns_404(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"sutra_id": "not-real"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "SUTRA_NOT_FOUND"

    def test_extract_missing_input_returns_400(self, client):
        resp = client.post("/api/extraction/extract", json={})
        assert resp.status_code == 400

    def test_extract_raw_text(self, client):
        resp = client.post(
            "/api/extraction/extract",
            json={"text": "சேயோன் மேய மைவரை", "tinai": "Kuṟiñci"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["entities"]) > 0

    def test_batch_extract_full_corpus(self, client):
        resp = client.post("/api/extraction/batch", json={})
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "batch_summary" in data
        assert data["batch_summary"]["total_passages"] > 0

    def test_batch_summary_schema(self, client):
        resp = client.post("/api/extraction/batch", json={})
        summary = resp.get_json()["data"]["batch_summary"]
        for key in ("total_passages", "total_entities", "total_relations", "total_events"):
            assert key in summary

    def test_relation_types_endpoint(self, client):
        resp = client.get("/api/extraction/relation-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        rts = data["data"]
        assert len(rts) >= 20

    def test_relation_types_schema(self, client):
        resp = client.get("/api/extraction/relation-types")
        for rt in resp.get_json()["data"]:
            assert "relation" in rt and "description" in rt

    def test_entity_categories_endpoint(self, client):
        resp = client.get("/api/extraction/entity-categories")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 8

    def test_entity_categories_all_8_present(self, client):
        resp = client.get("/api/extraction/entity-categories")
        values = {c["category"] for c in resp.get_json()["data"]}
        expected = {
            "PERSON", "PLACE", "OBJECT", "EVENT",
            "CONCEPT", "INSTITUTION", "LITERARY_CONCEPT", "ETHICAL_CONCEPT",
        }
        assert expected == values
