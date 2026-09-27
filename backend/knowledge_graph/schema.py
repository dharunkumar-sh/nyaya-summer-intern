"""
Neo4j Knowledge Graph Schema Definition and Migration Manager.

Defines core entity labels, controlled relationship types, uniqueness constraints,
and property indexes for the Nyāya-Inspired Neuro-Symbolic Reasoning Framework
for Classical Tamil Literature.

Keeps DDL schema setup and migration logic completely isolated from application routes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend root is on sys.path when executed as script
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from core.logger import logger
from core.exceptions import KnowledgeGraphError, CypherQueryError
from services.neo4j_service import Neo4jService, neo4j_service


# ==============================================================================
# 1. Canonical Node Labels
# ==============================================================================

class NodeLabels:
    """Core entity labels based on the project's structural and epistemic hierarchy."""

    # Structural & Provenance Hierarchy (L0 - L3)
    LITERATURE = "Literature"  # L0: Ancient treatise corpus (Sangam Literature)
    WORK = "Work"              # L1: Monograph/Treatise (Tolkāppiyam)
    SECTION = "Section"        # L2: Atikāram / Iyal (Poruḷatikāram, Akattiṇaiyiyal)
    PASSAGE = "Passage"        # L3: Sūtra / Verse
    EVIDENCE = "Evidence"      # L3: Grounded evidence chunk / citation

    # Conceptual & Domain Knowledge (L4 - L5)
    CONCEPT = "Concept"        # L4: Semiotic categories (Mutalporuḷ, Karupporuḷ, Uripporuḷ, Tiṇai)
    ENTITY = "Entity"          # L5: Concrete signifiers (Deity, Landscape, Flora, Fauna, Time)
    EVENT = "Event"            # L5: Poetic actions and affects (Puṇartal, Pirital)

    # Reasoning Pipeline Entities (Reasoning Layer)
    PREMISE = "Premise"        # Epistemic premise (Pakṣa, Hetu, Dṛṣṭānta)
    RULE = "Rule"              # Invariant concomitance rule (Vyāpti Horn-clause)
    INFERENCE = "Inference"    # Pañcāvayava inference stage (Pratijñā, Hetu, Udāharaṇa, Upanaya)
    CONCLUSION = "Conclusion"  # Final synthetic conclusion (Nigamana)

    # Base polymorphic label for all knowledge graph nodes
    KGNODE = "KGNode"

    @classmethod
    def all_primary_labels(cls) -> List[str]:
        """Returns all canonical domain and reasoning labels."""
        return [
            cls.LITERATURE,
            cls.WORK,
            cls.SECTION,
            cls.PASSAGE,
            cls.EVIDENCE,
            cls.CONCEPT,
            cls.ENTITY,
            cls.EVENT,
            cls.PREMISE,
            cls.RULE,
            cls.INFERENCE,
            cls.CONCLUSION,
        ]

    @classmethod
    def from_string(cls, val: str) -> Optional[str]:
        """Resolves a case-insensitive string into a canonical NodeLabel if recognized."""
        if not val:
            return None
        norm = val.strip().lower()
        if norm == cls.KGNODE.lower():
            return cls.KGNODE
        for label in cls.all_primary_labels():
            if label.lower() == norm:
                return label
        return None


# ==============================================================================
# 2. Canonical Relationship Types (5 Architectural Tiers)
# ==============================================================================

