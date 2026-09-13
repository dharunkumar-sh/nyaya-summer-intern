"""
Comprehensive test suite verifying all Knowledge Graph, Corpus, Retrieval,
and Reasoning Flask REST API endpoints.

Tests:
1.  Health checks (GET /api/health, GET /api/health/neo4j) ensuring no leaked credentials.
2.  Graph statistics (GET /api/kg/statistics).
3.  Literature and works endpoints (GET /api/corpus/literature, GET /api/corpus/works, GET /api/corpus/works/<id>).
4.  Sections and passages endpoints (GET /api/corpus/sections, GET /api/corpus/passages, GET /api/corpus/passages/<id>).
5.  Multi-hop graph traversal (POST /api/kg/traverse) with depth clamping and validation.
6.  Semantic vector search (POST /api/retrieval/semantic) with query length and top-k limits.
7.  3-channel Hybrid RAG retrieval (POST /api/retrieval/hybrid-rag) with evidence ranking.
8.  Nyāya Pañcāvayava deduction (POST /api/reasoning/deduce).
9.  Graphical proof trace (POST /api/reasoning/proof-trace) with insufficient evidence handling.
10. Final evidence-grounded answers (POST /api/reasoning/answer) with error handling.
"""
import sys
import pathlib
import pytest

backend = str(pathlib.Path(__file__).resolve().parent.parent)
if backend not in sys.path:
    sys.path.insert(0, backend)

from app import app


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# 1. Health Endpoints
# ---------------------------------------------------------------------------

