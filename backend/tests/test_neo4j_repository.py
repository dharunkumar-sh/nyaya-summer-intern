"""
Comprehensive Unit & Integration Test Suite for Neo4jRepository.

Tests:
1. Reusable single upsert methods (Literature, Work, Section, Passage, Entity, Concept, Event, Evidence, Relationship).
2. High-performance batch upsert methods (UNWIND batching in chunks).
3. Retrieval methods (get_passage_by_id, get_connected_entities_and_concepts, get_source_information, traverse_multi_hop, get_evidence_paths).
4. Idempotent execution (repeated ingestion produces 0 duplicate nodes and 0 duplicate relationships).
5. Safe parameterized queries (no string concatenation or SQL/Cypher injection).
6. Live Aura verification (skipped gracefully if cluster unreachable).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from knowledge_graph.neo4j_repository import Neo4jRepository, neo4j_repository
from knowledge_graph.schema import NodeLabels, RelTypes
from services.neo4j_service import Neo4jService, neo4j_service


# ==============================================================================
# 1. Single Entity / Relationship Upsert Tests (Mocked Service)
# ==============================================================================

class TestNeo4jRepositorySingleUpserts:
    """Tests single upsert methods using mocked Neo4jService."""

    @pytest.fixture
    def mock_service(self):
        svc = MagicMock(spec=Neo4jService)
        svc.get_driver.return_value = MagicMock()
        svc.execute_write.return_value = [{"id": "test_id", "label": "test_label"}]
        return svc

    @pytest.fixture
    def repo(self, mock_service):
        return Neo4jRepository(service=mock_service)

    def test_upsert_literature(self, repo, mock_service):
        result = repo.upsert_literature(
            literature_id="lit_sangam",
            name="Sangam Literature",
            period="Classical Sangam",
            total_works=18,
            metadata={"description": "Classical Tamil corpus"},
        )
        assert result["id"] == "test_id"
        assert mock_service.execute_write.called
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Literature {id: $id})" in query
        assert params["id"] == "lit_sangam"
        assert params["name"] == "Sangam Literature"
        assert params["total_works"] == 18

    def test_upsert_work(self, repo, mock_service):
        result = repo.upsert_work(
            work_id="work_tolkappiyam",
            name="Tolkāppiyam",
            literature_id="lit_sangam",
            english_title="Book of Poetics and Grammar",
            sutra_count=1610,
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Work {id: $id})" in query
        assert "MERGE (lit)-[r:HAS_WORK]->(n)" in query
        assert params["id"] == "work_tolkappiyam"
        assert params["literature_id"] == "lit_sangam"

    def test_upsert_section(self, repo, mock_service):
        result = repo.upsert_section(
            section_id="sec_porul",
            name="Poruḷatikāram",
            work_id="work_tolkappiyam",
            atikaram="Poruḷatikāram",
            iyal="Akattiṇaiyiyal",
            sutra_count=664,
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Section {id: $id})" in query
        assert "MERGE (w)-[r:HAS_SECTION]->(n)" in query
        assert params["id"] == "sec_porul"
        assert params["work_id"] == "work_tolkappiyam"

    def test_upsert_passage(self, repo, mock_service):
        result = repo.upsert_passage(
            passage_id="tol_porul_3",
            sutra_number=3,
            text="முதல்கரு உரிப்பொருள் என்ற மூன்றே",
            translation="Mutal, Karu, and Uri are three constituents.",
            tinai="General",
            section_id="sec_porul",
            confidence=1.0,
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Passage {id: $id})" in query
        assert "MERGE (sec)-[r:HAS_PASSAGE]->(n)" in query
        assert params["id"] == "tol_porul_3"
        assert params["sutra_number"] == 3
        assert "முதல்கரு" in params["text"]

    def test_upsert_entity(self, repo, mock_service):
        result = repo.upsert_entity(
            entity_id="entity_ceyon",
            label="Cēyōṉ",
            category="Deity",
            tinai="Kuṟiñci",
            confidence=0.98,
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Entity {id: $id})" in query
        assert params["id"] == "entity_ceyon"
        assert params["category"] == "Deity"
        assert params["tinai"] == "Kuṟiñci"

    def test_upsert_concept(self, repo, mock_service):
        result = repo.upsert_concept(
            concept_id="concept_mutal",
            label="Mutalporuḷ",
            category="EpistemicConstituent",
            description="Space and Time substrate",
            tinai="General",
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Concept {id: $id})" in query
        assert params["id"] == "concept_mutal"
        assert params["label"] == "Mutalporuḷ"

    def test_upsert_event(self, repo, mock_service):
        result = repo.upsert_event(
            event_id="event_punartal",
            label="Puṇartal",
            actor="Lovers",
            action="Union",
            location="Kuṟiñci mountain",
            time_ref="Midnight",
            tinai="Kuṟiñci",
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Event {id: $id})" in query
        assert params["id"] == "event_punartal"
        assert params["actor"] == "Lovers"
        assert params["action"] == "Union"

    def test_upsert_evidence(self, repo, mock_service):
        result = repo.upsert_evidence(
            evidence_id="ev_tol_porul_3_chunk1",
            citation="Tolkāppiyam Poruḷatikāram Sūtra 3",
            text="Mutalkaru uripporuḷ eṉṟa mūṉṟē...",
            passage_id="tol_porul_3",
            confidence=0.95,
        )
        assert result["id"] == "test_id"
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MERGE (n:KGNode:Evidence {id: $id})" in query
        assert "MERGE (n)-[r:SUPPORTED_BY]->(p)" in query
        assert params["id"] == "ev_tol_porul_3_chunk1"
        assert params["passage_id"] == "tol_porul_3"

    def test_upsert_relationship(self, repo, mock_service):
        result = repo.upsert_relationship(
            source_id="tol_porul_3",
            target_id="concept_mutal",
            relation_type="DISCUSSES",
            confidence=0.99,
            validation_level="corpus_grounded",
        )
        assert mock_service.execute_write.called
        call_args = mock_service.execute_write.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MATCH (s:KGNode {id: $source_id})" in query
        assert "MATCH (t:KGNode {id: $target_id})" in query
        assert "MERGE (s)-[r:DISCUSSES]->(t)" in query
        assert params["source_id"] == "tol_porul_3"
        assert params["target_id"] == "concept_mutal"
        assert params["confidence"] == 0.99


# ==============================================================================
# 2. Batch Ingestion Tests (Mocked Service)
# ==============================================================================

class TestNeo4jRepositoryBatchUpserts:
    """Tests high-performance batch operations using UNWIND."""

    @pytest.fixture
    def mock_service(self):
        svc = MagicMock(spec=Neo4jService)
        svc.get_driver.return_value = MagicMock()
        svc.execute_write.return_value = []
        return svc

    @pytest.fixture
    def repo(self, mock_service):
        return Neo4jRepository(service=mock_service)

    def test_batch_upsert_nodes(self, repo, mock_service):
        nodes = [
            {"id": f"entity_{i}", "label": f"Entity {i}", "type": "Entity", "confidence": 0.9}
            for i in range(120)
        ]
        res = repo.batch_upsert_nodes("Entity", nodes, batch_size=50)
        assert res["total_items"] == 120
        assert res["upserted"] == 120
        # 120 items with batch_size 50 -> 3 batches
        assert mock_service.execute_write.call_count == 3
        call_args = mock_service.execute_write.call_args_list[0][0]
        assert "UNWIND $batch AS item" in call_args[0]
        assert "MERGE (n:KGNode:Entity {id: item.id})" in call_args[0]
        assert len(call_args[1]["batch"]) == 50

    def test_batch_upsert_relationships(self, repo, mock_service):
        rels = [
            {"source_id": f"s_{i}", "target_id": f"t_{i}", "relation": "MENTIONS", "confidence": 0.9}
            for i in range(10)
        ] + [
            {"source_id": f"s_{i}", "target_id": f"c_{i}", "relation": "DISCUSSES", "confidence": 0.95}
            for i in range(5)
        ]
        res = repo.batch_upsert_relationships(rels, batch_size=100)
        assert res["total_items"] == 15
        assert res["upserted"] == 15
        # 2 distinct relationship types -> at least 2 queries
        assert mock_service.execute_write.call_count == 2

    def test_batch_upsert_passages(self, repo, mock_service):
        passages = [
            {"id": f"tol_sutra_{i}", "sutra_number": i, "text": f"text {i}", "section_id": "sec_porul"}
            for i in range(5)
        ]
        upserted = repo.batch_upsert_passages(passages)
        assert upserted == 5
        # 1 call for nodes, 1 call for section relationships
        assert mock_service.execute_write.call_count == 2

    def test_batch_upsert_evidence(self, repo, mock_service):
        evidence_items = [
            {"id": f"ev_{i}", "citation": f"Citation {i}", "text": f"Chunk {i}", "passage_id": f"pass_{i}"}
            for i in range(4)
        ]
        upserted = repo.batch_upsert_evidence(evidence_items)
        assert upserted == 4
        # 1 call for nodes, 1 call for SUPPORTED_BY relationships
        assert mock_service.execute_write.call_count == 2


# ==============================================================================
# 3. Query & Retrieval Tests (Mocked Service)
# ==============================================================================

class TestNeo4jRepositoryRetrieval:
    """Tests query and retrieval methods with mocked data."""

    @pytest.fixture
    def mock_service(self):
        svc = MagicMock(spec=Neo4jService)
        svc.get_driver.return_value = MagicMock()
        return svc

    @pytest.fixture
    def repo(self, mock_service):
        return Neo4jRepository(service=mock_service)

    def test_get_passage_by_id_found(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "passage": {
                "id": "tol_porul_3",
                "label": "Sūtra 3",
                "sutra_number": 3,
                "text": "முதல்கரு உரிப்பொருள்...",
                "translation": "Mutal, Karu, Uri...",
                "tinai": "General",
                "hierarchy": {
                    "section": "Poruḷatikāram",
                    "section_id": "sec_porul",
                    "work": "Tolkāppiyam",
                    "work_id": "work_tolkappiyam",
                    "literature": "Sangam Literature",
                    "literature_id": "lit_sangam",
                },
            }
        }]
        res = repo.get_passage_by_id("tol_porul_3")
        assert res is not None
        assert res["id"] == "tol_porul_3"
        assert res["sutra_number"] == 3
        assert res["hierarchy"]["work"] == "Tolkāppiyam"

    def test_get_passage_by_id_not_found(self, repo, mock_service):
        mock_service.execute_read.return_value = []
        res = repo.get_passage_by_id("non_existent_id")
        assert res is None

    def test_get_connected_entities_and_concepts(self, repo, mock_service):
        mock_service.execute_read.return_value = [
            {
                "id": "entity_ceyon",
                "label": "Cēyōṉ",
                "type": "Entity",
                "all_labels": ["KGNode", "Entity"],
                "category": "Deity",
                "tinai": "Kuṟiñci",
                "metadata_json": "{}",
                "relation_type": "MENTIONS",
                "edge_confidence": 0.95,
                "direction": "outgoing",
            },
            {
                "id": "concept_mutal",
                "label": "Mutalporuḷ",
                "type": "Concept",
                "all_labels": ["KGNode", "Concept"],
                "category": "EpistemicTripartite",
                "tinai": "General",
                "metadata_json": "{}",
                "relation_type": "DISCUSSES",
                "edge_confidence": 0.99,
                "direction": "outgoing",
            },
            {
                "id": "event_punartal",
                "label": "Puṇartal",
                "type": "Event",
                "all_labels": ["KGNode", "Event"],
                "category": "PoeticAction",
                "tinai": "Kuṟiñci",
                "metadata_json": "{}",
                "relation_type": "DESCRIBES",
                "edge_confidence": 0.92,
                "direction": "outgoing",
            },
        ]
        res = repo.get_connected_entities_and_concepts("tol_porul_3")
        assert res["passage_id"] == "tol_porul_3"
        assert len(res["entities"]) == 1
        assert res["entities"][0]["label"] == "Cēyōṉ"
        assert len(res["concepts"]) == 1
        assert res["concepts"][0]["label"] == "Mutalporuḷ"
        assert len(res["events"]) == 1
        assert res["events"][0]["label"] == "Puṇartal"
        assert res["total_connected"] == 3

    def test_get_source_information(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "target_node": {"id": "concept_mutal", "label": "Mutalporuḷ", "type": "Concept"},
            "provenance_ancestors": [
                {"id": "tol_porul_3", "label": "Sūtra 3", "type": "Passage", "sutra_number": 3},
                {"id": "sec_porul", "label": "Poruḷatikāram", "type": "Section"},
            ],
            "evidence_chunks": [
                {"id": "ev_1", "citation": "Sūtra 3 chunk", "text": "Mutalkaru..."}
            ],
        }]
        res = repo.get_source_information("concept_mutal")
        assert res["found"] is True
        assert len(res["provenance_chain"]) == 2
        assert len(res["evidence_chunks"]) == 1

    def test_traverse_multi_hop(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "path_nodes": [
                {"id": "ceyon", "label": "Cēyōṉ", "type": "Entity"},
                {"id": "kurinci", "label": "Kuṟiñci", "type": "Concept"},
                {"id": "punartal", "label": "Puṇartal", "type": "Event"},
            ],
            "path_relationships": [
                {"type": "PRESIDES_OVER", "confidence": 0.95},
                {"type": "HAS_URIPPORUL", "confidence": 0.90},
            ],
            "length": 2,
        }]
        paths = repo.traverse_multi_hop("ceyon", max_hops=3)
        assert len(paths) == 1
        p = paths[0]
        assert p["start_id"] == "ceyon"
        assert p["target_id"] == "punartal"
        assert p["length"] == 2
        # Propagated confidence: 0.95 * 0.90 = 0.855
        assert p["propagated_confidence"] == 0.855

    def test_get_evidence_paths(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "ground_id": "tol_porul_3",
            "ground_labels": ["KGNode", "Passage"],
            "nodes": [
                {"id": "tol_porul_3", "label": "Sūtra 3", "type": "Passage"},
                {"id": "concept_mutal", "label": "Mutalporuḷ", "type": "Concept"},
            ],
            "edges": [{"type": "DISCUSSES", "confidence": 0.98}],
            "length": 1,
        }]
        ev_paths = repo.get_evidence_paths("concept_mutal", max_depth=3)
        assert len(ev_paths) == 1
        assert ev_paths[0]["ground_id"] == "tol_porul_3"
        assert ev_paths[0]["ground_type"] == "Passage"
        assert ev_paths[0]["confidence"] == 0.98


# ==============================================================================
# 4. Live Neo4j Aura Integration & Idempotency Tests
# ==============================================================================

class TestNeo4jRepositoryLiveAura:
    """
    Live tests executed against the real Neo4j Aura cluster.
    Validates idempotent execution (zero duplicate nodes or edges on re-run).
    """

    @pytest.fixture(autouse=True)
    def check_aura_reachable(self):
        """Skip live test if Aura cluster cannot be reached."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura cluster unreachable; skipping live integration tests.")

    def test_live_passage_and_hierarchy_lookup(self):
        """Retrieves seeded passage and tests full hierarchy."""
        # Query seeded sūtras
        records = neo4j_service.execute_read(
            "MATCH (p:KGNode:Passage) RETURN p.id AS id ORDER BY p.id LIMIT 1"
        )
        if not records:
            pytest.skip("No seeded passages found in Neo4j Aura.")

        passage_id = records[0]["id"]
        res = neo4j_repository.get_passage_by_id(passage_id)
        assert res is not None
        assert res["id"] == passage_id
        assert "sutra_number" in res or "label" in res

    def test_live_connected_entities_retrieval(self):
        """Retrieves connected entities and concepts for a seeded passage."""
        records = neo4j_service.execute_read(
            "MATCH (p:KGNode:Passage)-[r]-(n:KGNode) RETURN p.id AS id LIMIT 1"
        )
        if not records:
            pytest.skip("No connected passages in Neo4j Aura.")

        passage_id = records[0]["id"]
        connected = neo4j_repository.get_connected_entities_and_concepts(passage_id)
        assert connected["passage_id"] == passage_id
        assert connected["total_connected"] > 0
        assert isinstance(connected["entities"], list)
        assert isinstance(connected["concepts"], list)

    def test_live_multi_hop_traversal(self):
        """Executes multi-hop traversal on live Neo4j Aura."""
        records = neo4j_service.execute_read(
            "MATCH (n:KGNode) WHERE (n)-[*1..2]-() RETURN n.id AS id LIMIT 1"
        )
        if not records:
            pytest.skip("No connected nodes found in Neo4j Aura.")

        node_id = records[0]["id"]
        paths = neo4j_repository.traverse_multi_hop(node_id, max_hops=2)
        assert isinstance(paths, list)
        if paths:
            assert paths[0]["start_id"] == node_id
            assert paths[0]["propagated_confidence"] > 0.0

    def test_idempotent_ingestion_duplicate_prevention(self):
        """
        Ingests the exact same test node and relationship twice.
        Verifies that node count and edge count for the entity do NOT increase.
        """
        test_entity_id = "test_idempotent_flora_kurinci"
        test_concept_id = "test_idempotent_concept_tinai"

        # 1. First Ingestion
        neo4j_repository.upsert_entity(
            entity_id=test_entity_id,
            label="Kuriñcimalar (Test)",
            category="Flora",
            tinai="Kuṟiñci",
            confidence=0.99,
        )
        neo4j_repository.upsert_concept(
            concept_id=test_concept_id,
            label="Kuṟiñci Semiotics (Test)",
            category="Tiṇai",
            tinai="Kuṟiñci",
        )
        neo4j_repository.upsert_relationship(
            source_id=test_entity_id,
            target_id=test_concept_id,
            relation_type="MANIFESTS_SIGNIFIER_FOR",
            confidence=0.95,
        )

        # Count occurrences after first ingestion
        res_nodes_1 = neo4j_service.execute_read(
            "MATCH (n:KGNode {id: $id}) RETURN count(n) AS cnt",
            {"id": test_entity_id},
        )
        res_edges_1 = neo4j_service.execute_read(
            "MATCH (s:KGNode {id: $s})-[r:MANIFESTS_SIGNIFIER_FOR]->(t:KGNode {id: $t}) RETURN count(r) AS cnt",
            {"s": test_entity_id, "t": test_concept_id},
        )
        assert res_nodes_1[0]["cnt"] == 1
        assert res_edges_1[0]["cnt"] == 1

        # 2. Second Ingestion (Exact same items)
        neo4j_repository.upsert_entity(
            entity_id=test_entity_id,
            label="Kuriñcimalar (Test)",
            category="Flora",
            tinai="Kuṟiñci",
            confidence=0.99,
        )
        neo4j_repository.upsert_concept(
            concept_id=test_concept_id,
            label="Kuṟiñci Semiotics (Test)",
            category="Tiṇai",
            tinai="Kuṟiñci",
        )
        neo4j_repository.upsert_relationship(
            source_id=test_entity_id,
            target_id=test_concept_id,
            relation_type="MANIFESTS_SIGNIFIER_FOR",
            confidence=0.95,
        )

        # Verify counts remained strictly 1 (Zero Duplication)
        res_nodes_2 = neo4j_service.execute_read(
            "MATCH (n:KGNode {id: $id}) RETURN count(n) AS cnt",
            {"id": test_entity_id},
        )
        res_edges_2 = neo4j_service.execute_read(
            "MATCH (s:KGNode {id: $s})-[r:MANIFESTS_SIGNIFIER_FOR]->(t:KGNode {id: $t}) RETURN count(r) AS cnt",
            {"s": test_entity_id, "t": test_concept_id},
        )
        assert res_nodes_2[0]["cnt"] == 1, "Duplicate node was created!"
        assert res_edges_2[0]["cnt"] == 1, "Duplicate relationship was created!"

        # Cleanup test entities
        neo4j_service.execute_write(
            "MATCH (n:KGNode) WHERE n.id IN [$e, $c] DETACH DELETE n",
            {"e": test_entity_id, "c": test_concept_id},
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
