"""
Dedicated Query Preprocessing Service for Classical Tamil Literature Search.

Performs:
1. Safe Unicode NFC normalization, zero-width character stripping, and noise removal
   while strictly preserving the original user query for display and auditing.
2. Accurate language detection: Tamil Unicode ('tamil'), English ('english'), or
   Mixed-Language ('mixed') with character script ratio metrics.
3. Domain-specific preservation of Classical Tamil literary terminology (Tolkāppiyam
   poetics, Aintiṇai landscapes, Mutal-Karu-Uri tripartite semiotics, Meyppāṭu rasas,
   and Nyāya epistemic terms) in both Tamil script and ISO 15919 transliteration.
4. Entity, concept, and canonical source citation extraction (e.g. "Sūtra 5", "அகத்திணையியல்").
5. Construction of a structured `ProcessedQuery` object with specialized representations
   tailored for:
   - BM25 Keyword Search (bm25_query, bm25_tokens)
   - Dense Vector Search (vector_query)
   - Knowledge Graph Retrieval (kg_seed_node_ids, kg_cypher_params)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from preprocessing.tamil_normalizer import TamilNormalizer
from preprocessing.tokenizer import TamilTokenizer
from .intent_classifier import IntentClassifier


# =============================================================================
# Domain Terminology & Citation Dictionaries
# =============================================================================

# Classical Tamil Poetics, Grammar, and Philosophical Knowledge Dictionary
# Maps surface forms (Tamil script, transliterated, and English) to canonical metadata
LITERARY_TERMINOLOGY: Dict[str, Dict[str, Any]] = {
    # 1. Tripartite Semiotic Architecture
    "முதற்பொருள்": {
        "canonical": "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "english": "Primary Space-Time Ground",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "mutalporul",
    },
    "mutalporul": {
        "canonical": "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "english": "Primary Space-Time Ground",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "mutalporul",
    },
    "mutal": {
        "canonical": "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "english": "Primary Ground",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "mutalporul",
    },
    "கருப்பொருள்": {
        "canonical": "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "english": "Biotic & Cultural Signifiers",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "karupporul",
    },
    "karupporul": {
        "canonical": "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "english": "Biotic & Cultural Signifiers",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "karupporul",
    },
    "karu": {
        "canonical": "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "english": "Biotic Signifiers",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "karupporul",
    },
    "உரிப்பொருள்": {
        "canonical": "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "english": "Affective Mood / Human Interiority",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "uripporul",
    },
    "uripporul": {
        "canonical": "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "english": "Affective Mood / Human Interiority",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "uripporul",
    },
    "uri": {
        "canonical": "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "english": "Affective Interiority",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "uripporul",
    },

    # 2. Five Eco-Poetic Landscapes (Aintiṇai)
    "குறிஞ்சி": {
        "canonical": "Kuṟiñci",
        "transliteration": "Kuṟiñci",
        "english": "Montane Forest Landscape",
        "category": "Landscape",
        "tinai": "Kuṟiñci",
        "kg_id": "kurinci",
    },
    "kurinci": {
        "canonical": "Kuṟiñci",
        "transliteration": "Kuṟiñci",
        "english": "Montane Forest Landscape",
        "category": "Landscape",
        "tinai": "Kuṟiñci",
        "kg_id": "kurinci",
    },
    "kurinji": {
        "canonical": "Kuṟiñci",
        "transliteration": "Kuṟiñci",
        "english": "Montane Forest Landscape",
        "category": "Landscape",
        "tinai": "Kuṟiñci",
        "kg_id": "kurinci",
    },
    "முல்லை": {
        "canonical": "Mullai",
        "transliteration": "Mullai",
        "english": "Pastoral Forest Landscape",
        "category": "Landscape",
        "tinai": "Mullai",
        "kg_id": "mullai",
    },
    "mullai": {
        "canonical": "Mullai",
        "transliteration": "Mullai",
        "english": "Pastoral Forest Landscape",
        "category": "Landscape",
        "tinai": "Mullai",
        "kg_id": "mullai",
    },
    "மருதம்": {
        "canonical": "Marutam",
        "transliteration": "Marutam",
        "english": "Agricultural River Plains",
        "category": "Landscape",
        "tinai": "Marutam",
        "kg_id": "marutam",
    },
    "marutam": {
        "canonical": "Marutam",
        "transliteration": "Marutam",
        "english": "Agricultural River Plains",
        "category": "Landscape",
        "tinai": "Marutam",
        "kg_id": "marutam",
    },
    "marudham": {
        "canonical": "Marutam",
        "transliteration": "Marutam",
        "english": "Agricultural River Plains",
        "category": "Landscape",
        "tinai": "Marutam",
        "kg_id": "marutam",
    },
    "நெய்தல்": {
        "canonical": "Neytal",
        "transliteration": "Neytal",
        "english": "Littoral Coastal Seashore",
        "category": "Landscape",
        "tinai": "Neytal",
        "kg_id": "neytal",
    },
    "neytal": {
        "canonical": "Neytal",
        "transliteration": "Neytal",
        "english": "Littoral Coastal Seashore",
        "category": "Landscape",
        "tinai": "Neytal",
        "kg_id": "neytal",
    },
    "neithal": {
        "canonical": "Neytal",
        "transliteration": "Neytal",
        "english": "Littoral Coastal Seashore",
        "category": "Landscape",
        "tinai": "Neytal",
        "kg_id": "neytal",
    },
    "பாலை": {
        "canonical": "Pālai",
        "transliteration": "Pālai",
        "english": "Arid Scorched Wasteland",
        "category": "Landscape",
        "tinai": "Pālai",
        "kg_id": "palai",
    },
    "palai": {
        "canonical": "Pālai",
        "transliteration": "Pālai",
        "english": "Arid Scorched Wasteland",
        "category": "Landscape",
        "tinai": "Pālai",
        "kg_id": "palai",
    },

    # 3. Canonical Deities (Teyvam) & Flora/Fauna Signifiers
    "சேயோன்": {
        "canonical": "Cēyōṉ",
        "transliteration": "Cēyōṉ",
        "english": "Red-hued Deity of Mountains (Murukaṉ)",
        "category": "Deity",
        "tinai": "Kuṟiñci",
        "kg_id": "ceyon",
    },
    "ceyon": {
        "canonical": "Cēyōṉ",
        "transliteration": "Cēyōṉ",
        "english": "Red-hued Deity of Mountains (Murukaṉ)",
        "category": "Deity",
        "tinai": "Kuṟiñci",
        "kg_id": "ceyon",
    },
    "மாயோன்": {
        "canonical": "Māyōṉ",
        "transliteration": "Māyōṉ",
        "english": "Dark-hued Pastoral Deity (Tirumāl)",
        "category": "Deity",
        "tinai": "Mullai",
        "kg_id": "mayon",
    },
    "mayon": {
        "canonical": "Māyōṉ",
        "transliteration": "Māyōṉ",
        "english": "Dark-hued Pastoral Deity (Tirumāl)",
        "category": "Deity",
        "tinai": "Mullai",
        "kg_id": "mayon",
    },
    "வேந்தன்": {
        "canonical": "Vēntan",
        "transliteration": "Vēntan",
        "english": "Sovereign Celestial Deity of Plains (Indra)",
        "category": "Deity",
        "tinai": "Marutam",
        "kg_id": "ventan",
    },
    "ventan": {
        "canonical": "Vēntan",
        "transliteration": "Vēntan",
        "english": "Sovereign Celestial Deity of Plains (Indra)",
        "category": "Deity",
        "tinai": "Marutam",
        "kg_id": "ventan",
    },
    "வருணன்": {
        "canonical": "Varuṇaṉ",
        "transliteration": "Varuṇaṉ",
        "english": "Oceanic Deity of Waters (Varuna)",
        "category": "Deity",
        "tinai": "Neytal",
        "kg_id": "varunan",
    },
    "varunan": {
        "canonical": "Varuṇaṉ",
        "transliteration": "Varuṇaṉ",
        "english": "Oceanic Deity of Waters (Varuna)",
        "category": "Deity",
        "tinai": "Neytal",
        "kg_id": "varunan",
    },
    "வேங்கை": {
        "canonical": "Vēṅkai",
        "transliteration": "Vēṅkai",
        "english": "Kino Tree (Flora biotic signifier of marriage readiness)",
        "category": "Flora",
        "tinai": "Kuṟiñci",
        "kg_id": "venkai",
    },
    "venkai": {
        "canonical": "Vēṅkai",
        "transliteration": "Vēṅkai",
        "english": "Kino Tree (Flora biotic signifier)",
        "category": "Flora",
        "tinai": "Kuṟiñci",
        "kg_id": "venkai",
    },

    # 4. Affective Events & Human Interiority (Uripporuḷ)
    "புணர்தல்": {
        "canonical": "Puṇartal",
        "transliteration": "Puṇartal",
        "english": "Intimate Clandestine Union",
        "category": "AffectiveEvent",
        "tinai": "Kuṟiñci",
        "kg_id": "punartal",
    },
    "punartal": {
        "canonical": "Puṇartal",
        "transliteration": "Puṇartal",
        "english": "Intimate Clandestine Union",
        "category": "AffectiveEvent",
        "tinai": "Kuṟiñci",
        "kg_id": "punartal",
    },
    "பிரிதல்": {
        "canonical": "Pirital",
        "transliteration": "Pirital",
        "english": "Separation / Parting of Lovers",
        "category": "AffectiveEvent",
        "tinai": "Pālai",
        "kg_id": "pirital",
    },
    "pirital": {
        "canonical": "Pirital",
        "transliteration": "Pirital",
        "english": "Separation / Parting of Lovers",
        "category": "AffectiveEvent",
        "tinai": "Pālai",
        "kg_id": "pirital",
    },
    "இருத்தல்": {
        "canonical": "Iruttal",
        "transliteration": "Iruttal",
        "english": "Patient Endurance / Hopeful Waiting",
        "category": "AffectiveEvent",
        "tinai": "Mullai",
        "kg_id": "iruttal",
    },
    "iruttal": {
        "canonical": "Iruttal",
        "transliteration": "Iruttal",
        "english": "Patient Endurance / Hopeful Waiting",
        "category": "AffectiveEvent",
        "tinai": "Mullai",
        "kg_id": "iruttal",
    },
    "இரங்கல்": {
        "canonical": "Iraṅkal",
        "transliteration": "Iraṅkal",
        "english": "Melancholic Pining / Anxious Yearning",
        "category": "AffectiveEvent",
        "tinai": "Neytal",
        "kg_id": "irankal",
    },
    "irankal": {
        "canonical": "Iraṅkal",
        "transliteration": "Iraṅkal",
        "english": "Melancholic Pining / Anxious Yearning",
        "category": "AffectiveEvent",
        "tinai": "Neytal",
        "kg_id": "irankal",
    },
    "ஊடல்": {
        "canonical": "Ūṭal",
        "transliteration": "Ūṭal",
        "english": "Feigned Lovers' Sulking / Estrangement",
        "category": "AffectiveEvent",
        "tinai": "Marutam",
        "kg_id": "udal",
    },
    "udal": {
        "canonical": "Ūṭal",
        "transliteration": "Ūṭal",
        "english": "Feigned Lovers' Sulking",
        "category": "AffectiveEvent",
        "tinai": "Marutam",
        "kg_id": "udal",
    },
    "மெய்ப்பாடு": {
        "canonical": "Meyppāṭu",
        "transliteration": "Meyppāṭu",
        "english": "Aesthetic Emotional Manifestation / Rasa",
        "category": "AestheticManifestation",
        "tinai": "General",
        "kg_id": "meyppatu",
    },
    "meyppatu": {
        "canonical": "Meyppāṭu",
        "transliteration": "Meyppāṭu",
        "english": "Aesthetic Emotional Manifestation",
        "category": "AestheticManifestation",
        "tinai": "General",
        "kg_id": "meyppatu",
    },
    "meyppadu": {
        "canonical": "Meyppāṭu",
        "transliteration": "Meyppāṭu",
        "english": "Aesthetic Emotional Manifestation",
        "category": "AestheticManifestation",
        "tinai": "General",
        "kg_id": "meyppatu",
    },

    # 5. Canonical Literary Works & Sections
    "தொல்காப்பியம்": {
        "canonical": "Tolkāppiyam",
        "transliteration": "Tolkāppiyam",
        "english": "Canonical Classical Treatise",
        "category": "Work",
        "tinai": "General",
        "kg_id": "tolkappiyam",
    },
    "tolkappiyam": {
        "canonical": "Tolkāppiyam",
        "transliteration": "Tolkāppiyam",
        "english": "Canonical Classical Treatise",
        "category": "Work",
        "tinai": "General",
        "kg_id": "tolkappiyam",
    },
    "பொருளதிகாரம்": {
        "canonical": "Poruḷatikāram",
        "transliteration": "Poruḷatikāram",
        "english": "Book on Poetics and Semiotics",
        "category": "Section",
        "tinai": "General",
        "kg_id": "porulatikaram",
    },
    "porulatikaram": {
        "canonical": "Poruḷatikāram",
        "transliteration": "Poruḷatikāram",
        "english": "Book on Poetics and Semiotics",
        "category": "Section",
        "tinai": "General",
        "kg_id": "porulatikaram",
    },
    "அகத்திணையியல்": {
        "canonical": "Akattiṇaiyiyal",
        "transliteration": "Akattiṇaiyiyal",
        "english": "Chapter on Interior Poetic Modes",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "akattinaiyiyal",
    },
    "akattinaiyiyal": {
        "canonical": "Akattiṇaiyiyal",
        "transliteration": "Akattiṇaiyiyal",
        "english": "Chapter on Interior Poetic Modes",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "akattinaiyiyal",
    },
    "புறத்திணையியல்": {
        "canonical": "Puṟattiṇaiyiyal",
        "transliteration": "Puṟattiṇaiyiyal",
        "english": "Chapter on Exterior Heroic Modes",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "purattinaiyiyal",
    },
    "purattinaiyiyal": {
        "canonical": "Puṟattiṇaiyiyal",
        "transliteration": "Puṟattiṇaiyiyal",
        "english": "Chapter on Exterior Heroic Modes",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "purattinaiyiyal",
    },
    "மெய்ப்பாட்டியல்": {
        "canonical": "Meyppāṭṭiyal",
        "transliteration": "Meyppāṭṭiyal",
        "english": "Chapter on Dramatic Realization & Rasa",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "meyppattiyal",
    },
    "meyppattiyal": {
        "canonical": "Meyppāṭṭiyal",
        "transliteration": "Meyppāṭṭiyal",
        "english": "Chapter on Dramatic Realization & Rasa",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "meyppattiyal",
    },
    "அறநெறி": {
        "canonical": "Aṟaneri",
        "transliteration": "Aṟaneri",
        "english": "Constitutional Righteousness / Justice",
        "category": "EthicalConcept",
        "tinai": "General",
        "kg_id": "araneri",
    },
    "araneri": {
        "canonical": "Aṟaneri",
        "transliteration": "Aṟaneri",
        "english": "Constitutional Righteousness / Justice",
        "category": "EthicalConcept",
        "tinai": "General",
        "kg_id": "araneri",
    },

    # 6. Nyāya Epistemic Syllogistic Concepts
    "வியாப்தி": {
        "canonical": "Vyāpti",
        "transliteration": "Vyāpti",
        "english": "Universal Invariable Concomitance",
        "category": "NyayaRule",
        "tinai": "General",
        "kg_id": "vyapti",
    },
    "vyapti": {
        "canonical": "Vyāpti",
        "transliteration": "Vyāpti",
        "english": "Universal Invariable Concomitance",
        "category": "NyayaRule",
        "tinai": "General",
        "kg_id": "vyapti",
    },
    "பிரமாணம்": {
        "canonical": "Pramāṇa",
        "transliteration": "Pramāṇa",
        "english": "Valid Means of Knowledge",
        "category": "NyayaConcept",
        "tinai": "General",
        "kg_id": "pramana",
    },
    "pramana": {
        "canonical": "Pramāṇa",
        "transliteration": "Pramāṇa",
        "english": "Valid Means of Knowledge",
        "category": "NyayaConcept",
        "tinai": "General",
        "kg_id": "pramana",
    },
    "ஹேது": {
        "canonical": "Hetu",
        "transliteration": "Hetu",
        "english": "Inferential Ground / Middle Term",
        "category": "NyayaStep",
        "tinai": "General",
        "kg_id": "hetu",
    },
    "hetu": {
        "canonical": "Hetu",
        "transliteration": "Hetu",
        "english": "Inferential Ground / Middle Term",
        "category": "NyayaStep",
        "tinai": "General",
        "kg_id": "hetu",
    },
    "ஹேத்வாபாசம்": {
        "canonical": "Hetvābhāsa",
        "transliteration": "Hetvābhāsa",
        "english": "Fallacy of the Middle Ground",
        "category": "NyayaValidation",
        "tinai": "General",
        "kg_id": "hetvabhasa",
    },
    "hetvabhasa": {
        "canonical": "Hetvābhāsa",
        "transliteration": "Hetvābhāsa",
        "english": "Fallacy of the Middle Ground",
        "category": "NyayaValidation",
        "tinai": "General",
        "kg_id": "hetvabhasa",
    },

    # 7. Classical Tamil Grammar & Poetics Concepts (Tolkāppiyam)
    "வழுவமைதி": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "valuvamaiti": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "vazhuvamaiti": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "vazhuvamaithi": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "error tolerance": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "syntactic exception": {
        "canonical": "Vaḻuvamaiti",
        "transliteration": "Vaḻuvamaiti",
        "tamil_term": "வழுவமைதி",
        "english": "Grammatical Error Tolerance / Syntactic Exception",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "valuvamaiti",
    },
    "திணைவழு": {
        "canonical": "Tiṇaivaḻu",
        "transliteration": "Tiṇaivaḻu",
        "tamil_term": "திணைவழு",
        "english": "Category Violation of Tiṇai / Poetic Incongruity",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "tinaivalu",
    },
    "tinaivalu": {
        "canonical": "Tiṇaivaḻu",
        "transliteration": "Tiṇaivaḻu",
        "tamil_term": "திணைவழு",
        "english": "Category Violation of Tiṇai / Poetic Incongruity",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "tinaivalu",
    },
    "சொல்லதிகாரம்": {
        "canonical": "Collatikāram",
        "transliteration": "Collatikāram",
        "tamil_term": "சொல்லதிகாரம்",
        "english": "Book on Morphology, Syntax and Parts of Speech",
        "category": "Section",
        "tinai": "General",
        "kg_id": "collatikaram",
    },
    "collatikaram": {
        "canonical": "Collatikāram",
        "transliteration": "Collatikāram",
        "tamil_term": "சொல்லதிகாரம்",
        "english": "Book on Morphology, Syntax and Parts of Speech",
        "category": "Section",
        "tinai": "General",
        "kg_id": "collatikaram",
    },
    "எழுத்ததிகாரம்": {
        "canonical": "Eḻuttatikāram",
        "transliteration": "Eḻuttatikāram",
        "tamil_term": "எழுத்ததிகாரம்",
        "english": "Book on Phonology and Orthography",
        "category": "Section",
        "tinai": "General",
        "kg_id": "eluttatikaram",
    },
    "eluttatikaram": {
        "canonical": "Eḻuttatikāram",
        "transliteration": "Eḻuttatikāram",
        "tamil_term": "எழுத்ததிகாரம்",
        "english": "Book on Phonology and Orthography",
        "category": "Section",
        "tinai": "General",
        "kg_id": "eluttatikaram",
    },
    "மரபியல்": {
        "canonical": "Marapiyal",
        "transliteration": "Marapiyal",
        "tamil_term": "மரபியல்",
        "english": "Chapter on Conventional Usage and Lexical Tradition",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "marapiyal",
    },
    "marapiyal": {
        "canonical": "Marapiyal",
        "transliteration": "Marapiyal",
        "tamil_term": "மரபியல்",
        "english": "Chapter on Conventional Usage and Lexical Tradition",
        "category": "Chapter",
        "tinai": "General",
        "kg_id": "marapiyal",
    },
    "வேற்றுமை": {
        "canonical": "Vēṟṟumai",
        "transliteration": "Vēṟṟumai",
        "tamil_term": "வேற்றுமை",
        "english": "Grammatical Case System / Declension",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "vettumai",
    },
    "vettumai": {
        "canonical": "Vēṟṟumai",
        "transliteration": "Vēṟṟumai",
        "tamil_term": "வேற்றுமை",
        "english": "Grammatical Case System / Declension",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "vettumai",
    },
    "vetrumai": {
        "canonical": "Vēṟṟumai",
        "transliteration": "Vēṟṟumai",
        "tamil_term": "வேற்றுமை",
        "english": "Grammatical Case System / Declension",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "vettumai",
    },
    "வினை": {
        "canonical": "Vinai",
        "transliteration": "Vinai",
        "tamil_term": "வினை",
        "english": "Verb / Predicative Action",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "vinai",
    },
    "vinai": {
        "canonical": "Vinai",
        "transliteration": "Vinai",
        "tamil_term": "வினை",
        "english": "Verb / Predicative Action",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "vinai",
    },
    "பெயர்": {
        "canonical": "Peyar",
        "transliteration": "Peyar",
        "tamil_term": "பெயர்",
        "english": "Noun / Substantive Nominal",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "peyar",
    },
    "peyar": {
        "canonical": "Peyar",
        "transliteration": "Peyar",
        "tamil_term": "பெயர்",
        "english": "Noun / Substantive Nominal",
        "category": "Grammar",
        "tinai": "General",
        "kg_id": "peyar",
    },
    "உவமம்": {
        "canonical": "Uvamam",
        "transliteration": "Uvamam",
        "tamil_term": "உவமம்",
        "english": "Simile / Figurative Comparison",
        "category": "Poetics",
        "tinai": "General",
        "kg_id": "uvamam",
    },
    "uvamam": {
        "canonical": "Uvamam",
        "transliteration": "Uvamam",
        "tamil_term": "உவமம்",
        "english": "Simile / Figurative Comparison",
        "category": "Poetics",
        "tinai": "General",
        "kg_id": "uvamam",
    },
    # English Conceptual Aliases
    "primary space-time ground": {
        "canonical": "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "tamil_term": "முதற்பொருள்",
        "english": "Primary Space-Time Ground",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "mutalporul",
    },
    "primary ground": {
        "canonical": "Mutalporuḷ",
        "transliteration": "Mutalporuḷ",
        "tamil_term": "முதற்பொருள்",
        "english": "Primary Space-Time Ground",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "mutalporul",
    },
    "environmental signifiers": {
        "canonical": "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "tamil_term": "கருப்பொருள்",
        "english": "Biotic & Cultural Signifiers",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "karupporul",
    },
    "biotic signifiers": {
        "canonical": "Karupporuḷ",
        "transliteration": "Karupporuḷ",
        "tamil_term": "கருப்பொருள்",
        "english": "Biotic & Cultural Signifiers",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "karupporul",
    },
    "affective mood": {
        "canonical": "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "tamil_term": "உரிப்பொருள்",
        "english": "Affective Mood / Human Interiority",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "uripporul",
    },
    "human interiority": {
        "canonical": "Uripporuḷ",
        "transliteration": "Uripporuḷ",
        "tamil_term": "உரிப்பொருள்",
        "english": "Affective Mood / Human Interiority",
        "category": "TripartiteSemiotics",
        "tinai": "General",
        "kg_id": "uripporul",
    },
    "interior poetics": {
        "canonical": "Akam",
        "transliteration": "Akam",
        "tamil_term": "அகம்",
        "english": "Interior Love Poetics",
        "category": "PoeticDomain",
        "tinai": "General",
        "kg_id": "akam",
    },
    "exterior poetics": {
        "canonical": "Puṟam",
        "transliteration": "Puṟam",
        "tamil_term": "புறம்",
        "english": "Exterior Heroic & Ethical Poetics",
        "category": "PoeticDomain",
        "tinai": "General",
        "kg_id": "puram",
    },
    "poetic union": {
        "canonical": "Puṇartal",
        "transliteration": "Puṇartal",
        "tamil_term": "புணர்தல்",
        "english": "Lovers' Secret Union / Conjunction",
        "category": "AffectiveEvent",
        "tinai": "Kuṟiñci",
        "kg_id": "punartal",
    },
    "patient endurance": {
        "canonical": "Iruttal",
        "transliteration": "Iruttal",
        "tamil_term": "இருத்தல்",
        "english": "Patient Endurance / Hopeful Waiting",
        "category": "AffectiveEvent",
        "tinai": "Mullai",
        "kg_id": "iruttal",
    },
    "feigned sulking": {
        "canonical": "Ūṭal",
        "transliteration": "Ūṭal",
        "tamil_term": "ஊடல்",
        "english": "Feigned Lovers' Sulking / Estrangement",
        "category": "AffectiveEvent",
        "tinai": "Marutam",
        "kg_id": "udal",
    },
    "melancholic pining": {
        "canonical": "Iraṅkal",
        "transliteration": "Iraṅkal",
        "tamil_term": "இரங்கல்",
        "english": "Melancholic Pining / Anxious Yearning",
        "category": "AffectiveEvent",
        "tinai": "Neytal",
        "kg_id": "irankal",
    },
    "anxious yearning": {
        "canonical": "Iraṅkal",
        "transliteration": "Iraṅkal",
        "tamil_term": "இரங்கல்",
        "english": "Melancholic Pining / Anxious Yearning",
        "category": "AffectiveEvent",
        "tinai": "Neytal",
        "kg_id": "irankal",
    },
}

# Authentic Canonical Tamil Script Mapping for Absolute Terminology Preservation
CANONICAL_TAMIL_TERMS: Dict[str, str] = {
    "Mutalporuḷ": "முதற்பொருள்",
    "Karupporuḷ": "கருப்பொருள்",
    "Uripporuḷ": "உரிப்பொருள்",
    "Kuṟiñci": "குறிஞ்சி",
    "Mullai": "முல்லை",
    "Marutam": "மருதம்",
    "Neytal": "நெய்தல்",
    "Pālai": "பாலை",
    "Cēyōṉ": "சேயோன்",
    "Māyōṉ": "மாயோன்",
    "Vēntan": "வேந்தன்",
    "Varuṇaṉ": "வருணன்",
    "Koṟṟavai": "கொற்றவை",
    "Puṇartal": "புணர்தல்",
    "Pirital": "பிரிதல்",
    "Iruttal": "இருத்தல்",
    "Iraṅkal": "இரங்கல்",
    "Ūṭal": "ஊடல்",
    "Meyppāṭu": "மெய்ப்பாடு",
    "Tolkāppiyam": "தொல்காப்பியம்",
    "Poruḷatikāram": "பொருளதிகாரம்",
    "Collatikāram": "சொல்லதிகாரம்",
    "Eḻuttatikāram": "எழுத்ததிகாரம்",
    "Akattiṇaiyiyal": "அகத்திணையியல்",
    "Puṟattiṇaiyiyal": "புறத்திணையியல்",
    "Kaḷaviyal": "களவியல்",
    "Kaṟpiyal": "கற்பியல்",
    "Poruḷiyal": "பொருளியல்",
    "Meyppāṭṭiyal": "மெய்ப்பாட்டியல்",
    "Uvamaviyal": "உவமவியல்",
    "Ceyyuḷiyal": "செய்யுளியல்",
    "Marapiyal": "மரபியல்",
    "Vaḻuvamaiti": "வழுவமைதி",
    "Tiṇaivaḻu": "திணைவழு",
    "Vēṟṟumai": "வேற்றுமை",
    "Vinai": "வினை",
    "Peyar": "பெயர்",
    "Uvamam": "உவமம்",
    "Akam": "அகம்",
    "Puṟam": "புறம்",
    "Aintiṇai": "ஐந்திணை",
    "Tiṇai": "திணை",
    "Nilam": "நிலம்",
    "Poḻutu": "பொழுது",
    "Vēṅkai": "வேங்கை",
    "Kāntal": "காந்தல்",
    "Koṉṟai": "கொன்றை",
    "Tāmarai": "தாமரை",
    "Tālai": "தாழை",
    "Neytal-flower": "நெய்தல்",
    "Kuraṅku": "குரங்கு",
    "Mayil": "மயில்",
    "Yāṉai": "யானை",
    "Puli": "புலி",
    "Kāṭai": "காடை",
    "Māṉ": "மான்",
    "Kalutam": "கழுதை",
    "Aṟaneri": "அறநெறி",
    "Vyāpti": "வியாப்தி",
    "Pramāṇa": "பிரமாணம்",
    "Hetu": "ஹேது",
    "Hetvābhāsa": "ஹேத்வாபாசம்",
    "Pratijñā": "பிரதிஞ்ஞை",
    "Udāharaṇa": "உதாரணம்",
    "Upanaya": "உபநயம்",
    "Nigamana": "நிகமமனம்",
}

# Stopwords to remove from search query tokens (without stripping literary terms)
QUERY_STOPWORDS: Set[str] = {
    # English generic search words
    "what", "is", "the", "in", "and", "of", "to", "how", "why", "does", "do",
    "explain", "describe", "meaning", "define", "show", "tell", "me", "about",
    "can", "are", "by", "for", "with", "between", "from", "which", "whose",
    # Tamil generic conversational question words
    "என்பது", "யாது", "என்ன", "எவை", "எப்படி", "விளக்குக", "கூறுக",
    "பற்றி", "உள்ள", "உடைய", "என்று", "எனப்படும்", "ஆகிய", "மற்றும்",
}


# =============================================================================
# Processed Query Output Data Model
# =============================================================================

@dataclass
class ProcessedQuery:
    """
    Structured query output produced by QueryPreprocessingService.
    Preserves original query untouched while providing standardized representations
    for lexical, vector, and knowledge graph retrieval channels.
    """
    # 1. Original User Input (Preserved for Auditing and Display)
    original_query: str

    # 2. Normalized Text (Safe Unicode NFC, whitespace collapsed, noise stripped)
    normalized_query: str

    # 3. Language & Script Classification
    language: str                # 'tamil' | 'english' | 'mixed'
    language_code: str           # 'ta' | 'en' | 'ta-en'
    script: str                  # 'Tamil Unicode' | 'Latin (English)' | 'Mixed (Tamil + Latin)' | 'ISO 15919 Transliteration'
    is_tamil: bool
    is_english: bool
    is_mixed: bool
    tamil_ratio: float
    english_ratio: float

    # 4. Extracted Lexical & Domain Terminology
    keywords: List[str]          # Cleaned content keywords for search indexing
    literary_terms: List[Dict[str, Any]] # Preserved poetics & grammar domain terms

    # 5. Semantic Entities & Concepts
    entities: List[Dict[str, Any]] # Extracted concrete entities (deities, landscapes, flora, fauna)
    concepts: List[Dict[str, Any]] # Extracted abstract poetics / semiotic concepts
    detected_tinai: str          # Kuṟiñci | Mullai | Marutam | Neytal | Pālai | General
    intent: Dict[str, Any]       # Epistemic question intent (Hetu, Vyāpti, Pakṣa, Pratijñā)

    # 6. Source References & Citations
    source_references: List[Dict[str, Any]] # Parsed sūtras, chapters, sections
    has_source_filter: bool

    # 7. Channel-Specific Search Payloads
    bm25_query: str              # Normalized string for BM25 keyword matching
    bm25_tokens: List[str]       # Tokenized word sequence for BM25Okapi / BM25Plus
    vector_query: str            # Clean representation for dense vector embeddings
    kg_seed_node_ids: List[str]  # Candidate node IDs for Neo4j / NetworkX graph expansion
    kg_cypher_params: Dict[str, Any] # Ready-to-use Cypher parameters

    # 8. Extra Diagnostics & Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 9. Multilingual Common Semantic Representation & Grounding
    detected_language: str = ""
    language_metadata: Dict[str, Any] = field(default_factory=dict)
    identified_entities: List[Dict[str, Any]] = field(default_factory=list)
    identified_concepts: List[Dict[str, Any]] = field(default_factory=list)
    identified_entities_concepts: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_representation: Dict[str, Any] = field(default_factory=dict)

    @property
    def preserved_tamil_terms(self) -> List[str]:
        """Returns preserved Tamil script terms extracted for this query."""
        if self.retrieval_representation and "preserved_tamil_terms" in self.retrieval_representation:
            return self.retrieval_representation["preserved_tamil_terms"]
        terms = []
        for item in (self.identified_entities + self.identified_concepts + self.literary_terms):
            tt = item.get("tamil_term") or item.get("term")
            if tt and any('\u0B80' <= c <= '\u0BFF' for c in tt):
                if tt not in terms:
                    terms.append(tt)
        return terms

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary fulfilling the Query Center backend specification."""
        d = asdict(self)
        # Ensure the exact top-level fields requested by the specification are first-class
        d["original_query"] = self.original_query
        d["detected_language"] = self.language or self.detected_language
        d["language_metadata"] = self.language_metadata or {
            "primary_language": self.language,
            "language": self.language,
            "language_code": self.language_code,
            "script": self.script,
            "is_tamil": self.is_tamil,
            "is_english": self.is_english,
            "is_mixed": self.is_mixed,
            "tamil_ratio": self.tamil_ratio,
            "english_ratio": self.english_ratio,
        }
        d["normalized_query"] = self.normalized_query
        d["identified_entities"] = self.identified_entities if self.identified_entities is not None else self.entities
        d["identified_concepts"] = self.identified_concepts if self.identified_concepts is not None else self.concepts
        d["identified_entities_concepts"] = (
            self.identified_entities_concepts
            if self.identified_entities_concepts
            else (d["identified_entities"] + d["identified_concepts"])
        )
        d["retrieval_representation"] = self.retrieval_representation
        return d


