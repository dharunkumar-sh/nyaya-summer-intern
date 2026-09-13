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
# 2. Canonical Relationship Types
# ==============================================================================

class RelTypes:
    """Controlled relationship vocabulary grounded in Tolkāppiyam semiotics and Nyāya deduction."""

    # Structural Containment Hierarchy
    HAS_WORK = "HAS_WORK"            # Literature -> Work
    HAS_SECTION = "HAS_SECTION"      # Work -> Section
    HAS_PASSAGE = "HAS_PASSAGE"      # Section -> Passage

    # Passage-to-Knowledge Grounding
    MENTIONS = "MENTIONS"            # Passage -> Entity
    DISCUSSES = "DISCUSSES"          # Passage -> Concept
    DESCRIBES = "DESCRIBES"          # Passage -> Event
    DEPICTS_EVENT = "DESCRIBES"      # Alias for DESCRIBES (Passage -> Event)
    BELONGS_TO_CATEGORY = "BELONGS_TO_CATEGORY"  # Passage -> Concept (Category)
    GROUNDS_IN_ONTOLOGY = "GROUNDS_IN_ONTOLOGY"  # Passage/Concept -> Ontology Concept

    # Domain Semiotic Relationships (actual Tolkāppiyam Tiṇai model)
    GROUNDS_IN = "GROUNDS_IN"        # Concept -> Concept (e.g. Mutalporuḷ -> Uripporuḷ)
    PRESIDES_OVER = "PRESIDES_OVER"  # Entity -> Entity (e.g. Cēyōṉ -> Kuṟiñci)
    HAS_URIPPORUL = "HAS_URIPPORUL"  # Entity -> Event (e.g. Kuṟiñci -> Puṇartal)
    HAS_HABITAT = "HAS_HABITAT"      # Concept (Tiṇai) -> Entity (Landscape/Habitat)
    MANIFESTS_SIGNIFIER_FOR = "MANIFESTS_SIGNIFIER_FOR"  # Entity -> Concept
    INCLUDES_COMPONENT = "INCLUDES_COMPONENT"            # Concept -> Entity (Karupporuḷ -> Vēṅkai)
    MANIFESTS_AS = "MANIFESTS_AS"    # Event -> Concept (Puṇartal -> Meyppāṭu)

    # Epistemic Reasoning Pipeline Relationships
    SUPPORTED_BY = "SUPPORTED_BY"    # Premise/Rule -> Evidence / Passage
    DERIVED_FROM = "DERIVED_FROM"    # Conclusion -> Premise / Rule, Premise -> Passage
    CONTRADICTS = "CONTRADICTS"      # Hetvābhāsa fallacy detection
    SUB_SUMES = "SUB_SUMES"          # Upanaya inference application

    # Mapping from legacy or raw relation names to canonical uppercase relationships
    RELATION_MAP = {
        "contains_work": HAS_WORK,
        "contains_section": HAS_SECTION,
        "contains_passage": HAS_PASSAGE,
        "mentions": MENTIONS,
        "mentions_entity": MENTIONS,
        "instantiates_entity": MENTIONS,
        "discusses": DISCUSSES,
        "exposes_concept": DISCUSSES,
        "describes": DESCRIBES,
        "describes_event": DESCRIBES,
        "depicts_event": DESCRIBES,
        "depictsevent": DESCRIBES,
        "belongs_to_category": BELONGS_TO_CATEGORY,
        "belongstocategory": BELONGS_TO_CATEGORY,
        "grounds_in_ontology": GROUNDS_IN_ONTOLOGY,
        "groundsinontology": GROUNDS_IN_ONTOLOGY,
        "supported_by": SUPPORTED_BY,
        "grounds_deduction": SUPPORTED_BY,
        "derived_from": DERIVED_FROM,
        "groundsin": GROUNDS_IN,
        "grounds_in": GROUNDS_IN,
        "consistsof": GROUNDS_IN,
        "presidesover": PRESIDES_OVER,
        "presides_over": PRESIDES_OVER,
        "hasuripporul": HAS_URIPPORUL,
        "has_uripporul": HAS_URIPPORUL,
        "hashabitat": HAS_HABITAT,
        "has_habitat": HAS_HABITAT,
        "manifestssignifierfor": MANIFESTS_SIGNIFIER_FOR,
        "manifests_signifier_for": MANIFESTS_SIGNIFIER_FOR,
        "includescomponent": INCLUDES_COMPONENT,
        "includes_component": INCLUDES_COMPONENT,
        "manifestsas": MANIFESTS_AS,
        "manifests_as": MANIFESTS_AS,
        "evokesaffect": MANIFESTS_AS,
        "evokes_affect": MANIFESTS_AS,
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
    ("index_kgnode_type", NodeLabels.KGNODE, "type"),
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
                RelTypes.HAS_WORK,
                RelTypes.HAS_SECTION,
                RelTypes.HAS_PASSAGE,
                RelTypes.MENTIONS,
                RelTypes.DISCUSSES,
                RelTypes.DESCRIBES,
                RelTypes.GROUNDS_IN,
                RelTypes.PRESIDES_OVER,
                RelTypes.HAS_URIPPORUL,
                RelTypes.MANIFESTS_SIGNIFIER_FOR,
                RelTypes.INCLUDES_COMPONENT,
                RelTypes.MANIFESTS_AS,
                RelTypes.SUPPORTED_BY,
                RelTypes.DERIVED_FROM,
            ],
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
    parser.add_argument("--info", action="store_true", help="Print schema specification metadata")

    args = parser.parse_args()

    if args.info or not (args.setup or args.verify or args.seed):
        print("\n=== Neo4j Knowledge Graph Schema Specification ===")
        print(json.dumps(Neo4jSchemaManager.get_schema_metadata(), indent=2))

    if args.setup:
        print("\n=== Applying Neo4j Schema Constraints & Indexes ===")
        res = neo4j_schema_manager.setup_schema()
        print(json.dumps(res, indent=2))

    if args.seed:
        print("\n=== Seeding Canonical Knowledge Graph into Neo4j ===")
        res = neo4j_schema_manager.seed_canonical_schema_graph()
        print(json.dumps(res, indent=2))

    if args.verify:
        print("\n=== Verifying Neo4j Schema Active Constraints & Indexes ===")
        res = neo4j_schema_manager.verify_schema()
        print(json.dumps(res, indent=2))
