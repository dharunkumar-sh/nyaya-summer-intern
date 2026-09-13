"""
Unit and Integration Test Suite for the Clean Flask Search REST API (/api/search).
Tests POST and GET endpoints, hybrid/keyword/semantic modes, query normalization,
pagination, metadata filters, graph context, input validation, and error shielding.
"""
from unittest.mock import patch
import pytest
from app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_search_api_default_hybrid_post(client):
    """Verifies POST /api/search with default hybrid mode returns expected schema and graph context."""
    res = client.post("/api/search", json={"query": "அச்சம் மெய்ப்பாடு", "top_k": 3})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    assert "data" in payload

    data = payload["data"]
    assert data["original_query"] == "அச்சம் மெய்ப்பாடு"
    assert "normalized_query" in data
    assert data["mode"] == "hybrid"
    assert data["result_count"] <= 3
    assert data["total_results"] >= data["result_count"]
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert "total_pages" in data

    ranked = data["ranked_results"]
    assert len(ranked) > 0
    first = ranked[0]
    assert first["rank"] == 1
    assert "passage_id" in first
    assert "text" in first
    assert len(first["text"]) > 0

    # Relevance scores
    scores = first["relevance_scores"]
    assert "combined_score" in scores
    assert isinstance(scores["combined_score"], (int, float))

    # Source metadata
    meta = first["source_metadata"]
    assert "work" in meta
    assert "section" in meta
    assert "source_id" in meta

    # Graph context
    graph_ctx = first.get("graph_context")
    if graph_ctx is not None:
        assert "graph_relevance_score" in graph_ctx
        assert "subgraph" in graph_ctx