def test_health_endpoints(client):
    """Verifies /api/health and /api/health/neo4j."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "HEALTHY"
    assert "corpus" in data["data"]
    assert "neo4j" in data["data"]

    # Check that database password is not exposed in payload
    res_neo4j = client.get("/api/health/neo4j")
    assert res_neo4j.status_code in [200, 503]
    body_str = res_neo4j.get_data(as_text=True)
    assert "password" not in body_str.lower()
    assert "bolt://" not in body_str.lower() or "@" not in body_str


# ---------------------------------------------------------------------------
# 2. Knowledge Graph Statistics
# ---------------------------------------------------------------------------

def test_kg_statistics_endpoint(client):
    """Verifies GET /api/kg/statistics returns graph metrics and schema info."""
    res = client.get("/api/kg/statistics")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert "total_nodes" in data
    assert "total_edges" in data
    assert "hierarchy_distribution" in data
    assert "categories" in data
    assert data["total_nodes"] > 0


# ---------------------------------------------------------------------------
# 3. Literature and Works Endpoints
# ---------------------------------------------------------------------------

def test_literature_and_works_endpoints(client):
    """Verifies literature (L0) and works (L1) endpoints."""
    # L0 Literature
    res_lit = client.get("/api/corpus/literature")
    assert res_lit.status_code == 200
    lit_data = res_lit.get_json()["data"]
    assert lit_data["hierarchy_level"] == "L0"
    assert "Tolkāppiyam" in lit_data["primary_treatise"]

    # L1 Works list
    res_works = client.get("/api/corpus/works")
    assert res_works.status_code == 200
    works = res_works.get_json()["data"]
    assert len(works) >= 1
    assert works[0]["id"] == "tolkappiyam"

    # L1 Single Work detail
    res_work = client.get("/api/corpus/works/tolkappiyam")
    assert res_work.status_code == 200
    assert "Tolkāppiyam" in res_work.get_json()["data"]["name"]

    # L1 Invalid work 404
    res_404 = client.get("/api/corpus/works/unknown-treatise-xyz")
    assert res_404.status_code == 404
    assert res_404.get_json()["success"] is False


# ---------------------------------------------------------------------------
# 4. Sections and Passages Endpoints
# ---------------------------------------------------------------------------

def test_sections_and_passages_endpoints(client):
    """Verifies sections (L2) and passages (L3) endpoints with pagination and filtering."""
    # L2 Sections list
    res_sec = client.get("/api/corpus/sections")
    assert res_sec.status_code == 200
    sections = res_sec.get_json()["data"]
    assert len(sections) >= 1

    # L3 Passages paginated list
    res_pass = client.get("/api/corpus/passages?page=1&page_size=5")
    assert res_pass.status_code == 200
    pass_payload = res_pass.get_json()
    assert pass_payload["success"] is True
    assert len(pass_payload["data"]) <= 5
    assert pass_payload["meta"]["page"] == 1
    assert pass_payload["meta"]["total"] >= 1

    # L3 Specific Passage
    res_single = client.get("/api/corpus/passages/tol-porul-akam-003")
    assert res_single.status_code == 200
    single_data = res_single.get_json()["data"]
    assert single_data["id"] == "tol-porul-akam-003"
    assert "முதல்கரு" in single_data.get("tamil_text", "") or "Mutalporuḷ" in single_data.get("english_translation", "")

    # L3 Non-existent passage 404
    res_pass_404 = client.get("/api/corpus/passages/tol-non-existent-999")
    assert res_pass_404.status_code == 404
    assert res_pass_404.get_json()["success"] is False


# ---------------------------------------------------------------------------
# 5. Multi-Hop Graph Traversal
# ---------------------------------------------------------------------------

def test_graph_traversal_endpoint(client):
    """Verifies POST /api/kg/traverse with depth enforcement and seed validation."""
    # Valid traversal
    res_valid = client.post(
        "/api/kg/traverse",
        json={"seed_ids": ["mutalporul"], "depth": 2, "limit": 50},
    )
    assert res_valid.status_code == 200
    t_data = res_valid.get_json()["data"]
    assert t_data["depth"] == 2
    assert "nodes" in t_data
    assert "relationships" in t_data
    assert len(t_data["nodes"]) >= 1

    # Depth clamping (depth=10 clamped to 5)
    res_clamped = client.post(
        "/api/kg/traverse",
        json={"seed_ids": ["mutalporul"], "depth": 10},
    )
    assert res_clamped.status_code == 200
    assert res_clamped.get_json()["data"]["depth"] == 5

    # Missing seeds 400 error
    res_bad = client.post("/api/kg/traverse", json={"seed_ids": []})
    assert res_bad.status_code == 400
    assert res_bad.get_json()["success"] is False


# ---------------------------------------------------------------------------
# 6. Semantic Vector Search
# ---------------------------------------------------------------------------

def test_semantic_search_endpoint(client):
    """Verifies POST /api/retrieval/semantic with query bounds validation."""
    # Valid semantic search
    res = client.post(
        "/api/retrieval/semantic",
        json={"query": "குறிஞ்சி நிலம் மலை", "top_k": 3},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    assert "results" in payload["data"]

    # Empty query 400 error
    res_empty = client.post("/api/retrieval/semantic", json={"query": ""})
    assert res_empty.status_code == 400

    # Query too long (>500 chars) 400 error
    res_long = client.post("/api/retrieval/semantic", json={"query": "a" * 501})
    assert res_long.status_code == 400
    assert res_long.get_json()["error_code"] == "QUERY_TOO_LONG"


# ---------------------------------------------------------------------------
# 7. 3-Channel Hybrid RAG Retrieval
# ---------------------------------------------------------------------------

def test_hybrid_rag_retrieval_endpoint(client):
    """Verifies POST /api/retrieval/hybrid-rag executes 3-channel retrieval."""
    res = client.post(
        "/api/retrieval/hybrid-rag",
        json={"query": "குறிஞ்சி நிலத்தின் முதற்பொருள்", "top_k": 3},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    col = payload["data"]
    assert "items" in col
    assert len(col["items"]) >= 1
    # Check evidence ranking components exist on top item
    top_item = col["items"][0]
    assert "score_components" in top_item
    assert "relevance_score" in top_item
    assert "badge_info" in top_item


# ---------------------------------------------------------------------------
# 8. Reasoning Pañcāvayava Deduction
# ---------------------------------------------------------------------------

def test_reasoning_deduce_endpoint(client):
    """Verifies POST /api/reasoning/deduce synthesizes 5 stages and proof trace."""
    res = client.post(
        "/api/reasoning/deduce",
        json={"queryText": "குறிஞ்சி நில ஒழுக்கம்", "tinai": "Kuṟiñci"},
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["reasoningStages"]) == 5
    assert len(data["proofNodes"]) == 7
    assert len(data["proofEdges"]) >= 6
    assert len(data["traceSteps"]) == 7


# ---------------------------------------------------------------------------
# 9. Graphical Proof Trace Endpoint
# ---------------------------------------------------------------------------

def test_proof_trace_endpoint(client):
    """Verifies POST /api/reasoning/proof-trace handles sufficient and insufficient evidence."""
    # Sufficient evidence
    evidence = [
        {"passage_id": "tol-porul-akam-003", "text": "Mutal verse"},
        {"passage_id": "tol-porul-akam-005", "text": "Karu verse"},
    ]
    res_valid = client.post(
        "/api/reasoning/proof-trace",
        json={"queryText": "Kuṟiñci", "evidenceItems": evidence},
    )
    assert res_valid.status_code == 200
    data_valid = res_valid.get_json()["data"]
    assert data_valid["isValid"] is True
    assert data_valid["insufficientEvidence"] is False
    assert len(data_valid["proofNodes"]) == 7

    # Insufficient evidence (< 2 items)
    res_insufficient = client.post(
        "/api/reasoning/proof-trace",
        json={"queryText": "Unknown", "evidenceItems": []},
    )
    assert res_insufficient.status_code == 200
    data_ins = res_insufficient.get_json()["data"]
    assert data_ins["insufficientEvidence"] is True
    assert data_ins["status"] == "INSUFFICIENT_EVIDENCE"
    assert data_ins["conclusionId"] is None


# ---------------------------------------------------------------------------
# 10. Evidence-Grounded Final Answer Endpoint
# ---------------------------------------------------------------------------

def test_reasoning_answer_endpoint(client):
    """Verifies POST /api/reasoning/answer generates grounded verdict."""
    res = client.post(
        "/api/reasoning/answer",
        json={"queryText": "குறிஞ்சி நிலத்தின் புணர்தல் ஒழுக்கம் எவ்வாறு அமைகிறது?", "depth": 2},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert "finalAnswer" in data
    assert "tamilAnswer" in data["finalAnswer"]
    assert "englishAnswer" in data["finalAnswer"]
    assert "proofTrace" in data

    # Empty query 422
    res_empty = client.post("/api/reasoning/answer", json={"queryText": ""})
    assert res_empty.status_code == 422
    assert res_empty.get_json()["success"] is False
