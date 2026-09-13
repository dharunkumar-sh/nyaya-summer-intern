"""
Tests for Knowledge Graph API graph retrieval endpoints.
Verifies /api/kg/graph and /api/kg/neo4j/graph endpoints with schema and properties preservation.
"""
import pytest
from app import create_app
from services.neo4j_service import neo4j_service


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_kg_graph_endpoint_schema(client):
    """Verifies /api/kg/graph returns valid structure with nodes and relationships/edges."""
    res = client.get("/api/kg/graph?source=inmemory")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data
    graph_data = data["data"]
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) > 0
    assert len(graph_data["edges"]) > 0

    # Verify node fields
    sample_node = graph_data["nodes"][0]
    assert "id" in sample_node
    assert "label" in sample_node

    # Verify edge fields
    sample_edge = graph_data["edges"][0]
    assert "source" in sample_edge
    assert "target" in sample_edge


def test_kg_neo4j_graph_endpoint(client):
    """Verifies /api/kg/graph?source=neo4j or /api/kg/neo4j/graph when Aura is connected."""
    if not neo4j_service.is_connected():
        pytest.skip("Neo4j Aura not connected in test environment")

    res = client.get("/api/kg/neo4j/graph?limit=50")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    graph_data = data["data"]
    assert "nodes" in graph_data
    assert "relationships" in graph_data
    assert "edges" in graph_data
    assert graph_data["source"] == "neo4j_aura"
    assert len(graph_data["nodes"]) > 0

    # Verify Neo4j node properties and metadata preservation
    node = graph_data["nodes"][0]
    assert "id" in node
    assert "label" in node
    assert "metadata" in node

    # Verify Neo4j relationship properties and metadata preservation
    if graph_data["relationships"]:
        rel = graph_data["relationships"][0]
        assert "id" in rel
        assert "source" in rel
        assert "target" in rel
        assert "type" in rel
        assert "relation" in rel
        assert "confidence" in rel


def test_kg_neo4j_subgraph_endpoint(client):
    """Verifies /api/kg/neo4j/subgraph extracts neighborhood for seed node."""
    if not neo4j_service.is_connected():
        pytest.skip("Neo4j Aura not connected in test environment")

    res = client.get("/api/kg/neo4j/subgraph?center_id=mutalporul&hops=2&limit=30")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    graph_data = data["data"]
    assert graph_data["center_id"] == "mutalporul"
    assert len(graph_data["nodes"]) > 0
    assert any(n["id"] == "mutalporul" for n in graph_data["nodes"])
