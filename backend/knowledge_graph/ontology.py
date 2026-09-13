"""
Ontology definitions for Classical Tamil Tolkāppiyam semiotics.
Defines entity categories, structural hierarchy (L0-L5), 5 logical layers,
predicates, and taxonomic styling for frontend visualizations.
"""
from typing import Dict, Any, List


class TolkappiyamOntology:
    """Taxonomic classes, structural hierarchy, and valid edge relations for the epistemic graph."""

    # 6-Level Structural Hierarchy
    HIERARCHY_LEVELS = {
        "L0": {
            "level": "L0",
            "name": "Literature",
            "label_ta": "இலக்கியப் பொதுமை",
            "description": "Canonical corpus level: Classical Tamil Sangam literature",
            "color": "#1e293b",
        },
        "L1": {
            "level": "L1",
            "name": "Work",
            "label_ta": "நூல்",
            "description": "Monumental treatise or collection: Tolkāppiyam",
            "color": "#334155",
        },
        "L2": {
            "level": "L2",
            "name": "Section",
            "label_ta": "அதிகாரம் / இயல்",
            "description": "Major structural sections: Poruḷatikāram, Akattiṇaiyiyal, etc.",
            "color": "#475569",
        },
        "L3": {
            "level": "L3",
            "name": "Verse/Passage",
            "label_ta": "சூத்திரம் / செய்யுள்",
            "description": "Canonical sūtras and poetic verses with textual provenance",
            "color": "#e11d48",
        },
        "L4": {
            "level": "L4",
            "name": "Concept",
            "label_ta": "கோட்பாடு",
            "description": "Ontological categories: Mutalporuḷ, Karupporuḷ, Uripporuḷ, Tiṇai",
            "color": "#059669",
        },
        "L5": {
            "level": "L5",
            "name": "Entity/Event",
            "label_ta": "உறுப்பு / நிகழ்வு",
            "description": "Concrete deities, flora, fauna, landscapes, and affective events",
            "color": "#2563eb",
        },
    }

    # 5 Logical Epistemic Layers
    LOGICAL_LAYERS = {
        "Source Layer": {
            "id": "source_layer",
            "name": "Source Layer",
            "label_ta": "மூல அடுக்கு",
            "description": "Provenance layer preserving Literature, Work, Section, and Verse references",
            "color": "#e11d48",
            "bg": "#fff1f2",
        },
        "Entity Layer": {
            "id": "entity_layer",
            "name": "Entity Layer",
            "label_ta": "உறுப்பு அடுக்கு",
            "description": "Concrete named entities: Deities (Teyvam), Landscapes (Nilam), Biota (Karupporuḷ)",
            "color": "#2563eb",
            "bg": "#eff6ff",
        },
        "Concept Layer": {
            "id": "concept_layer",
            "name": "Concept Layer",
            "label_ta": "கோட்பாட்டு அடுக்கு",
            "description": "Tripartite semiotics (Mutal, Karu, Uri) and poetic conventions (Tiṇai)",
            "color": "#059669",
            "bg": "#ecfdf5",
        },
        "Event Layer": {
            "id": "event_layer",
            "name": "Event Layer",
            "label_ta": "நிகழ்வு அடுக்கு",
            "description": "Poetic situations, affective events (Puṇartal, Pirital, Iruttal, Iraṅkal, Ūṭal)",
            "color": "#d97706",
            "bg": "#fffbeb",
        },
        "Reasoning Layer": {
            "id": "reasoning_layer",
            "name": "Reasoning Layer",
            "label_ta": "அளவை அடுக்கு",
            "description": "Nyāya syllogistic members (Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana) and fallacies",
            "color": "#7c3aed",
            "bg": "#f5f3ff",
        },
    }

    # Node Category Styling Configuration
    CATEGORIES = {
        "Person": {
            "label": "Person / Deity (மாந்தர் / தெய்வம்)",
            "color": "#7c3aed",
            "fill": "#f5f3ff",
            "stroke": "#7c3aed",
            "text": "#4c1d95",
        },
        "Event": {
            "label": "Event / Affect (நிகழ்வு / மெய்ப்பாடு)",
            "color": "#d97706",
            "fill": "#fffbeb",
            "stroke": "#d97706",
            "text": "#78350f",
        },
        "Object": {
            "label": "Landscape / Biota (நிலம் / கருப்பொருள்)",
            "color": "#2563eb",
            "fill": "#eff6ff",
            "stroke": "#2563eb",
            "text": "#1e3a8a",
        },
        "Concept": {
            "label": "Concept / Axiom (கோட்பாடு / நெறி)",
            "color": "#059669",
            "fill": "#ecfdf5",
            "stroke": "#059669",
            "text": "#064e3b",
        },
        "Evidence": {
            "label": "Sūtra Evidence (சூத்திரச் சான்று)",
            "color": "#e11d48",
            "fill": "#fff1f2",
            "stroke": "#e11d48",
            "text": "#881337",
        },
        "Literature": {
            "label": "Literature Corpus (இலக்கியத் தொகுதி)",
            "color": "#1e293b",
            "fill": "#f8fafc",
            "stroke": "#1e293b",
            "text": "#0f172a",
        },
        "Work": {
            "label": "Work Treatise (நூல்)",
            "color": "#334155",
            "fill": "#f1f5f9",
            "stroke": "#334155",
            "text": "#1e293b",
        },
        "Section": {
            "label": "Section / Chapter (அதிகாரம் / இயல்)",
            "color": "#475569",
            "fill": "#e2e8f0",
            "stroke": "#475569",
            "text": "#334155",
        },
        "Reasoning": {
            "label": "Nyāya Syllogism (அளவை உறுப்பு)",
            "color": "#9333ea",
            "fill": "#faf5ff",
            "stroke": "#9333ea",
            "text": "#581c87",
        },
    }

    # Controlled Relation Vocabulary
    RELATIONS = {
        # Hierarchy Relations
        "contains_work": "Contains Treatise Work (நூலை உள்ளடக்கியது)",
        "contains_section": "Contains Section / Book (அதிகாரத்தை உள்ளடக்கியது)",
        "contains_passage": "Contains Verse / Sūtra (செய்யுளைக் கொண்டது)",
        "exposes_concept": "Exposes Ontological Concept (கோட்பாட்டை விளக்குகிறது)",
        "instantiates_entity": "Instantiates Entity / Biota (உறுப்பைக் குறிப்பிடுகிறது)",
        # Semiotic Relations
        "groundsIn": "Grounds Ontological Affect (நிலைகொள்கிறது)",
        "presidesOver": "Presides Over Landscape (முதன்மைத் தெய்வம்)",
        "hasHabitat": "Has Mountain/Forest Habitat (இயற்கை நிலம்)",
        "hasUripporuḷ": "Manifests Primary Affect (உரிப்பொருள் நெறி)",
        "consistsOf": "Constituent Axiom (அங்கமாகும்)",
        "includesComponent": "Signifier Component (கருப்பொருள் உறுப்பு)",
        "manifestsSignifierFor": "Invariable Signifier (குறியீடாகிறது)",
        "evokesAffect": "Evokes Emotional Interiority (மெய்ப்பாடு எழுப்புகிறது)",
        "manifestsAs": "Manifests Realization (உணர்த்துகிறது)",
        # Cross-Domain Controlled Relations
        "accused_of": "Accused of (குற்றஞ்சாட்டப்பட்டது)",
        "judged": "Judged by / as (தீர்ப்பளிக்கப்பட்டது)",
        "presented": "Presented in (முன்வைக்கப்பட்டது)",
        "contains": "Contains (அடக்கியுள்ளது)",
        "husband_of": "Husband of (கணவன்)",
        "possesses": "Possesses (உடைத்தாயுள்ளது)",
        "located_in": "Located in (இடங்கொண்டது)",
        "causes": "Causes / Determinant (ஏதுவாகிறது)",
        "contradicts": "Contradicts / Fallacy (முரண்படுகிறது)",
        "supports": "Supports / Justifies (ஆதரிக்கிறது)",
        "part_of": "Part of (உறுப்பாகும்)",
        "classified_as": "Classified as (வகையமைக்கப்பட்டது)",
    }

    @classmethod
    def get_category_config(cls) -> Dict[str, Any]:
        """Returns categories dictionary for API consumption."""
        return cls.CATEGORIES

    @classmethod
    def get_hierarchy_config(cls) -> Dict[str, Any]:
        """Returns 6-level hierarchy configuration."""
        return cls.HIERARCHY_LEVELS

    @classmethod
    def get_layer_config(cls) -> Dict[str, Any]:
        """Returns 5 logical layers configuration."""
        return cls.LOGICAL_LAYERS
