"""
Integration tests for all REST API endpoints.
Verifies complete JSON response structure for frontend communication.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_api_query_analyze_valid(client):
    """Tests POST /api/query/analyze with Classical Tamil query."""
    payload = {
        "queryText": "குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?",
        "depth": 3,
        "focus": "Relationship",
    }
    response = client.post("/api/query/analyze", json=payload)
    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data["success"] is True
    data = json_data["data"]

    assert data["detectedTinai"] == "Kuṟiñci"
    assert len(data["evidenceRecords"]) > 0
    assert len(data["reasoningStages"]) == 5
    assert len(data["proofNodes"]) == 7
    assert data["validationResults"]["soundnessScore"] >= 0.95
    assert "tamilAnswer" in data["finalAnswer"]
    assert "englishAnswer" in data["finalAnswer"]
    assert len(data["finalAnswer"]["keySources"]) > 0


def test_api_query_analyze_empty_error(client):
    """Tests POST /api/query/analyze with empty query returns 422 error."""
    payload = {"queryText": "   "}
    response = client.post("/api/query/analyze", json=payload)
    assert response.status_code == 422

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "INVALID_QUERY"


def test_api_query_examples(client):
    """Tests GET /api/query/examples."""
    response = client.get("/api/query/examples")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert len(json_data["data"]) >= 4


def test_api_corpus_info_and_sutras(client):
    """Tests GET /api/corpus/info and GET /api/corpus/sutras."""
    info_resp = client.get("/api/corpus/info")
    assert info_resp.status_code == 200
    info_data = info_resp.get_json()["data"]
    assert "Tolkāppiyam" in info_data["corpus_name"]
    assert info_data["total_sutras_canonical"] == 1610

    sutras_resp = client.get("/api/corpus/sutras")
    assert sutras_resp.status_code == 200
    sutras_data = sutras_resp.get_json()["data"]
    assert len(sutras_data) > 0

    # Specific sūtra lookup
    first_id = sutras_data[0]["id"]
    detail_resp = client.get(f"/api/corpus/sutras/{first_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["data"]["id"] == first_id


def test_api_kg_endpoints(client):
    """Tests GET /api/kg/graph, /api/kg/subgraph, /api/kg/health."""
    graph_resp = client.get("/api/kg/graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.get_json()["data"]
    assert graph_data["total_nodes"] >= 9

    subgraph_resp = client.get("/api/kg/subgraph?centerId=kurinci&depth=2")
    assert subgraph_resp.status_code == 200
    subgraph_data = subgraph_resp.get_json()["data"]
    assert len(subgraph_data["nodes"]) > 0

    health_resp = client.get("/api/kg/health")
    assert health_resp.status_code == 200
    assert health_resp.get_json()["data"]["valid"] is True


def test_api_reasoning_endpoints(client):
    """Tests POST /api/reasoning/deduce and POST /api/reasoning/validate-fallacies."""
    deduce_resp = client.post(
        "/api/reasoning/deduce",
        json={"queryText": "முல்லை ஒழுக்கம்", "tinai": "Mullai"},
    )
    assert deduce_resp.status_code == 200
    deduce_data = deduce_resp.get_json()["data"]
    assert len(deduce_data["reasoningStages"]) == 5
    assert len(deduce_data["proofNodes"]) == 7

    val_resp = client.post(
        "/api/reasoning/validate-fallacies",
        json={"tinai": "Kuṟiñci", "evidenceCount": 5},
    )
    assert val_resp.status_code == 200
    val_data = val_resp.get_json()["data"]
    assert val_data["soundnessScore"] >= 0.95
    assert len(val_data["checks"]) == 5


def test_api_analytics_endpoints(client):
    """Tests GET /api/analytics/benchmark."""
    resp = client.get("/api/analytics/benchmark")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["corpus"]["total_sutras"] == 1610
    assert data["latency"]["average_inference_ms"] > 0