class RelTypes:
    """
    Controlled relationship vocabulary grounded in Tolkāppiyam semiotics and Nyāya deduction.
    Separated into 5 distinct architectural tiers:
    - Tier 1: Literary Structure Relationships
    - Tier 2: Semantic Knowledge Relationships
    - Tier 3: Contextual Relationships
    - Tier 4: Evidence & Textual Provenance Relationships
    - Tier 5: Epistemic Reasoning Pipeline Relationships
    """

    # --------------------------------------------------------------------------
    # Tier 1: Literary Structure Relationships (Corpus Containment)
    # --------------------------------------------------------------------------
    CONTAINS_WORK = "CONTAINS_WORK"          # Literature -> Work
    HAS_WORK = "HAS_WORK"                    # Compatibility alias
    CONTAINS_SECTION = "CONTAINS_SECTION"    # Work -> Section (Book / Chapter)
    HAS_SECTION = "HAS_SECTION"              # Compatibility alias
    CONTAINS_PASSAGE = "CONTAINS_PASSAGE"    # Section -> Passage (Sūtra)
    HAS_PASSAGE = "HAS_PASSAGE"              # Compatibility alias

    # --------------------------------------------------------------------------
    # Tier 2: Semantic Knowledge Relationships (Tolkāppiyam Semiotics & Ontology)
    # --------------------------------------------------------------------------
    SUB_CONCEPT_OF = "SUB_CONCEPT_OF"        # Concept -> Concept taxonomy
    GROUNDS_IN = "GROUNDS_IN"                # Concept -> Concept (e.g. Mutalporuḷ -> Uripporuḷ)
    CHARACTERISTIC_OF = "CHARACTERISTIC_OF"  # Entity -> Concept
    PRESIDES_OVER = "PRESIDES_OVER"          # Entity -> Concept/Entity (e.g. Cēyōṉ -> Kuṟiñci)
    INCLUDES_COMPONENT = "INCLUDES_COMPONENT" # Concept -> Entity/Concept (Karupporuḷ -> Flora/Fauna)
    EVOKES_AFFECT = "EVOKES_AFFECT"          # Event -> Concept / Meyppāṭu
    MANIFESTS_AS = "MANIFESTS_AS"            # Event -> Concept (Puṇartal -> Meyppāṭu)
    HAS_URIPPORUL = "HAS_URIPPORUL"          # Concept/Entity -> Event (Kuṟiñci -> Puṇartal)
    MANIFESTS_SIGNIFIER_FOR = "MANIFESTS_SIGNIFIER_FOR" # Entity -> Concept
    BELONGS_TO_CATEGORY = "BELONGS_TO_CATEGORY" # Passage/Concept -> Category
    GROUNDS_IN_ONTOLOGY = "GROUNDS_IN_ONTOLOGY" # Passage/Concept -> Ontology Concept

    # --------------------------------------------------------------------------
    # Tier 3: Contextual Relationships (Spatiotemporal, Ecological, Poetic)
    # --------------------------------------------------------------------------
    OCCURS_IN_HABITAT = "OCCURS_IN_HABITAT"  # Fauna/Flora in Landscape / Nilam
    HAS_HABITAT = "HAS_HABITAT"              # Compatibility alias for OCCURS_IN_HABITAT
    ASSOCIATED_WITH_SEASON = "ASSOCIATED_WITH_SEASON" # Entity/Concept -> Season (Kālam)
    ASSOCIATED_WITH_TIME = "ASSOCIATED_WITH_TIME"     # Entity/Concept -> Time of Day (Poḻutu)
    ASSOCIATED_WITH_TINAI = "ASSOCIATED_WITH_TINAI"   # Entity/Event -> Tiṇai
    LOCATED_IN_CONTEXT = "LOCATED_IN_CONTEXT"         # Event/Entity -> Context

    # --------------------------------------------------------------------------
    # Tier 4: Evidence & Textual Provenance Grounding (Passage Grounding)
    # --------------------------------------------------------------------------
    ATTESTS_ENTITY = "ATTESTS_ENTITY"        # Passage -> Entity (canonical textual attestation)
    MENTIONS = "MENTIONS"                    # Backward-compatible alias
    ATTESTS_CONCEPT = "ATTESTS_CONCEPT"      # Passage -> Concept (canonical textual attestation)
    DISCUSSES = "DISCUSSES"                  # Backward-compatible alias
    ATTESTS_EVENT = "ATTESTS_EVENT"          # Passage -> Event (canonical textual attestation)
    DESCRIBES = "DESCRIBES"                  # Backward-compatible alias
    DEPICTS_EVENT = "DESCRIBES"              # Alias for DESCRIBES
    GROUNDED_IN = "GROUNDED_IN"              # Entity/Concept/Event/Rule -> Passage (direct provenance)
    SUPPORTED_BY = "SUPPORTED_BY"            # Evidence/Premise/Rule -> Passage

    # --------------------------------------------------------------------------
    # Tier 5: Epistemic Reasoning Pipeline Relationships (Nyāya Deduction)
    # --------------------------------------------------------------------------
    APPLIES_TO = "APPLIES_TO"                # Rule -> Concept (Invariant scope)
    DERIVED_FROM = "DERIVED_FROM"            # Inference -> Premise, Premise -> Passage
    INFERRED_FROM = "INFERRED_FROM"          # Conclusion -> Inference
    CONTRADICTS = "CONTRADICTS"              # Hetvābhāsa fallacy detection
    SUB_SUMES = "SUB_SUMES"                  # Upanaya application

    # Mapping from legacy or raw relation names to canonical uppercase relationships
    RELATION_MAP = {
        # Tier 1
        "contains_work": CONTAINS_WORK,
        "containswork": CONTAINS_WORK,
        "has_work": HAS_WORK,
        "haswork": HAS_WORK,
        "contains_section": CONTAINS_SECTION,
        "containssection": CONTAINS_SECTION,
        "has_section": HAS_SECTION,
        "hassection": HAS_SECTION,
        "contains_passage": CONTAINS_PASSAGE,
        "containspassage": CONTAINS_PASSAGE,
        "has_passage": HAS_PASSAGE,
        "haspassage": HAS_PASSAGE,
        # Tier 2
        "sub_concept_of": SUB_CONCEPT_OF,
        "subconceptof": SUB_CONCEPT_OF,
        "characteristic_of": CHARACTERISTIC_OF,
        "characteristicof": CHARACTERISTIC_OF,
        "presides_over": PRESIDES_OVER,
        "presidesover": PRESIDES_OVER,
        "includes_component": INCLUDES_COMPONENT,
        "includescomponent": INCLUDES_COMPONENT,
        "consistsof": INCLUDES_COMPONENT,
        "consists_of": INCLUDES_COMPONENT,
        "hasconstituent": INCLUDES_COMPONENT,
        "has_constituent": INCLUDES_COMPONENT,
        "has_uripporul": HAS_URIPPORUL,
        "hasuripporul": HAS_URIPPORUL,
        "manifests_signifier_for": MANIFESTS_SIGNIFIER_FOR,
        "manifestssignifierfor": MANIFESTS_SIGNIFIER_FOR,
        "manifests_as": MANIFESTS_AS,
        "manifestsas": MANIFESTS_AS,
        "evokes_affect": EVOKES_AFFECT,
        "evokesaffect": EVOKES_AFFECT,
        "belongs_to_category": BELONGS_TO_CATEGORY,
        "belongstocategory": BELONGS_TO_CATEGORY,
        "grounds_in_ontology": GROUNDS_IN_ONTOLOGY,
        "groundsinontology": GROUNDS_IN_ONTOLOGY,
        "groundsin": GROUNDS_IN,
        "grounds_in": GROUNDS_IN,
        # Tier 3
        "occurs_in_habitat": OCCURS_IN_HABITAT,
        "occursinhabitat": OCCURS_IN_HABITAT,
        "has_habitat": HAS_HABITAT,
        "hashabitat": OCCURS_IN_HABITAT,
        "associated_with_season": ASSOCIATED_WITH_SEASON,
        "associatedwithseason": ASSOCIATED_WITH_SEASON,
        "associated_with_time": ASSOCIATED_WITH_TIME,
        "associatedwithtime": ASSOCIATED_WITH_TIME,
        "associated_with_tinai": ASSOCIATED_WITH_TINAI,
        "associatedwithtinai": ASSOCIATED_WITH_TINAI,
        "located_in_context": LOCATED_IN_CONTEXT,
        "locatedincontext": LOCATED_IN_CONTEXT,
        # Tier 4
        "attests_entity": ATTESTS_ENTITY,
        "attestsentity": ATTESTS_ENTITY,
        "mentions": MENTIONS,
        "mentions_entity": MENTIONS,
        "instantiates_entity": MENTIONS,
        "attests_concept": ATTESTS_CONCEPT,
        "attestsconcept": ATTESTS_CONCEPT,
        "discusses": DISCUSSES,
        "exposes_concept": DISCUSSES,
        "attests_event": ATTESTS_EVENT,
        "attestsevent": ATTESTS_EVENT,
        "describes": DESCRIBES,
        "describes_event": DESCRIBES,
        "depicts_event": DESCRIBES,
        "depictsevent": DESCRIBES,
        "grounded_in": GROUNDED_IN,
        "groundedin": GROUNDED_IN,
        "supported_by": SUPPORTED_BY,
        "supportedby": SUPPORTED_BY,
        "grounds_deduction": SUPPORTED_BY,
        # Tier 5
        "applies_to": APPLIES_TO,
        "appliesto": APPLIES_TO,
        "derived_from": DERIVED_FROM,
        "derivedfrom": DERIVED_FROM,
        "inferred_from": INFERRED_FROM,
        "inferredfrom": INFERRED_FROM,
        "contradicts": CONTRADICTS,
        "sub_sumes": SUB_SUMES,
        "subsumes": SUB_SUMES,
    }

    @classmethod
    def canonicalize(cls, rel: str) -> str:
        """Translates any raw relation predicate into canonical uppercase Cypher type."""
        if not rel:
            return "RELATED_TO"
        normalized = rel.lower().replace("-", "_").replace(" ", "_")
        if normalized in cls.RELATION_MAP:
            return cls.RELATION_MAP[normalized]
        cleaned = "".join(c if c.isalnum() else "_" for c in rel).upper()
        return cleaned or "RELATED_TO"

    @classmethod
    def tier_1_literary(cls) -> List[str]:
        return [cls.CONTAINS_WORK, cls.HAS_WORK, cls.CONTAINS_SECTION, cls.HAS_SECTION, cls.CONTAINS_PASSAGE, cls.HAS_PASSAGE]

    @classmethod
    def tier_2_semantic(cls) -> List[str]:
        return [
            cls.SUB_CONCEPT_OF, cls.GROUNDS_IN, cls.CHARACTERISTIC_OF, cls.PRESIDES_OVER,
            cls.INCLUDES_COMPONENT, cls.EVOKES_AFFECT, cls.MANIFESTS_AS, cls.HAS_URIPPORUL,
            cls.MANIFESTS_SIGNIFIER_FOR, cls.BELONGS_TO_CATEGORY, cls.GROUNDS_IN_ONTOLOGY,
        ]

    @classmethod
    def tier_3_contextual(cls) -> List[str]:
        return [
            cls.OCCURS_IN_HABITAT, cls.HAS_HABITAT, cls.ASSOCIATED_WITH_SEASON,
            cls.ASSOCIATED_WITH_TIME, cls.ASSOCIATED_WITH_TINAI, cls.LOCATED_IN_CONTEXT,
        ]

    @classmethod
    def tier_4_evidence(cls) -> List[str]:
        return [
            cls.ATTESTS_ENTITY, cls.MENTIONS, cls.ATTESTS_CONCEPT, cls.DISCUSSES,
            cls.ATTESTS_EVENT, cls.DESCRIBES, cls.GROUNDED_IN, cls.SUPPORTED_BY,
        ]

    @classmethod
    def tier_5_reasoning(cls) -> List[str]:
        return [cls.APPLIES_TO, cls.DERIVED_FROM, cls.INFERRED_FROM, cls.CONTRADICTS, cls.SUB_SUMES]


