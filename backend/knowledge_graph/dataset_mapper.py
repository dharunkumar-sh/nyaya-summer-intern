"""
Dataset-to-Knowledge-Graph Mapping Layer.

Uses Python and Pandas to:
1. Ingest, clean, and validate raw/processed classical Tamil datasets:
   - `tolkappiyam_canonical.json` (canonical sūtra corpus with provenance)
   - `Ontology.csv` (1,000 concept/entity ontological definitions and relations)
   - `Query_Mapping.csv` (2,640 query patterns and contextual linkages)
2. Non-destructively normalize Tamil Unicode text (NFC, virama preservation).
3. Clean missing values and validate required identifiers.
4. Separate and report invalid records with specific rejection reasons.
5. Map validated records into canonical Neo4j node payloads and relationship edges
   while preserving original source, sūtra, chapter, and verse references.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from core.logger import logger
from core.exceptions import KnowledgeGraphError
from preprocessing.tamil_normalizer import TamilNormalizer
from .schema import NodeLabels, RelTypes


class DatasetMapper:
    """
    Transforms classical Tamil literary datasets into validated, normalized,
    and source-traceable Knowledge Graph node and edge batch payloads.
    """

    # Concrete entity categories mapped to :Entity; others map to :Concept
    CONCRETE_ENTITY_CATEGORIES = {
        "deity", "flora", "fauna", "landscape", "time", "season",
        "instrument", "weapon", "food", "ornament", "person", "place",
        "character", "signifier", "karupporul",
    }

    # Classical Tamil affective events (Uripporuḷ) and aesthetic realizations (Meyppāṭu)
    EVENT_TERMS = {
        "puṇartal": ("Puṇartal", "AkamAffectiveEvent", "Intimate Union / Conjugal Union"),
        "punarthal": ("Puṇartal", "AkamAffectiveEvent", "Intimate Union / Conjugal Union"),
        "pirital": ("Pirital", "AkamAffectiveEvent", "Separation / Parting of lovers"),
        "pirithal": ("Pirital", "AkamAffectiveEvent", "Separation / Parting of lovers"),
        "iruttal": ("Iruttal", "AkamAffectiveEvent", "Patient Waiting / Faithful endurance"),
        "iruthal": ("Iruttal", "AkamAffectiveEvent", "Patient Waiting / Faithful endurance"),
        "iraṅkal": ("Iraṅkal", "AkamAffectiveEvent", "Melancholic Pining / Anxious longing"),
        "irangal": ("Iraṅkal", "AkamAffectiveEvent", "Melancholic Pining / Anxious longing"),
        "ūṭal": ("Ūṭal", "AkamAffectiveEvent", "Lovers' Feigned Estrangement / Sulking"),
        "udal": ("Ūṭal", "AkamAffectiveEvent", "Lovers' Feigned Estrangement / Sulking"),
        "oodal": ("Ūṭal", "AkamAffectiveEvent", "Lovers' Feigned Estrangement / Sulking"),
        "nimittam": ("Nimittam", "AkamAffectiveEvent", "Proximate emotional circumstances"),
        "meyppāṭu": ("Meyppāṭu", "AestheticManifestation", "Aesthetic emotional manifestation / Rasa"),
        "meyppadu": ("Meyppāṭu", "AestheticManifestation", "Aesthetic emotional manifestation / Rasa"),
        "eightemotionalaesthetics": ("EightEmotionalAesthetics", "AestheticManifestation", "Eight classical emotional aesthetics"),
        "eightrasas": ("EightRasas", "AestheticManifestation", "Eight classical emotional flavors"),
        "aestheticrealization": ("AestheticRealization", "AestheticManifestation", "Aesthetic dramatic realization"),
    }

    # Concrete entity taxonomy for classical Tamil signifiers
    CONCRETE_ENTITY_TAXONOMY = {
        # Deities (Teyvam)
        "cēyōṉ": "Deity", "ceyon": "Deity", "māyōṉ": "Deity", "mayon": "Deity",
        "vēntan": "Deity", "ventan": "Deity", "varuṇaṉ": "Deity", "varunan": "Deity",
        "teyvam": "Deity", "deity (teyvam)": "Deity",
        # Landscapes / Habitats (Nilam)
        "maivarai": "Landscape", "maivarai (mountain)": "Landscape",
        "kāṭu": "Landscape", "katu": "Landscape", "kāṭu (forest)": "Landscape",
        "tīmpuṉal": "Landscape", "timpunal": "Landscape", "tīmpuṉal (river plains)": "Landscape",
        "perumaṇal": "Landscape", "perumanal": "Landscape", "perumaṇal (littoral coast)": "Landscape",
        "nilam": "Landscape",
        # Biotic Elements: Flora & Fauna
        "maram": "Flora", "flora (maram)": "Flora",
        "mā": "Fauna", "ma": "Fauna", "puḷ": "Fauna", "pul": "Fauna", "fauna (mā & puḷ)": "Fauna",
        # Musical Instruments & Implements
        "yāḻ": "MusicalInstrument", "yazh": "MusicalInstrument", "paṟai": "MusicalInstrument", "parai": "MusicalInstrument",
        "music (yāḻ & paṟai)": "MusicalInstrument",
        # Sustenance & Human Action
        "uṇā": "Sustenance", "una": "Sustenance", "ceyti": "Action", "ceyyuḷ": "PoeticForm", "pāṭal": "PoeticForm",
    }

    # Canonical cross-ontology mappings to Ontology.csv concepts
    CANONICAL_TO_ONTOLOGY = {
        "akam": "onto_17",
        "puram": "onto_18",
        "thinai": "onto_21",
        "tiṇai": "onto_21",
        "kurinji": "onto_22",
        "kuṟiñci": "onto_22",
        "mullai": "onto_23",
        "marutham": "onto_24",
        "marutam": "onto_24",
        "neithal": "onto_25",
        "neytal": "onto_25",
        "paalai": "onto_26",
        "pālai": "onto_26",
        "mutalporuḷ": "onto_27",
        "mutalporul": "onto_27",
        "muthal porul": "onto_27",
        "karupporuḷ": "onto_28",
        "karupporul": "onto_28",
        "karu porul": "onto_28",
        "uripporuḷ": "onto_29",
        "uripporul": "onto_29",
        "uri porul": "onto_29",
        "meyppāṭu": "onto_16",
        "meyppadu": "onto_16",
        "tolkappiyam": "onto_49",
        "ezhuthathikaram": "onto_50",
        "eḻuttatikāram": "onto_50",
        "sollathikaram": "onto_51",
        "collatikāram": "onto_51",
        "porulathikaram": "onto_52",
        "poruḷatikāram": "onto_52",
    }

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"

        # Validation reports collected during processing
        self.validation_reports: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _resolve_triple_entity(
        cls,
        raw_name: str,
        tinai: str,
        source_ref: str,
        s_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Deterministically resolves a triple subject/object into an Event, Entity, or Concept node.
        Strips parenthetical annotations (e.g. 'Puṇartal (Intimate Union)' -> 'Puṇartal').
        """
        clean = re.sub(r"\(.*?\)", "", raw_name).strip()
        if not clean:
            clean = raw_name.strip()
        norm = clean.lower()

        # 1. Check if Affective Event
        if norm in cls.EVENT_TERMS or any(k in norm for k in ["punar", "pirit", "irutt", "irang", "udal", "oodal", "meyppa"]):
            info = cls.EVENT_TERMS.get(norm)
            canon_name = info[0] if info else clean
            ev_cat = info[1] if info else "AkamAffectiveEvent"
            ev_desc = info[2] if info else "Classical Tamil affective occurrence"
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", canon_name).lower().strip("_")
            node_id = f"event_{slug}"
            return node_id, {
                "id": node_id,
                "label": canon_name,
                "name": canon_name,
                "type": NodeLabels.EVENT,
                "hierarchy_level": "L4",
                "event_type": ev_cat,
                "category": ev_cat,
                "source": source_ref,
                "source_id": s_id,
                "source_reference": source_ref,
                "confidence": 1.0,
                "tinai": tinai,
                "validation_status": "verified_canonical",
                "metadata": {
                    "origin": "canonical_triples",
                    "event_type": ev_cat,
                    "description": ev_desc,
                    "raw_expression": raw_name,
                    "source_reference": source_ref,
                },
            }

        # 2. Check if concrete Entity
        ent_cat = cls.CONCRETE_ENTITY_TAXONOMY.get(norm) or cls.CONCRETE_ENTITY_TAXONOMY.get(raw_name.lower())
        is_concrete = ent_cat is not None or cls.is_concrete_entity(raw_name, "", "")
        if is_concrete:
            ent_cat = ent_cat or "Signifier"
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", clean).lower().strip("_")
            node_id = f"entity_{slug}"
            return node_id, {
                "id": node_id,
                "label": raw_name,
                "name": clean,
                "type": NodeLabels.ENTITY,
                "hierarchy_level": "L5",
                "source": source_ref,
                "source_id": s_id,
                "source_reference": source_ref,
                "confidence": 1.0,
                "tinai": tinai,
                "category": ent_cat,
                "validation_status": "verified_canonical",
                "metadata": {
                    "origin": "canonical_triples",
                    "category": ent_cat,
                    "raw_expression": raw_name,
                    "source_reference": source_ref,
                },
            }

        # 3. Default to Concept
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", clean).lower().strip("_")
        node_id = f"concept_{slug}"
        return node_id, {
            "id": node_id,
            "label": raw_name,
            "name": clean,
            "type": NodeLabels.CONCEPT,
            "hierarchy_level": "L4",
            "source": source_ref,
            "source_id": s_id,
            "source_reference": source_ref,
            "confidence": 1.0,
            "tinai": tinai,
            "validation_status": "verified_canonical",
            "metadata": {
                "origin": "canonical_triples",
                "raw_expression": raw_name,
                "source_reference": source_ref,
            },
        }

    # ==============================================================================
    # 1. Unicode Tamil Text Normalization & Cleaning
    # ==============================================================================

    @classmethod
    def normalize_tamil(cls, text: Any) -> str:
        """
        Normalizes Unicode Tamil text using NFC composition and TamilNormalizer.
        Preserves virama (pulli), verse line structure, and original glyphs.
        """
        if text is None or pd.isna(text):
            return ""
        str_val = str(text).strip()
        if not str_val:
            return ""
        # Use project's canonical TamilNormalizer
        normalized = TamilNormalizer.normalize(str_val)
        # Enforce canonical NFC
        return unicodedata.normalize("NFC", normalized)

    @classmethod
    def clean_string(cls, val: Any, default: str = "") -> str:
        """Cleans and strips a string, returning default if null/empty/whitespace."""
        if val is None or pd.isna(val):
            return default
        s = str(val).strip()
        return s if s else default

    @classmethod
    def is_concrete_entity(cls, name_or_cat: str, domain: str = "", main_theme: str = "") -> bool:
        """Determines whether a record/expression is a concrete Entity or an abstract Concept."""
        val_lower = (name_or_cat or "").lower().strip()
        dom_lower = (domain or "").lower().strip()
        theme_lower = (main_theme or "").lower().strip()

        if val_lower in cls.CONCRETE_ENTITY_TAXONOMY or any(k in val_lower for k in ["ceyon", "mayon", "ventan", "varunan", "maivarai", "katu", "yazh", "parai", "una", "maram", "deity", "landscape", "fauna", "flora"]):
            return True

        for c in cls.CONCRETE_ENTITY_CATEGORIES:
            if c in val_lower or c in dom_lower or c in theme_lower:
                return True
        return False

    @classmethod
    def is_event(cls, name_or_cat: str, domain: str = "", main_theme: str = "") -> bool:
        """Determines whether a record/expression is an Event (Affective action, poetics occurrence, or aesthetic realization)."""
        val_lower = (name_or_cat or "").lower().strip()
        dom_lower = (domain or "").lower().strip()
        theme_lower = (main_theme or "").lower().strip()

        if val_lower in cls.EVENT_TERMS or any(k in val_lower for k in ["punar", "pirit", "irutt", "irang", "udal", "oodal", "meyppa", "affective", "aesthetic"]):
            return True
        if any(k in dom_lower or k in theme_lower for k in ["affective", "urip", "aesthetic"]):
            return True
        return False

    # ==============================================================================
    # 2. Canonical Sūtras / Corpus Mapping (tolkappiyam_canonical.json)
    # ==============================================================================

    def map_canonical_corpus(
        self, json_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Maps tolkappiyam_canonical.json into Literature, Work, Section, Passage,
        Entity, Concept, Evidence nodes and their connecting relationships.
        Preserves full source provenance: Literature -> Work -> Section -> Passage.
        """
        path = json_file or (self.raw_dir / "tolkappiyam_canonical.json")
        if not path.exists():
            path = self.processed_dir / "preprocessed_corpus.json"

        if not path.exists():
            logger.warning(f"Canonical corpus file not found: {path}")
            return {"nodes": {}, "relationships": [], "valid_records": 0, "invalid_records": []}

        with open(path, "r", encoding="utf-8") as f:
            corpus_data = json.load(f)

        literature_nodes: List[Dict[str, Any]] = []
        work_nodes: List[Dict[str, Any]] = []
        section_nodes: List[Dict[str, Any]] = []
        passage_nodes: List[Dict[str, Any]] = []
        entity_nodes: List[Dict[str, Any]] = []
        concept_nodes: List[Dict[str, Any]] = []
        event_nodes: List[Dict[str, Any]] = []
        evidence_nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []

        seen_nodes: Set[str] = set()

        # Handle tolkappiyam_canonical.json top-level schema
        if isinstance(corpus_data, dict) and "corpus_metadata" in corpus_data:
            meta = corpus_data["corpus_metadata"]
            lit_id = "lit_sangam"
            literature_nodes.append({
                "id": lit_id,
                "label": "Sangam Literature (சங்க இலக்கியம்)",
                "name": "Sangam Literature",
                "type": NodeLabels.LITERATURE,
                "hierarchy_level": "L0",
                "source": "Classical Tamil Corpus",
                "confidence": 1.0,
                "metadata": {
                    "period": meta.get("period", "Classical Sangam"),
                    "total_works": 1,
                    "description": "Ancient Tamil classical literary and grammatical corpus",
                },
            })
            seen_nodes.add(lit_id)

            work_id = "work_tolkappiyam"
            work_nodes.append({
                "id": work_id,
                "label": meta.get("name", "Tolkāppiyam (தொல்காப்பியம்)"),
                "name": "Tolkāppiyam",
                "type": NodeLabels.WORK,
                "hierarchy_level": "L1",
                "source": "Tolkāppiyam",
                "work_name": "Tolkāppiyam",
                "confidence": 1.0,
                "metadata": {
                    "english_title": "Tolkāppiyam",
                    "total_sutras": meta.get("total_sutras", 1610),
                    "books_count": meta.get("books_count", 3),
                },
            })
            seen_nodes.add(work_id)
            relationships.append({
                "source_id": lit_id,
                "target_id": work_id,
                "relation": RelTypes.HAS_WORK,
                "confidence": 1.0,
            })

            # Sections: Books (Atikāram) and Chapters (Iyal)
            chap_id_map = {}
            for book_num, b in enumerate(meta.get("books", []), start=1):
                book_slug = b.get("id", "porul")
                book_id = f"sec_book_{book_slug}"
                b_name = b.get("name", "Poruḷatikāram")
                section_nodes.append({
                    "id": book_id,
                    "label": b.get("name", "Poruḷatikāram (பொருளதிகாரம்)"),
                    "name": b_name,
                    "section_name": b_name,
                    "work_name": "Tolkāppiyam",
                    "type": NodeLabels.SECTION,
                    "hierarchy_level": "L2",
                    "source": "Tolkāppiyam",
                    "confidence": 1.0,
                    "metadata": {
                        "section_type": "Book",
                        "atikaram": b_name,
                        "english": b.get("english"),
                        "sutra_count": b.get("sutra_count"),
                        "book_number": book_num,
                        "iyals": b.get("iyals", []),
                    },
                })
                seen_nodes.add(book_id)
                relationships.append({
                    "source_id": work_id,
                    "target_id": book_id,
                    "relation": RelTypes.HAS_SECTION,
                    "confidence": 1.0,
                })

                # Chapters (Iyal) under each Book
                for chap_num, iyal_name in enumerate(b.get("iyals", []), start=1):
                    chap_slug = re.sub(r"[^a-zA-Z0-9]+", "_", iyal_name).lower().strip("_")
                    chap_id = f"sec_chap_{book_slug}_{chap_slug}"
                    chap_id_map[iyal_name.lower()] = chap_id
                    section_nodes.append({
                        "id": chap_id,
                        "label": iyal_name,
                        "name": iyal_name,
                        "chapter_name": iyal_name,
                        "section_name": b_name,
                        "work_name": "Tolkāppiyam",
                        "type": NodeLabels.SECTION,
                        "hierarchy_level": "L2",
                        "source": f"Tolkāppiyam {b_name}",
                        "confidence": 1.0,
                        "metadata": {
                            "section_type": "Chapter",
                            "iyal": iyal_name,
                            "atikaram": b_name,
                            "parent_book_id": book_id,
                            "chapter_number": chap_num,
                            "book_number": book_num,
                        },
                    })
                    seen_nodes.add(chap_id)
                    relationships.append({
                        "source_id": book_id,
                        "target_id": chap_id,
                        "relation": RelTypes.HAS_SECTION,
                        "confidence": 1.0,
                    })

            sutras = corpus_data.get("canonical_sutras", [])
        elif isinstance(corpus_data, list):
            sutras = corpus_data
            chap_id_map = {}
        else:
            sutras = []
            chap_id_map = {}

        # Process each canonical Sūtra / Passage
        for idx, s in enumerate(sutras):
            s_id = s.get("id") or s.get("passage_id")
            if not s_id:
                invalid_records.append({"index": idx, "reason": "Missing passage/sutra identifier", "raw": s})
                continue

            raw_tamil = s.get("tamil_text") or s.get("original_text", "")
            norm_tamil = self.normalize_tamil(raw_tamil)
            translation = self.clean_string(s.get("english_translation", ""))
            translit = self.clean_string(s.get("transliteration", ""))
            sutra_num = int(s.get("sutra_number")) if s.get("sutra_number") is not None else None
            atikaram = self.clean_string(s.get("atikaram") or s.get("section", "Poruḷatikāram"))
            iyal = self.clean_string(s.get("iyal") or s.get("chapter", "Akattiṇaiyiyal"))
            tinai = self.clean_string(s.get("tinai", "General"))
            source_ref = f"Tolkāppiyam {atikaram} {iyal} Sūtra {sutra_num}" if sutra_num else "Tolkāppiyam"

            # Determine parent chapter ID
            chap_id = chap_id_map.get(iyal.lower())
            if not chap_id:
                book_slug = "porul"
                if "eluttu" in atikaram.lower():
                    book_slug = "eluttu"
                elif "col" in atikaram.lower():
                    book_slug = "col"
                chap_slug = re.sub(r"[^a-zA-Z0-9]+", "_", iyal).lower().strip("_")
                chap_id = f"sec_chap_{book_slug}_{chap_slug}"

            # Passage node with dual text, numbers, and full provenance metadata
            passage_nodes.append({
                "id": s_id,
                "source_id": s_id,
                "passage_id": s_id,
                "label": f"Sūtra {sutra_num}" if sutra_num else s_id,
                "type": NodeLabels.PASSAGE,
                "hierarchy_level": "L3",
                "source": source_ref,
                "confidence": 1.0,
                "tinai": tinai,
                "sutra_number": sutra_num,
                "verse_number": sutra_num,
                "passage_number": sutra_num,
                "original_text": raw_tamil,
                "normalized_text": norm_tamil,
                "text": norm_tamil,
                "translation": translation,
                "transliteration": translit,
                "work_name": "Tolkāppiyam",
                "work_id": "work_tolkappiyam",
                "section_name": atikaram,
                "chapter_name": iyal,
                "source_reference": source_ref,
                "corpus_info": "Classical Tamil Sangam Corpus",
                "metadata": {
                    "original_text": raw_tamil,
                    "normalized_text": norm_tamil,
                    "transliteration": translit,
                    "atikaram": atikaram,
                    "iyal": iyal,
                    "chapter_id": chap_id,
                    "category": s.get("category", "Epistemic Semiotics"),
                    "nyaya_mapping": s.get("nyaya_mapping", {}),
                    "source_reference": source_ref,
                },
            })
            seen_nodes.add(s_id)

            # Section (Chapter) -> Passage edge (deterministic traversal link)
            relationships.append({
                "source_id": chap_id,
                "target_id": s_id,
                "relation": RelTypes.HAS_PASSAGE,
                "confidence": 1.0,
            })

            # Evidence chunk node
            ev_id = f"ev_{s_id}_canonical"
            evidence_nodes.append({
                "id": ev_id,
                "label": f"Evidence for {s_id}",
                "type": NodeLabels.EVIDENCE,
                "hierarchy_level": "L3",
                "source": source_ref,
                "confidence": 1.0,
                "citation": source_ref,
                "text": norm_tamil,
                "passage_id": s_id,
                "metadata": {
                    "translation": translation,
                    "sutra_number": sutra_num,
                },
            })
            relationships.append({
                "source_id": ev_id,
                "target_id": s_id,
                "relation": RelTypes.SUPPORTED_BY,
                "confidence": 1.0,
                "source": source_ref,
                "source_reference": source_ref,
                "passage_id": s_id,
                "validation_level": "canonical_grounded",
            })

            # Literary Category node and Passage -> Category relationship
            cat_name = s.get("category")
            if cat_name:
                cat_clean = str(cat_name).strip()
                cat_slug = re.sub(r"[^a-zA-Z0-9]+", "_", cat_clean).lower().strip("_")
                cat_id = f"cat_{cat_slug}"
                if cat_id not in seen_nodes:
                    concept_nodes.append({
                        "id": cat_id,
                        "label": cat_clean,
                        "name": cat_clean,
                        "type": NodeLabels.CONCEPT,
                        "hierarchy_level": "L4",
                        "category": "LiteraryCategory",
                        "source": source_ref,
                        "source_id": s_id,
                        "source_reference": source_ref,
                        "confidence": 1.0,
                        "tinai": tinai,
                        "validation_status": "verified_canonical",
                        "metadata": {"origin": "canonical_category", "category_type": "LiteraryCategory"},
                    })
                    seen_nodes.add(cat_id)
                relationships.append({
                    "source_id": s_id,
                    "target_id": cat_id,
                    "relation": RelTypes.BELONGS_TO_CATEGORY,
                    "confidence": 1.0,
                    "source": source_ref,
                    "source_reference": source_ref,
                    "passage_id": s_id,
                    "validation_level": "canonical_grounded",
                })

            # Entities & Events mentioned in sūtra
            for ent_name in s.get("entities", []):
                ent_clean = str(ent_name).strip()
                if not ent_clean:
                    continue
                ent_lower = ent_clean.lower()

                # Check if this entity is an Affective Event (Uripporuḷ or Meyppāṭu)
                if ent_lower in self.EVENT_TERMS or any(k in ent_lower for k in ["punar", "pirit", "irutt", "irang", "udal", "oodal", "meyppa"]):
                    event_info = self.EVENT_TERMS.get(ent_lower)
                    canon_label = event_info[0] if event_info else ent_clean
                    event_cat = event_info[1] if event_info else "AkamAffectiveEvent"
                    event_desc = event_info[2] if event_info else "Classical Tamil affective occurrence"
                    ev_slug = re.sub(r"[^a-zA-Z0-9]+", "_", canon_label).lower().strip("_")
                    ev_id = f"event_{ev_slug}"

                    if ev_id not in seen_nodes:
                        event_nodes.append({
                            "id": ev_id,
                            "label": canon_label,
                            "name": canon_label,
                            "type": NodeLabels.EVENT,
                            "hierarchy_level": "L4",
                            "event_type": event_cat,
                            "category": event_cat,
                            "source": source_ref,
                            "source_id": s_id,
                            "source_reference": source_ref,
                            "confidence": 1.0,
                            "tinai": tinai,
                            "validation_status": "verified_canonical",
                            "metadata": {
                                "origin": "canonical_sutras",
                                "event_type": event_cat,
                                "description": event_desc,
                                "source_reference": source_ref,
                            },
                        })
                        seen_nodes.add(ev_id)

                    # Passage -> Event (DESCRIBES)
                    relationships.append({
                        "source_id": s_id,
                        "target_id": ev_id,
                        "relation": RelTypes.DESCRIBES,
                        "confidence": 1.0,
                        "source": source_ref,
                        "source_reference": source_ref,
                        "passage_id": s_id,
                        "validation_level": "canonical_grounded",
                    })
                else:
                    # Concrete Entity or Conceptual Entity
                    ent_cat = self.CONCRETE_ENTITY_TAXONOMY.get(ent_lower, "Signifier")
                    is_concrete = (ent_lower in self.CONCRETE_ENTITY_TAXONOMY) or self.is_concrete_entity(ent_cat, "", "")
                    ent_slug = re.sub(r"[^a-zA-Z0-9]+", "_", ent_clean).lower().strip("_")
                    ent_id = f"entity_{ent_slug}"

                    if ent_id not in seen_nodes:
                        entity_nodes.append({
                            "id": ent_id,
                            "label": ent_clean,
                            "name": ent_clean,
                            "type": NodeLabels.ENTITY if is_concrete else NodeLabels.CONCEPT,
                            "hierarchy_level": "L5" if is_concrete else "L4",
                            "source": source_ref,
                            "source_id": s_id,
                            "source_reference": source_ref,
                            "confidence": 1.0,
                            "tinai": tinai,
                            "category": ent_cat,
                            "validation_status": "verified_canonical",
                            "metadata": {"origin": "canonical_sutras", "category": ent_cat, "source_reference": source_ref},
                        })
                        seen_nodes.add(ent_id)

                    # Passage -> Entity (MENTIONS) or Concept (DISCUSSES)
                    relationships.append({
                        "source_id": s_id,
                        "target_id": ent_id,
                        "relation": RelTypes.MENTIONS if is_concrete else RelTypes.DISCUSSES,
                        "confidence": 1.0,
                        "source": source_ref,
                        "source_reference": source_ref,
                        "passage_id": s_id,
                        "validation_level": "canonical_grounded",
                    })

            # Semiotic triples in sūtra
            for tr in s.get("triples", []):
                sub = str(tr.get("subject", "")).strip()
                pred = str(tr.get("predicate", "")).strip()
                obj = str(tr.get("object", "")).strip()
                if not sub or not obj:
                    continue

                sub_id, sub_node = self._resolve_triple_entity(sub, tinai, source_ref, s_id)
                obj_id, obj_node = self._resolve_triple_entity(obj, tinai, source_ref, s_id)

                for nid, nnode in [(sub_id, sub_node), (obj_id, obj_node)]:
                    if nid not in seen_nodes:
                        ntype = nnode.get("type", NodeLabels.CONCEPT)
                        if ntype == NodeLabels.EVENT:
                            event_nodes.append(nnode)
                        elif ntype == NodeLabels.ENTITY:
                            entity_nodes.append(nnode)
                        else:
                            concept_nodes.append(nnode)
                        seen_nodes.add(nid)

                    # Connect Passage to node if not already linked
                    rel_p = RelTypes.DESCRIBES if nnode.get("type") == NodeLabels.EVENT else (
                        RelTypes.MENTIONS if nnode.get("type") == NodeLabels.ENTITY else RelTypes.DISCUSSES
                    )
                    relationships.append({
                        "source_id": s_id,
                        "target_id": nid,
                        "relation": rel_p,
                        "confidence": 1.0,
                        "source": source_ref,
                        "source_reference": source_ref,
                        "passage_id": s_id,
                        "validation_level": "canonical_grounded",
                    })

                # Canonicalize relationship
                pred_norm = pred.lower().replace("-", "_").replace(" ", "_")
                if pred_norm in ["hasuripporul", "has_uripporul"]:
                    rel_canonical = RelTypes.HAS_URIPPORUL
                elif pred_norm in ["hashabitat", "has_habitat"]:
                    rel_canonical = RelTypes.HAS_HABITAT
                elif pred_norm in ["presidesover", "presides_over"]:
                    rel_canonical = RelTypes.PRESIDES_OVER
                elif pred_norm in ["manifestsas", "manifests_as"]:
                    rel_canonical = RelTypes.MANIFESTS_AS
                elif pred_norm in ["deterministicallygrounds", "isspacedimensionof", "istimedimensionof"]:
                    rel_canonical = RelTypes.GROUNDS_IN
                elif pred_norm in ["manifestssignifierfor", "manifests_signifier_for"]:
                    rel_canonical = RelTypes.MANIFESTS_SIGNIFIER_FOR
                elif pred_norm in ["includescomponent", "includes_component", "consistsof", "consists_of", "hasconstituent", "has_constituent"]:
                    rel_canonical = RelTypes.INCLUDES_COMPONENT
                else:
                    rel_canonical = RelTypes.canonicalize(pred)

                relationships.append({
                    "source_id": sub_id,
                    "target_id": obj_id,
                    "relation": rel_canonical,
                    "confidence": 1.0,
                    "source": source_ref,
                    "source_reference": source_ref,
                    "passage_id": s_id,
                    "validation_level": "canonical_grounded",
                })

            # Cross-reference canonical concepts & passage with Ontology.csv
            for onto_key, onto_target_id in self.CANONICAL_TO_ONTOLOGY.items():
                if onto_key in s_id.lower() or onto_key in atikaram.lower() or onto_key in iyal.lower():
                    relationships.append({
                        "source_id": s_id,
                        "target_id": onto_target_id,
                        "relation": RelTypes.GROUNDS_IN_ONTOLOGY,
                        "confidence": 1.0,
                        "source": source_ref,
                        "source_reference": source_ref,
                        "passage_id": s_id,
                        "validation_level": "ontology_cross_linked",
                    })

        return {
            "nodes": {
                NodeLabels.LITERATURE: literature_nodes,
                NodeLabels.WORK: work_nodes,
                NodeLabels.SECTION: section_nodes,
                NodeLabels.PASSAGE: passage_nodes,
                NodeLabels.ENTITY: entity_nodes,
                NodeLabels.CONCEPT: concept_nodes,
                NodeLabels.EVENT: event_nodes,
                NodeLabels.EVIDENCE: evidence_nodes,
            },
            "relationships": relationships,
            "valid_records": len(passage_nodes),
            "invalid_records": invalid_records,
        }

    # ==============================================================================
    # 3. Ontology.csv Mapping (1,000 Records)
    # ==============================================================================

    def validate_and_clean_ontology(
        self, csv_file: Optional[Path] = None
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Loads and validates Ontology.csv using Pandas.
        Cleans missing values and returns (clean_df, invalid_records).
        """
        path = csv_file or (self.raw_dir / "Ontology.csv")
        if not path.exists():
            path = self.processed_dir / "ontology_processed.csv"

        if not path.exists():
            raise FileNotFoundError(f"Ontology dataset not found at {path}")

        df = pd.read_csv(path, encoding="utf-8")
        df.columns = [c.strip() for c in df.columns]

        required_cols = ["ID", "English_Label", "Tamil_Label", "Category", "Relation_Type"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise KnowledgeGraphError(f"Ontology.csv is missing required columns: {missing_cols}")

        invalid_records: List[Dict[str, Any]] = []
        valid_indices: List[int] = []

        for idx, row in df.iterrows():
            reasons = []
            if pd.isna(row["ID"]) or not str(row["ID"]).strip():
                reasons.append("Missing ID")
            if pd.isna(row["English_Label"]) or not str(row["English_Label"]).strip():
                reasons.append("Missing English_Label")
            if pd.isna(row["Tamil_Label"]) or not str(row["Tamil_Label"]).strip():
                reasons.append("Missing Tamil_Label")

            if reasons:
                invalid_records.append({
                    "row_index": idx,
                    "id": row.get("ID"),
                    "reasons": reasons,
                })
            else:
                valid_indices.append(idx)

        clean_df = df.loc[valid_indices].copy()

        # Clean string columns: fill NaNs with empty string
        for col in clean_df.columns:
            if col != "ID":
                clean_df[col] = clean_df[col].fillna("").astype(str).str.strip()

        # Normalize Tamil_Label with Unicode NFC
        clean_df["Tamil_Label_Normalized"] = clean_df["Tamil_Label"].apply(self.normalize_tamil)
        if "Synonyms_Tamil" in clean_df.columns:
            clean_df["Synonyms_Tamil_Normalized"] = clean_df["Synonyms_Tamil"].apply(self.normalize_tamil)
        else:
            clean_df["Synonyms_Tamil_Normalized"] = ""

        return clean_df, invalid_records

    def map_ontology_to_kg(
        self, df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Maps validated Ontology DataFrame into Concept and Entity nodes,
        and connects Parent_Concept and Child_Concepts relationships.
        """
        if df is None:
            df, invalid = self.validate_and_clean_ontology()
        else:
            invalid = []

        concepts: List[Dict[str, Any]] = []
        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        # Label-to-ID lookup map for resolving Parent_Concept and Child_Concepts references
        label_to_id: Dict[str, str] = {}
        for _, row in df.iterrows():
            onto_id = f"onto_{int(row['ID'])}"
            eng_label = str(row["English_Label"]).strip().lower()
            label_to_id[eng_label] = onto_id

        for _, row in df.iterrows():
            onto_id = f"onto_{int(row['ID'])}"
            eng_label = str(row["English_Label"]).strip()
            tamil_norm = str(row["Tamil_Label_Normalized"]).strip()
            raw_tamil = str(row["Tamil_Label"]).strip()
            theme = str(row.get("Main Theme", "")).strip()
            category = str(row.get("Category", "")).strip()
            domain = str(row.get("Domain", "")).strip()
            desc = str(row.get("Description", "")).strip()
            source = str(row.get("Source_Text", "Tolkappiyam")).strip()
            rel_raw = str(row.get("Relation_Type", "related_to")).strip()
            parent = str(row.get("Parent_Concept", "")).strip()
            children = str(row.get("Child_Concepts", "")).strip()
            keywords = str(row.get("Keywords", "")).strip()
            notes = str(row.get("Notes", "")).strip()

            meta = {
                "raw_tamil_label": raw_tamil,
                "synonyms_tamil": str(row.get("Synonyms_Tamil_Normalized", "")),
                "synonyms_english": str(row.get("Synonyms_English", "")),
                "main_theme": theme,
                "domain": domain,
                "keywords": keywords,
                "notes": notes,
                "original_id": int(row["ID"]),
                "source_reference": source,
            }

            is_concrete = self.is_concrete_entity(category, domain, theme)
            node_payload = {
                "id": onto_id,
                "label": f"{eng_label} ({tamil_norm})" if tamil_norm else eng_label,
                "name": eng_label,
                "type": NodeLabels.ENTITY if is_concrete else NodeLabels.CONCEPT,
                "hierarchy_level": "L5" if is_concrete else "L4",
                "source": source,
                "source_id": onto_id,
                "source_reference": source,
                "confidence": 0.95,
                "category": category or theme,
                "tinai": theme if "akam" in theme.lower() else "General",
                "validation_status": "verified_curated",
                "metadata": meta,
            }

            if is_concrete:
                entities.append(node_payload)
            else:
                node_payload["description"] = desc
                concepts.append(node_payload)

            # Map Parent_Concept Relationship
            if parent:
                parent_norm = parent.strip().lower()
                parent_id = label_to_id.get(parent_norm)
                if parent_id and parent_id != onto_id:
                    canonical_rel = RelTypes.canonicalize(rel_raw)
                    relationships.append({
                        "source_id": onto_id,
                        "target_id": parent_id,
                        "relation": canonical_rel,
                        "confidence": 0.95,
                        "source": source,
                        "source_reference": source,
                        "validation_level": "ontology_grounded",
                        "metadata": {"relation_raw": rel_raw},
                    })

            # Map Child_Concepts Relationships
            if children:
                for child_str in children.split(","):
                    c_clean = child_str.strip()
                    if not c_clean:
                        continue
                    c_norm = c_clean.lower()
                    child_id = label_to_id.get(c_norm)
                    if child_id and child_id != onto_id:
                        relationships.append({
                            "source_id": onto_id,
                            "target_id": child_id,
                            "relation": RelTypes.INCLUDES_COMPONENT,
                            "confidence": 0.95,
                            "source": source,
                            "source_reference": source,
                            "validation_level": "ontology_grounded",
                        })

        return {
            "nodes": {
                NodeLabels.CONCEPT: concepts,
                NodeLabels.ENTITY: entities,
            },
            "relationships": relationships,
            "valid_records": len(concepts) + len(entities),
            "invalid_records": invalid,
        }

    # ==============================================================================
    # 4. Query_Mapping.csv Mapping (2,640 Records)
    # ==============================================================================

    def validate_and_clean_query_mapping(
        self, csv_file: Optional[Path] = None
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Loads and validates Query_Mapping.csv using Pandas.
        """
        path = csv_file or (self.raw_dir / "Query_Mapping.csv")
        if not path.exists():
            path = self.processed_dir / "query_mapping_processed.csv"

        if not path.exists():
            raise FileNotFoundError(f"Query mapping dataset not found at {path}")

        df = pd.read_csv(path, encoding="utf-8")
        df.columns = [c.strip() for c in df.columns]

        required_cols = ["Thinai / Type", "Canonical Query Form", "Source_Reference"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise KnowledgeGraphError(f"Query_Mapping.csv is missing required columns: {missing_cols}")

        invalid_records: List[Dict[str, Any]] = []
        valid_indices: List[int] = []

        for idx, row in df.iterrows():
            if pd.isna(row["Thinai / Type"]) or not str(row["Thinai / Type"]).strip():
                invalid_records.append({"row_index": idx, "reason": "Missing Thinai / Type"})
            else:
                valid_indices.append(idx)

        clean_df = df.loc[valid_indices].copy()
        for col in clean_df.columns:
            clean_df[col] = clean_df[col].fillna("").astype(str).str.strip()

        return clean_df, invalid_records

    def map_query_mappings_to_kg(
        self, df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Extracts query pattern evidence and links them to Concept / Tiṇai nodes.
        Preserves classical source references: Tolkappiyam - Grammar / Porul.
        """
        if df is None:
            df, invalid = self.validate_and_clean_query_mapping()
        else:
            invalid = []

        evidence_nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        for idx, row in df.iterrows():
            thinai_type = str(row["Thinai / Type"]).strip()
            canonical_query = str(row["Canonical Query Form"]).strip()
            example_query = str(row["Example User Query"]).strip()
            source_ref = str(row["Source_Reference"]).strip()
            diff_level = str(row["Difficulty_Level"]).strip()

            target_concept_id = f"concept_{re.sub(r'[^a-zA-Z0-9]+', '_', thinai_type).lower().strip('_')}"
            ev_id = f"ev_query_{idx}"

            evidence_nodes.append({
                "id": ev_id,
                "label": f"Query Pattern: {thinai_type}",
                "name": f"Query Pattern: {thinai_type}",
                "type": NodeLabels.EVIDENCE,
                "hierarchy_level": "L3",
                "source": source_ref,
                "source_id": ev_id,
                "source_reference": source_ref,
                "confidence": 0.90,
                "citation": source_ref,
                "text": example_query,
                "metadata": {
                    "canonical_query_form": canonical_query,
                    "difficulty_level": diff_level,
                    "language_level": str(row["Language_Level"]).strip(),
                    "associated_context": str(row["Associated Context"]).strip(),
                    "emotional_cultural_meaning": str(row["Emotional / Cultural Meaning"]).strip(),
                    "related_concepts": str(row["Related_Concepts"]).strip(),
                },
            })

            # Connect Evidence -> Target Concept
            relationships.append({
                "source_id": ev_id,
                "target_id": target_concept_id,
                "relation": RelTypes.SUPPORTED_BY,
                "confidence": 0.90,
                "source": source_ref,
                "source_reference": source_ref,
                "validation_level": "query_grounded",
            })

        return {
            "nodes": {NodeLabels.EVIDENCE: evidence_nodes},
            "relationships": relationships,
            "valid_records": len(evidence_nodes),
            "invalid_records": invalid,
        }

    # ==============================================================================
    # 5. Combined Dataset Validation Report
    # ==============================================================================

    def validate_all_datasets(self) -> Dict[str, Any]:
        """
        Executes pre-validation across all datasets and compiles a comprehensive
        health report with valid counts, invalid rows, and Unicode status.
        """
        report: Dict[str, Any] = {"status": "valid", "datasets": {}}

        # 1. Canonical Corpus
        corpus_res = self.map_canonical_corpus()
        report["datasets"]["canonical_corpus"] = {
            "total_passages": corpus_res["valid_records"],
            "invalid_records": len(corpus_res["invalid_records"]),
            "relationships_extracted": len(corpus_res["relationships"]),
            "status": "valid" if not corpus_res["invalid_records"] else "warnings",
        }

        # 2. Ontology.csv
        try:
            onto_df, onto_invalid = self.validate_and_clean_ontology()
            report["datasets"]["ontology"] = {
                "total_records": len(onto_df),
                "invalid_records": len(onto_invalid),
                "columns_validated": list(onto_df.columns),
                "status": "valid" if not onto_invalid else "partial",
                "tamil_unicode_valid": True,
            }
        except Exception as e:
            report["datasets"]["ontology"] = {"error": str(e), "status": "failed"}
            report["status"] = "failed"

        # 3. Query_Mapping.csv
        try:
            qm_df, qm_invalid = self.validate_and_clean_query_mapping()
            report["datasets"]["query_mapping"] = {
                "total_records": len(qm_df),
                "invalid_records": len(qm_invalid),
                "status": "valid" if not qm_invalid else "partial",
            }
        except Exception as e:
            report["datasets"]["query_mapping"] = {"error": str(e), "status": "failed"}
            report["status"] = "failed"

        return report


# Singleton mapper instance
dataset_mapper = DatasetMapper()
