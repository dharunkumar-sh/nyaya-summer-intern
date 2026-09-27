"""
Unit and Integration Tests for Post-Response Cache Clearance.

Verifies:
1. GraphHybridSearchService._graph_context_cache is cleared after response generation.
2. Neo4jService._connectivity_cache is cleared on clear_cache().
3. All HTTP API responses automatically include strict no-cache headers.
4. Dedicated endpoints POST /api/retrieval/clear-cache and POST /api/system/clear-cache.
5. HybridRAGPipeline.answer_query() clears runtime cache upon completion.
"""
import pytest
from app import create_app
from retrieval.graph_hybrid_search import graph_hybrid_search_service
from services.neo4j_service import neo4j_service
from retrieval.rag_service import rag_engine


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_graph_hybrid_search_cache_clear():
    """Verify in-memory graph context cache can be populated and explicitly cleared."""
    # Populate mock cache entry
    graph_hybrid_search_service._graph_context_cache[("test_passage_1", 2)] = MagicContext = {
        "passage_id": "test_passage_1"
    }
    assert len(graph_hybrid_search_service._graph_context_cache) > 0

    # Clear cache
    graph_hybrid_search_service.clear_cache()
    assert len(graph_hybrid_search_service._graph_context_cache) == 0


def test_neo4j_connectivity_cache_clear():
    """Verify Neo4j connectivity cache is cleared."""
    neo4j_service._connectivity_cache = {"connected": True}
    neo4j_service._connectivity_cache_time = 12345.0

    neo4j_service.clear_cache()
    assert neo4j_service._connectivity_cache is None
    assert neo4j_service._connectivity_cache_time == 0.0


def test_rag_engine_clear_runtime_cache():
    """Verify rag_engine.clear_runtime_cache() flushes all component caches."""
    graph_hybrid_search_service._graph_context_cache[("test_p2", 1)] = {}
    neo4j_service._connectivity_cache = {"connected": False}

    rag_engine.clear_runtime_cache()

    assert len(graph_hybrid_search_service._graph_context_cache) == 0
    assert neo4j_service._connectivity_cache is None


def test_no_cache_headers_on_all_responses(client):
    """Verify after_request adds strict no-cache headers to every API response."""
    endpoints = [
        ("/api/health", "GET"),
        ("/api/system/status", "GET"),
        ("/api/retrieval/clear-cache", "POST"),
        ("/api/system/clear-cache", "POST"),
    ]

    for path, method in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)

        assert resp.status_code in (200, 503)
        cache_ctrl = resp.headers.get("Cache-Control", "")
        assert "no-store" in cache_ctrl
        assert "no-cache" in cache_ctrl
        assert "must-revalidate" in cache_ctrl
        assert resp.headers.get("Pragma") == "no-cache"
        assert resp.headers.get("Expires") == "0"


def test_clear_cache_endpoints(client):
    """Verify /api/retrieval/clear-cache and /api/system/clear-cache endpoints."""
    # Populate dummy entries
    graph_hybrid_search_service._graph_context_cache[("dummy", 1)] = {}

    resp1 = client.post("/api/retrieval/clear-cache")
    assert resp1.status_code == 200
    data1 = resp1.get_json()
    assert data1["success"] is True
    assert len(graph_hybrid_search_service._graph_context_cache) == 0

    graph_hybrid_search_service._graph_context_cache[("dummy2", 1)] = {}
    resp2 = client.post("/api/system/clear-cache")
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2["success"] is True
    assert len(graph_hybrid_search_service._graph_context_cache) == 0


def test_answer_query_automatically_clears_cache_after_response(client):
    """Verify that after /api/retrieval/answer generates a response, caches are cleared."""
    payload = {
        "query": "முல்லை நிலத்தின் தெய்வம் யார்?",
        "top_k": 2,
    }
    resp = client.post("/api/retrieval/answer", json=payload)
    assert resp.status_code == 200
    # Cache must be 0 after response generation finishes
    assert len(graph_hybrid_search_service._graph_context_cache) == 0
