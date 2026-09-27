"""
Integration & Unit Test Suite for Strict Neo4j Knowledge Graph Synchronization.

Validates the authoritative flow:
Neo4j Mutation -> Confirmed DB Response -> Fresh Cypher Subgraph -> API Response

Guarantees:
1. Neo4j is always the authoritative source of truth.
2. No optimistic UI or unconfirmed graph updates can succeed if Neo4j is disconnected or fails.
3. Successful mutations immediately return the fresh subgraph re-queried from Neo4j.
4. Connection failures and database errors return proper HTTP error codes (503 / 500) gracefully.
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


# ==============================================================================
# 1. Connectivity & Pre-flight Checks
# ==============================================================================

def test_strict_mutation_aborted_when_neo4j_unavailable(client):
    """
    Verifies that all mutations are strictly aborted (HTTP 503) if Neo4j is unreachable,
    preventing any detached or unconfirmed state.
    """
    with patch("api.routes.kg_routes.neo4j_service.is_connected", return_value=False):
        # Test generic mutate endpoint
        res = client.post("/api/kg/mutate", json={
            "action": "upsert_entity",
            "entity": {"id": "test_node_1", "label": "பரிசோதனை"}
        })
        assert res.status_code == 503
        data = res.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "NEO4J_UNAVAILABLE"
        assert "Neo4j Aura is unreachable" in data["message"]

        # Test convenience entity endpoint
        res2 = client.post("/api/kg/entity", json={
            "id": "test_node_2", "label": "பரிசோதனை 2"
        })
        assert res2.status_code == 503

        # Test convenience relationship endpoint
        res3 = client.post("/api/kg/relationship", json={
            "source_id": "a", "target_id": "b", "relation_type": "RELATED_TO"
        })
        assert res3.status_code == 503


# ==============================================================================
# 2. Validation & Payload Integrity
# ==============================================================================

def test_strict_mutation_invalid_payloads(client):
    """
    Verifies that malformed payloads (missing IDs, labels, or unsupported actions)
    are rejected with HTTP 400 without touching the database.
    """
    with patch("api.routes.kg_routes.neo4j_service.is_connected", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.is_available", return_value=True):

        # Missing action / unrecognized action
        res = client.post("/api/kg/mutate", json={"action": "unknown_action"})
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "INVALID_ACTION"

        # Missing id/label for entity
        res_entity = client.post("/api/kg/entity", json={"category": "Signifier"})
        assert res_entity.status_code == 400
        assert res_entity.get_json()["error"]["code"] == "INVALID_PAYLOAD"

        # Missing source/target for relationship
        res_rel = client.post("/api/kg/relationship", json={"source_id": "node_a"})
        assert res_rel.status_code == 400
        assert res_rel.get_json()["error"]["code"] == "INVALID_PAYLOAD"


# ==============================================================================
# 3. Successful Entity Mutation -> Fresh Subgraph Query
# ==============================================================================

def test_strict_entity_mutation_flow(client):
    """
    Tests the complete strict synchronization flow for an Entity:
    1. neo4j_repository.upsert_entity is called.
    2. Confirmation is returned by Neo4j.
    3. Fresh Cypher subgraph retrieval is executed.
    4. Both the mutation confirmation and the fresh graph are returned to the caller.
    """
    mock_upsert = MagicMock(return_value={
        "id": "tinai_kurinci_test",
        "label": "குறிஞ்சி நிலம்",
        "category": "Signifier",
        "status": "upserted",
    })

    fresh_subgraph_data = {
        "nodes": [
            {"id": "tinai_kurinci_test", "label": "குறிஞ்சி நிலம்", "category": "Signifier", "degree": 1},
            {"id": "seyon_test", "label": "சேயோன்", "category": "Deity", "degree": 1}
        ],
        "relationships": [
            {"id": "r1", "source": "tinai_kurinci_test", "target": "seyon_test", "type": "HAS_DEITY"}
        ],
        "metadata": {
            "query": "",
            "node_count": 2,
            "relationship_count": 1,
            "source": "neo4j_aura",
        }
    }

    mock_retrieve = MagicMock(return_value=fresh_subgraph_data)

    with patch("api.routes.kg_routes.neo4j_service.is_connected", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.is_available", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.upsert_entity", mock_upsert), \
         patch("api.routes.kg_routes.graph_retrieval_service.retrieve_query_subgraph", mock_retrieve):

        res = client.post("/api/kg/entity", json={
            "id": "tinai_kurinci_test",
            "label": "குறிஞ்சி நிலம்",
            "category": "Signifier",
            "tinai": "Kuṟiñci",
            "confidence": 0.98,
        })

        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True

        # Check that upsert was executed in Neo4j with exact parameters
        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args[1]
        assert call_kwargs["entity_id"] == "tinai_kurinci_test"
        assert call_kwargs["label"] == "குறிஞ்சி நிலம்"
        assert call_kwargs["category"] == "Signifier"
        assert call_kwargs["tinai"] == "Kuṟiñci"

        # Check that fresh Cypher subgraph retrieval was executed centered on the seed
        mock_retrieve.assert_called_once()
        retrieve_call = mock_retrieve.call_args[1]
        assert "tinai_kurinci_test" in retrieve_call["query_input"]["seed_ids"]

        # Check authoritative response payload
        assert "nodes" in body
        assert "relationships" in body
        assert "metadata" in body
        assert len(body["nodes"]) == 2
        assert len(body["relationships"]) == 1
        assert body["metadata"]["mutated_seeds"] == ["tinai_kurinci_test"]


# ==============================================================================
# 4. Successful Relationship Mutation -> Fresh Subgraph Query
# ==============================================================================

def test_strict_relationship_mutation_flow(client):
    """
    Tests the complete strict synchronization flow for a Relationship:
    1. neo4j_repository.upsert_relationship is called.
    2. Confirmation is returned by Neo4j.
    3. Fresh Cypher subgraph retrieval is executed for both seed endpoints.
    4. Dual-compatible graph payload is returned.
    """
    mock_upsert_rel = MagicMock(return_value={
        "source": "kurinci",
        "target": "punartal",
        "type": "ASSOCIATED_WITH",
        "confidence": 0.95,
        "status": "upserted",
    })

    fresh_subgraph_data = {
        "nodes": [
            {"id": "kurinci", "label": "குறிஞ்சி"},
            {"id": "punartal", "label": "புணர்தல்"}
        ],
        "relationships": [
            {"id": "rel_k_p", "source": "kurinci", "target": "punartal", "type": "ASSOCIATED_WITH", "confidence": 0.95}
        ],
        "metadata": {
            "query": "",
            "node_count": 2,
            "relationship_count": 1,
            "source": "neo4j_aura",
        }
    }
    mock_retrieve = MagicMock(return_value=fresh_subgraph_data)

    with patch("api.routes.kg_routes.neo4j_service.is_connected", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.is_available", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.upsert_relationship", mock_upsert_rel), \
         patch("api.routes.kg_routes.graph_retrieval_service.retrieve_query_subgraph", mock_retrieve):

        res = client.post("/api/kg/relationship", json={
            "source_id": "kurinci",
            "target_id": "punartal",
            "relation_type": "ASSOCIATED_WITH",
            "confidence": 0.95,
            "validation_level": "corpus_grounded",
        })

        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True

        mock_upsert_rel.assert_called_once()
        rel_kwargs = mock_upsert_rel.call_args[1]
        assert rel_kwargs["source_id"] == "kurinci"
        assert rel_kwargs["target_id"] == "punartal"
        assert rel_kwargs["relation_type"] == "ASSOCIATED_WITH"

        mock_retrieve.assert_called_once()
        seeds = mock_retrieve.call_args[1]["query_input"]["seed_ids"]
        assert "kurinci" in seeds
        assert "punartal" in seeds

        assert body["data"]["mutation"]["status"] == "upserted"
        assert len(body["relationships"]) == 1
        assert body["relationships"][0]["type"] == "ASSOCIATED_WITH"


# ==============================================================================
# 5. Database Failure / Rollback Handling
# ==============================================================================

def test_strict_mutation_handles_database_write_failure(client):
    """
    Verifies that if Neo4j raises an exception during write (e.g., deadlock, timeout, constraint),
    the endpoint returns HTTP 500 with 'NEO4J_MUTATION_FAILED' and no unconfirmed graph state.
    """
    mock_upsert_fail = MagicMock(side_effect=RuntimeError("Neo4j Aura connection dropped mid-transaction"))

    with patch("api.routes.kg_routes.neo4j_service.is_connected", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.is_available", return_value=True), \
         patch("api.routes.kg_routes.neo4j_repository.upsert_entity", mock_upsert_fail):

        res = client.post("/api/kg/mutate", json={
            "action": "upsert_entity",
            "entity": {"id": "fail_node", "label": "தோல்வி"}
        })

        assert res.status_code == 500
        body = res.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "NEO4J_MUTATION_FAILED"
        assert "No changes were applied" in body["message"]