# ==============================================================================
# 3. DDL Constraints & Indexes Definitions
# ==============================================================================

# Uniqueness constraints ensuring stable IDs across primary labels and base KGNode
UNIQUENESS_CONSTRAINTS: List[Tuple[str, str, str]] = [
    # (Constraint Name, Label, Property)
    ("constraint_kgnode_id", NodeLabels.KGNODE, "id"),
    ("constraint_literature_id", NodeLabels.LITERATURE, "id"),
    ("constraint_work_id", NodeLabels.WORK, "id"),
    ("constraint_section_id", NodeLabels.SECTION, "id"),
    ("constraint_passage_id", NodeLabels.PASSAGE, "id"),
    ("constraint_evidence_id", NodeLabels.EVIDENCE, "id"),
    ("constraint_concept_id", NodeLabels.CONCEPT, "id"),
    ("constraint_entity_id", NodeLabels.ENTITY, "id"),
    ("constraint_event_id", NodeLabels.EVENT, "id"),
    ("constraint_premise_id", NodeLabels.PREMISE, "id"),
    ("constraint_rule_id", NodeLabels.RULE, "id"),
    ("constraint_inference_id", NodeLabels.INFERENCE, "id"),
    ("constraint_conclusion_id", NodeLabels.CONCLUSION, "id"),
]