# =============================================================================
# Dedicated Query Preprocessing Service
# =============================================================================

class QueryPreprocessingService:
    """
    Dedicated Preprocessing Service for Classical Tamil Literary Searches.
    Encapsulates normalization, language identification, terminology preservation,
    citation parsing, and multi-channel search query generation.
    """

    TAMIL_CHAR_REGEX = re.compile(r"[\u0B80-\u0BFF]")
    LATIN_CHAR_REGEX = re.compile(r"[a-zA-Z]")
    ISO_DIACRITICS_REGEX = re.compile(r"[āīūṛṝḷḹēōñṅṇṭṟśṣḥṁṉ]", re.IGNORECASE)

    @staticmethod
    def strip_diacritics(text: str) -> str:
        """Removes ISO-15919 diacritical marks to ensure robust fuzzy transliteration matching."""
        if not text:
            return ""
        replacements = {
            'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u',
            'ṟ': 'r', 'ṉ': 'n', 'ṇ': 'n', 'ḷ': 'l', 'ṭ': 't',
            'ñ': 'n', 'ṅ': 'n', 'ś': 's', 'ṣ': 's', 'ḻ': 'l',
            'Ā': 'A', 'Ē': 'E', 'Ī': 'I', 'Ō': 'O', 'Ū': 'U',
            'Ṟ': 'R', 'Ṉ': 'N', 'Ṇ': 'N', 'Ḷ': 'L', 'Ṭ': 'T',
            'Ñ': 'N', 'Ṅ': 'N', 'Ś': 'S', 'Ṣ': 'S', 'Ḻ': 'L',
        }
        res = text
        for char, rep in replacements.items():
            res = res.replace(char, rep)
        return res

    # Regex patterns to detect sūtra and verse citations
    SUTRA_PATTERNS = [
        re.compile(r"(?:sūtra|sutra|சூத்திரம்|சூத்|verse|பாடல்)\s*#?\s*(\d+)", re.IGNORECASE),
        re.compile(r"#\s*(\d+)", re.IGNORECASE),
        re.compile(r"tol-(?:[a-zA-Z0-9]+-)+(\d+)", re.IGNORECASE),
        re.compile(r"tol-(?:porul|akam|puram|mey)-(\d+)", re.IGNORECASE),
    ]

    # Regex patterns for canonical sections and chapters
    SECTION_PATTERNS = {
        "Akattiṇaiyiyal": [re.compile(r"akatti[nṇ]aiyiyal|அகத்திணையியல்|akam", re.IGNORECASE)],
        "Puṟattiṇaiyiyal": [re.compile(r"pu[rṟ]atti[nṇ]aiyiyal|புறத்திணையியல்|puram", re.IGNORECASE)],
        "Poruḷatikāram": [re.compile(r"poru[lḷ]atik[aā]ram|பொருளதிகாரம்", re.IGNORECASE)],
        "Collatikāram": [re.compile(r"collatik[aā]ram|சொல்லதிகாரம்", re.IGNORECASE)],
        "Eḻuttatikāram": [re.compile(r"e[lḻ]uttatik[aā]ram|எழுத்ததிகாரம்", re.IGNORECASE)],
        "Meyppāṭṭiyal": [re.compile(r"meypp[aā][tṭ][tṭ]iyal|மெய்ப்பாட்டியல்|meyppadu|meyppatu", re.IGNORECASE)],
    }

    @classmethod
    def preprocess(cls, query: str, focus: str = "Relationship") -> ProcessedQuery:
        """
        Executes full preprocessing pipeline and returns a structured ProcessedQuery.
        The original query is retained completely unmodified.
        """
        original_query = query if query is not None else ""

        if not original_query.strip():
            # Handle empty query gracefully
            return cls._build_empty_processed_query(original_query)

        # 1. Safe Unicode Normalization & Noise Cleaning
        normalized_query = cls.normalize_query_text(original_query)

        # 2. Language & Script Detection
        lang_info = cls.detect_language_and_script(normalized_query)

        # 3. Extract Explicit Source Citations & References
        source_references = cls.extract_source_references(normalized_query)
        has_source_filter = len(source_references) > 0

        # 4. Extract Literary Terminology & Tiṇai Context
        literary_terms = cls.extract_literary_terms(normalized_query)
        detected_tinai = cls.resolve_tinai(literary_terms, normalized_query)

        # 5. Extract Categorized Entities and Concepts
        entities, concepts = cls.categorize_terms(literary_terms)

        # 6. Extract Clean Search Keywords (BM25 tokens)
        keywords, bm25_tokens = cls.extract_search_tokens(normalized_query, literary_terms)

        # 7. Epistemic Intent Classification
        intent = IntentClassifier.classify_intent(normalized_query)

        # 8. Build Specialized Channel Payloads
        # 8a. BM25 Payload
        bm25_query = " ".join(bm25_tokens) if bm25_tokens else normalized_query

        # 8b. Dense Vector Payload (Cleaned semantic representation)
        vector_query = cls.build_vector_query(normalized_query, detected_tinai, literary_terms)

        # 8c. Knowledge Graph Seed Nodes & Cypher Parameters
        kg_seed_node_ids, kg_cypher_params = cls.build_kg_payload(
            entities, concepts, detected_tinai, source_references, literary_terms
        )

        # 8d. Common Multilingual Semantic Representation & Dense Shared Embedding
        detected_language = {
            "primary_language": lang_info["language"],
            "language": lang_info["language"],
            "language_code": lang_info["language_code"],
            "script": lang_info["script"],
            "is_tamil": lang_info["is_tamil"],
            "is_english": lang_info["is_english"],
            "is_mixed": lang_info["is_mixed"],
            "tamil_ratio": lang_info["tamil_ratio"],
            "english_ratio": lang_info["english_ratio"],
            "confidence": 0.95 if (lang_info["is_mixed"] or lang_info["is_tamil"]) else 0.90,
        }

        common_semantic_query = cls.build_common_semantic_query(
            normalized_query, detected_tinai, literary_terms, lang_info["language"]
        )

        retrieval_representation = cls.build_retrieval_representation(
            semantic_query=common_semantic_query,
            vector_query=vector_query,
            bm25_query=bm25_query,
            bm25_tokens=bm25_tokens,
            kg_seed_node_ids=kg_seed_node_ids,
            kg_cypher_params=kg_cypher_params,
            literary_terms=literary_terms,
        )

        return ProcessedQuery(
            original_query=original_query,
            normalized_query=normalized_query,
            language=lang_info["language"],
            language_code=lang_info["language_code"],
            script=lang_info["script"],
            is_tamil=lang_info["is_tamil"],
            is_english=lang_info["is_english"],
            is_mixed=lang_info["is_mixed"],
            tamil_ratio=lang_info["tamil_ratio"],
            english_ratio=lang_info["english_ratio"],
            keywords=keywords,
            literary_terms=literary_terms,
            entities=entities,
            concepts=concepts,
            detected_tinai=detected_tinai,
            intent=intent,
            source_references=source_references,
            has_source_filter=has_source_filter,
            bm25_query=bm25_query,
            bm25_tokens=bm25_tokens,
            vector_query=vector_query,
            kg_seed_node_ids=kg_seed_node_ids,
            kg_cypher_params=kg_cypher_params,
            metadata={
                "focus": focus,
                "token_count": len(bm25_tokens),
                "has_entities": len(entities) > 0,
                "has_concepts": len(concepts) > 0,
                "pipeline_version": "2.6.0",
            },
            detected_language=lang_info["language"],
            language_metadata=detected_language,
            identified_entities=entities,
            identified_concepts=concepts,
            identified_entities_concepts=entities + concepts,
            retrieval_representation=retrieval_representation,
        )

    @classmethod
    def normalize_query_text(cls, text: str) -> str:
        """
        Normalizes Unicode Tamil text safely without destroying poetic structures:
        - Unicode NFC normalization
        - Strips zero-width and invisible characters (\u200B, \u200C, \u200D, \uFEFF)
        - Normalizes virama (pulli)
        - Collapses spurious whitespace and standardizes quotes/dashes
        """
        if not text:
            return ""

        # 1. Unicode NFC canonical composition
        cleaned = unicodedata.normalize("NFC", text)

        # 2. Strip invisible control and zero-width codes
        cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff\u202a-\u202e]", "", cleaned)

        # 3. Standardize curly quotes and typographical dashes
        cleaned = re.sub(r"[\u2018\u2019]", "'", cleaned)
        cleaned = re.sub(r"[\u201c\u201d]", '"', cleaned)
        cleaned = re.sub(r"[\u2013\u2014]", " - ", cleaned)

        # 4. Canonical virama (pulli) handling
        cleaned = TamilNormalizer.normalize_virama(cleaned)

        # 5. Remove non-semantic noise characters while preserving hyphens, hashtags, quotes
        cleaned = re.sub(r"[!~`@$%^&*_+={}\[\]|\\:;<>?]+", " ", cleaned)

        # 6. Collapse multiple whitespace and spaces around hyphens
        cleaned = re.sub(r"[ \t\r\n]+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def detect_language_and_script(cls, text: str) -> Dict[str, Any]:
        """
        Classifies query into 'tamil', 'english', or 'mixed'.
        Computes character counts and script ratios.
        """
        if not text:
            return {
                "language": "unknown",
                "language_code": "unk",
                "script": "Empty",
                "is_tamil": False,
                "is_english": False,
                "is_mixed": False,
                "tamil_ratio": 0.0,
                "english_ratio": 0.0,
            }

        tamil_chars = len(cls.TAMIL_CHAR_REGEX.findall(text))
        latin_chars = len(cls.LATIN_CHAR_REGEX.findall(text))
        iso_chars = len(cls.ISO_DIACRITICS_REGEX.findall(text))
        total_letters = max(tamil_chars + latin_chars, 1)

        tamil_ratio = round(tamil_chars / total_letters, 3)
        english_ratio = round(latin_chars / total_letters, 3)

        # Mixed language detection (both Tamil script and English/Latin characters exist)
        if tamil_chars > 0 and latin_chars > 0:
            is_mixed = True
            is_tamil = False
            is_english = False
            language = "mixed"
            language_code = "ta-en"
            script = "Mixed (Tamil + Latin)"
        elif tamil_chars > 0 and latin_chars == 0:
            is_mixed = False
            is_tamil = True
            is_english = False
            language = "tamil"
            language_code = "ta"
            script = "Tamil Unicode"
        else:
            is_mixed = False
            is_tamil = False
            is_english = True
            language = "english"
            language_code = "en"
            if iso_chars > 1:
                script = "ISO 15919 Transliteration"
            else:
                script = "Latin (English)"

        return {
            "language": language,
            "language_code": language_code,
            "script": script,
            "is_tamil": is_tamil,
            "is_english": is_english,
            "is_mixed": is_mixed,
            "tamil_ratio": tamil_ratio,
            "english_ratio": english_ratio,
        }

    @classmethod
    def extract_source_references(cls, text: str) -> List[Dict[str, Any]]:
        """
        Parses explicit citations: sūtra/verse numbers, section/chapter names, and works.
        """
        references: List[Dict[str, Any]] = []
        seen_sutras: Set[int] = set()

        # 1. Parse sūtra numbers
        for pat in cls.SUTRA_PATTERNS:
            for match in pat.finditer(text):
                try:
                    sutra_num = int(match.group(1))
                    if sutra_num not in seen_sutras and 1 <= sutra_num <= 1612:
                        seen_sutras.add(sutra_num)
                        references.append({
                            "type": "sutra",
                            "sutra_number": sutra_num,
                            "work": "Tolkāppiyam",
                            "raw_match": match.group(0),
                            "citation": f"Tolkāppiyam Sūtra {sutra_num}",
                        })
                except Exception:
                    continue

        # 2. Parse sections and chapters
        for sec_name, pats in cls.SECTION_PATTERNS.items():
            for p in pats:
                if p.search(text):
                    # Attach section to existing sūtra reference or add as standalone
                    if references:
                        for ref in references:
                            ref.setdefault("section", sec_name)
                            if ref.get("sutra_number"):
                                ref["citation"] = f"Tolkāppiyam {sec_name} Sūtra {ref['sutra_number']}"
                    else:
                        references.append({
                            "type": "section",
                            "section": sec_name,
                            "work": "Tolkāppiyam",
                            "citation": f"Tolkāppiyam {sec_name}",
                        })
                    break

        return references

    @classmethod
    def extract_literary_terms(cls, text: str) -> List[Dict[str, Any]]:
        """
        Identifies and preserves domain-specific Classical Tamil poetics and grammar terms.
        Supports Tamil script, raw transliteration, and diacritic-normalized Latin forms.
        """
        terms: List[Dict[str, Any]] = []
        text_lower = text.lower()
        text_plain = cls.strip_diacritics(text).lower()
        seen_canonical: Set[str] = set()

        for surface_form, meta in LITERARY_TERMINOLOGY.items():
            sf_lower = surface_form.lower()
            sf_plain = cls.strip_diacritics(surface_form).lower()
            canonical_plain = cls.strip_diacritics(meta["canonical"]).lower()

            # Robust matching across Tamil script, exact lower, and diacritic-free transliteration
            matched = (
                surface_form in text
                or sf_lower in text_lower
                or sf_plain in text_plain
                or canonical_plain in text_plain
            )
            if matched:
                canonical = meta["canonical"]
                if canonical not in seen_canonical:
                    seen_canonical.add(canonical)
                    tamil_term = meta.get("tamil_term") or CANONICAL_TAMIL_TERMS.get(canonical)
                    if not tamil_term and any(0x0B80 <= ord(c) <= 0x0BFF for c in surface_form):
                        tamil_term = surface_form
                    terms.append({
                        "surface_form": surface_form,
                        "canonical": meta["canonical"],
                        "tamil_term": tamil_term or meta["canonical"],
                        "transliteration": meta["transliteration"],
                        "english": meta["english"],
                        "category": meta["category"],
                        "tinai": meta.get("tinai", "General"),
                        "kg_id": meta.get("kg_id"),
                    })

        return terms

    @classmethod
    def resolve_tinai(cls, literary_terms: List[Dict[str, Any]], text: str) -> str:
        """Resolves the primary Tiṇai context from extracted terms or text."""
        # 1. Check direct terms
        for term in literary_terms:
            t = term.get("tinai")
            if t and t != "General":
                return t

        # 2. Text heuristics
        text_plain = cls.strip_diacritics(text).lower()
        if "குறிஞ்சி" in text or "kurinci" in text_plain or "kurinji" in text_plain or "ceyon" in text_plain:
            return "Kuṟiñci"
        if "முல்லை" in text or "mullai" in text_plain or "mayon" in text_plain:
            return "Mullai"
        if "மருதம்" in text or "marutam" in text_plain or "marudham" in text_plain or "ventan" in text_plain:
            return "Marutam"
        if "நெய்தல்" in text or "neytal" in text_plain or "neithal" in text_plain or "varunan" in text_plain:
            return "Neytal"
        if "பாலை" in text or "palai" in text_plain:
            return "Pālai"

        return "General"


    @classmethod
    def categorize_terms(
        cls, literary_terms: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Splits terms into concrete entities vs abstract concepts while strictly preserving original Tamil terminology."""
        entities: List[Dict[str, Any]] = []
        concepts: List[Dict[str, Any]] = []

        concrete_categories = {"Deity", "Flora", "Fauna", "Landscape", "Work"}

        for t in literary_terms:
            canonical = t["canonical"]
            tamil_term = t.get("tamil_term") or CANONICAL_TAMIL_TERMS.get(canonical, canonical)
            item = {
                "term": canonical,
                "canonical": canonical,
                "tamil_term": tamil_term,
                "surface_form": t["surface_form"],
                "transliteration": t["transliteration"],
                "english": t.get("english", ""),
                "category": t["category"],
                "tinai": t.get("tinai", "General"),
                "kg_id": t.get("kg_id"),
            }
            if t["category"] in concrete_categories:
                entities.append(item)
            else:
                concepts.append(item)

        return entities, concepts

    @classmethod
    def extract_search_tokens(
        cls, text: str, literary_terms: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Extracts cleaned search keywords and BM25 tokens, filtering out generic
        stopwords while preserving all domain literary terms and compound roots.
        """
        # Preserved surface terms
        preserved_surface = {t["surface_form"].lower() for t in literary_terms}
        preserved_canonical = {t["canonical"].lower() for t in literary_terms}

        # Tokenize using TamilTokenizer
        raw_tokens = TamilTokenizer.tokenize_words(text, remove_stopwords=False)

        keywords: List[str] = []
        bm25_tokens: List[str] = []
        seen: Set[str] = set()

        for token in raw_tokens:
            tok_clean = token.strip()
            if not tok_clean:
                continue

            tok_lower = tok_clean.lower()

            # Always preserve literary terms even if they look like stopwords
            is_domain_term = (
                tok_lower in preserved_surface
                or tok_lower in preserved_canonical
                or any(tok_lower in sf for sf in preserved_surface)
            )

            if is_domain_term:
                if tok_lower not in seen:
                    seen.add(tok_lower)
                    keywords.append(tok_clean)
                    bm25_tokens.append(tok_clean)
                continue

            # Skip general stopwords
            if tok_lower in QUERY_STOPWORDS or len(tok_clean) <= 1:
                continue

            if tok_lower not in seen:
                seen.add(tok_lower)
                keywords.append(tok_clean)
                bm25_tokens.append(tok_clean)

        return keywords, bm25_tokens

    @classmethod
    def build_vector_query(
        cls, normalized_text: str, tinai: str, literary_terms: List[Dict[str, Any]]
    ) -> str:
        """
        Constructs dense vector input representation enriched with domain concepts
        for optimal multilingual SentenceTransformers embedding projection.
        """
        components = [normalized_text]
        if tinai and tinai != "General" and tinai.lower() not in normalized_text.lower():
            components.append(f"Tiṇai: {tinai}")

        english_terms = [t["english"] for t in literary_terms if t.get("english")]
        if english_terms:
            components.append(" | Concepts: " + ", ".join(english_terms[:3]))

        return " ".join(components)

    @classmethod
    def build_common_semantic_query(
        cls,
        normalized_text: str,
        detected_tinai: str,
        literary_terms: List[Dict[str, Any]],
        language: str = "tamil",
    ) -> str:
        """
        Builds a common cross-lingual semantic representation for Tamil, English,
        and mixed-language queries.
        Preserves original Tamil terminology in Tamil script alongside canonical
        transliterations and English concept glosses so that queries in all languages
        project into the same neighborhood in the shared embedding space.
        """
        components = [normalized_text]

        # 1. Preserved Tamil terminology
        tamil_terms = []
        for t in literary_terms:
            tt = t.get("tamil_term")
            if tt and tt not in normalized_text and tt not in tamil_terms:
                tamil_terms.append(tt)
        if tamil_terms:
            components.append("தமிழ்: " + " ".join(tamil_terms[:5]))

        # 2. Canonical concept labels & English glosses
        canonicals = [t["canonical"] for t in literary_terms if t.get("canonical")]
        english_glosses = [t["english"] for t in literary_terms if t.get("english")]
        concept_anchors = []
        for c in canonicals[:4]:
            if c.lower() not in normalized_text.lower() and c not in concept_anchors:
                concept_anchors.append(c)
        for eg in english_glosses[:3]:
            if eg.lower() not in normalized_text.lower() and eg not in concept_anchors:
                concept_anchors.append(eg)
        if concept_anchors:
            components.append("Concepts: " + ", ".join(concept_anchors))

        # 3. Tiṇai context
        if detected_tinai and detected_tinai != "General" and detected_tinai.lower() not in normalized_text.lower():
            components.append(f"Tiṇai: {detected_tinai}")

        return " | ".join(components)

    @classmethod
    def get_embedding_generator(cls):
        """Lazy-loads shared SentenceTransformerEmbeddingGenerator instance."""
        if not hasattr(cls, "_embedding_generator") or cls._embedding_generator is None:
            from retrieval.embeddings import SentenceTransformerEmbeddingGenerator
            cls._embedding_generator = SentenceTransformerEmbeddingGenerator()
        return cls._embedding_generator

    @classmethod
    def build_retrieval_representation(
        cls,
        semantic_query: str,
        vector_query: str,
        bm25_query: str,
        bm25_tokens: List[str],
        kg_seed_node_ids: List[str],
        kg_cypher_params: Dict[str, Any],
        literary_terms: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Constructs the unified retrieval representation in the shared multilingual semantic space.
        Generates the dense embedding vector, records preserved Tamil terms, and prepares
        downstream channel payloads.
        """
        generator = cls.get_embedding_generator()
        emb_vector = generator.encode_one(semantic_query)
        embedding_list = [round(float(v), 6) for v in emb_vector]

        preserved_tamil_terms = []
        for t in literary_terms:
            tt = t.get("tamil_term")
            if tt and tt not in preserved_tamil_terms:
                preserved_tamil_terms.append(tt)

        return {
            "common_semantic_query": semantic_query,
            "semantic_query": semantic_query,
            "embedding": embedding_list,
            "vector_dimension": len(embedding_list),
            "embedding_model": getattr(generator, "model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            "model_name": getattr(generator, "model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            "shared_space": True,
            "preserved_tamil_terms": preserved_tamil_terms,
            "canonical_concepts": [t["canonical"] for t in literary_terms],
            "channel_payloads": {
                "vector_query": vector_query,
                "bm25_query": bm25_query,
                "bm25_tokens": bm25_tokens,
                "kg_seed_node_ids": kg_seed_node_ids,
                "kg_cypher_params": kg_cypher_params,
            },
        }

    @classmethod
    def build_kg_payload(
        cls,
        entities: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]],
        tinai: str,
        source_references: List[Dict[str, Any]],
        literary_terms: List[Dict[str, Any]],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Generates candidate Knowledge Graph seed node IDs and Cypher parameters
        for anchoring BFS hops and multi-hop graph queries.
        """
        seed_ids: List[str] = []

        # 1. Add KG IDs from extracted entities and concepts
        for item in entities + concepts:
            kg_id = item.get("kg_id")
            if kg_id and kg_id not in seed_ids:
                seed_ids.append(kg_id)

        # 2. Add Tiṇai seed fallback
        tinai_to_id = {
            "Kuṟiñci": "kurinci",
            "Mullai": "mullai",
            "Marutam": "marutam",
            "Neytal": "neytal",
            "Pālai": "palai",
        }
        if tinai in tinai_to_id and tinai_to_id[tinai] not in seed_ids:
            seed_ids.append(tinai_to_id[tinai])

        # 3. Do not inject synthetic seeds for unmatched queries
        if not seed_ids:
            seed_ids = []

        # 4. Cypher parameters
        sutra_number = None
        for ref in source_references:
            if ref.get("sutra_number"):
                sutra_number = ref["sutra_number"]
                break

        cypher_params = {
            "seed_ids": seed_ids,
            "tinai": tinai,
            "sutra_number": sutra_number,
            "search_terms": [t["canonical"] for t in literary_terms],
        }

        return seed_ids, cypher_params

    @classmethod
    def _build_empty_processed_query(cls, raw: str) -> ProcessedQuery:
        """Returns structured default representation for empty inquiries."""
        return ProcessedQuery(
            original_query=raw,
            normalized_query="",
            language="unknown",
            language_code="unk",
            script="Empty",
            is_tamil=False,
            is_english=False,
            is_mixed=False,
            tamil_ratio=0.0,
            english_ratio=0.0,
            keywords=[],
            literary_terms=[],
            entities=[],
            concepts=[],
            detected_tinai="General",
            intent={
                "intent": "What / Fact",
                "tamil_label": "பொருள் / உண்மை",
                "primary_nyaya_focus": "Pratijñā (Target Proposition)",
            },
            source_references=[],
            has_source_filter=False,
            bm25_query="",
            bm25_tokens=[],
            vector_query="",
            kg_seed_node_ids=[],
            kg_cypher_params={"seed_ids": [], "tinai": "General", "sutra_number": None, "search_terms": []},
            metadata={"focus": "Relationship", "is_empty": True},
            detected_language="unknown",
            language_metadata={
                "primary_language": "unknown",
                "language": "unknown",
                "language_code": "unk",
                "script": "Empty",
                "is_tamil": False,
                "is_english": False,
                "is_mixed": False,
                "tamil_ratio": 0.0,
                "english_ratio": 0.0,
                "confidence": 0.0,
            },
            identified_entities=[],
            identified_concepts=[],
            identified_entities_concepts=[],
            retrieval_representation={
                "common_semantic_query": "",
                "semantic_query": "",
                "embedding": [0.0] * 384,
                "vector_dimension": 384,
                "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "shared_space": True,
                "preserved_tamil_terms": [],
                "canonical_concepts": [],
                "channel_payloads": {
                    "vector_query": "",
                    "bm25_query": "",
                    "bm25_tokens": [],
                    "kg_seed_node_ids": [],
                    "kg_cypher_params": {"seed_ids": [], "tinai": "General", "sutra_number": None, "search_terms": []},
                },
            },
        )


# Singleton instance
query_preprocessor = QueryPreprocessingService()
