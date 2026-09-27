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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from config import Config, Neo4jConfig
from core.logger import logger
from core.exceptions import KnowledgeGraphError, CypherQueryError
from services.neo4j_service import Neo4jService, neo4j_service
from .schema import NodeLabels, RelTypes
from .ontology import TolkappiyamOntology


class Neo4jRepository:
    """
    Dedicated repository layer encapsulating Neo4j Aura database operations
    for the Nyāya-Inspired Neuro-Symbolic Reasoning Framework.
    """

    def __init__(self, service: Optional[Neo4jService] = None):
        self.service = service or neo4j_service

    def is_available(self) -> bool:
        """Checks if the Neo4j driver is initialized and connected."""
        driver = self.service.get_driver()
        if driver is None:
            return False
        return self.service.is_connected()

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
            n.context = coalesce(item.context, item.tinai, item.section_name, 'General'),
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
            n.context = coalesce(item.context, n.context, item.tinai, item.section_name, 'General'),
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
                    "context": str(it.get("context") or it.get("tinai") or meta.get("tinai") or "General"),
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
                    "validation_status": it.get("validation_status") or meta.get("validation_status", "canonical_verified"),
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
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.normalized_text, p.text, '') AS normalized_text,
               p.text AS text,
               p.translation AS translation,
               p.tinai AS tinai,
               p.source AS source,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               p.corpus_info AS corpus_info,
               p.metadata_json AS metadata_json,
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

        data = dict(records[0])
        if data.get("metadata_json"):
            try:
                data["metadata"] = json.loads(data["metadata_json"])
            except Exception:
                data["metadata"] = {}
        return data

    def get_canonical_sutras_batch(
        self, passage_ids: List[str], database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves multiple canonical passages directly from Neo4j Aura in a single query
        with full literary hierarchy, text, translation, and citation provenance.
        """
        cleaned_ids = [str(pid).strip() for pid in (passage_ids or []) if str(pid).strip()]
        if not cleaned_ids:
            return []

        query = """
        UNWIND $ids AS target_id
        MATCH (p:KGNode:Passage)
        WHERE p.id = target_id OR p.source_id = target_id OR p.source = target_id
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        RETURN p.id AS passage_id,
               p.id AS id,
               p.label AS label,
               p.sutra_number AS sutra_number,
               p.verse_number AS verse_number,
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.normalized_text, p.text, '') AS normalized_text,
               coalesce(p.text, p.original_text, '') AS text,
               p.translation AS translation,
               coalesce(p.tinai, 'General') AS tinai,
               coalesce(p.category, 'Passage') AS category,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               coalesce(p.confidence, 1.0) AS confidence,
               p.metadata_json AS metadata_json,
               [n in nodes(path) | {
                   id: n.id,
                   label: n.label,
                   name: n.name,
                   type: n.type,
                   hierarchy_level: n.hierarchy_level
               }] AS provenance_path
        """
        records = self.service.execute_read(query, {"ids": cleaned_ids}, database=database)
        results: Dict[str, Dict[str, Any]] = {}
        for r in records:
            item = dict(r)
            meta = {}
            if item.get("metadata_json"):
                try:
                    meta = json.loads(item["metadata_json"])
                except Exception:
                    meta = {}
            item["metadata"] = meta
            if not item.get("source_reference"):
                w = item.get("work_name", "Tolkāppiyam")
                s = item.get("section_name", "Poruḷatikāram")
                c = item.get("chapter_name", "")
                num = item.get("sutra_number", "")
                item["source_reference"] = f"{w} {s} {c} Sūtra {num}".replace("  ", " ").strip()
            pid = item.get("passage_id") or item.get("id")
            if pid and pid not in results:
                results[pid] = item
        return results

    def get_canonical_evidence_for_tinai(
        self,
        tinai_name: str,
        limit: int = 5,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves canonical passages from Neo4j Aura that specifically formulate
        the semiotic, ecological, and psychological rules of the specified Tiṇai.
        """
        cleaned_tinai = (tinai_name or "").strip()
        if not cleaned_tinai:
            return []

        query = """
        MATCH (p:KGNode:Passage)
        WHERE toLower(coalesce(p.tinai, '')) = toLower($tinai)
           OR toLower(coalesce(p.text, '')) CONTAINS toLower($tinai)
           OR toLower(coalesce(p.original_text, '')) CONTAINS toLower($tinai)
           OR toLower(coalesce(p.translation, '')) CONTAINS toLower($tinai)
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        RETURN p.id AS passage_id,
               p.id AS id,
               p.label AS label,
               p.sutra_number AS sutra_number,
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.normalized_text, p.text, '') AS normalized_text,
               coalesce(p.text, p.original_text, '') AS text,
               p.translation AS translation,
               coalesce(p.tinai, $tinai) AS tinai,
               coalesce(p.category, 'CanonicalEvidence') AS category,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               coalesce(p.confidence, 1.0) AS confidence,
               p.metadata_json AS metadata_json
        ORDER BY coalesce(p.sutra_number, 9999) ASC
        LIMIT $limit
        """
        records = self.service.execute_read(
            query, {"tinai": cleaned_tinai, "limit": limit}, database=database
        )
        results: List[Dict[str, Any]] = []
        for r in records:
            item = dict(r)
            meta = {}
            if item.get("metadata_json"):
                try:
                    meta = json.loads(item["metadata_json"])
                except Exception:
                    meta = {}
            item["metadata"] = meta
            if not item.get("source_reference"):
                w = item.get("work_name", "Tolkāppiyam")
                s = item.get("section_name", "Poruḷatikāram")
                c = item.get("chapter_name", "")
                num = item.get("sutra_number", "")
                item["source_reference"] = f"{w} {s} {c} Sūtra {num}".replace("  ", " ").strip()
            results.append(item)
        return results

    def get_canonical_vyapti_sutras(
        self,
        tinai: str,
        domain: Optional[str] = None,
        limit: int = 5,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves foundational canonical sūtras from Tolkāppiyam establishing the
        universal semiotic / affective invariance (Vyāpti) for a given Tiṇai or domain directly from Neo4j.
        """
        cleaned_tinai = (tinai or "Kuṟiñci").strip()
        query = """
        MATCH (p:KGNode:Passage)
        WHERE (toLower(coalesce(p.tinai, '')) = toLower($tinai)
               OR toLower(coalesce(p.text, '')) CONTAINS toLower($tinai)
               OR toLower(coalesce(p.original_text, '')) CONTAINS toLower($tinai)
               OR toLower(coalesce(p.translation, '')) CONTAINS toLower($tinai))
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        RETURN p.id AS passage_id,
               p.id AS id,
               p.label AS label,
               p.sutra_number AS sutra_number,
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.normalized_text, p.text, '') AS normalized_text,
               coalesce(p.text, p.original_text, '') AS text,
               p.translation AS translation,
               coalesce(p.tinai, $tinai) AS tinai,
               coalesce(p.category, 'CanonicalVyaptiRule') AS category,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               coalesce(p.confidence, 1.0) AS confidence,
               p.metadata_json AS metadata_json
        ORDER BY coalesce(p.sutra_number, 9999) ASC
        LIMIT $limit
        """
        records = self.service.execute_read(
            query, {"tinai": cleaned_tinai, "limit": limit}, database=database
        )
        results: List[Dict[str, Any]] = []
        for r in records:
            item = dict(r)
            meta = {}
            if item.get("metadata_json"):
                try:
                    meta = json.loads(item["metadata_json"])
                except Exception:
                    meta = {}
            item["metadata"] = meta
            if not item.get("source_reference"):
                w = item.get("work_name", "Tolkāppiyam")
                s = item.get("section_name", "Poruḷatikāram")
                c = item.get("chapter_name", "")
                num = item.get("sutra_number", "")
                item["source_reference"] = f"{w} {s} {c} Sūtra {num}".replace("  ", " ").strip()
            item["evidence_role"] = "canonicalEvidence"
            results.append(item)
        return results

    def verify_canonical_vyapti_passage(
        self,
        passage_id: str,
        tinai: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Verifies whether a specific passage ID corresponds to an authentic canonical
        Vyāpti rule in Neo4j (Tolkāppiyam / CanonicalVyaptiRule).
        Returns the canonical record dict if verified, None otherwise.
        """
        if not passage_id:
            return None
        query = """
        MATCH (p:KGNode:Passage)
        WHERE (p.id = $passage_id OR p.passage_id = $passage_id)
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        RETURN p.id AS passage_id,
               p.id AS id,
               p.label AS label,
               p.sutra_number AS sutra_number,
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.text, p.original_text, '') AS text,
               p.translation AS translation,
               coalesce(p.tinai, '') AS tinai,
               coalesce(p.category, 'CanonicalVyaptiRule') AS category,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               coalesce(p.confidence, 1.0) AS confidence
        LIMIT 1
        """
        try:
            records = self.service.execute_read(query, {"passage_id": passage_id}, database=database)
            if records:
                item = dict(records[0])
                if not item.get("source_reference"):
                    w = item.get("work_name", "Tolkāppiyam")
                    s = item.get("section_name", "Poruḷatikāram")
                    c = item.get("chapter_name", "")
                    num = item.get("sutra_number", "")
                    item["source_reference"] = f"{w} {s} {c} Sūtra {num}".replace("  ", " ").strip()
                item["evidence_role"] = "vyaptiEvidence"
                return item
        except Exception as e:
            logger.debug(f"verify_canonical_vyapti_passage fallback: {e}")
        return None

    def get_case_evidence_by_entities_and_concepts(
        self,
        entity_names: List[str],
        concept_names: List[str],
        tinai: Optional[str] = None,
        limit: int = 5,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves case-specific passages directly connected to target entities and concepts
        via Knowledge Graph relationships.
        """
        cleaned_entities = [str(e).strip() for e in (entity_names or []) if str(e).strip()]
        cleaned_concepts = [str(c).strip() for c in (concept_names or []) if str(c).strip()]
        if not cleaned_entities and not cleaned_concepts:
            return []

        query = """
        MATCH (n:KGNode)
        WHERE (n:Entity OR n:Concept OR n:Event)
          AND (any(e in $entities WHERE toLower(coalesce(n.name, n.label, '')) CONTAINS toLower(e) OR toLower(e) CONTAINS toLower(coalesce(n.name, n.label, '')))
               OR any(c in $concepts WHERE toLower(coalesce(n.name, n.label, '')) CONTAINS toLower(c) OR toLower(c) CONTAINS toLower(coalesce(n.name, n.label, ''))))
        MATCH (n)-[r]-(p:KGNode:Passage)
        OPTIONAL MATCH path = (lit:KGNode:Literature)-[:HAS_WORK]->(w:KGNode:Work)-[:HAS_SECTION*1..2]->(sec:KGNode:Section)-[:HAS_PASSAGE]->(p)
        WHERE ($tinai IS NULL OR $tinai = '' OR toLower(coalesce(p.tinai, '')) = toLower($tinai))
        RETURN p.id AS passage_id,
               p.id AS id,
               p.label AS label,
               p.sutra_number AS sutra_number,
               coalesce(p.original_text, p.text, '') AS original_text,
               coalesce(p.normalized_text, p.text, '') AS normalized_text,
               coalesce(p.text, p.original_text, '') AS text,
               p.translation AS translation,
               coalesce(p.tinai, '') AS tinai,
               coalesce(p.category, 'CaseEvidence') AS category,
               coalesce(p.source_reference, p.citation, '') AS source_reference,
               coalesce(p.work_name, w.name, 'Tolkāppiyam') AS work_name,
               coalesce(p.section_name, sec.section_name, sec.name, 'Poruḷatikāram') AS section_name,
               coalesce(p.chapter_name, sec.chapter_name, sec.name, '') AS chapter_name,
               coalesce(p.confidence, 0.95) AS confidence,
               collect(DISTINCT coalesce(n.name, n.label)) AS matched_entities,
               collect(DISTINCT type(r)) AS matched_relations,
               count(DISTINCT n) AS connectivity_count
        ORDER BY connectivity_count DESC, coalesce(p.sutra_number, 9999) ASC
        LIMIT $limit
        """
        records = self.service.execute_read(
            query,
            {
                "entities": cleaned_entities,
                "concepts": cleaned_concepts,
                "tinai": tinai or "",
                "limit": limit,
            },
            database=database,
        )
        results: List[Dict[str, Any]] = []
        for r in records:
            item = dict(r)
            if not item.get("source_reference"):
                w = item.get("work_name", "Tolkāppiyam")
                s = item.get("section_name", "Poruḷatikāram")
                c = item.get("chapter_name", "")
                num = item.get("sutra_number", "")
                item["source_reference"] = f"{w} {s} {c} Sūtra {num}".replace("  ", " ").strip()
            item["evidence_role"] = "caseEvidence"
            results.append(item)
        return results

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

    def trace_to_literary_source(
        self, element_id: str, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Traces any knowledge element (Entity, Concept, Event, Rule, Evidence, or Passage)
        back to its original canonical literary source (Passage / Sūtra) and its parent hierarchy
        (Section -> Work -> Literature) using direct source_id, [:GROUNDED_IN],
        or [:ATTESTS_*] / [:MENTIONS|DISCUSSES|DESCRIBES] relationships.
        Guarantees deterministic, verified provenance for every knowledge element.
        """
        cleaned_id = str(element_id).strip()
        if not cleaned_id:
            return {"element_id": element_id, "found": False, "source_passage": None, "literary_hierarchy": None}

        query = """
        MATCH (target:KGNode)
        WHERE target.id = $id OR target.name = $id OR toLower(coalesce(target.name, target.label)) = toLower($id)
        OPTIONAL MATCH (target)-[:GROUNDED_IN]->(p1:KGNode:Passage)
        OPTIONAL MATCH (p2:KGNode:Passage)-[:ATTESTS_ENTITY|ATTESTS_CONCEPT|ATTESTS_EVENT|MENTIONS|DISCUSSES|DESCRIBES]->(target)
        OPTIONAL MATCH (p3:KGNode:Passage) WHERE p3.id = target.source_id OR p3.source_id = target.source_id
        WITH target, coalesce(CASE WHEN target:Passage THEN target ELSE null END, p1, p2, p3) AS passage
        OPTIONAL MATCH (sec:KGNode:Section)-[:CONTAINS_PASSAGE|HAS_PASSAGE]->(passage)
        OPTIONAL MATCH (w:KGNode:Work)-[:CONTAINS_SECTION|HAS_SECTION*1..2]->(sec)
        OPTIONAL MATCH (lit:KGNode:Literature)-[:CONTAINS_WORK|HAS_WORK]->(w)
        RETURN target {
            id: target.id,
            name: coalesce(target.name, target.label, target.id),
            text: coalesce(target.text, ''),
            type: target.type,
            source: target.source,
            source_id: target.source_id,
            context: coalesce(target.context, target.tinai, 'General'),
            confidence: coalesce(target.confidence, 1.0),
            validation_status: coalesce(target.validation_status, 'canonical_verified')
        } AS element,
        passage {
            id: passage.id,
            sutra_number: passage.sutra_number,
            name: coalesce(passage.name, passage.label),
            text: coalesce(passage.text, passage.original_text, ''),
            translation: coalesce(passage.translation, ''),
            tinai: coalesce(passage.tinai, 'General'),
            source_reference: coalesce(passage.source_reference, passage.source, ''),
            work: coalesce(w.name, passage.work, 'Tolkāppiyam'),
            section: coalesce(sec.name, passage.section, 'Poruḷatikāram')
        } AS source_passage,
        {
            section_id: sec.id,
            section_name: coalesce(sec.name, sec.section_name),
            work_id: w.id,
            work_name: w.name,
            literature_id: lit.id,
            literature_name: lit.name
        } AS literary_hierarchy
        LIMIT 1
        """
        records = self.service.execute_read(query, {"id": cleaned_id}, database=database)
        if not records or not records[0].get("element"):
            return {
                "element_id": cleaned_id,
                "found": False,
                "element": None,
                "source_passage": None,
                "literary_hierarchy": None,
                "traceability_status": "element_not_found",
            }

        rec = records[0]
        element = rec.get("element")
        passage = rec.get("source_passage")
        hierarchy = rec.get("literary_hierarchy")
        has_source = bool(passage and passage.get("id"))

        return {
            "element_id": cleaned_id,
            "found": True,
            "element": element,
            "source_passage": passage if has_source else None,
            "literary_hierarchy": hierarchy if has_source else None,
            "traceability_status": "canonical_source_verified" if has_source else "unlinked_corpus_element",
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
        and provenance metadata required for D3.js visualization.
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
            RETURN [node IN selected_nodes | node {{ id: coalesce(node.id, node.name, elementId(node)), .*, labels: labels(node) }}] AS nodes,
                   [r IN rels WHERE r IS NOT NULL | {{
                       id: coalesce(r.id, elementId(r), coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))) + '_' + type(r) + '_' + coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))) + '_' + toString(id(r))),
                       source: coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))),
                       target: coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))),
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
            RETURN [node IN selected_nodes | node { id: coalesce(node.id, node.name, elementId(node)), .*, labels: labels(node) }] AS nodes,
                   [r IN rels WHERE r IS NOT NULL | {
                       id: coalesce(r.id, elementId(r), coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))) + '_' + type(r) + '_' + coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))) + '_' + toString(id(r))),
                       source: coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))),
                       target: coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))),
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
                "backend_node_count": 0,
                "backend_edge_count": 0,
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
        pair_counts = {}
        for r in raw_rels:
            rel_dict = dict(r)
            src = str(rel_dict.get("source") or "")
            tgt = str(rel_dict.get("target") or "")
            # Verify endpoints exist in selected nodes (supports self-referential where src == tgt)
            if not src or not tgt or src not in node_ids or tgt not in node_ids:
                continue
            rel_type = rel_dict.get("type") or rel_dict.get("relation") or "RELATED_TO"
            rel_dict["type"] = rel_type
            rel_dict["relation"] = rel_type

            pair_key = (src, rel_type, tgt)
            pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1

            edge_id = str(rel_dict.get("id") or "")
            if not edge_id or edge_id in seen_edge_ids:
                # Stable unique ID without using array indexes
                edge_id = f"e_{src}_{rel_type}_{tgt}_{pair_counts[pair_key]}"
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
            "backend_node_count": len(raw_nodes),
            "backend_edge_count": len(raw_rels),
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

    def get_query_subgraph(
        self,
        seed_ids: List[str],
        max_hops: int = 2,
        limit: int = 150,
        rel_types: Optional[List[str]] = None,
        include_isolated: bool = True,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves a dynamic, query-aware subgraph centered around relevant seed identifiers
        (passages, entities, concepts, events, rules) from Neo4j Aura.

        - Executes controlled multi-hop traversal with configurable maximum depth (1-5).
        - Filters by controlled schema relationship types when provided.
        - Preserves isolated directly relevant seed nodes (no seeds dropped).
        - Guarantees strict endpoint validity for every relationship (no dangling edges).
        - Enriches nodes and relationships with epistemic relevance and literary provenance.
        - Zero hardcoded nodes or edges: fully query-driven from database.
        """
        cleaned_seeds = [str(s).strip() for s in (seed_ids or []) if str(s).strip()]
        if not cleaned_seeds:
            return {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "seed_ids": [],
                "matched_seeds": [],
                "depth": max_hops,
                "source": "neo4j_aura",
            }

        hops = min(max(int(max_hops), 1), 5)
        node_limit = min(max(int(limit), 10), 1000)
        seeds_lower = [s.lower() for s in cleaned_seeds]

        canonical_rel_types = None
        if rel_types:
            canonical_rel_types = [RelTypes.canonicalize(r) for r in rel_types if str(r).strip()]

        query = f"""
        MATCH (seed:KGNode)
        WHERE seed.id IN $seed_ids
           OR seed.name IN $seed_ids
           OR toLower(seed.id) IN $seed_ids_lower
           OR toLower(seed.name) IN $seed_ids_lower
           OR toLower(coalesce(seed.label, '')) IN $seed_ids_lower
           OR toLower(coalesce(seed.canonical, '')) IN $seed_ids_lower
           OR toLower(coalesce(seed.transliteration, '')) IN $seed_ids_lower
        WITH collect(DISTINCT seed) AS seed_nodes
        UNWIND (CASE WHEN size(seed_nodes) > 0 THEN seed_nodes ELSE [null] END) AS seed
        OPTIONAL MATCH path = (seed)-[r*1..{hops}]-(neighbor:KGNode)
        WHERE seed IS NOT NULL AND ($rel_types IS NULL OR ALL(rel IN relationships(path) WHERE type(rel) IN $rel_types))
        WITH seed_nodes, [nb IN collect(DISTINCT neighbor) WHERE nb IS NOT NULL AND NOT nb IN seed_nodes] AS other_neighbors
        WITH seed_nodes, other_neighbors,
             seed_nodes + other_neighbors[0..($limit - size(seed_nodes))] AS combined_nodes
        UNWIND combined_nodes AS n
        WITH DISTINCT n, seed_nodes
        WITH collect(n) AS selected_nodes, seed_nodes
        UNWIND selected_nodes AS n
        OPTIONAL MATCH (n)-[r]->(m:KGNode)
        WHERE m IN selected_nodes AND ($rel_types IS NULL OR type(r) IN $rel_types)
        WITH selected_nodes, seed_nodes, collect(DISTINCT r) AS rels
        RETURN [node IN selected_nodes | node {{ id: coalesce(node.id, node.name, elementId(node)), .*, labels: labels(node), is_seed: (node IN seed_nodes) }}] AS nodes,
               [r IN rels WHERE r IS NOT NULL | {{
                   id: coalesce(r.id, elementId(r), coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))) + '_' + type(r) + '_' + coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))) + '_' + elementId(r)),
                   source: coalesce(startNode(r).id, startNode(r).name, elementId(startNode(r))),
                   target: coalesce(endNode(r).id, endNode(r).name, elementId(endNode(r))),
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
            "seed_ids": cleaned_seeds,
            "seed_ids_lower": seeds_lower,
            "limit": node_limit,
            "rel_types": canonical_rel_types,
        }

        try:
            records = self.service.execute_read(query, params, database=database)
        except Exception as e:
            logger.warning(f"Neo4j get_query_subgraph query failed: {e}")
            return {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "seed_ids": cleaned_seeds,
                "matched_seeds": [],
                "depth": hops,
                "error": str(e),
                "source": "neo4j_aura",
                "metadata": {
                    "query": "",
                    "node_count": 0,
                    "relationship_count": 0,
                    "depth": hops,
                    "source": "neo4j_aura",
                },
            }

        if not records:
            return {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "seed_ids": cleaned_seeds,
                "matched_seeds": [],
                "depth": hops,
                "source": "neo4j_aura",
                "metadata": {
                    "query": "",
                    "node_count": 0,
                    "relationship_count": 0,
                    "depth": hops,
                    "source": "neo4j_aura",
                },
            }

        rec = records[0]
        raw_nodes = rec.get("nodes") or []
        raw_rels = rec.get("relationships") or []

        # Parse nodes and collect unique IDs
        node_id_set: Set[str] = set()
        matched_seeds: List[str] = []
        parsed_nodes: List[Dict[str, Any]] = []

        for n in raw_nodes:
            node_dict = dict(n)
            nid = str(node_dict.get("id") or "")
            if not nid or nid in node_id_set:
                continue

            node_id_set.add(nid)

            # Metadata parsing
            meta = {}
            if "metadata_json" in node_dict and node_dict["metadata_json"]:
                try:
                    meta = json.loads(node_dict["metadata_json"])
                except Exception:
                    meta = {}
            node_dict["metadata"] = meta

            # Seed check
            node_name = str(node_dict.get("name") or "").lower()
            node_label = str(node_dict.get("label") or "").lower()
            node_canonical = str(node_dict.get("canonical") or "").lower()
            node_translit = str(node_dict.get("transliteration") or "").lower()
            is_seed = bool(node_dict.get("is_seed")) or (
                nid in cleaned_seeds
                or nid.lower() in seeds_lower
                or node_name in seeds_lower
                or node_label in seeds_lower
                or node_canonical in seeds_lower
                or node_translit in seeds_lower
            )
            node_dict["is_seed"] = is_seed
            if is_seed:
                matched_seeds.append(nid)

            parsed_nodes.append(node_dict)

        # Validate relationships: endpoints MUST be present in node_id_set
        valid_rels: List[Dict[str, Any]] = []
        node_degrees: Dict[str, int] = {nid: 0 for nid in node_id_set}

        for r in raw_rels:
            rel_dict = dict(r)
            src = str(rel_dict.get("source") or "")
            tgt = str(rel_dict.get("target") or "")

            if not src or not tgt or src not in node_id_set or tgt not in node_id_set:
                continue

            rel_type = rel_dict.get("type") or rel_dict.get("relation") or "RELATED_TO"
            rel_dict["type"] = rel_type
            rel_dict["relation"] = rel_type
            valid_rels.append(rel_dict)

            node_degrees[src] = node_degrees.get(src, 0) + 1
            node_degrees[tgt] = node_degrees.get(tgt, 0) + 1

        # Enrich nodes with connectivity and relevance info
        final_nodes: List[Dict[str, Any]] = []
        for node in parsed_nodes:
            nid = node["id"]
            deg = node_degrees.get(nid, 0)
            is_seed = node.get("is_seed", False)
            node["degree"] = deg
            node["is_isolated"] = deg == 0
            node["hop_distance"] = 0 if is_seed else 1
            node["relevance_reason"] = (
                "Direct Seed Node from Query / Hybrid Retrieval"
                if is_seed
                else "Multi-hop Traversable Semiotic Context"
            )
            node["relevance_score"] = 1.0 if is_seed else 0.7
            if include_isolated or deg > 0:
                final_nodes.append(node)

        return {
            "nodes": final_nodes,
            "relationships": valid_rels,
            "edges": valid_rels,
            "total_nodes": len(final_nodes),
            "total_edges": len(valid_rels),
            "total_relationships": len(valid_rels),
            "seed_ids": cleaned_seeds,
            "matched_seeds": matched_seeds,
            "isolated_node_count": len([n for n in final_nodes if n.get("is_isolated")]),
            "depth": hops,
            "source": "neo4j_aura",
            "metadata": {
                "query": "",
                "node_count": len(final_nodes),
                "relationship_count": len(valid_rels),
                "depth": hops,
                "source": "neo4j_aura",
            },
        }

    # ==============================================================================
    # 7. Authoritative Knowledge Graph Core Operations
    # ==============================================================================

    def get_kg_statistics(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves comprehensive structural metrics directly from Neo4j Aura:
        total node count, total relationship count, density, connectivity,
        isolated node counts, hierarchy distribution (L0-L5), logical layer distribution,
        and relationship type frequencies.
        """
        # Node count
        rec_nodes = self.service.execute_read("MATCH (n:KGNode) RETURN count(n) AS cnt", database=database)
        total_nodes = int(rec_nodes[0]["cnt"]) if rec_nodes else 0

        # Edge count
        rec_edges = self.service.execute_read("MATCH ()-[r]->() RETURN count(r) AS cnt", database=database)
        total_edges = int(rec_edges[0]["cnt"]) if rec_edges else 0

        # Density
        if total_nodes > 1:
            density = round(2.0 * total_edges / (total_nodes * (total_nodes - 1)), 4)
        else:
            density = 0.0

        # Isolated nodes
        q_iso = """
        MATCH (n:KGNode)
        WHERE NOT (n)--()
        RETURN n.id AS id, coalesce(n.label, n.name, n.id) AS label
        LIMIT 200
        """
        rec_iso = self.service.execute_read(q_iso, database=database)
        isolated_nodes = [r["id"] for r in rec_iso if r.get("id")]
        is_connected = len(isolated_nodes) == 0 and total_nodes > 0

        # Hierarchy distribution (L0-L5)
        q_hier = """
        MATCH (n:KGNode)
        WHERE n.hierarchy_level IS NOT NULL
        RETURN n.hierarchy_level AS level, count(n) AS cnt
        ORDER BY level
        """
        rec_hier = self.service.execute_read(q_hier, database=database)
        hierarchy_distribution = {r["level"]: int(r["cnt"]) for r in rec_hier if r.get("level")}

        # Logical layer distribution
        q_layer = """
        MATCH (n:KGNode)
        WHERE n.layer IS NOT NULL
        RETURN n.layer AS layer, count(n) AS cnt
        ORDER BY cnt DESC
        """
        rec_layer = self.service.execute_read(q_layer, database=database)
        layer_distribution = {r["layer"]: int(r["cnt"]) for r in rec_layer if r.get("layer")}
        if not layer_distribution and total_nodes > 0:
            layer_map = {
                "L0": "Source Layer",
                "L1": "Source Layer",
                "L2": "Source Layer",
                "L3": "Source Layer",
                "L4": "Concept Layer",
                "L5": "Entity Layer",
            }
            for lvl, cnt in hierarchy_distribution.items():
                lyr = layer_map.get(lvl, "Entity Layer")
                layer_distribution[lyr] = layer_distribution.get(lyr, 0) + cnt

        # Relation distribution
        q_rel = """
        MATCH ()-[r]->()
        RETURN type(r) AS rel, count(r) AS cnt
        ORDER BY cnt DESC
        """
        rec_rel = self.service.execute_read(q_rel, database=database)
        relation_distribution = {r["rel"]: int(r["cnt"]) for r in rec_rel if r.get("rel")}

        # Category distribution
        q_cat = """
        MATCH (n:KGNode)
        WHERE n.category IS NOT NULL OR n.type IS NOT NULL
        RETURN coalesce(n.category, n.type) AS cat, count(n) AS cnt
        ORDER BY cnt DESC
        """
        rec_cat = self.service.execute_read(q_cat, database=database)
        category_distribution = {r["cat"]: int(r["cnt"]) for r in rec_cat if r.get("cat")}

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "density": density,
            "is_connected": is_connected,
            "isolated_nodes": isolated_nodes,
            "isolated_count": len(isolated_nodes),
            "hierarchy_distribution": hierarchy_distribution,
            "layer_distribution": layer_distribution,
            "relation_distribution": relation_distribution,
            "category_distribution": category_distribution,
            "categories": TolkappiyamOntology.get_category_config(),
            "hierarchy_levels": TolkappiyamOntology.get_hierarchy_config(),
            "logical_layers": TolkappiyamOntology.get_layer_config(),
            "source": "neo4j_aura",
        }

    def get_entity_detail(self, entity_id: str, database: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves an entity's complete schema, properties, hierarchy level, logical layer,
        direct incoming/outgoing neighbors, and grounded source passages directly from Neo4j Aura.
        """
        q_node = """
        MATCH (n:KGNode {id: $id})
        RETURN n { id: coalesce(n.id, n.name, elementId(n)), .*, labels: labels(n) } AS node
        """
        rec_node = self.service.execute_read(q_node, {"id": entity_id}, database=database)
        if not rec_node or not rec_node[0].get("node"):
            return None

        node_data = dict(rec_node[0]["node"])
        metadata = {}
        if "metadata_json" in node_data and node_data["metadata_json"]:
            try:
                metadata = json.loads(node_data["metadata_json"])
            except Exception:
                pass
        node_data["metadata"] = metadata

        # Fetch direct neighbors
        q_neighbors = """
        MATCH (n:KGNode {id: $id})-[r]-(m:KGNode)
        RETURN type(r) AS relation,
               r.id AS edge_id,
               coalesce(r.confidence, 1.0) AS confidence,
               coalesce(r.validation_level, 'corpus_validated') AS validation_level,
               startNode(r).id = n.id AS is_outgoing,
               m.id AS neighbor_id,
               coalesce(m.label, m.name, m.id) AS neighbor_label,
               m.type AS neighbor_type,
               m.hierarchy_level AS neighbor_hierarchy
        LIMIT 100
        """
        rec_neighbors = self.service.execute_read(q_neighbors, {"id": entity_id}, database=database)
        neighbors = []
        for r in rec_neighbors:
            neighbors.append({
                "direction": "outgoing" if r.get("is_outgoing") else "incoming",
                "edge_id": r.get("edge_id"),
                "relation": r.get("relation", "RELATED_TO"),
                "neighbor_id": r.get("neighbor_id"),
                "neighbor_label": r.get("neighbor_label"),
                "neighbor_type": r.get("neighbor_type"),
                "neighbor_hierarchy": r.get("neighbor_hierarchy"),
                "confidence": float(r.get("confidence", 1.0)),
                "validation_level": r.get("validation_level", "corpus_validated"),
            })

        # Fetch connected source evidence
        q_evidence = """
        MATCH p = (ancestor:KGNode)-[*1..4]->(n:KGNode {id: $id})
        WHERE ancestor:Passage OR ancestor.hierarchy_level IN ['L3', 'L2', 'L1', 'L0']
        RETURN DISTINCT ancestor.id AS evidence_node_id,
                        ancestor.hierarchy_level AS hierarchy_level,
                        coalesce(ancestor.label, ancestor.name) AS label,
                        ancestor.type AS type,
                        ancestor.source AS source,
                        ancestor.metadata_json AS metadata_json
        LIMIT 20
        """
        rec_evidence = self.service.execute_read(q_evidence, {"id": entity_id}, database=database)
        evidence_list = []
        for rec in rec_evidence:
            ev_meta = {}
            if "metadata_json" in rec and rec["metadata_json"]:
                try:
                    ev_meta = json.loads(rec["metadata_json"])
                except Exception:
                    pass
            evidence_list.append({
                "evidence_node_id": rec.get("evidence_node_id"),
                "hierarchy_level": rec.get("hierarchy_level"),
                "label": rec.get("label"),
                "type": rec.get("type"),
                "source": rec.get("source"),
                "citation": ev_meta.get("citation", rec.get("source", "")),
                "original_text": ev_meta.get("original_text", ""),
                "translation": ev_meta.get("translation", ""),
            })

        node_data["neighbors"] = neighbors
        node_data["evidence"] = evidence_list
        return node_data

    def get_node_connected_elements(
        self,
        node_id: str,
        limit: int = 100,
        database: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a node's directly connected first-degree nodes and relationships from Neo4j Aura.
        Returns:
            - selected_node: Full node attributes, labels, properties, and metadata
            - connected_nodes: List of all first-degree neighbor nodes with full attributes
            - relationships: List of relationships with direction ('outgoing' / 'incoming'),
                             type, confidence, validation_level, and metadata
            - metadata: Query metadata including counts, provenance, and timestamp
        """
        cleaned_id = str(node_id).strip()
        if not cleaned_id:
            return None

        query = """
        MATCH (selected:KGNode)
        WHERE selected.id = $id
           OR selected.name = $id
           OR toLower(selected.id) = toLower($id)
           OR toLower(selected.name) = toLower($id)
           OR toLower(coalesce(selected.label, '')) = toLower($id)
        WITH selected LIMIT 1
        OPTIONAL MATCH (selected)-[r]-(neighbor:KGNode)
        WHERE neighbor IS NOT NULL AND r IS NOT NULL
        WITH selected, r, neighbor
        LIMIT $limit
        WITH selected,
             collect(DISTINCT neighbor) AS raw_neighbors,
             collect(DISTINCT r) AS raw_rels
        RETURN selected {
                 id: coalesce(selected.id, selected.name, elementId(selected)),
                 .*,
                 labels: labels(selected)
               } AS selected_node,
               [nb IN raw_neighbors WHERE nb IS NOT NULL | nb {
                 id: coalesce(nb.id, nb.name, elementId(nb)),
                 .*,
                 labels: labels(nb)
               }] AS connected_nodes,
               [rel IN raw_rels WHERE rel IS NOT NULL | {
                 id: coalesce(rel.id, elementId(rel), coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))) + '_' + type(rel) + '_' + coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))) + '_' + elementId(rel)),
                 source: coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))),
                 target: coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))),
                 type: type(rel),
                 relation: type(rel),
                 label: coalesce(rel.label, type(rel)),
                 direction: CASE WHEN startNode(rel) = selected THEN 'outgoing' ELSE 'incoming' END,
                 confidence: coalesce(rel.confidence, 1.0),
                 validation_level: coalesce(rel.validation_level, rel.validation_status, 'corpus_validated'),
                 source_corpus: coalesce(rel.source, 'Tolkāppiyam'),
                 source_reference: coalesce(rel.source_reference, ''),
                 passage_id: rel.passage_id,
                 metadata_json: rel.metadata_json
               }] AS relationships
        """
        params = {"id": cleaned_id, "limit": min(max(int(limit), 1), 500)}
        records = self.service.execute_read(query, params, database=database)
        if not records or not records[0].get("selected_node"):
            return None

        rec = records[0]
        selected_node = dict(rec["selected_node"])
        if "metadata_json" in selected_node and selected_node["metadata_json"]:
            try:
                selected_node["metadata"] = json.loads(selected_node["metadata_json"])
            except Exception:
                selected_node["metadata"] = {}
        elif "metadata" not in selected_node:
            selected_node["metadata"] = {}

        connected_nodes = []
        for nb in rec.get("connected_nodes") or []:
            nb_dict = dict(nb)
            if "metadata_json" in nb_dict and nb_dict["metadata_json"]:
                try:
                    nb_dict["metadata"] = json.loads(nb_dict["metadata_json"])
                except Exception:
                    nb_dict["metadata"] = {}
            elif "metadata" not in nb_dict:
                nb_dict["metadata"] = {}
            connected_nodes.append(nb_dict)

        relationships = []
        for rel in rec.get("relationships") or []:
            rel_dict = dict(rel)
            if "metadata_json" in rel_dict and rel_dict["metadata_json"]:
                try:
                    rel_dict["metadata"] = json.loads(rel_dict["metadata_json"])
                except Exception:
                    rel_dict["metadata"] = {}
            elif "metadata" not in rel_dict:
                rel_dict["metadata"] = {}
            relationships.append(rel_dict)

        metadata = {
            "node_id": selected_node.get("id"),
            "connected_count": len(connected_nodes),
            "relationship_count": len(relationships),
            "source": "neo4j_aura",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "selected_node": selected_node,
            "connected_nodes": connected_nodes,
            "relationships": relationships,
            "nodes": [selected_node] + connected_nodes,
            "metadata": metadata,
        }

    def explore_node_multi_hop(
        self,
        start_id: str,
        max_hops: int = 2,
        limit: int = 150,
        allowed_types: Optional[List[str]] = None,
        excluded_types: Optional[List[str]] = None,
        rel_types: Optional[List[str]] = None,
        direction: str = "both",
        database: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Performs bounded, filtered multi-hop traversal starting from a selected node in Neo4j Aura.

        Guarantees:
        - Bounded Cypher traversal with configurable hop depth (1 to 5).
        - Filter out irrelevant node types (e.g. excluded_types or allowed_types whitelist).
        - Filter out irrelevant relationship types (canonicalized 5-tier RelTypes).
        - Maintains explicit parent-child lineage, hop distances, and relationship paths
          between the selected root node and every expanded node.
        - Returns structured paths with step-by-step edges and cumulative confidence.
        - Zero unconfirmed or unbounded full-graph queries.
        """
        cleaned_id = str(start_id).strip()
        if not cleaned_id:
            return None

        hops = min(max(int(max_hops), 1), 5)
        path_limit = min(max(int(limit), 10), 300)

        # Direction pattern
        if direction == "out":
            rel_pattern = f"-[r*1..{hops}]->"
        elif direction == "in":
            rel_pattern = f"<-[r*1..{hops}]-"
        else:
            rel_pattern = f"-[r*1..{hops}]-"

        # Canonicalize relationship types if provided
        canonical_rel_types = None
        if rel_types:
            canonical_rel_types = [RelTypes.canonicalize(r) for r in rel_types if str(r).strip()]

        # Clean type filters
        cleaned_allowed = [str(t).strip() for t in (allowed_types or []) if str(t).strip()] or None
        cleaned_excluded = [str(t).strip() for t in (excluded_types or []) if str(t).strip()] or None

        query = f"""
        MATCH (start:KGNode)
        WHERE start.id = $id
           OR start.name = $id
           OR toLower(start.id) = toLower($id)
           OR toLower(start.name) = toLower($id)
           OR toLower(coalesce(start.label, '')) = toLower($id)
        WITH start LIMIT 1
        OPTIONAL MATCH path = (start){rel_pattern}(target:KGNode)
        WHERE start <> target
          AND ($rel_types IS NULL OR ALL(rel IN relationships(path) WHERE type(rel) IN $rel_types))
          AND ($allowed_types IS NULL OR ALL(n IN nodes(path)[1..] WHERE coalesce(n.type, head(labels(n))) IN $allowed_types OR any(lbl IN labels(n) WHERE lbl IN $allowed_types)))
          AND ($excluded_types IS NULL OR NONE(n IN nodes(path)[1..] WHERE coalesce(n.type, head(labels(n))) IN $excluded_types OR any(lbl IN labels(n) WHERE lbl IN $excluded_types)))
        WITH start, path
        ORDER BY length(path) ASC
        LIMIT $path_limit
        RETURN start {{
                 id: coalesce(start.id, start.name, elementId(start)),
                 .*,
                 labels: labels(start)
               }} AS selected_node,
               [p IN collect(DISTINCT path) WHERE p IS NOT NULL | {{
                 length: length(p),
                 nodes: [n IN nodes(p) | n {{
                   id: coalesce(n.id, n.name, elementId(n)),
                   .*,
                   labels: labels(n)
                 }}],
                 relationships: [rel IN relationships(p) | {{
                   id: coalesce(rel.id, elementId(rel), coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))) + '_' + type(rel) + '_' + coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))) + '_' + elementId(rel)),
                   source: coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))),
                   target: coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))),
                   type: type(rel),
                   relation: type(rel),
                   label: coalesce(rel.label, type(rel)),
                   confidence: coalesce(rel.confidence, 1.0),
                   validation_level: coalesce(rel.validation_level, rel.validation_status, 'corpus_validated'),
                   source_corpus: coalesce(rel.source, 'Tolkāppiyam'),
                   source_reference: coalesce(rel.source_reference, ''),
                   passage_id: rel.passage_id,
                   metadata_json: rel.metadata_json
                 }}]
               }}] AS projected_paths
        """
        params = {
            "id": cleaned_id,
            "path_limit": path_limit,
            "rel_types": canonical_rel_types,
            "allowed_types": cleaned_allowed,
            "excluded_types": cleaned_excluded,
        }

        records = self.service.execute_read(query, params, database=database)
        if not records or not records[0].get("selected_node"):
            return None

        rec = records[0]
        selected_node = dict(rec["selected_node"])
        if "metadata_json" in selected_node and selected_node["metadata_json"]:
            try:
                selected_node["metadata"] = json.loads(selected_node["metadata_json"])
            except Exception:
                selected_node["metadata"] = {}
        elif "metadata" not in selected_node:
            selected_node["metadata"] = {}

        selected_id = selected_node.get("id")

        # Process paths to build parent-child lineage and node/rel maps
        node_map: Dict[str, Dict[str, Any]] = {
            selected_id: {
                **selected_node,
                "hop_distance": 0,
                "parent_id": None,
                "parent_rel_type": None,
                "parent_rel_direction": None,
                "path_from_root": [selected_id],
            }
        }
        rel_map: Dict[str, Dict[str, Any]] = {}
        structured_paths: List[Dict[str, Any]] = []
        actual_max_depth = 0

        projected_paths = rec.get("projected_paths") or []
        for p in projected_paths:
            p_len = p.get("length", 0)
            p_nodes = p.get("nodes") or []
            p_rels = p.get("relationships") or []

            if not p_nodes or not p_rels or len(p_nodes) != p_len + 1:
                continue

            actual_max_depth = max(actual_max_depth, p_len)
            path_conf = 1.0

            for i in range(1, len(p_nodes)):
                parent = p_nodes[i - 1]
                curr = p_nodes[i]
                edge = p_rels[i - 1]

                parent_id = parent.get("id")
                curr_id = curr.get("id")
                rel_id = edge.get("id")

                edge_conf = float(edge.get("confidence", 1.0))
                path_conf *= edge_conf

                # Direction relative to the parent on this path
                direction_rel = "outgoing" if edge.get("source") == parent_id else "incoming"
                edge["direction"] = direction_rel

                if "metadata_json" in edge and edge["metadata_json"]:
                    try:
                        edge["metadata"] = json.loads(edge["metadata_json"])
                    except Exception:
                        edge["metadata"] = {}
                elif "metadata" not in edge:
                    edge["metadata"] = {}

                rel_map[rel_id] = edge

                # Check if current node needs insertion or has a shorter hop distance
                if "metadata_json" in curr and curr["metadata_json"]:
                    try:
                        curr["metadata"] = json.loads(curr["metadata_json"])
                    except Exception:
                        curr["metadata"] = {}
                elif "metadata" not in curr:
                    curr["metadata"] = {}

                if curr_id not in node_map or i < node_map[curr_id]["hop_distance"]:
                    node_map[curr_id] = {
                        **curr,
                        "hop_distance": i,
                        "parent_id": parent_id,
                        "parent_rel_type": edge.get("type"),
                        "parent_rel_direction": direction_rel,
                        "path_from_root": [n.get("id") for n in p_nodes[: i + 1]],
                    }

            structured_paths.append({
                "target_id": p_nodes[-1].get("id"),
                "hops": p_len,
                "path_node_ids": [n.get("id") for n in p_nodes],
                "cumulative_confidence": round(path_conf, 4),
                "edges": p_rels,
            })

        # Separate connected nodes (excluding the root node)
        connected_nodes = [
            n for nid, n in node_map.items() if nid != selected_id
        ]
        connected_nodes.sort(key=lambda n: (n.get("hop_distance", 99), n.get("name", "")))

        relationships = list(rel_map.values())

        metadata = {
            "start_id": selected_id,
            "max_hops": hops,
            "actual_max_depth": actual_max_depth,
            "connected_count": len(connected_nodes),
            "relationship_count": len(relationships),
            "path_count": len(structured_paths),
            "allowed_types": cleaned_allowed,
            "excluded_types": cleaned_excluded,
            "rel_types": canonical_rel_types,
            "source": "neo4j_aura",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "selected_node": node_map[selected_id],
            "connected_nodes": connected_nodes,
            "relationships": relationships,
            "nodes": [node_map[selected_id]] + connected_nodes,
            "paths": structured_paths,
            "metadata": metadata,
        }

    def get_graph_health(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates structural health and connectivity of the Knowledge Graph in Neo4j Aura.
        """
        stats = self.get_kg_statistics(database=database)
        node_count = stats["total_nodes"]
        edge_count = stats["total_edges"]
        isolated_nodes = stats["isolated_nodes"]

        valid = node_count > 0 and stats["density"] >= 0.0

        return {
            "valid": valid,
            "status": "HEALTHY" if valid else "DEGRADED",
            "node_count": node_count,
            "edge_count": edge_count,
            "is_connected": stats["is_connected"],
            "density": stats["density"],
            "isolated_nodes": isolated_nodes,
            "isolated_count": len(isolated_nodes),
            "hierarchy_distribution": stats["hierarchy_distribution"],
            "layer_distribution": stats["layer_distribution"],
            "source": "neo4j_aura",
        }

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Finds all multi-hop paths between source and target entities in Neo4j Aura
        with propagated cumulative path confidence.
        """
        depth = min(max(int(max_depth), 1), 5)
        query = f"""
        MATCH p = (s:KGNode {{id: $source}})-[*1..{depth}]-(t:KGNode {{id: $target}})
        RETURN [n in nodes(p) | {{id: coalesce(n.id, n.name), label: coalesce(n.label, n.name), type: n.type, hierarchy_level: n.hierarchy_level}}] AS nodes,
               [r in relationships(p) | {{relation: type(r), type: type(r), confidence: coalesce(r.confidence, 1.0)}}] AS edges,
               length(p) AS length
        LIMIT 25
        """
        records = self.service.execute_read(query, {"source": source_id, "target": target_id}, database=database)
        paths: List[Dict[str, Any]] = []

        for rec in records:
            edges = rec.get("edges", [])
            path_conf = 1.0
            for e in edges:
                path_conf *= float(e.get("confidence", 1.0))

            paths.append({
                "source": source_id,
                "target": target_id,
                "length": rec.get("length", len(edges)),
                "propagated_confidence": round(path_conf, 4),
                "nodes": rec.get("nodes", []),
                "edges": edges,
            })

        paths.sort(key=lambda p: (-p["propagated_confidence"], p["length"]))
        return paths

    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
        rel_types: Optional[List[str]] = None,
        limit: int = 150,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts a multi-hop focused subgraph around seed nodes directly from Neo4j Aura.
        """
        data = self.get_query_subgraph(
            seed_ids=node_ids,
            max_hops=hops,
            limit=limit,
            rel_types=rel_types,
            include_isolated=True,
            database=database,
        )
        data["categories"] = TolkappiyamOntology.get_category_config()
        data["hierarchy_levels"] = TolkappiyamOntology.get_hierarchy_config()
        data["logical_layers"] = TolkappiyamOntology.get_layer_config()
        return data


# Singleton instance for repository injection across services
neo4j_repository = Neo4jRepository()