# Property indexes for high-speed lookup and filtering
PROPERTY_INDEXES: List[Tuple[str, str, str]] = [
    # (Index Name, Label, Property)
    ("index_kgnode_label", NodeLabels.KGNODE, "label"),
    ("index_kgnode_name", NodeLabels.KGNODE, "name"),
    ("index_kgnode_type", NodeLabels.KGNODE, "type"),
    ("index_kgnode_source_id", NodeLabels.KGNODE, "source_id"),
    ("index_kgnode_context", NodeLabels.KGNODE, "context"),
    ("index_kgnode_validation_status", NodeLabels.KGNODE, "validation_status"),
    ("index_passage_sutra_number", NodeLabels.PASSAGE, "sutra_number"),
    ("index_passage_tinai", NodeLabels.PASSAGE, "tinai"),
    ("index_entity_category", NodeLabels.ENTITY, "category"),
    ("index_concept_label", NodeLabels.CONCEPT, "label"),
    ("index_event_label", NodeLabels.EVENT, "label"),
    ("index_event_category", NodeLabels.EVENT, "category"),
    ("index_event_tinai", NodeLabels.EVENT, "tinai"),
    ("index_rule_tinai", NodeLabels.RULE, "tinai"),
]


# ==============================================================================
# 4. Schema Manager Implementation
# ==============================================================================

