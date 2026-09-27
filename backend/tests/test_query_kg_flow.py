"""
Integration and dynamic query Knowledge Graph retrieval test suite.
Verifies the complete flow:
User Query -> Flask API -> Entity/Seed Resolution -> Neo4j Subgraph / In-Memory -> Bounded Response Schema.
Ensures zero mock fallbacks for unmatched queries.
"""
import pytest
from app import create_app
from services.graph_retrieval_service import graph_retrieval_service


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_service_retrieval_matched_entity():
    """Verify that querying a known Tolkāppiyam concept retrieves relevant nodes and metadata."""
    res = graph_retrieval_service.retrieve_query_subgraph(
        query_input={"query": "குறிஞ்சி நிலம் மற்றும் புணர்தல் ஒழுக்கம்"},
        max_hops=2,
        limit=50,
    )
    assert isinstance(res, dict)
    assert "nodes" in res
    assert "relationships" in res
    assert "metadata" in res
    assert res["metadata"]["node_count"] == len(res["nodes"])
    assert res["metadata"]["relationship_count"] == len(res["relationships"])
    assert len(res["nodes"]) > 0
    # Check that returned nodes are relevant to kurinci/punartal
    node_names = [n.get("id", "").lower() for n in res["nodes"]]
    assert any("kurinci" in n or "punartal" in n or "akam" in n or "tinai" in n for n in node_names)


def test_service_retrieval_unmatched_query_empty_result():
    """Verify that an arbitrary unmatched query returns an empty result without fallback mock nodes."""
    res = graph_retrieval_service.retrieve_query_subgraph(
        query_input={"query": "xyzrandomnonexistentquery12345"},
        max_hops=2,
        limit=50,
    )
    assert isinstance(res, dict)
    assert res["nodes"] == []
    assert res["relationships"] == []
    assert res["metadata"]["node_count"] == 0
    assert res["metadata"]["relationship_count"] == 0
    # Ensure no fallback to mutalporul / uriporul occurred
    assert res.get("seed_ids") == []


def test_api_kg_query_post_endpoint(client):
    """Verify POST /api/kg/query dynamic retrieval endpoint adheres to the required response schema."""
    payload = {
        "query": "முல்லை நிலம் மாயோன் தெய்வம்",
        "hops": 2,
        "limit": 50,
    }
    response = client.post("/api/kg/query", json=payload)
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    data = body["data"]

    # Verify top-level structure matches the exact requested schema
    assert "nodes" in body
    assert "relationships" in body
    assert "metadata" in body
    assert body["metadata"]["node_count"] == len(body["nodes"])
    assert body["metadata"]["relationship_count"] == len(body["relationships"])

    # Verify nested data structure
    assert "nodes" in data
    assert "relationships" in data
    assert "metadata" in data
    assert "query" in data["metadata"]
    assert "node_count" in data["metadata"]
    assert "relationship_count" in data["metadata"]

    assert data["metadata"]["node_count"] == len(data["nodes"])
    assert data["metadata"]["relationship_count"] == len(data["relationships"])
    assert len(data["nodes"]) > 0


def test_api_kg_query_get_endpoint(client):
    """Verify GET /api/kg/query endpoint with query parameters."""
    response = client.get("/api/kg/query?query=kurinci&hops=1&limit=25")
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    data = body["data"]
    assert "nodes" in data
    assert "relationships" in data
    assert "metadata" in data
    assert data["metadata"]["node_count"] == len(data["nodes"])


def test_api_kg_query_empty_query_returns_empty_graph(client):
    """Verify that an unknown query via API returns empty graph without mock injection."""
    response = client.post("/api/kg/query", json={"query": "9876543210unknownterms"})
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["nodes"] == []
    assert data["relationships"] == []
    assert data["metadata"]["node_count"] == 0
    assert data["metadata"]["relationship_count"] == 0


