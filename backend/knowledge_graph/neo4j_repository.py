"""
Dedicated Neo4j Repository Layer for Knowledge Graph Operations.

Provides reusable, strongly-typed, idempotent, and parameterized Cypher operations
for Classical Tamil Literature (Tolkāppiyam semiotics and Nyāya epistemic deduction).

Capabilities:
- Idempotent single and batch upserts for Literature, Work, Section, Passage,
  Entity, Concept, Event, Evidence, and Relationships.
- Batch processing using Cypher UNWIND transactions.
- Zero duplicate nodes or duplicate relationships on repeated runs.
- Granular retrieval methods (Passage by ID, connected entities/concepts,
  source provenance tracing, multi-hop traversals, and evidence paths).
- Complete isolation from Flask web request handling.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from config import Config, Neo4jConfig
from core.logger import logger
from core.exceptions import KnowledgeGraphError, CypherQueryError
from services.neo4j_service import Neo4jService, neo4j_service
from .schema import NodeLabels, RelTypes


class Neo4jRepository:
    """
    Dedicated repository layer encapsulating Neo4j Aura database operations
    for the Nyāya-Inspired Neuro-Symbolic Reasoning Framework.
    """

    def __init__(self, service: Optional[Neo4jService] = None):
        self.service = service or neo4j_service

    def is_available(self) -> bool:
        """Checks if the Neo4j driver is initialized and available."""
        return self.service.get_driver() is not None

    # ==============================================================================
    # 1. Reusable Single Entity / Node Upserts (Idempotent MERGE)
    # ==============================================================================

    def upsert_literature(
        self,
        literature_id: str,
        name: str,
        period: Optional[str] = None,
        total_works: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L0 Literature corpus root node."""
        query = """
        MERGE (n:KGNode:Literature {id: $id})
        ON CREATE SET
            n.label = $name,
            n.name = $name,
            n.type = 'Literature',
            n.hierarchy_level = 'L0',
            n.period = $period,
            n.total_works = $total_works,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $name,
            n.name = $name,
            n.period = coalesce($period, n.period),
            n.total_works = coalesce($total_works, n.total_works),
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        RETURN n.id AS id, n.label AS label
        """
        params = {
            "id": literature_id,
            "name": name,
            "period": period or "Classical Sangam",
            "total_works": total_works or 1,
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": literature_id, "label": name}

    def upsert_work(
        self,
        work_id: str,
        name: str,
        literature_id: Optional[str] = None,
        english_title: Optional[str] = None,
        sutra_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L1 Work monograph node with optional HAS_WORK edge."""
        query = """
        MERGE (n:KGNode:Work {id: $id})
        ON CREATE SET
            n.label = $name,
            n.name = $name,
            n.english_title = $english_title,
            n.type = 'Work',
            n.hierarchy_level = 'L1',
            n.sutra_count = $sutra_count,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $name,
            n.name = $name,
            n.english_title = coalesce($english_title, n.english_title),
            n.sutra_count = coalesce($sutra_count, n.sutra_count),
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        WITH n
        OPTIONAL MATCH (lit:KGNode:Literature {id: $literature_id})
        WHERE $literature_id IS NOT NULL
        FOREACH (_ IN CASE WHEN lit IS NOT NULL THEN [1] ELSE [] END |
            MERGE (lit)-[r:HAS_WORK]->(n)
            ON CREATE SET r.created_at = timestamp()
        )
        RETURN n.id AS id, n.label AS label
        """
        params = {
            "id": work_id,
            "name": name,
            "literature_id": literature_id,
            "english_title": english_title,
            "sutra_count": sutra_count,
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": work_id, "label": name}

    def upsert_section(
        self,
        section_id: str,
        name: str,
        work_id: Optional[str] = None,
        atikaram: Optional[str] = None,
        iyal: Optional[str] = None,
        sutra_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L2 Section node with optional HAS_SECTION edge."""
        query = """
        MERGE (n:KGNode:Section {id: $id})
        ON CREATE SET
            n.label = $name,
            n.name = $name,
            n.atikaram = $atikaram,
            n.iyal = $iyal,
            n.type = 'Section',
            n.hierarchy_level = 'L2',
            n.sutra_count = $sutra_count,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $name,
            n.name = $name,
            n.atikaram = coalesce($atikaram, n.atikaram),
            n.iyal = coalesce($iyal, n.iyal),
            n.sutra_count = coalesce($sutra_count, n.sutra_count),
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        WITH n
        OPTIONAL MATCH (w:KGNode:Work {id: $work_id})
        WHERE $work_id IS NOT NULL
        FOREACH (_ IN CASE WHEN w IS NOT NULL THEN [1] ELSE [] END |
            MERGE (w)-[r:HAS_SECTION]->(n)
            ON CREATE SET r.created_at = timestamp()
        )
        RETURN n.id AS id, n.label AS label
        """
        params = {
            "id": section_id,
            "name": name,
            "work_id": work_id,
            "atikaram": atikaram or name,
            "iyal": iyal,
            "sutra_count": sutra_count,
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": section_id, "label": name}

    def upsert_passage(
        self,
        passage_id: str,
        sutra_number: Optional[int] = None,
        text: str = "",
        translation: str = "",
        transliteration: str = "",
        tinai: str = "General",
        section_id: Optional[str] = None,
        source: str = "Tolkāppiyam",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L3 Passage / Sūtra node with optional HAS_PASSAGE edge."""
        label = f"Sūtra {sutra_number}" if sutra_number else passage_id
        combined_meta = dict(metadata or {})
        if text:
            combined_meta["text"] = text
        if translation:
            combined_meta["translation"] = translation
        if transliteration:
            combined_meta["transliteration"] = transliteration

        query = """
        MERGE (n:KGNode:Passage {id: $id})
        ON CREATE SET
            n.label = $label,
            n.sutra_number = $sutra_number,
            n.text = $text,
            n.translation = $translation,
            n.transliteration = $transliteration,
            n.tinai = $tinai,
            n.type = 'Passage',
            n.hierarchy_level = 'L3',
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $label,
            n.sutra_number = coalesce($sutra_number, n.sutra_number),
            n.text = CASE WHEN $text <> '' THEN $text ELSE n.text END,
            n.translation = CASE WHEN $translation <> '' THEN $translation ELSE n.translation END,
            n.transliteration = CASE WHEN $transliteration <> '' THEN $transliteration ELSE n.transliteration END,
            n.tinai = $tinai,
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        WITH n
        OPTIONAL MATCH (sec:KGNode:Section {id: $section_id})
        WHERE $section_id IS NOT NULL
        FOREACH (_ IN CASE WHEN sec IS NOT NULL THEN [1] ELSE [] END |
            MERGE (sec)-[r:HAS_PASSAGE]->(n)
            ON CREATE SET r.created_at = timestamp()
        )
        RETURN n.id AS id, n.label AS label, n.sutra_number AS sutra_number
        """
        params = {
            "id": passage_id,
            "label": label,
            "sutra_number": sutra_number,
            "text": text,
            "translation": translation,
            "transliteration": transliteration,
            "tinai": tinai,
            "section_id": section_id,
            "source": source,
            "confidence": float(confidence),
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": passage_id, "label": label}

    def upsert_entity(
        self,
        entity_id: str,
        label: str,
        category: str = "Signifier",
        tinai: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source: str = "Tolkāppiyam",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L5 Entity node (flora, fauna, deity, landscape, time)."""
        combined_meta = dict(metadata or {})
        if properties:
            combined_meta.update(properties)

        query = """
        MERGE (n:KGNode:Entity {id: $id})
        ON CREATE SET
            n.label = $label,
            n.name = $label,
            n.category = $category,
            n.tinai = $tinai,
            n.type = 'Entity',
            n.hierarchy_level = 'L5',
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $label,
            n.name = $label,
            n.category = $category,
            n.tinai = coalesce($tinai, n.tinai),
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        RETURN n.id AS id, n.label AS label, n.category AS category
        """
        params = {
            "id": entity_id,
            "label": label,
            "category": category,
            "tinai": tinai or "General",
            "source": source,
            "confidence": float(confidence),
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": entity_id, "label": label}

    def upsert_concept(
        self,
        concept_id: str,
        label: str,
        category: str = "SemioticCategory",
        description: str = "",
        tinai: Optional[str] = None,
        source: str = "Tolkāppiyam",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L4 Concept node (Mutalporuḷ, Karupporuḷ, Uripporuḷ, Tiṇai)."""
        combined_meta = dict(metadata or {})
        if description:
            combined_meta["description"] = description

        query = """
        MERGE (n:KGNode:Concept {id: $id})
        ON CREATE SET
            n.label = $label,
            n.name = $label,
            n.category = $category,
            n.description = $description,
            n.tinai = $tinai,
            n.type = 'Concept',
            n.hierarchy_level = 'L4',
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $label,
            n.name = $label,
            n.category = $category,
            n.description = CASE WHEN $description <> '' THEN $description ELSE n.description END,
            n.tinai = coalesce($tinai, n.tinai),
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        RETURN n.id AS id, n.label AS label, n.category AS category
        """
        params = {
            "id": concept_id,
            "label": label,
            "category": category,
            "description": description,
            "tinai": tinai or "General",
            "source": source,
            "confidence": float(confidence),
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": concept_id, "label": label}

    def upsert_event(
        self,
        event_id: str,
        label: str,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        object_ref: Optional[str] = None,
        location: Optional[str] = None,
        time_ref: Optional[str] = None,
        tinai: Optional[str] = None,
        condition: Optional[str] = None,
        source: str = "Tolkāppiyam",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L5 Event node (poetic actions, union, separation)."""
        combined_meta = dict(metadata or {})
        for k, v in [
            ("actor", actor), ("action", action), ("object", object_ref),
            ("location", location), ("time", time_ref), ("condition", condition),
        ]:
            if v:
                combined_meta[k] = v

        query = """
        MERGE (n:KGNode:Event {id: $id})
        ON CREATE SET
            n.label = $label,
            n.name = $label,
            n.actor = $actor,
            n.action = $action,
            n.object = $object_ref,
            n.location = $location,
            n.time = $time_ref,
            n.condition = $condition,
            n.tinai = $tinai,
            n.type = 'Event',
            n.hierarchy_level = 'L5',
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $label,
            n.name = $label,
            n.actor = coalesce($actor, n.actor),
            n.action = coalesce($action, n.action),
            n.object = coalesce($object_ref, n.object),
            n.location = coalesce($location, n.location),
            n.time = coalesce($time_ref, n.time),
            n.condition = coalesce($condition, n.condition),
            n.tinai = coalesce($tinai, n.tinai),
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        RETURN n.id AS id, n.label AS label
        """
        params = {
            "id": event_id,
            "label": label,
            "actor": actor,
            "action": action,
            "object_ref": object_ref,
            "location": location,
            "time_ref": time_ref,
            "condition": condition,
            "tinai": tinai or "General",
            "source": source,
            "confidence": float(confidence),
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": event_id, "label": label}

    def upsert_evidence(
        self,
        evidence_id: str,
        citation: str,
        text: str,
        passage_id: Optional[str] = None,
        source: str = "Tolkāppiyam",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently upserts an L3 Evidence chunk node with optional SUPPORTED_BY edge."""
        combined_meta = dict(metadata or {})
        combined_meta["citation"] = citation
        combined_meta["text"] = text

        query = """
        MERGE (n:KGNode:Evidence {id: $id})
        ON CREATE SET
            n.label = $citation,
            n.citation = $citation,
            n.text = $text,
            n.passage_id = $passage_id,
            n.type = 'Evidence',
            n.hierarchy_level = 'L3',
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = $citation,
            n.citation = $citation,
            n.text = $text,
            n.passage_id = coalesce($passage_id, n.passage_id),
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json,
            n.updated_at = timestamp()
        WITH n
        OPTIONAL MATCH (p:KGNode:Passage {id: $passage_id})
        WHERE $passage_id IS NOT NULL
        FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
            MERGE (n)-[r:SUPPORTED_BY]->(p)
            ON CREATE SET r.created_at = timestamp()
        )
        RETURN n.id AS id, n.label AS label
        """
        params = {
            "id": evidence_id,
            "citation": citation,
            "text": text,
            "passage_id": passage_id,
            "source": source,
            "confidence": float(confidence),
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"id": evidence_id, "label": citation}

    def upsert_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: float = 1.0,
        validation_level: str = "corpus_grounded",
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Idempotently creates or updates a relationship between two nodes in Neo4j.
        Uses MERGE (s)-[r:REL]->(t) ensuring no duplicate edges are created on repeated execution.
        """
        canonical_rel = RelTypes.canonicalize(relation_type)
        combined_meta = dict(metadata or {})
        if properties:
            combined_meta.update(properties)

        query = f"""
        MATCH (s:KGNode {{id: $source_id}})
        MATCH (t:KGNode {{id: $target_id}})
        MERGE (s)-[r:{canonical_rel}]->(t)
        ON CREATE SET
            r.relation = $relation,
            r.confidence = $confidence,
            r.validation_level = $validation_level,
            r.metadata_json = $metadata_json,
            r.created_at = timestamp()
        ON MATCH SET
            r.relation = $relation,
            r.confidence = $confidence,
            r.validation_level = $validation_level,
            r.metadata_json = $metadata_json,
            r.updated_at = timestamp()
        RETURN type(r) AS rel_type, $source_id AS source, $target_id AS target
        """
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "relation": canonical_rel,
            "confidence": float(confidence),
            "validation_level": validation_level,
            "metadata_json": json.dumps(combined_meta, ensure_ascii=False),
        }
        res = self.service.execute_write(query, params, database=database)
        return res[0] if res else {"rel_type": canonical_rel, "source": source_id, "target": target_id}

    # ==============================================================================
    # 2. High-Performance Batch Insertion (UNWIND $batch)
    # ==============================================================================

    def batch_upsert_nodes(
        self,
        label: str,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Batch upserts nodes into Neo4j using UNWIND in chunks of batch_size.
        Idempotent: merges on `id` ensuring zero duplicates.
        """
        if not items:
            return {"total_items": 0, "upserted": 0}

        canonical_label = NodeLabels.from_string(label) or "".join(c for c in label if c.isalnum()) or "Entity"

        query = f"""
        UNWIND $batch AS item
        MERGE (n:KGNode:{canonical_label} {{id: item.id}})
        ON CREATE SET
            n.label = item.label,
            n.name = coalesce(item.name, item.label),
            n.type = item.type,
            n.hierarchy_level = item.hierarchy_level,
            n.source = item.source,
            n.source_id = item.source_id,
            n.confidence = item.confidence,
            n.tinai = item.tinai,
            n.category = item.category,
            n.text = item.text,
            n.original_text = item.original_text,
            n.normalized_text = item.normalized_text,
            n.translation = item.translation,
            n.sutra_number = item.sutra_number,
            n.verse_number = item.verse_number,
            n.passage_number = item.passage_number,
            n.work_name = item.work_name,
            n.section_name = item.section_name,
            n.chapter_name = item.chapter_name,
            n.source_reference = item.source_reference,
            n.corpus_info = item.corpus_info,
            n.section_type = item.section_type,
            n.book_number = item.book_number,
            n.chapter_number = item.chapter_number,
            n.event_type = item.event_type,
            n.validation_status = item.validation_status,
            n.metadata_json = item.metadata_json,
            n.created_at = timestamp()
        ON MATCH SET
            n.label = item.label,
            n.name = coalesce(item.name, n.name, item.label),
            n.type = item.type,
            n.hierarchy_level = item.hierarchy_level,
            n.source = item.source,
            n.source_id = coalesce(item.source_id, n.source_id),
            n.confidence = item.confidence,
            n.tinai = coalesce(item.tinai, n.tinai),
            n.category = coalesce(item.category, n.category),
            n.text = CASE WHEN item.text <> '' THEN item.text ELSE n.text END,
            n.original_text = CASE WHEN item.original_text <> '' THEN item.original_text ELSE n.original_text END,
            n.normalized_text = CASE WHEN item.normalized_text <> '' THEN item.normalized_text ELSE n.normalized_text END,
            n.translation = CASE WHEN item.translation <> '' THEN item.translation ELSE n.translation END,
            n.sutra_number = coalesce(item.sutra_number, n.sutra_number),
            n.verse_number = coalesce(item.verse_number, n.verse_number),
            n.passage_number = coalesce(item.passage_number, n.passage_number),
            n.work_name = coalesce(item.work_name, n.work_name),
            n.section_name = coalesce(item.section_name, n.section_name),
            n.chapter_name = coalesce(item.chapter_name, n.chapter_name),
            n.source_reference = coalesce(item.source_reference, n.source_reference),
            n.corpus_info = coalesce(item.corpus_info, n.corpus_info),
            n.section_type = coalesce(item.section_type, n.section_type),
            n.book_number = coalesce(item.book_number, n.book_number),
            n.chapter_number = coalesce(item.chapter_number, n.chapter_number),
            n.event_type = coalesce(item.event_type, n.event_type),
            n.validation_status = coalesce(item.validation_status, n.validation_status),
            n.metadata_json = item.metadata_json,
            n.updated_at = timestamp()
        """

        total_upserted = 0
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            serialized_chunk = []
            for it in chunk:
                meta = it.get("metadata", {})
                raw_txt = it.get("original_text") or meta.get("original_text", "")
                norm_txt = it.get("normalized_text") or meta.get("normalized_text", "")
                txt = it.get("text") or norm_txt or raw_txt
                s_num = it.get("sutra_number") or meta.get("sutra_number")
                v_num = it.get("verse_number") or it.get("passage_number") or s_num

                serialized_chunk.append({
                    "id": str(it["id"]),
                    "label": str(it.get("label", it["id"])),
                    "name": str(it.get("name") or it.get("label", it["id"])),
                    "type": str(it.get("type", canonical_label)),
                    "hierarchy_level": str(it.get("hierarchy_level", "L5")),
                    "source": str(it.get("source", "Tolkāppiyam")),
                    "source_id": str(it.get("source_id", it["id"])),
                    "confidence": float(it.get("confidence", 1.0)),
                    "tinai": it.get("tinai") or meta.get("tinai"),
                    "category": it.get("category") or meta.get("category"),
                    "text": txt,
                    "original_text": raw_txt,
                    "normalized_text": norm_txt,
                    "translation": it.get("translation") or meta.get("translation", ""),
                    "sutra_number": s_num,
                    "verse_number": v_num,
                    "passage_number": it.get("passage_number") or s_num,
                    "work_name": it.get("work_name") or meta.get("work_name"),
                    "section_name": it.get("section_name") or meta.get("section_name"),
                    "chapter_name": it.get("chapter_name") or meta.get("chapter_name"),
                    "source_reference": it.get("source_reference") or meta.get("source_reference", it.get("source", "")),
                    "corpus_info": it.get("corpus_info") or meta.get("corpus_info"),
                    "section_type": it.get("section_type") or meta.get("section_type"),
                    "book_number": it.get("book_number") or meta.get("book_number"),
                    "chapter_number": it.get("chapter_number") or meta.get("chapter_number"),
                    "event_type": it.get("event_type") or meta.get("event_type"),
                    "validation_status": it.get("validation_status") or meta.get("validation_status", "verified"),
                    "metadata_json": json.dumps(meta, ensure_ascii=False),
                })
            self.service.execute_write(query, {"batch": serialized_chunk}, database=database)
            total_upserted += len(serialized_chunk)

        logger.info(f"Batch upserted {total_upserted} nodes with label :{canonical_label}")
        return {"total_items": len(items), "upserted": total_upserted}

    def batch_upsert_relationships(
        self,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Batch upserts relationships grouped by canonical relationship type.
        Uses Cypher UNWIND with MERGE (s)-[r:REL]->(t) to prevent edge duplication.
        Preserves provenance: source, source_reference, passage_id, confidence, validation_level.
        """
        if not items:
            return {"total_items": 0, "upserted": 0}

        # Group by canonical relation type to allow static Cypher pattern
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            rel = RelTypes.canonicalize(it.get("relation", it.get("rel_type", "RELATED_TO")))
            grouped.setdefault(rel, []).append(it)

        total_upserted = 0
        for rel_type, rel_items in grouped.items():
            query = f"""
            UNWIND $batch AS item
            MATCH (s:KGNode {{id: item.source_id}})
            MATCH (t:KGNode {{id: item.target_id}})
            MERGE (s)-[r:{rel_type}]->(t)
            ON CREATE SET
                r.relation = '{rel_type}',
                r.confidence = item.confidence,
                r.validation_level = item.validation_level,
                r.source = item.source,
                r.source_reference = item.source_reference,
                r.passage_id = item.passage_id,
                r.metadata_json = item.metadata_json,
                r.created_at = timestamp()
            ON MATCH SET
                r.relation = '{rel_type}',
                r.confidence = item.confidence,
                r.validation_level = item.validation_level,
                r.source = coalesce(item.source, r.source),
                r.source_reference = coalesce(item.source_reference, r.source_reference),
                r.passage_id = coalesce(item.passage_id, r.passage_id),
                r.metadata_json = item.metadata_json,
                r.updated_at = timestamp()
            """
            for i in range(0, len(rel_items), batch_size):
                chunk = rel_items[i : i + batch_size]
                serialized_chunk = []
                for it in chunk:
                    meta = it.get("metadata", {})
                    serialized_chunk.append({
                        "source_id": str(it["source_id"]),
                        "target_id": str(it["target_id"]),
                        "confidence": float(it.get("confidence", 1.0)),
                        "validation_level": str(it.get("validation_level", "corpus_grounded")),
                        "source": str(it.get("source") or meta.get("source", "Tolkāppiyam")),
                        "source_reference": str(it.get("source_reference") or meta.get("source_reference", "")),
                        "passage_id": str(it.get("passage_id") or meta.get("passage_id", "")),
                        "metadata_json": json.dumps(meta, ensure_ascii=False),
                    })
                self.service.execute_write(query, {"batch": serialized_chunk}, database=database)
                total_upserted += len(serialized_chunk)

        logger.info(f"Batch upserted {total_upserted} relationships across {len(grouped)} types")
        return {"total_items": len(items), "upserted": total_upserted}

    def batch_upsert_passages(
        self,
        passages: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> int:
        """Batch upserts Passage nodes and their HAS_PASSAGE parent links."""
        res = self.batch_upsert_nodes(NodeLabels.PASSAGE, passages, batch_size=batch_size, database=database)

        # Batch link to sections if section_id present
        edges = []
        for p in passages:
            sec_id = p.get("section_id")
            if sec_id:
                edges.append({
                    "source_id": sec_id,
                    "target_id": p["id"],
                    "relation": RelTypes.HAS_PASSAGE,
                    "confidence": 1.0,
                })
        if edges:
            self.batch_upsert_relationships(edges, batch_size=batch_size, database=database)

        return res["upserted"]

    def batch_upsert_entities(
        self,
        entities: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> int:
        """Batch upserts Entity nodes."""
        res = self.batch_upsert_nodes(NodeLabels.ENTITY, entities, batch_size=batch_size, database=database)
        return res["upserted"]

    def batch_upsert_concepts(
        self,
        concepts: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> int:
        """Batch upserts Concept nodes."""
        res = self.batch_upsert_nodes(NodeLabels.CONCEPT, concepts, batch_size=batch_size, database=database)
        return res["upserted"]

    def batch_upsert_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        batch_size: int = 500,
        database: Optional[str] = None,
    ) -> int:
        """Batch upserts Evidence chunk nodes and links them to Passages."""
        res = self.batch_upsert_nodes(NodeLabels.EVIDENCE, evidence_items, batch_size=batch_size, database=database)

        # Link evidence -> passage
        edges = []
        for ev in evidence_items:
            pass_id = ev.get("passage_id")
            if pass_id:
                edges.append({
                    "source_id": ev["id"],
                    "target_id": pass_id,
                    "relation": RelTypes.SUPPORTED_BY,
                    "confidence": float(ev.get("confidence", 1.0)),
                })
        if edges:
            self.batch_upsert_relationships(edges, batch_size=batch_size, database=database)

        return res["upserted"]

    # ==============================================================================
    # 3. Query & Retrieval Operations
    # ==============================================================================

    def get_passage_by_id(
        self, passage_id: str, database: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a Passage node by its unique ID, including original/normalized text,
        translation, sutra/verse numbers, tinai, and its full parent hierarchy
        (Section -> Work -> Literature).
        """
        query = """
        MATCH (p:KGNode:Passage {id: $id})
        OPTIONAL MATCH (chap:KGNode:Section)-[:HAS_PASSAGE]->(p)
        OPTIONAL MATCH (w:KGNode:Work)-[:HAS_SECTION*1..2]->(chap)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:HAS_WORK]->(w)
        RETURN p {
            .*,
            hierarchy: {
                section: chap.name,
                section_id: chap.id,
                atikaram: coalesce(chap.section_name, chap.name, p.section_name),
                iyal: coalesce(chap.chapter_name, chap.name, p.chapter_name),
                work: coalesce(w.name, p.work_name),
                work_id: w.id,
                literature: lit.name,
                literature_id: lit.id
            }
        } AS passage
        """
        records = self.service.execute_read(query, {"id": passage_id}, database=database)
        if not records or not records[0].get("passage"):
            return None

        data = dict(records[0]["passage"])
        if "metadata_json" in data and data["metadata_json"]:
            try:
                data["metadata"] = json.loads(data["metadata_json"])
            except Exception:
                data["metadata"] = {}
        return data

    def get_passages_by_work(
        self,
        work_id_or_name: str,
        limit: int = 50,
        skip: int = 0,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all passages belonging to a specific classical work,
        ordered by sutra/verse number.
        """
        query = """
        MATCH (w:KGNode:Work)
        WHERE w.id = $work 
           OR toLower(w.name) = toLower($work) 
           OR toLower(w.label) = toLower($work)
           OR toLower(w.name) CONTAINS toLower($work)
           OR toLower(w.label) CONTAINS toLower($work)
           OR toLower(w.id) CONTAINS toLower($work)
        MATCH (w)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p:KGNode:Passage)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:HAS_WORK]->(w)
        RETURN p {
            .*,
            hierarchy: {
                section: sec.name,
                section_id: sec.id,
                atikaram: coalesce(sec.section_name, sec.name, p.section_name),
                iyal: coalesce(sec.chapter_name, sec.name, p.chapter_name),
                work: coalesce(w.name, p.work_name),
                work_id: w.id,
                literature: lit.name,
                literature_id: lit.id
            }
        } AS passage
        ORDER BY coalesce(p.sutra_number, p.verse_number, 9999), p.id
        SKIP $skip LIMIT $limit
        """
        records = self.service.execute_read(
            query,
            {"work": work_id_or_name, "limit": limit, "skip": skip},
            database=database,
        )
        passages: List[Dict[str, Any]] = []
        for r in records:
            p = dict(r["passage"])
            if "metadata_json" in p and p["metadata_json"]:
                try:
                    p["metadata"] = json.loads(p["metadata_json"])
                except Exception:
                    p["metadata"] = {}
            passages.append(p)
        return passages

    def get_passages_by_chapter(
        self,
        chapter_name_or_id: str,
        work_name_or_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves passages belonging to a specific chapter (Iyal) or section (Atikāram),
        with optional work filtering.
        """
        query = """
        MATCH (sec:KGNode:Section)
        WHERE sec.id = $chapter 
           OR toLower(sec.name) = toLower($chapter) 
           OR toLower(sec.label) = toLower($chapter)
           OR toLower(coalesce(sec.chapter_name, '')) = toLower($chapter)
           OR toLower(coalesce(sec.section_name, '')) = toLower($chapter)
           OR toLower(sec.name) CONTAINS toLower($chapter)
        MATCH (sec)-[:HAS_PASSAGE]->(p:KGNode:Passage)
        OPTIONAL MATCH (w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:HAS_WORK]->(w)
        WHERE ($work IS NULL OR w.id = $work OR toLower(w.name) = toLower($work) OR toLower(w.name) CONTAINS toLower($work))
        RETURN p {
            .*,
            hierarchy: {
                section: sec.name,
                section_id: sec.id,
                atikaram: coalesce(sec.section_name, sec.name, p.section_name),
                iyal: coalesce(sec.chapter_name, sec.name, p.chapter_name),
                work: coalesce(w.name, p.work_name),
                work_id: w.id,
                literature: lit.name,
                literature_id: lit.id
            }
        } AS passage
        ORDER BY coalesce(p.sutra_number, p.verse_number, 9999), p.id
        SKIP $skip LIMIT $limit
        """
        records = self.service.execute_read(
            query,
            {"chapter": chapter_name_or_id, "work": work_name_or_id, "limit": limit, "skip": skip},
            database=database,
        )
        passages: List[Dict[str, Any]] = []
        for r in records:
            p = dict(r["passage"])
            if "metadata_json" in p and p["metadata_json"]:
                try:
                    p["metadata"] = json.loads(p["metadata_json"])
                except Exception:
                    p["metadata"] = {}
            passages.append(p)
        return passages

    def get_passage_by_verse(
        self,
        verse_number: int,
        chapter: Optional[str] = None,
        work: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific passage by verse / sutra number with optional
        chapter and work constraints.
        """
        query = """
        MATCH (p:KGNode:Passage)
        WHERE (p.sutra_number = $verse_num OR p.verse_number = $verse_num OR p.passage_number = $verse_num)
        OPTIONAL MATCH (sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        OPTIONAL MATCH (w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:HAS_WORK]->(w)
        WHERE ($chapter IS NULL OR sec.id = $chapter OR toLower(sec.name) = toLower($chapter) OR toLower(coalesce(sec.chapter_name, '')) = toLower($chapter) OR toLower(coalesce(p.chapter_name, '')) = toLower($chapter))
          AND ($work IS NULL OR w.id = $work OR toLower(w.name) = toLower($work) OR toLower(coalesce(p.work_name, '')) = toLower($work))
        RETURN p {
            .*,
            hierarchy: {
                section: sec.name,
                section_id: sec.id,
                atikaram: coalesce(sec.section_name, sec.name, p.section_name),
                iyal: coalesce(sec.chapter_name, sec.name, p.chapter_name),
                work: coalesce(w.name, p.work_name),
                work_id: w.id,
                literature: lit.name,
                literature_id: lit.id
            }
        } AS passage
        LIMIT 1
        """
        records = self.service.execute_read(
            query,
            {"verse_num": verse_number, "chapter": chapter, "work": work},
            database=database,
        )
        if not records or not records[0].get("passage"):
            return None

        data = dict(records[0]["passage"])
        if "metadata_json" in data and data["metadata_json"]:
            try:
                data["metadata"] = json.loads(data["metadata_json"])
            except Exception:
                data["metadata"] = {}
        return data

    def get_passage_by_source_id(
        self, source_id: str, database: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a passage by its source identifier (e.g. 'tol-porul-akam-003').
        """
        query = """
        MATCH (p:KGNode:Passage)
        WHERE p.id = $source_id OR p.source_id = $source_id OR p.source = $source_id
        OPTIONAL MATCH (sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        OPTIONAL MATCH (w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:HAS_WORK]->(w)
        RETURN p {
            .*,
            hierarchy: {
                section: sec.name,
                section_id: sec.id,
                atikaram: coalesce(sec.section_name, sec.name, p.section_name),
                iyal: coalesce(sec.chapter_name, sec.name, p.chapter_name),
                work: coalesce(w.name, p.work_name),
                work_id: w.id,
                literature: lit.name,
                literature_id: lit.id
            }
        } AS passage
        LIMIT 1
        """
        records = self.service.execute_read(query, {"source_id": source_id}, database=database)
        if not records or not records[0].get("passage"):
            return None

        data = dict(records[0]["passage"])
        if "metadata_json" in data and data["metadata_json"]:
            try:
                data["metadata"] = json.loads(data["metadata_json"])
            except Exception:
                data["metadata"] = {}
        return data

    def get_source_hierarchy_for_passage(
        self, passage_id: str, database: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Performs a deterministic traversal from a passage back to its exact classical source:
        Passage ◄── HAS_PASSAGE ── Section (Iyal) ◄── HAS_SECTION ── Section (Book) ◄── HAS_SECTION ── Work ◄── HAS_WORK ── Literature
        """
        query = """
        MATCH (p:KGNode:Passage {id: $id})
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        RETURN p.id AS passage_id,
               p.label AS passage_label,
               p.sutra_number AS sutra_number,
               p.verse_number AS verse_number,
               p.original_text AS original_text,
               p.normalized_text AS normalized_text,
               p.translation AS translation,
               p.source AS source,
               p.source_reference AS source_reference,
               p.work_name AS work_name,
               p.section_name AS section_name,
               p.chapter_name AS chapter_name,
               p.corpus_info AS corpus_info,
               [n in nodes(path) | {
                   id: n.id,
                   label: n.label,
                   name: n.name,
                   type: n.type,
                   hierarchy_level: n.hierarchy_level,
                   section_type: n.section_type,
                   book_number: n.book_number,
                   chapter_number: n.chapter_number
               }] AS provenance_path,
               [r in relationships(path) | type(r)] AS relationship_types
        LIMIT 1
        """
        records = self.service.execute_read(query, {"id": passage_id}, database=database)
        if not records or not records[0].get("passage_id"):
            return None

        return dict(records[0])

    def get_connected_entities_and_concepts(
        self, passage_id: str, database: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves all Entity, Concept, and Event nodes directly connected to a Passage,
        categorized by type with relationship metadata.
        """
        query = """
        MATCH (p:KGNode {id: $id})-[r]-(n:KGNode)
        WHERE NOT n:Passage AND NOT n:Section AND NOT n:Work AND NOT n:Literature
        RETURN n.id AS id,
               n.label AS label,
               n.type AS type,
               labels(n) AS all_labels,
               n.category AS category,
               n.tinai AS tinai,
               n.metadata_json AS metadata_json,
               type(r) AS relation_type,
               r.confidence AS edge_confidence,
               CASE WHEN startNode(r) = p THEN 'outgoing' ELSE 'incoming' END AS direction
        """
        records = self.service.execute_read(query, {"id": passage_id}, database=database)

        entities: List[Dict[str, Any]] = []
        concepts: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []
        other: List[Dict[str, Any]] = []

        for r in records:
            meta = {}
            if r.get("metadata_json"):
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass

            item = {
                "id": r["id"],
                "label": r["label"],
                "type": r["type"],
                "category": r.get("category"),
                "tinai": r.get("tinai"),
                "relation": r["relation_type"],
                "direction": r["direction"],
                "confidence": float(r.get("edge_confidence", 1.0)),
                "metadata": meta,
            }

            all_lbls = r.get("all_labels") or []
            if NodeLabels.ENTITY in all_lbls or r.get("type") == "Entity":
                entities.append(item)
            elif NodeLabels.CONCEPT in all_lbls or r.get("type") == "Concept":
                concepts.append(item)
            elif NodeLabels.EVENT in all_lbls or r.get("type") == "Event":
                events.append(item)
            else:
                other.append(item)

        return {
            "passage_id": passage_id,
            "entities": entities,
            "concepts": concepts,
            "events": events,
            "other": other,
            "total_connected": len(records),
        }

    def get_source_information(
        self, node_id: str, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Traces provenance backwards from any node to find its supporting Passage,
        Section, Work, Literature root, and attached Evidence citations.
        """
        query = """
        MATCH (target:KGNode {id: $id})
        OPTIONAL MATCH p = (ancestor:KGNode)-[*1..4]->(target)
        WHERE ancestor:Passage OR ancestor:Section OR ancestor:Work OR ancestor:Literature
        WITH target, collect(distinct ancestor) AS ancestors
        OPTIONAL MATCH (ev:KGNode:Evidence)-[:SUPPORTED_BY]->(pass:KGNode:Passage)
        WHERE pass IN ancestors OR pass = target
        RETURN target {.*} AS target_node,
               [a in ancestors | {
                   id: a.id,
                   label: a.label,
                   type: a.type,
                   hierarchy_level: a.hierarchy_level,
                   source: a.source,
                   sutra_number: a.sutra_number,
                   tinai: a.tinai,
                   text: a.text,
                   translation: a.translation
               }] AS provenance_ancestors,
               [e in collect(distinct ev) | {
                   id: e.id,
                   citation: e.citation,
                   text: e.text,
                   source: e.source
               }] AS evidence_chunks
        """
        records = self.service.execute_read(query, {"id": node_id}, database=database)
        if not records:
            return {"node_id": node_id, "found": False, "ancestors": [], "evidence": []}

        rec = records[0]
        target_node = rec.get("target_node") or {}
        if "metadata_json" in target_node and target_node["metadata_json"]:
            try:
                target_node["metadata"] = json.loads(target_node["metadata_json"])
            except Exception:
                pass

        return {
            "node_id": node_id,
            "found": bool(target_node),
            "target": target_node,
            "provenance_chain": rec.get("provenance_ancestors", []),
            "evidence_chunks": rec.get("evidence_chunks", []),
        }

    def traverse_multi_hop(
        self,
        start_id: str,
        max_hops: int = 3,
        target_labels: Optional[List[str]] = None,
        rel_types: Optional[List[str]] = None,
        direction: str = "both",
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs multi-hop graph traversal up to max_hops from start_id,
        returning structured paths with intermediate nodes, relationships,
        and propagated cumulative confidence scores.
        """
        hops = min(max(max_hops, 1), 5)

        # Direction pattern
        if direction == "out":
            rel_pattern = f"-[r*1..{hops}]->"
        elif direction == "in":
            rel_pattern = f"<-[r*1..{hops}]-"
        else:
            rel_pattern = f"-[r*1..{hops}]-"

        query = f"""
        MATCH path = (start:KGNode {{id: $start_id}}){rel_pattern}(target:KGNode)
        WHERE start <> target
        RETURN [n in nodes(path) | {{
                   id: n.id,
                   label: n.label,
                   type: n.type,
                   hierarchy_level: n.hierarchy_level,
                   category: n.category,
                   tinai: n.tinai
               }}] AS path_nodes,
               [rel in relationships(path) | {{
                   type: type(rel),
                   confidence: coalesce(rel.confidence, 1.0),
                   validation_level: rel.validation_level
               }}] AS path_relationships,
               length(path) AS length
        LIMIT 50
        """
        records = self.service.execute_read(query, {"start_id": start_id}, database=database)
        results: List[Dict[str, Any]] = []

        for rec in records:
            p_nodes = rec.get("path_nodes", [])
            p_rels = rec.get("path_relationships", [])
            if not p_nodes or not p_rels:
                continue

            target_node = p_nodes[-1]
            # Filter by target_labels if requested
            if target_labels:
                target_type = target_node.get("type", "")
                if not any(lbl.lower() == target_type.lower() for lbl in target_labels):
                    continue

            # Filter by rel_types if requested
            if rel_types:
                rel_types_upper = {r.upper() for r in rel_types}
                if not all(e.get("type", "").upper() in rel_types_upper for e in p_rels):
                    continue

            # Calculate cumulative propagated confidence
            cumulative_conf = 1.0
            for rel in p_rels:
                cumulative_conf *= float(rel.get("confidence", 1.0))

            results.append({
                "start_id": start_id,
                "target_id": target_node.get("id"),
                "target_label": target_node.get("label"),
                "target_type": target_node.get("type"),
                "length": rec.get("length", len(p_rels)),
                "propagated_confidence": round(cumulative_conf, 4),
                "nodes": p_nodes,
                "relationships": p_rels,
            })

        # Sort paths by confidence (descending) and length (ascending)
        results.sort(key=lambda p: (-p["propagated_confidence"], p["length"]))
        return results

    def get_evidence_paths(
        self,
        concept_or_entity_id: str,
        max_depth: int = 4,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discovers proof trace paths connecting a given Concept or Entity
        back to primary Evidence or Passage nodes for Nyāya epistemic verification.
        """
        depth = min(max(max_depth, 1), 5)
        query = f"""
        MATCH path = (ground:KGNode)-[*1..{depth}]-(target:KGNode {{id: $id}})
        WHERE (ground:Evidence OR ground:Passage)
          AND ground <> target
        RETURN [n in nodes(path) | {{
                   id: n.id,
                   label: n.label,
                   type: n.type,
                   hierarchy_level: n.hierarchy_level,
                   text: n.text,
                   citation: n.citation
               }}] AS nodes,
               [r in relationships(path) | {{
                   type: type(r),
                   confidence: coalesce(r.confidence, 1.0)
               }}] AS edges,
               ground.id AS ground_id,
               labels(ground) AS ground_labels,
               length(path) AS length
        LIMIT 30
        """
        records = self.service.execute_read(query, {"id": concept_or_entity_id}, database=database)
        evidence_paths: List[Dict[str, Any]] = []

        for rec in records:
            edges = rec.get("edges", [])
            conf = 1.0
            for e in edges:
                conf *= float(e.get("confidence", 1.0))

            evidence_paths.append({
                "target_id": concept_or_entity_id,
                "ground_id": rec.get("ground_id"),
                "ground_type": "Evidence" if "Evidence" in rec.get("ground_labels", []) else "Passage",
                "length": rec.get("length", len(edges)),
                "confidence": round(conf, 4),
                "nodes": rec.get("nodes", []),
                "edges": edges,
            })

        evidence_paths.sort(key=lambda p: (-p["confidence"], p["length"]))
        return evidence_paths

    def find_semantic_paths(
        self,
        start_id: str,
        end_id: str,
        max_hops: int = 3,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discovers multi-hop semantic reasoning paths between two entities or concepts.
        Returns ordered sequences of nodes, edge types, confidence scores, and source citations.
        """
        hops = min(max(max_hops, 1), 5)
        query = f"""
        MATCH (start:KGNode {{id: $start_id}})
        MATCH (dest:KGNode {{id: $end_id}})
        MATCH path = (start)-[*1..{hops}]-(dest)
        WHERE start <> dest
        RETURN [n in nodes(path) | {{
                   id: n.id,
                   label: n.label,
                   name: n.name,
                   type: n.type,
                   category: n.category,
                   tinai: n.tinai
               }}] AS nodes,
               [r in relationships(path) | {{
                   type: type(r),
                   confidence: coalesce(r.confidence, 1.0),
                   source: r.source,
                   source_reference: r.source_reference,
                   passage_id: r.passage_id
               }}] AS edges,
               length(path) AS hop_count
        ORDER BY hop_count ASC
        LIMIT 20
        """
        records = self.service.execute_read(
            query, {"start_id": start_id, "end_id": end_id}, database=database
        )
        paths: List[Dict[str, Any]] = []
        for r in records:
            edges = r.get("edges", [])
            cumulative_conf = 1.0
            for e in edges:
                cumulative_conf *= float(e.get("confidence", 1.0))
            paths.append({
                "start_id": start_id,
                "end_id": end_id,
                "hop_count": r.get("hop_count", len(edges)),
                "cumulative_confidence": round(cumulative_conf, 4),
                "nodes": r.get("nodes", []),
                "edges": edges,
            })
        return paths

    def get_semantic_evidence_neighborhood(
        self,
        node_id: str,
        max_hops: int = 2,
        limit: int = 30,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves a node and its multi-hop semantic neighborhood (Entities, Concepts, Events),
        along with all supporting Passages and Evidence nodes.
        """
        hops = min(max(max_hops, 1), 3)
        query = f"""
        MATCH (center:KGNode {{id: $node_id}})
        OPTIONAL MATCH path = (center)-[*1..{hops}]-(neighbor:KGNode)
        WHERE neighbor <> center
          AND NOT neighbor:Literature AND NOT neighbor:Work AND NOT neighbor:Section
        WITH center, collect(DISTINCT neighbor) AS neighbors
        UNWIND (case when size(neighbors) = 0 then [null] else neighbors end) AS n
        OPTIONAL MATCH (p:KGNode:Passage)-[:DISCUSSES|MENTIONS|DESCRIBES|BELONGS_TO_CATEGORY]-(target)
        WHERE target = center OR (n IS NOT NULL AND target = n)
        RETURN center {{ .* }} AS center_node,
               collect(DISTINCT {{
                   id: n.id,
                   label: n.label,
                   name: n.name,
                   type: n.type,
                   category: n.category,
                   tinai: n.tinai
               }}) AS neighbors,
               collect(DISTINCT {{
                   passage_id: p.id,
                   sutra_number: p.sutra_number,
                   chapter_name: p.chapter_name,
                   source_reference: p.source_reference,
                   text: p.text
               }}) AS supporting_passages
        """
        records = self.service.execute_read(
            query, {"node_id": node_id}, database=database
        )
        if not records or not records[0].get("center_node"):
            return {"center_node": None, "neighbors": [], "supporting_passages": []}

        rec = records[0]
        neighbors = [n for n in rec.get("neighbors", []) if n and n.get("id")]
        passages = [p for p in rec.get("supporting_passages", []) if p and p.get("passage_id")]

        return {
            "center_node": rec["center_node"],
            "neighbors": neighbors[:limit],
            "supporting_passages": passages[:limit],
            "total_neighbors": len(neighbors),
            "total_passages": len(passages),
        }

    def get_literary_context_for_passage(
        self,
        passage_id: str,
        database: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the complete contextual graph for a Passage:
        - 4-tier literary hierarchy (Literature -> Work -> Section -> Passage)
        - Discussed Concepts ([:DISCUSSES])
        - Mentioned Entities ([:MENTIONS])
        - Described Events ([:DESCRIBES])
        - Literary / Grammatical Categories ([:BELONGS_TO_CATEGORY])
        - Supporting Evidence ([:SUPPORTED_BY])
        - Connected Ontology concepts
        """
        query = """
        MATCH (p:KGNode:Passage {id: $id})
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        OPTIONAL MATCH (p)-[:DISCUSSES]->(c:KGNode:Concept)
        WHERE coalesce(c.category, '') <> 'LiteraryCategory'
        OPTIONAL MATCH (p)-[:MENTIONS]->(ent:KGNode:Entity)
        OPTIONAL MATCH (p)-[:DESCRIBES]->(ev:KGNode:Event)
        OPTIONAL MATCH (p)-[:BELONGS_TO_CATEGORY]->(cat:KGNode:Concept)
        OPTIONAL MATCH (p)<-[:SUPPORTED_BY]-(evidence:KGNode:Evidence)
        OPTIONAL MATCH (c)-[:GROUNDS_IN_ONTOLOGY]->(onto:KGNode)
        RETURN p { .* } AS passage,
               [n in nodes(path) | {
                   id: n.id,
                   label: n.label,
                   name: n.name,
                   type: n.type,
                   hierarchy_level: n.hierarchy_level
               }] AS provenance_path,
               collect(DISTINCT { id: c.id, label: c.label, name: c.name, type: c.type, tinai: c.tinai }) AS concepts,
               collect(DISTINCT { id: ent.id, label: ent.label, name: ent.name, type: ent.type, category: ent.category }) AS entities,
               collect(DISTINCT { id: ev.id, label: ev.label, name: ev.name, type: ev.type, event_type: ev.event_type }) AS events,
               collect(DISTINCT { id: cat.id, label: cat.label, name: cat.name, type: cat.type }) AS categories,
               collect(DISTINCT { id: evidence.id, citation: evidence.citation, text: evidence.text }) AS evidence,
               collect(DISTINCT { id: onto.id, label: onto.label, name: onto.name, type: onto.type }) AS ontology_links
        """
        records = self.service.execute_read(query, {"id": passage_id}, database=database)
        if not records or not records[0].get("passage"):
            return None

        rec = records[0]
        data = dict(rec["passage"])
        return {
            "passage": data,
            "provenance_path": rec.get("provenance_path", []),
            "concepts": [c for c in rec.get("concepts", []) if c and c.get("id")],
            "entities": [e for e in rec.get("entities", []) if e and e.get("id")],
            "events": [ev for ev in rec.get("events", []) if ev and ev.get("id")],
            "categories": [cat for cat in rec.get("categories", []) if cat and cat.get("id")],
            "evidence": [ev for ev in rec.get("evidence", []) if ev and ev.get("id")],
            "ontology_links": [o for o in rec.get("ontology_links", []) if o and o.get("id")],
        }

    def query_tinai_tripartite_graph(
        self,
        tinai_name: str,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Traverses the classical Tamil poetics tripartite semiotic model for a specific Tiṇai:
        - Mutalporuḷ: Space (Nilam) and Time (Poḻutu)
        - Karupporuḷ: Presiding deity, flora, fauna, instruments, sustenance
        - Uripporuḷ: Affective mood event (Puṇartal, Pirital, etc.)
        - Passages: Sūtras formulating this landscape
        """
        query = """
        MATCH (tinai:KGNode)
        WHERE (tinai:Concept OR tinai:Entity)
          AND (toLower(tinai.label) CONTAINS toLower($tinai) 
               OR toLower(tinai.name) CONTAINS toLower($tinai)
               OR toLower(tinai.id) CONTAINS toLower($tinai))
        OPTIONAL MATCH (deity:KGNode:Entity)-[:PRESIDES_OVER]->(tinai)
        OPTIONAL MATCH (tinai)-[:HAS_HABITAT]->(landscape:KGNode)
        OPTIONAL MATCH (tinai)-[:HAS_URIPPORUL]->(event:KGNode:Event)
        OPTIONAL MATCH (karu:KGNode:Concept)
        WHERE toLower(karu.label) CONTAINS 'karupporu' OR toLower(karu.name) CONTAINS 'karupporu'
        OPTIONAL MATCH (karu)-[:INCLUDES_COMPONENT]->(biotic:KGNode:Entity)
        OPTIONAL MATCH (p:KGNode:Passage)-[:DISCUSSES|MENTIONS|DESCRIBES]->(target)
        WHERE target IN [tinai, deity, landscape, event]
        RETURN tinai { .* } AS tinai_node,
               collect(DISTINCT deity { .* }) AS deities,
               collect(DISTINCT landscape { .* }) AS landscapes,
               collect(DISTINCT event { .* }) AS uripporul_events,
               collect(DISTINCT biotic { .* }) AS biotic_signifiers,
               collect(DISTINCT {
                   id: p.id,
                   sutra_number: p.sutra_number,
                   chapter_name: p.chapter_name,
                   source_reference: p.source_reference,
                   text: p.text
               }) AS passages
        """
        records = self.service.execute_read(query, {"tinai": tinai_name}, database=database)
        if not records or not records[0].get("tinai_node"):
            return {
                "tinai": tinai_name,
                "found": False,
                "mutalporul": {},
                "karupporul": {},
                "uripporul": {},
                "passages": [],
            }

        rec = records[0]
        tinai_node = rec["tinai_node"]
        deities = [d for d in rec.get("deities", []) if d and d.get("id")]
        landscapes = [l for l in rec.get("landscapes", []) if l and l.get("id")]
        events = [e for e in rec.get("uripporul_events", []) if e and e.get("id")]
        biotic = [b for b in rec.get("biotic_signifiers", []) if b and b.get("id")]
        passages = [p for p in rec.get("passages", []) if p and p.get("id")]

        return {
            "tinai": tinai_name,
            "found": True,
            "tinai_node": tinai_node,
            "mutalporul": {
                "landscapes": landscapes,
                "description": "Spatial (Nilam) and Temporal (Poḻutu) habitat locus",
            },
            "karupporul": {
                "presiding_deities": deities,
                "biotic_and_cultural_signifiers": biotic,
                "description": "Biotic, cultural, and environmental signifiers",
            },
            "uripporul": {
                "affective_events": events,
                "description": "Affective psychological moods and emotional occurrences",
            },
            "supporting_passages": passages,
        }

    def get_graph_elements(
        self,
        limit: int = 250,
        center_id: Optional[str] = None,
        hops: int = 2,
        include_ontology: bool = False,
        category: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves graph nodes and relationships directly from Neo4j Aura,
        preserving all entity properties, relationship types, source references,
        and provenance metadata required for Cytoscape visualization.
        """
        hops = min(max(int(hops), 1), 4)
        limit = min(max(int(limit), 10), 1500)

        if center_id:
            query = f"""
            MATCH (center:KGNode {{id: $center_id}})
            OPTIONAL MATCH (center)-[r*1..{hops}]-(m:KGNode)
            WHERE ($include_ontology = true OR NOT m:Concept OR NOT m.id STARTS WITH 'onto_')
            WITH center, collect(DISTINCT m) + [center] AS neighborhood
            UNWIND neighborhood AS n
            WITH DISTINCT n LIMIT $limit
            WITH collect(n) AS selected_nodes
            UNWIND selected_nodes AS n
            OPTIONAL MATCH (n)-[r]->(m:KGNode)
            WHERE m IN selected_nodes
            WITH selected_nodes, collect(DISTINCT r) AS rels
            RETURN [node IN selected_nodes | node {{ .*, labels: labels(node) }}] AS nodes,
                   [r IN rels WHERE r IS NOT NULL | {{
                       id: coalesce(r.id, elementId(r), startNode(r).id + '_' + type(r) + '_' + endNode(r).id + '_' + toString(id(r))),
                       source: startNode(r).id,
                       target: endNode(r).id,
                       type: type(r),
                       relation: type(r),
                       label: coalesce(r.label, type(r)),
                       confidence: coalesce(r.confidence, 1.0),
                       validation_level: coalesce(r.validation_level, 'corpus_validated'),
                       source_corpus: coalesce(r.source, 'Tolkāppiyam'),
                       source_reference: coalesce(r.source_reference, ''),
                       passage_id: r.passage_id,
                       metadata_json: r.metadata_json
                   }}] AS relationships
            """
            params = {
                "center_id": center_id,
                "include_ontology": bool(include_ontology),
                "limit": limit,
            }
        else:
            query = """
            MATCH (n:KGNode)
            WHERE ($include_ontology = true OR NOT n:Concept OR NOT n.id STARTS WITH 'onto_')
              AND ($category IS NULL OR n.category = $category OR n.type = $category)
            WITH n LIMIT $limit
            WITH collect(n) AS selected_nodes
            UNWIND selected_nodes AS n
            OPTIONAL MATCH (n)-[r]->(m:KGNode)
            WHERE m IN selected_nodes
            WITH selected_nodes, collect(DISTINCT r) AS rels
            RETURN [node IN selected_nodes | node { .*, labels: labels(node) }] AS nodes,
                   [r IN rels WHERE r IS NOT NULL | {
                       id: coalesce(r.id, elementId(r), startNode(r).id + '_' + type(r) + '_' + endNode(r).id + '_' + toString(id(r))),
                       source: startNode(r).id,
                       target: endNode(r).id,
                       type: type(r),
                       relation: type(r),
                       label: coalesce(r.label, type(r)),
                       confidence: coalesce(r.confidence, 1.0),
                       validation_level: coalesce(r.validation_level, 'corpus_validated'),
                       source_corpus: coalesce(r.source, 'Tolkāppiyam'),
                       source_reference: coalesce(r.source_reference, ''),
                       passage_id: r.passage_id,
                       metadata_json: r.metadata_json
                   }] AS relationships
            """
            params = {
                "include_ontology": bool(include_ontology),
                "category": category,
                "limit": limit,
            }

        records = self.service.execute_read(query, params, database=database)
        if not records:
            return {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "source": "neo4j_aura",
            }

        rec = records[0]
        raw_nodes = rec.get("nodes") or []
        raw_rels = rec.get("relationships") or []

        parsed_nodes = []
        node_ids = set()
        for n in raw_nodes:
            node_dict = dict(n)
            nid = str(node_dict.get("id") or "")
            if not nid:
                continue
            meta = {}
            if "metadata_json" in node_dict and node_dict["metadata_json"]:
                try:
                    meta = json.loads(node_dict["metadata_json"])
                except Exception:
                    meta = {}
            node_dict["metadata"] = meta
            if nid not in node_ids:
                node_ids.add(nid)
                parsed_nodes.append(node_dict)

        parsed_rels = []
        seen_edge_ids = set()
        for idx, r in enumerate(raw_rels):
            rel_dict = dict(r)
            src = str(rel_dict.get("source") or "")
            tgt = str(rel_dict.get("target") or "")
            # Verify endpoints exist in selected nodes
            if not src or not tgt or src not in node_ids or tgt not in node_ids:
                continue
            rel_type = rel_dict.get("type") or rel_dict.get("relation") or "RELATED_TO"
            rel_dict["type"] = rel_type
            rel_dict["relation"] = rel_type
            edge_id = str(rel_dict.get("id") or "")
            if not edge_id or edge_id in seen_edge_ids:
                edge_id = f"e_{src}_{rel_type}_{tgt}_{idx}"
                rel_dict["id"] = edge_id
            seen_edge_ids.add(edge_id)

            meta = {}
            if "metadata_json" in rel_dict and rel_dict["metadata_json"]:
                try:
                    meta = json.loads(rel_dict["metadata_json"])
                except Exception:
                    meta = {}
            rel_dict["metadata"] = meta
            parsed_rels.append(rel_dict)

        return {
            "nodes": parsed_nodes,
            "relationships": parsed_rels,
            "edges": parsed_rels,
            "total_nodes": len(parsed_nodes),
            "total_edges": len(parsed_rels),
            "source": "neo4j_aura",
            "database": database or self.service.database or "neo4j",
        }

    # ==============================================================================
    # 7. Passage Vector Indexing & Embedding Operations
    # ==============================================================================

    def ensure_passage_vector_index(
        self,
        index_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        similarity_function: Optional[str] = None,
        model_name: Optional[str] = None,
        encoder: Optional[Any] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Idempotently registers a Neo4j 5+ vector index on Passage nodes for semantic search.
        Dynamically resolves dimensions from the active embedding model/encoder if not explicitly provided,
        ensuring the index dimensions exactly match the embedding model's output without hardcoding errors.
        Uses backtick-quoted indexConfig options for vector.dimensions and vector.similarity_function.
        """
        idx_name = index_name or Neo4jConfig.VECTOR_INDEX_NAME
        sim_fn = (similarity_function or Neo4jConfig.VECTOR_SIMILARITY_FUNCTION).lower()
        if sim_fn not in ("cosine", "euclidean"):
            sim_fn = "cosine"

        if dimensions is not None and int(dimensions) > 0:
            dim = int(dimensions)
        else:
            dim = Neo4jConfig.resolve_vector_dimensions(model_name=model_name, encoder=encoder)

        query = f"""
        CREATE VECTOR INDEX {idx_name} IF NOT EXISTS
        FOR (p:Passage)
        ON (p.embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {dim},
            `vector.similarity_function`: '{sim_fn}'
        }}}}
        """
        try:
            self.service.execute_write(query, {}, database=database)
            logger.info(f"Neo4j vector index '{idx_name}' ensured (dim={dim}, metric={sim_fn})")
            return {
                "status": "ready",
                "index_name": idx_name,
                "dimensions": dim,
                "similarity_function": sim_fn,
            }
        except Exception as e:
            logger.warning(f"Failed to create vector index '{idx_name}': {e}. Falling back to standard property storage.")
            return {
                "status": "error",
                "error": str(e),
                "index_name": idx_name,
                "dimensions": dim,
                "similarity_function": sim_fn,
            }

    def batch_set_passage_embeddings(
        self,
        items: List[Dict[str, Any]],
        batch_size: int = 100,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Batch-updates Passage nodes with dense vector embeddings using Cypher UNWIND.
        Attaches embedding, embedding_model, embedding_dim, and embedded_at timestamp.
        Idempotent on passage ID.
        """
        if not items:
            return {"total_items": 0, "updated": 0}

        query = """
        UNWIND $batch AS item
        MATCH (p:KGNode:Passage {id: item.passage_id})
        SET p.embedding = item.embedding,
            p.embedding_model = item.embedding_model,
            p.embedding_dim = item.embedding_dim,
            p.embedded_at = timestamp()
        RETURN count(p) AS updated_count
        """
        total_updated = 0
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            serialized_chunk = []
            for it in chunk:
                raw_emb = it.get("embedding", [])
                if hasattr(raw_emb, "tolist"):
                    raw_emb = raw_emb.tolist()
                elif isinstance(raw_emb, (list, tuple)):
                    raw_emb = [float(v) for v in raw_emb]
                else:
                    raw_emb = []

                serialized_chunk.append({
                    "passage_id": str(it["passage_id"]),
                    "embedding": raw_emb,
                    "embedding_model": str(it.get("embedding_model", "")),
                    "embedding_dim": int(it.get("embedding_dim", len(raw_emb))),
                })

            res = self.service.execute_write(query, {"batch": serialized_chunk}, database=database)
            if res and len(res) > 0:
                total_updated += int(res[0].get("updated_count", len(serialized_chunk)))
            else:
                total_updated += len(serialized_chunk)

        logger.info(f"Batch set embeddings on {total_updated} Passage nodes in Neo4j")
        return {"total_items": len(items), "updated": total_updated}

    def vector_similarity_search(
        self,
        embedding: Union[List[float], np.ndarray],
        top_k: int = 5,
        index_name: Optional[str] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes vector similarity search against the Neo4j vector index.
        Accepts a dense vector embedding and configurable top-K.
        Returns a list of structured passage records with:
        - passage_id: canonical ID
        - similarity_score: float cosine score
        - text: original / normalized Tamil text
        - source_metadata: dictionary with work_name, section_name, chapter_name, sutra_number, tinai, source_reference, translation
        """
        idx_name = index_name or Neo4jConfig.VECTOR_INDEX_NAME
        raw_vec = embedding.tolist() if hasattr(embedding, "tolist") else [float(v) for v in embedding]

        query = f"""
        CALL db.index.vector.queryNodes('{idx_name}', $top_k, $vector)
        YIELD node, score
        RETURN node.id AS id,
               node.label AS label,
               node.sutra_number AS sutra_number,
               node.text AS text,
               node.original_text AS original_text,
               node.translation AS translation,
               node.source_reference AS source_reference,
               node.tinai AS tinai,
               node.work_name AS work_name,
               node.section_name AS section_name,
               node.chapter_name AS chapter_name,
               node.metadata_json AS metadata_json,
               score
        ORDER BY score DESC
        LIMIT $top_k
        """
        try:
            records = self.service.execute_read(query, {"top_k": int(top_k), "vector": raw_vec}, database=database)
            results = []
            for r in records:
                meta = {}
                if r.get("metadata_json"):
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        meta = {}

                source_meta = {
                    "sutra_number": r.get("sutra_number"),
                    "work_name": r.get("work_name") or meta.get("work_name", "Tolkāppiyam"),
                    "section_name": r.get("section_name") or meta.get("section_name", "Poruḷatikāram"),
                    "chapter_name": r.get("chapter_name") or meta.get("chapter_name", meta.get("iyal", "")),
                    "source_reference": r.get("source_reference") or meta.get("source_reference", f"Sūtra {r.get('sutra_number')}"),
                    "tinai": r.get("tinai") or meta.get("tinai", "General"),
                    "translation": r.get("translation") or meta.get("translation", ""),
                    "metadata": meta,
                }

                score_val = float(r.get("score", 0.0))
                passage_id = str(r.get("id") or "")
                text_val = str(r.get("text") or r.get("original_text") or meta.get("text", ""))

                results.append({
                    "passage_id": passage_id,
                    "id": passage_id,
                    "similarity_score": round(score_val, 4),
                    "score": round(score_val, 4),
                    "text": text_val,
                    "source_metadata": source_meta,
                })
            return results
        except Exception as e:
            logger.warning(f"Vector similarity search on index '{idx_name}' failed: {e}")
            return []

    def query_passages_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 5,
        index_name: Optional[str] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible alias for vector_similarity_search."""
        return self.vector_similarity_search(
            embedding=query_vector,
            top_k=top_k,
            index_name=index_name,
            database=database,
        )


# Singleton instance for repository injection across services
neo4j_repository = Neo4jRepository()