class Neo4jSchemaManager:
    """
    Manages DDL schema operations in Neo4j Aura:
    - Creates uniqueness constraints and property indexes
    - Verifies active constraints and indexes
    - Seeds the canonical Tamil literary hierarchy
    - Isolates schema management from web routes
    """

    def __init__(self, service: Optional[Neo4jService] = None):
        self.service = service or neo4j_service

    def setup_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Applies all uniqueness constraints and property indexes to Neo4j.
        Returns execution statistics.
        """
        driver = self.service.get_driver()
        if driver is None:
            raise KnowledgeGraphError(
                "Cannot setup schema: Neo4j Aura driver is not connected or configured"
            )

        constraints_created = 0
        indexes_created = 0
        errors = []

        # 1. Apply Uniqueness Constraints
        for c_name, label, prop in UNIQUENESS_CONSTRAINTS:
            cypher = (
                f"CREATE CONSTRAINT {c_name} IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            )
            try:
                self.service.run_query(cypher, database=database)
                constraints_created += 1
                logger.info(f"Created/verified constraint: {c_name} on :{label}({prop})")
            except Exception as e:
                msg = f"Constraint {c_name} error: {e}"
                logger.warning(msg)
                errors.append(msg)

        # 2. Apply Property Indexes
        for idx_name, label, prop in PROPERTY_INDEXES:
            cypher = (
                f"CREATE INDEX {idx_name} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.{prop})"
            )
            try:
                self.service.run_query(cypher, database=database)
                indexes_created += 1
                logger.info(f"Created/verified index: {idx_name} on :{label}({prop})")
            except Exception as e:
                msg = f"Index {idx_name} error: {e}"
                logger.warning(msg)
                errors.append(msg)

        return {
            "status": "COMPLETED",
            "constraints_applied": constraints_created,
            "total_constraints_defined": len(UNIQUENESS_CONSTRAINTS),
            "indexes_applied": indexes_created,
            "total_indexes_defined": len(PROPERTY_INDEXES),
            "errors": errors,
            "database": database or self.service.database,
        }

    def verify_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects Neo4j schema via SHOW CONSTRAINTS and SHOW INDEXES.
        Returns active constraints and indexes in the database.
        """
        driver = self.service.get_driver()
        if driver is None:
            return {
                "status": "DISCONNECTED",
                "connected": False,
                "database": database or self.service.database,
                "constraints": [],
                "indexes": [],
                "error": "Driver not initialized",
            }

        try:
            constraints_records = self.service.run_query("SHOW CONSTRAINTS", database=database)
            indexes_records = self.service.run_query("SHOW INDEXES", database=database)

            constraints = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "entityType": r.get("entityType"),
                    "labelsOrTypes": r.get("labelsOrTypes"),
                    "properties": r.get("properties"),
                }
                for r in constraints_records
            ]

            indexes = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "entityType": r.get("entityType"),
                    "labelsOrTypes": r.get("labelsOrTypes"),
                    "properties": r.get("properties"),
                    "state": r.get("state"),
                }
                for r in indexes_records
            ]

            return {
                "status": "VERIFIED",
                "connected": True,
                "database": database or self.service.database,
                "constraints_count": len(constraints),
                "indexes_count": len(indexes),
                "constraints": constraints,
                "indexes": indexes,
            }
        except Exception as e:
            logger.error(f"Error inspecting Neo4j schema: {e}")
            return {
                "status": "ERROR",
                "connected": False,
                "database": database or self.service.database,
                "error": str(e),
            }

    def seed_canonical_schema_graph(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Seeds canonical Tamil Literary Knowledge Graph nodes and edges into Neo4j Aura
        using canonical node labels and controlled relationship types.
        """
        from knowledge_graph.graph_builder import kg_instance

        driver = self.service.get_driver()
        if driver is None:
            raise KnowledgeGraphError("Cannot seed graph: Neo4j Aura driver is not connected")

        # First ensure schema constraints are active
        self.setup_schema(database=database)

        nodes_upserted = 0
        edges_upserted = 0

        # Upsert nodes with dual labels (:KGNode and :SpecificLabel)
        for node in kg_instance.store.get_all_nodes():
            primary_label = self._resolve_primary_label(node.type, node.hierarchy_level)
            query = f"""
            MERGE (n:KGNode {{id: $id}})
            SET n:{primary_label},
                n.label = $label,
                n.type = $type,
                n.hierarchy_level = $hierarchy_level,
                n.source = $source,
                n.confidence = $confidence,
                n.tinai = $tinai,
                n.sutra_number = $sutra_number,
                n.metadata_json = $metadata_json
            """
            params = {
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "hierarchy_level": node.hierarchy_level,
                "source": node.source,
                "confidence": float(node.confidence),
                "tinai": node.metadata.get("tinai", "General"),
                "sutra_number": node.metadata.get("sutra_number"),
                "metadata_json": json.dumps(node.metadata, ensure_ascii=False),
            }
            self.service.execute_write(query, params, database=database)
            nodes_upserted += 1

        # Upsert edges with canonical relationship types
        for edge in kg_instance.store.get_all_edges():
            canonical_rel = RelTypes.canonicalize(edge.relation)
            query = f"""
            MATCH (s:KGNode {{id: $source}})
            MATCH (t:KGNode {{id: $target}})
            MERGE (s)-[r:{canonical_rel} {{id: $edge_id}}]->(t)
            SET r.relation = $relation,
                r.source_id = $source_id,
                r.confidence = $confidence,
                r.validation_level = $validation_level,
                r.metadata_json = $metadata_json
            """
            params = {
                "source": edge.source,
                "target": edge.target,
                "edge_id": edge.id,
                "relation": edge.relation,
                "source_id": edge.source_id,
                "confidence": float(edge.confidence),
                "validation_level": edge.validation_level,
                "metadata_json": json.dumps(edge.metadata, ensure_ascii=False),
            }
            self.service.execute_write(query, params, database=database)
            edges_upserted += 1

        return {
            "status": "SEEDED",
            "database": database or self.service.database,
            "nodes_upserted": nodes_upserted,
            "edges_upserted": edges_upserted,
        }

    def migrate_and_normalize_graph(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an in-place semantic migration and normalization of the Neo4j Knowledge Graph:
        1. Ensures all uniqueness constraints and property indexes are applied.
        2. Strips obsolete/legacy labels (:L0..:L5, :Verse) while ensuring canonical primary labels.
        3. Standardizes properties on all nodes: id, name, text, type, source, source_id, context,
           confidence, and validation_status.
        4. Re-types legacy/un-normalized relationships (HASHABITAT -> OCCURS_IN_HABITAT,
           PRESIDESOVER -> PRESIDES_OVER, CONSISTSOF -> INCLUDES_COMPONENT, etc.).
        5. Synchronizes canonical 5-tier relationships (CONTAINS_WORK, CONTAINS_SECTION, CONTAINS_PASSAGE,
           ATTESTS_ENTITY, ATTESTS_CONCEPT, ATTESTS_EVENT).
        6. Establishes explicit [:GROUNDED_IN] edges from every entity/concept/event/rule
           back to its source literary Passage.
        """
        driver = self.service.get_driver()
        if driver is None:
            raise KnowledgeGraphError("Cannot migrate graph: Neo4j Aura driver is not connected")

        logger.info("Starting Neo4j graph semantic migration and normalization...")

        # Step 1: Ensure constraints and indexes
        schema_res = self.setup_schema(database=database)

        # Step 2: Strip obsolete hierarchy and duplicate labels
        strip_query = """
        MATCH (n:KGNode)
        REMOVE n:L0, n:L1, n:L2, n:L3, n:L4, n:L5, n:Verse
        RETURN count(n) AS cleaned_count
        """
        res_strip = self.service.execute_write(strip_query, {}, database=database)
        nodes_stripped = res_strip[0].get("cleaned_count", 0) if res_strip else 0

        # Step 3: Enforce primary semantic labels on all nodes
        label_queries = [
            ("MATCH (n:KGNode) WHERE n.hierarchy_level = 'L0' OR n.type = 'Literature' SET n:Literature", "Literature"),
            ("MATCH (n:KGNode) WHERE n.hierarchy_level = 'L1' OR n.type = 'Work' SET n:Work", "Work"),
            ("MATCH (n:KGNode) WHERE n.hierarchy_level = 'L2' OR n.type = 'Section' SET n:Section", "Section"),
            ("MATCH (n:KGNode) WHERE (n.hierarchy_level = 'L3' OR n.sutra_number IS NOT NULL OR n.id STARTS WITH 'tol-') AND n.type <> 'Evidence' SET n:Passage", "Passage"),
            ("MATCH (n:KGNode) WHERE n.type = 'Evidence' OR n.id STARTS WITH 'ev_' SET n:Evidence", "Evidence"),
            ("MATCH (n:KGNode) WHERE (n.hierarchy_level = 'L4' OR n.type = 'Concept') AND NOT n:Passage AND NOT n:Section AND NOT n:Work AND NOT n:Literature AND NOT n:Evidence SET n:Concept", "Concept"),
            ("MATCH (n:KGNode) WHERE (n.hierarchy_level = 'L5' OR n.type = 'Entity') AND NOT n:Event AND NOT n:Passage AND NOT n:Section AND NOT n:Work AND NOT n:Literature SET n:Entity", "Entity"),
            ("MATCH (n:KGNode) WHERE n.type = 'Event' OR n.event_type IS NOT NULL OR n.id STARTS WITH 'event_' SET n:Event", "Event"),
        ]
        for q, lbl in label_queries:
            self.service.execute_write(q, {}, database=database)

        # Step 4: Standardize properties on all nodes
        prop_query = """
        MATCH (n:KGNode)
        SET n.name = coalesce(n.name, n.label, n.id),
            n.text = coalesce(n.text, n.tamil_text, n.original_text, n.normalized_text, n.description, n.label, n.name, ''),
            n.type = coalesce(n.type, [l IN labels(n) WHERE l <> 'KGNode'][0], 'Entity'),
            n.source = coalesce(n.source, n.source_reference, 'Tolkāppiyam'),
            n.source_id = coalesce(n.source_id, n.passage_id, CASE WHEN n:Passage THEN n.id ELSE null END),
            n.context = coalesce(n.context, n.tinai, n.section_name, 'General'),
            n.confidence = coalesce(n.confidence, 1.0),
            n.validation_status = coalesce(n.validation_status, 'canonical_verified')
        RETURN count(n) AS prop_count
        """
        res_prop = self.service.execute_write(prop_query, {}, database=database)
        nodes_standardized = res_prop[0].get("prop_count", 0) if res_prop else 0

        # Also standardize Passage specific hierarchy fields
        passage_prop_query = """
        MATCH (p:Passage)
        SET p.work = coalesce(p.work, p.work_name, 'Tolkāppiyam'),
            p.section = coalesce(p.section, p.section_name, 'Poruḷatikāram'),
            p.chapter = coalesce(p.chapter, p.chapter_name, p.iyal, '')
        """
        self.service.execute_write(passage_prop_query, {}, database=database)

        # Step 5: Normalize and migrate legacy relationships
        rel_migrations = [
            ("HASHABITAT", RelTypes.OCCURS_IN_HABITAT),
            ("PRESIDESOVER", RelTypes.PRESIDES_OVER),
            ("CONSISTSOF", RelTypes.INCLUDES_COMPONENT),
            ("EVOKESAFFECT", RelTypes.EVOKES_AFFECT),
            ("HASURIPPORUL", RelTypes.HAS_URIPPORUL),
            ("HASURIPPORUḶ", RelTypes.HAS_URIPPORUL),
            ("MANIFESTSSIGNIFIERFOR", RelTypes.MANIFESTS_SIGNIFIER_FOR),
            ("INCLUDESCOMPONENT", RelTypes.INCLUDES_COMPONENT),
            ("MANIFESTSAS", RelTypes.MANIFESTS_AS),
            ("GROUNDSIN", RelTypes.GROUNDS_IN),
            ("HASCONSTITUENT", RelTypes.INCLUDES_COMPONENT),
            ("DETERMINISTICALLYGROUNDS", RelTypes.GROUNDS_IN),
            ("ISSPACEDIMENSIONOF", RelTypes.OCCURS_IN_HABITAT),
            ("ISTIMEDIMENSIONOF", RelTypes.ASSOCIATED_WITH_TIME),
            ("HAS_LANDSCAPE", RelTypes.OCCURS_IN_HABITAT),
            ("HAS_TIME", RelTypes.ASSOCIATED_WITH_TIME),
            ("ASSOCIATED_DEITY", RelTypes.PRESIDES_OVER),
            ("HAS_THINAI", RelTypes.ASSOCIATED_WITH_TINAI),
        ]
        migrated_rels = 0
        for old_rel, new_rel in rel_migrations:
            retype_cypher = f"""
            MATCH (s:KGNode)-[r:{old_rel}]->(t:KGNode)
            MERGE (s)-[r2:{new_rel}]->(t)
            SET r2 += properties(r),
                r2.relation = '{new_rel}',
                r2.source = coalesce(r.source, 'Tolkāppiyam')
            DELETE r
            RETURN count(r2) AS cnt
            """
            try:
                res_rel = self.service.execute_write(retype_cypher, {}, database=database)
                cnt = res_rel[0].get("cnt", 0) if res_rel else 0
                if cnt > 0:
                    logger.info(f"Migrated {cnt} relationships from {old_rel} to {new_rel}")
                    migrated_rels += cnt
            except Exception as e:
                logger.debug(f"Retype {old_rel} notice: {e}")

        # Step 6: Synchronize canonical Literary Structure edges
        lit_struct_sync = [
            ("MATCH (lit:Literature)-[r:HAS_WORK]->(w:Work) MERGE (lit)-[r2:CONTAINS_WORK]->(w) SET r2 += properties(r), r2.relation = 'CONTAINS_WORK'", "CONTAINS_WORK"),
            ("MATCH (w:Work)-[r:HAS_SECTION]->(sec:Section) MERGE (w)-[r2:CONTAINS_SECTION]->(sec) SET r2 += properties(r), r2.relation = 'CONTAINS_SECTION'", "CONTAINS_SECTION"),
            ("MATCH (sec:Section)-[r:HAS_PASSAGE]->(p:Passage) MERGE (sec)-[r2:CONTAINS_PASSAGE]->(p) SET r2 += properties(r), r2.relation = 'CONTAINS_PASSAGE'", "CONTAINS_PASSAGE"),
        ]
        for q, rel_name in lit_struct_sync:
            try:
                self.service.execute_write(q, {}, database=database)
            except Exception as e:
                logger.debug(f"Sync {rel_name} notice: {e}")

        # Step 7: Synchronize canonical Evidence Attestation edges
        evidence_attest_sync = [
            ("MATCH (p:Passage)-[r:MENTIONS]->(e:Entity) MERGE (p)-[r2:ATTESTS_ENTITY]->(e) SET r2 += properties(r), r2.relation = 'ATTESTS_ENTITY', r2.passage_id = p.id", "ATTESTS_ENTITY"),
            ("MATCH (p:Passage)-[r:DISCUSSES]->(c:Concept) MERGE (p)-[r2:ATTESTS_CONCEPT]->(c) SET r2 += properties(r), r2.relation = 'ATTESTS_CONCEPT', r2.passage_id = p.id", "ATTESTS_CONCEPT"),
            ("MATCH (p:Passage)-[r:DESCRIBES]->(ev:Event) MERGE (p)-[r2:ATTESTS_EVENT]->(ev) SET r2 += properties(r), r2.relation = 'ATTESTS_EVENT', r2.passage_id = p.id", "ATTESTS_EVENT"),
            ("MATCH (s:Entity)-[r:HAS_HABITAT]->(t:Entity) MERGE (s)-[r2:OCCURS_IN_HABITAT]->(t) SET r2 += properties(r), r2.relation = 'OCCURS_IN_HABITAT'", "OCCURS_IN_HABITAT"),
        ]
        for q, rel_name in evidence_attest_sync:
            try:
                self.service.execute_write(q, {}, database=database)
            except Exception as e:
                logger.debug(f"Sync {rel_name} notice: {e}")

        # Step 8: Direct Literary Provenance Grounding ([:GROUNDED_IN])
        grounding_queries = [
            # Connect elements with source_id directly matching a Passage
            """
            MATCH (n:KGNode), (p:Passage)
            WHERE n.source_id = p.id AND n <> p AND NOT n:Section AND NOT n:Work AND NOT n:Literature
            MERGE (n)-[r:GROUNDED_IN]->(p)
            SET r.relation = 'GROUNDED_IN',
                r.confidence = 1.0,
                r.validation_level = 'corpus_grounded',
                r.source = coalesce(p.source, p.source_reference, 'Tolkāppiyam'),
                r.passage_id = p.id
            RETURN count(r) AS grounded_cnt
            """,
            # Connect entities/concepts/events attested by passages back to those passages
            """
            MATCH (p:Passage)-[att:ATTESTS_ENTITY|ATTESTS_CONCEPT|ATTESTS_EVENT|MENTIONS|DISCUSSES|DESCRIBES]->(n:KGNode)
            WHERE n <> p
            MERGE (n)-[r:GROUNDED_IN]->(p)
            SET r.relation = 'GROUNDED_IN',
                r.confidence = coalesce(att.confidence, 1.0),
                r.validation_level = 'corpus_grounded',
                r.source = coalesce(p.source, p.source_reference, 'Tolkāppiyam'),
                r.passage_id = p.id
            RETURN count(r) AS grounded_cnt
            """,
        ]
        grounded_edges = 0
        for g_q in grounding_queries:
            try:
                res_g = self.service.execute_write(g_q, {}, database=database)
                grounded_edges += res_g[0].get("grounded_cnt", 0) if res_g else 0
            except Exception as e:
                logger.debug(f"Grounding query notice: {e}")

        # Step 9: Inspection of post-migration graph statistics
        cnt_nodes = self.service.execute_read("MATCH (n:KGNode) RETURN count(n) AS cnt", database=database)
        cnt_edges = self.service.execute_read("MATCH ()-[r]->() RETURN count(r) AS cnt", database=database)
        total_nodes = cnt_nodes[0].get("cnt", 0) if cnt_nodes else 0
        total_edges = cnt_edges[0].get("cnt", 0) if cnt_edges else 0

        # Query label distribution
        lbl_dist_q = """
        MATCH (n:KGNode)
        UNWIND labels(n) AS lbl
        WITH lbl, n
        WHERE lbl <> 'KGNode'
        RETURN lbl, count(n) AS cnt
        ORDER BY cnt DESC
        """
        lbl_records = self.service.execute_read(lbl_dist_q, database=database)
        label_counts = {r["lbl"]: r["cnt"] for r in lbl_records}

        # Query relationship distribution
        rel_dist_q = """
        MATCH ()-[r]->()
        RETURN type(r) AS rel, count(r) AS cnt
        ORDER BY cnt DESC
        """
        rel_records = self.service.execute_read(rel_dist_q, database=database)
        rel_counts = {r["rel"]: r["cnt"] for r in rel_records}

        summary = {
            "status": "MIGRATION_COMPLETED",
            "database": database or self.service.database,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_standardized": nodes_standardized,
            "relationships_migrated": migrated_rels,
            "grounded_edges_created": grounded_edges,
            "constraints_applied": schema_res.get("constraints_applied", 0),
            "indexes_applied": schema_res.get("indexes_applied", 0),
            "label_distribution": label_counts,
            "relationship_distribution": rel_counts,
        }
        logger.info(f"Graph migration completed successfully: {total_nodes} nodes, {total_edges} relationships")
        return summary

    @staticmethod
    def _resolve_primary_label(node_type: str, hierarchy_level: str) -> str:
        """Maps node type and hierarchy level to canonical Neo4j label."""
        type_str = (node_type or "").capitalize()
        if type_str in NodeLabels.all_primary_labels():
            return type_str
        if type_str == "Verse":
            return NodeLabels.PASSAGE
        if hierarchy_level == "L0":
            return NodeLabels.LITERATURE
        if hierarchy_level == "L1":
            return NodeLabels.WORK
        if hierarchy_level == "L2":
            return NodeLabels.SECTION
        if hierarchy_level == "L3":
            return NodeLabels.PASSAGE
        if hierarchy_level == "L4":
            return NodeLabels.CONCEPT
        if hierarchy_level == "L5":
            return NodeLabels.ENTITY
        return NodeLabels.ENTITY

    @classmethod
    def get_schema_metadata(cls) -> Dict[str, Any]:
        """Returns static metadata describing the schema contract."""
        return {
            "entity_labels": NodeLabels.all_primary_labels(),
            "base_label": NodeLabels.KGNODE,
            "uniqueness_constraints": [
                {"name": c[0], "label": c[1], "property": c[2]}
                for c in UNIQUENESS_CONSTRAINTS
            ],
            "property_indexes": [
                {"name": i[0], "label": i[1], "property": i[2]}
                for i in PROPERTY_INDEXES
            ],
            "relationship_types": [
                RelTypes.CONTAINS_WORK,
                RelTypes.CONTAINS_SECTION,
                RelTypes.CONTAINS_PASSAGE,
                RelTypes.HAS_WORK,
                RelTypes.HAS_SECTION,
                RelTypes.HAS_PASSAGE,
                RelTypes.ATTESTS_ENTITY,
                RelTypes.ATTESTS_CONCEPT,
                RelTypes.ATTESTS_EVENT,
                RelTypes.MENTIONS,
                RelTypes.DISCUSSES,
                RelTypes.DESCRIBES,
                RelTypes.GROUNDED_IN,
                RelTypes.GROUNDS_IN,
                RelTypes.PRESIDES_OVER,
                RelTypes.OCCURS_IN_HABITAT,
                RelTypes.HAS_HABITAT,
                RelTypes.HAS_URIPPORUL,
                RelTypes.MANIFESTS_SIGNIFIER_FOR,
                RelTypes.INCLUDES_COMPONENT,
                RelTypes.MANIFESTS_AS,
                RelTypes.EVOKES_AFFECT,
                RelTypes.SUPPORTED_BY,
                RelTypes.DERIVED_FROM,
                RelTypes.APPLIES_TO,
                RelTypes.INFERRED_FROM,
                RelTypes.CONTRADICTS,
            ],
            "relationship_tiers": {
                "tier_1_literary_structure": RelTypes.tier_1_literary(),
                "tier_2_semantic_knowledge": RelTypes.tier_2_semantic(),
                "tier_3_contextual_relationships": RelTypes.tier_3_contextual(),
                "tier_4_evidence_grounding": RelTypes.tier_4_evidence(),
                "tier_5_epistemic_reasoning": RelTypes.tier_5_reasoning(),
            },
        }


# Singleton schema manager instance
neo4j_schema_manager = Neo4jSchemaManager()


# ==============================================================================
# CLI Entry Point
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neo4j Knowledge Graph Schema Manager")
    parser.add_argument("--setup", action="store_true", help="Create uniqueness constraints and property indexes")
    parser.add_argument("--verify", action="store_true", help="Inspect active constraints and indexes in Neo4j")
    parser.add_argument("--seed", action="store_true", help="Seed canonical Tamil literary knowledge graph into Neo4j")
    parser.add_argument("--migrate", action="store_true", help="Migrate and normalize existing Neo4j graph into 5-tier canonical schema")
    parser.add_argument("--info", action="store_true", help="Print schema specification metadata")

    args = parser.parse_args()

    if args.info or not (args.setup or args.verify or args.seed or args.migrate):
        print("\n=== Neo4j Knowledge Graph Schema Specification ===")
        print(json.dumps(Neo4jSchemaManager.get_schema_metadata(), indent=2))

    if args.setup:
        print("\n=== Applying Neo4j Schema Constraints & Indexes ===")
        res = neo4j_schema_manager.setup_schema()
        print(json.dumps(res, indent=2))

    if args.migrate:
        print("\n=== Migrating and Normalizing Knowledge Graph in Neo4j ===")
        res = neo4j_schema_manager.migrate_and_normalize_graph()
        print(json.dumps(res, indent=2))

    if args.seed:
        print("\n=== Seeding Canonical Knowledge Graph into Neo4j ===")
        res = neo4j_schema_manager.seed_canonical_schema_graph()
        print(json.dumps(res, indent=2))

    if args.verify:
        print("\n=== Verifying Neo4j Schema Active Constraints & Indexes ===")
        res = neo4j_schema_manager.verify_schema()
        print(json.dumps(res, indent=2))