def test_api_kg_query_subgraph_backward_compatible(client):
    """Verify that /api/kg/query-subgraph functions identically and returns correct schema."""
    response = client.post("/api/kg/query-subgraph", json={"query": "marutam"})
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    data = body["data"]
    assert "nodes" in data
    assert "relationships" in data
    assert "metadata" in data
    assert data["metadata"]["node_count"] == len(data["nodes"])


def test_query_driven_kg_retrieval_with_pipeline_evidence(client):
    """
    Verify that providing retrieval pipeline entities, concepts, and evidence
    directly drives the Neo4j subgraph and populates the required metadata fields:
    - current query
    - number of retrieved nodes
    - number of relationships
    - relevant literary sources
    - evidence count
    """
    payload = {
        "query": "குறிஞ்சி நிலத்தின் புணர்தல் ஒழுக்கம்",
        "entities": ["ceyon", "kurinci"],
        "concepts": ["punartal", "akam"],
        "passages": ["tol-porul-akam-003", "tol-porul-akam-005"],
        "evidence": [
            {
                "id": "tol-porul-akam-003",
                "source": "Tolkāppiyam, Poruḷatikāram, Akattiṇaiyiyal, Sūtra 3",
                "entities": ["kurinci", "punartal"],
                "concepts": ["akam"],
            },
            {
                "id": "tol-porul-akam-005",
                "source": "Tolkāppiyam, Poruḷatikāram, Akattiṇaiyiyal, Sūtra 5",
                "entities": ["ceyon"],
                "concepts": ["deity"],
            }
        ],
        "hops": 2,
        "limit": 50,
    }
    response = client.post("/api/kg/query", json=payload)
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    data = body["data"]
    meta = data["metadata"]

    # Verify all 5 required metadata fields are present and accurate
    assert meta["query"] == "குறிஞ்சி நிலத்தின் புணர்தல் ஒழுக்கம்"
    assert meta["node_count"] == len(data["nodes"])
    assert meta["relationship_count"] == len(data["relationships"])
    assert "literary_sources" in meta
    assert isinstance(meta["literary_sources"], list)
    assert len(meta["literary_sources"]) > 0
    assert any("Tolkāppiyam" in src or "Akattiṇaiyiyal" in src for src in meta["literary_sources"])
    assert meta["evidence_count"] >= 2
    assert len(data["nodes"]) > 0


def test_distinct_queries_yield_distinct_subgraphs(client):
    """
    Verify that Query A and Query B return distinct subgraphs without carrying over
    unrelated nodes from Query A into Query B.
    Query A (Kuṟiñci) -> Subgraph A (contains kurinci, does not contain neytal)
    Query B (Neytal)  -> Subgraph B (contains neytal, does not contain kurinci)
    """
    # Query A: Kuṟiñci
    res_a = client.post("/api/kg/query", json={"query": "குறிஞ்சி நிலம் புணர்தல்", "hops": 1})
    assert res_a.status_code == 200
    nodes_a = {n["id"] for n in res_a.get_json()["data"]["nodes"]}
    assert "kurinci" in nodes_a
    assert "neytal" not in nodes_a

    # Query B: Neytal
    res_b = client.post("/api/kg/query", json={"query": "நெய்தல் நிலம் இரங்கல்", "hops": 1})
    assert res_b.status_code == 200
    nodes_b = {n["id"] for n in res_b.get_json()["data"]["nodes"]}
    assert "neytal" in nodes_b
    assert "kurinci" not in nodes_b


def test_query_execution_does_not_mutate_neo4j(client):
    """
    Verify that querying does not execute write operations on Neo4j Aura.
    Query results represent a read-only query-specific view from existing Neo4j data.
    """
    from unittest.mock import patch
    with patch("services.neo4j_service.neo4j_service.execute_write") as mock_write:
        response = client.post("/api/kg/query", json={"query": "முல்லை நிலம்"})
        assert response.status_code == 200
        mock_write.assert_not_called()

