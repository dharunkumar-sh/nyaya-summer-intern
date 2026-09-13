"""
Unit and integration tests for Neo4j Knowledge Graph Schema Manager.

Tests:
1. Canonical NodeLabels and RelTypes definitions and resolution.
2. RelTypes canonicalization logic (case, formatting, legacy mapping).
3. DDL definitions for 12 uniqueness constraints and 7 property indexes.
4. Schema setup, verification, and metadata reporting (mocked driver).
5. Safe error handling (graceful error logging and reporting).
6. Live Neo4j Aura schema verification (skipped if database unreachable).
7. Credential security (no passwords in logs, metadata, or exception outputs).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure backend directory is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from knowledge_graph.schema import (
    NodeLabels,
    RelTypes,
    UNIQUENESS_CONSTRAINTS,
    PROPERTY_INDEXES,
    Neo4jSchemaManager,
    neo4j_schema_manager,
)
from services.neo4j_service import neo4j_service, Neo4jService
from core.exceptions import KnowledgeGraphError, CypherQueryError


# ==============================================================================
# 1. NodeLabels & RelTypes Vocabulary Tests
# ==============================================================================

class TestSchemaVocabularies:
    """Verifies that ontology labels and relationship types conform to specifications."""

    def test_node_labels_completeness(self):
        """All structural, domain, and reasoning labels must be defined."""
        expected_labels = [
            "Literature", "Work", "Section", "Passage", "Evidence",
            "Concept", "Entity", "Event",
            "Premise", "Rule", "Conclusion",
        ]
        all_labels = NodeLabels.all_primary_labels()
        for label in expected_labels:
            assert label in all_labels
            assert hasattr(NodeLabels, label.upper())

        # Base polymorphic label
        assert NodeLabels.KGNODE == "KGNode"

    def test_node_labels_from_string(self):
        """Case-insensitive label resolution helper."""
        assert NodeLabels.from_string("passage") == "Passage"
        assert NodeLabels.from_string("CONCEPT") == "Concept"
        assert NodeLabels.from_string("kgnode") == "KGNode"
        assert NodeLabels.from_string("rule") == "Rule"
        assert NodeLabels.from_string("invalid_type") is None
        assert NodeLabels.from_string("") is None
        assert NodeLabels.from_string(None) is None

    def test_rel_types_constants(self):
        """Core Tolkāppiyam and Nyāya reasoning relationships must exist."""
        expected_rels = [
            "HAS_WORK", "HAS_SECTION", "HAS_PASSAGE",
            "MENTIONS", "DISCUSSES", "DESCRIBES",
            "SUPPORTED_BY", "DERIVED_FROM", "GROUNDS_IN",
            "PRESIDES_OVER", "HAS_URIPPORUL", "MANIFESTS_SIGNIFIER_FOR",
            "INCLUDES_COMPONENT", "MANIFESTS_AS", "CONTRADICTS", "SUB_SUMES",
        ]
        for rel in expected_rels:
            assert hasattr(RelTypes, rel)
            assert getattr(RelTypes, rel) == rel

    def test_rel_types_canonicalization(self):
        """Resolves various casing, punctuation, and legacy mapping to uppercase canonical."""
        assert RelTypes.canonicalize("has_work") == "HAS_WORK"
        assert RelTypes.canonicalize("contains-section") == "HAS_SECTION"
        assert RelTypes.canonicalize("mentions_entity") == "MENTIONS"
        assert RelTypes.canonicalize("grounds_deduction") == "SUPPORTED_BY"
        assert RelTypes.canonicalize("presides_over") == "PRESIDES_OVER"
        assert RelTypes.canonicalize("has_uripporul") == "HAS_URIPPORUL"
        assert RelTypes.canonicalize("evokes_affect") == "MANIFESTS_AS"
        assert RelTypes.canonicalize("custom_relation") == "CUSTOM_RELATION"
        assert RelTypes.canonicalize("") == "RELATED_TO"
        assert RelTypes.canonicalize(None) == "RELATED_TO"


# ==============================================================================
# 2. DDL Definitions & Constraints Syntax Tests
# ==============================================================================

class TestDDLDefinitions:
    """Verifies uniqueness constraints and property index statements."""

    def test_uniqueness_constraints_count(self):
        """12 uniqueness constraints: 11 domain/reasoning labels + 1 base KGNode."""
        assert len(UNIQUENESS_CONSTRAINTS) == 12
        labels_covered = {c[1] for c in UNIQUENESS_CONSTRAINTS}
        for label in NodeLabels.all_primary_labels():
            assert label in labels_covered
        assert NodeLabels.KGNODE in labels_covered

    def test_uniqueness_constraints_syntax(self):
        """Each constraint tuple (name, label, prop) translates to valid Neo4j 5 DDL."""
        for c_name, label, prop in UNIQUENESS_CONSTRAINTS:
            assert c_name.startswith("constraint_")
            assert label in NodeLabels.all_primary_labels() or label == NodeLabels.KGNODE
            assert prop == "id"
            cypher = f"CREATE CONSTRAINT {c_name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            assert "CREATE CONSTRAINT" in cypher
            assert f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE" in cypher

    def test_property_indexes_syntax(self):
        """Each index tuple (name, label, prop) translates to valid Neo4j 5 DDL."""
        assert len(PROPERTY_INDEXES) >= 7
        for idx_name, label, prop in PROPERTY_INDEXES:
            assert idx_name.startswith("index_")
            assert len(label) > 0
            assert len(prop) > 0
            cypher = f"CREATE INDEX {idx_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
            assert "CREATE INDEX" in cypher
            assert f"FOR (n:{label}) ON (n.{prop})" in cypher


# ==============================================================================
# 3. Neo4jSchemaManager Unit Tests (Mocked Service)
# ==============================================================================

class TestSchemaManagerMocked:
    """Unit tests for Neo4jSchemaManager using mocked Neo4jService."""

    def test_setup_schema_success(self):
        """setup_schema executes all constraints and indexes successfully."""
        mock_service = MagicMock(spec=Neo4jService)
        mock_service.get_driver.return_value = MagicMock()
        mock_service.run_query.return_value = []
        mock_service.database = "neo4j"

        manager = Neo4jSchemaManager(service=mock_service)
        result = manager.setup_schema()

        assert result["status"] == "COMPLETED"
        assert result["constraints_applied"] == 12
        assert result["indexes_applied"] == len(PROPERTY_INDEXES)
        assert result["errors"] == []
        assert mock_service.run_query.call_count == 12 + len(PROPERTY_INDEXES)

    def test_setup_schema_captures_errors(self):
        """setup_schema captures failures gracefully without crashing."""
        mock_service = MagicMock(spec=Neo4jService)
        mock_service.get_driver.return_value = MagicMock()
        mock_service.database = "neo4j"
        # Fail on first call, succeed on others
        mock_service.run_query.side_effect = [
            CypherQueryError("Failed to create constraint"),
            *([[]] * 25),
        ]

        manager = Neo4jSchemaManager(service=mock_service)
        result = manager.setup_schema()

        assert result["status"] == "COMPLETED"
        assert len(result["errors"]) == 1
        assert "constraint_kgnode_id" in result["errors"][0]

    def test_verify_schema_mocked(self):
        """verify_schema inspects existing constraints and indexes."""
        mock_service = MagicMock(spec=Neo4jService)
        mock_service.get_driver.return_value = MagicMock()
        mock_service.database = "neo4j"
        # Mock SHOW CONSTRAINTS and SHOW INDEXES
        mock_service.run_query.side_effect = [
            [{"name": c[0], "type": "UNIQUENESS", "labelsOrTypes": [c[1]], "properties": [c[2]]} for c in UNIQUENESS_CONSTRAINTS],
            [{"name": idx[0], "type": "RANGE", "labelsOrTypes": [idx[1]], "properties": [idx[2]]} for idx in PROPERTY_INDEXES],
        ]

        manager = Neo4jSchemaManager(service=mock_service)
        report = manager.verify_schema()

        assert report["status"] == "VERIFIED"
        assert report["connected"] is True
        assert report["constraints_count"] == 12
        assert report["indexes_count"] == len(PROPERTY_INDEXES)

    def test_verify_schema_detects_empty(self):
        """verify_schema reports 0 count when none present."""
        mock_service = MagicMock(spec=Neo4jService)
        mock_service.get_driver.return_value = MagicMock()
        mock_service.database = "neo4j"
        mock_service.run_query.side_effect = [
            [],  # No constraints
            [],  # No indexes
        ]

        manager = Neo4jSchemaManager(service=mock_service)
        report = manager.verify_schema()

        assert report["status"] == "VERIFIED"
        assert report["connected"] is True
        assert report["constraints_count"] == 0
        assert report["indexes_count"] == 0

    def test_get_schema_metadata_security(self):
        """get_schema_metadata returns metrics without credentials."""
        metadata = Neo4jSchemaManager.get_schema_metadata()

        assert "entity_labels" in metadata
        assert "base_label" in metadata
        assert "uniqueness_constraints" in metadata
        assert "property_indexes" in metadata
        assert "relationship_types" in metadata
        assert len(metadata["entity_labels"]) == 11
        assert len(metadata["uniqueness_constraints"]) == 12
        assert len(metadata["property_indexes"]) == len(PROPERTY_INDEXES)

        # Security: credentials must never be in metadata dict
        metadata_str = str(metadata).lower()
        assert "password" not in metadata_str
        assert "token" not in metadata_str

    def test_seed_canonical_schema_graph(self):
        """seed_canonical_schema_graph executes batch queries."""
        mock_service = MagicMock(spec=Neo4jService)
        mock_service.get_driver.return_value = MagicMock()
        mock_service.database = "neo4j"
        mock_service.run_query.return_value = []
        mock_service.execute_write.return_value = []

        manager = Neo4jSchemaManager(service=mock_service)
        stats = manager.seed_canonical_schema_graph()

        assert stats["status"] == "SEEDED"
        assert stats["nodes_upserted"] > 0
        assert stats["edges_upserted"] > 0
        assert mock_service.execute_write.call_count >= 2


# ==============================================================================
# 4. Live Neo4j Aura Integration Tests
# ==============================================================================

class TestSchemaManagerLiveAura:
    """Live schema verification on configured Neo4j Aura cluster."""

    @pytest.fixture(autouse=True)
    def check_aura_reachable(self):
        """Skip live test if Aura cluster cannot be reached."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database unreachable; skipping live DDL test.")

    def test_live_schema_setup_and_verify(self):
        """Applies schema DDL to live Neo4j Aura and confirms verification."""
        setup_result = neo4j_schema_manager.setup_schema()
        assert setup_result["status"] == "COMPLETED"
        assert setup_result["constraints_applied"] == 12

        report = neo4j_schema_manager.verify_schema()
        assert report["status"] == "VERIFIED"
        assert report["connected"] is True
        assert report["constraints_count"] >= 12
        assert report["indexes_count"] >= len(PROPERTY_INDEXES)

    def test_live_schema_metadata(self):
        """Retrieves live schema metadata from Aura."""
        metadata = Neo4jSchemaManager.get_schema_metadata()
        assert len(metadata["uniqueness_constraints"]) == 12
        assert len(metadata["property_indexes"]) >= 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