def test_search_api_keyword_mode(client):
    """Verifies POST /api/search with mode='keyword' executes lexical BM25 search."""
    res = client.post("/api/search", json={
        "query": "முதல்கரு",
        "mode": "keyword",
        "top_k": 3,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["mode"] == "keyword"
    assert len(data["ranked_results"]) > 0
    first = data["ranked_results"][0]
    assert "lexical_score" in first["relevance_scores"]


def test_search_api_semantic_mode(client):
    """Verifies POST /api/search with mode='semantic' executes dense vector search."""
    res = client.post("/api/search", json={
        "query": "fear dread emotion",
        "mode": "semantic",
        "top_k": 3,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["mode"] == "semantic"
    assert len(data["ranked_results"]) > 0
    first = data["ranked_results"][0]
    assert "semantic_score" in first["relevance_scores"]


def test_search_api_get_query_params(client):
    """Verifies GET /api/search supports URL query parameters with identical schema."""
    res = client.get("/api/search?q=மெய்ப்பாடு&mode=hybrid&top_k=2")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["original_query"] == "மெய்ப்பாடு"
    assert data["mode"] == "hybrid"
    assert data["result_count"] <= 2


def test_search_api_validation_empty_query(client):
    """Verifies empty or whitespace-only queries return HTTP 400 INVALID_QUERY."""
    res1 = client.post("/api/search", json={"query": ""})
    assert res1.status_code == 400
    assert res1.get_json()["error_code"] == "INVALID_QUERY"

    res2 = client.post("/api/search", json={"query": "     "})
    assert res2.status_code == 400
    assert res2.get_json()["error_code"] == "INVALID_QUERY"

    res3 = client.get("/api/search?q=")
    assert res3.status_code == 400
    assert res3.get_json()["error_code"] == "INVALID_QUERY"


def test_search_api_validation_query_length_limit(client):
    """Verifies queries exceeding 500 characters return HTTP 400 QUERY_TOO_LONG."""
    long_query = "அச்சம் " * 150
    assert len(long_query) > 500
    res = client.post("/api/search", json={"query": long_query})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["error_code"] == "QUERY_TOO_LONG"
    assert "500" in payload["message"]


def test_search_api_validation_invalid_mode(client):
    """Verifies unsupported search modes return HTTP 400 INVALID_SEARCH_MODE."""
    res = client.post("/api/search", json={"query": "அச்சம்", "mode": "unknown_mode_xyz"})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["error_code"] == "INVALID_SEARCH_MODE"
    assert "hybrid" in payload["message"]


def test_search_api_validation_malformed_numbers(client):
    """Verifies invalid numeric parameters return HTTP 400 VALIDATION_ERROR."""
    res_page = client.post("/api/search", json={"query": "அச்சம்", "page": 0})
    assert res_page.status_code == 400
    assert res_page.get_json()["error_code"] == "VALIDATION_ERROR"

    res_weight = client.post("/api/search", json={"query": "அச்சம்", "lexical_weight": 1.5})
    assert res_weight.status_code == 400
    assert res_weight.get_json()["error_code"] == "VALIDATION_ERROR"


def test_search_api_metadata_filtering(client):
    """Verifies root-level and nested metadata filtering restricts returned passages."""
    res = client.post("/api/search", json={
        "query": "அச்சம்",
        "work": "Tolkappiyam",
        "mode": "keyword",
        "top_k": 5,
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["filters_applied"].get("work") == "Tolkappiyam"
    for item in data["ranked_results"]:
        assert item["source_metadata"]["work"] == "Tolkappiyam"


def test_search_api_pagination(client):
    """Verifies 1-indexed pagination slices candidates without overlap."""
    res_page1 = client.post("/api/search", json={
        "query": "மெய்ப்பாடு",
        "mode": "hybrid",
        "page": 1,
        "page_size": 2,
    })
    res_page2 = client.post("/api/search", json={
        "query": "மெய்ப்பாடு",
        "mode": "hybrid",
        "page": 2,
        "page_size": 2,
    })

    assert res_page1.status_code == 200
    assert res_page2.status_code == 200

    data1 = res_page1.get_json()["data"]
    data2 = res_page2.get_json()["data"]

    assert data1["page"] == 1
    assert data2["page"] == 2
    assert data1["page_size"] == 2
    assert data2["page_size"] == 2

    if data1["total_results"] >= 4:
        assert data1["result_count"] == 2
        assert data2["result_count"] == 2
        # Ranks must be continuous
        assert [r["rank"] for r in data1["ranked_results"]] == [1, 2]
        assert [r["rank"] for r in data2["ranked_results"]] == [3, 4]
        # Passage IDs must not overlap
        pids1 = {r["passage_id"] for r in data1["ranked_results"]}
        pids2 = {r["passage_id"] for r in data2["ranked_results"]}
        assert pids1.isdisjoint(pids2)


def test_search_api_error_shielding(client):
    """Verifies internal server errors are caught and sanitized without leaking tracebacks."""
    with patch("api.routes.search_routes._execute_search", side_effect=RuntimeError("Secret database error at /var/data/secret")):
        res = client.post("/api/search", json={"query": "அச்சம்"})
        assert res.status_code == 500
        payload = res.get_json()
        assert payload["success"] is False
        assert payload["error_code"] == "SEARCH_PROCESSING_ERROR"
        # Verify internal implementation details / paths are NOT exposed to client
        assert "Secret database error" not in payload["error"]
        assert "/var/data/secret" not in payload["error"]
        assert "traceback" not in payload


def test_search_api_hybrid_rag_pipeline_preserves_metadata(client):
    """
    Verifies that the primary Flask search endpoint:
    1. Connects directly to the 3-channel Hybrid RAG pipeline (BM25 + vector + KG traversal).
    2. Normalizes the query and executes multi-channel retrieval.
    3. Deduplicates candidates using stable passage IDs.
    4. Fuses and normalizes scores.
    5. Returns real corpus/Aura data (never mock data).
    6. Preserves text, source, work, section, entity/concept metadata, retrieval method, and relevance scores.
    """
    res = client.post("/api/search", json={
        "query": "குறிஞ்சி நிலத்தின் முதற்பொருள்",
        "mode": "hybrid",
        "top_k": 5,
        "include_graph": True,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True
    data = payload["data"]

    # Query normalization
    assert "normalized_query" in data
    assert len(data["normalized_query"]) > 0

    # 3-channel retrieval stats
    stats = data.get("retrieval_stats")
    assert stats is not None
    assert "channel_a_semantic_count" in stats
    assert "channel_b_keyword_count" in stats
    assert "channel_c_graph_count" in stats
    assert "weights_used" in stats

    ranked = data["ranked_results"]
    assert len(ranked) >= 1

    # Candidate deduplication by stable passage ID
    pids = [item["passage_id"] for item in ranked]
    assert len(pids) == len(set(pids)), "Passage IDs must be strictly deduplicated"

    for item in ranked:
        # Stable passage ID
        assert item["passage_id"].startswith("tol-")

        # Grounded text from real dataset
        assert isinstance(item["text"], str)
        assert len(item["text"].strip()) > 0
        assert "mock" not in item["text"].lower()

        # Source provenance
        assert item.get("source") is not None
        src_meta = item["source_metadata"]
        assert isinstance(src_meta, dict)

        # Work and section preserved directly
        assert "work" in item
        assert "Tolk" in item["work"]
        assert "section" in item
        assert len(item["section"]) > 0

        # Entity/concept metadata preserved
        assert "entity_metadata" in item
        assert "entities" in item["entity_metadata"]
        assert "concepts" in item["entity_metadata"]
        assert "entities" in item
        assert "concepts" in item

        # Retrieval method preserved
        assert "retrieval_method" in item
        assert "retrieval_methods" in item
        assert isinstance(item["retrieval_methods"], list)
        assert len(item["retrieval_methods"]) >= 1

        # Relevance scores preserved
        scores = item["relevance_scores"]
        assert "combined_score" in scores
        assert "relevance_score" in scores
        assert 0.0 <= scores["combined_score"] <= 1.0

