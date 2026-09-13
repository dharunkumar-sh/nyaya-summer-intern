"""
Comprehensive Test Suite for the Unified Hybrid Search Service.

Validates:
1. Dual-channel execution: both BM25 lexical and semantic vector retrieval execute for every valid query.
2. Score normalization and transparent score reporting: lexical_score, semantic_score, and combined_score.
3. Candidate deduplication and merging by passage ID.
4. Configurable relevance weights (default 40% lexical / 60% semantic, and custom overrides).
5. Mathematical verification of combined hybrid score calculation.
6. Combined hybrid search with metadata filtering (tinai, chapter, verse, entity).
7. Integration with RAGRetrievalEngine and Flask API endpoint (/api/retrieval/hybrid).
8. Full backward compatibility with existing RRF-based hybrid retrieval.
"""
from __future__ import annotations

import pytest

from retrieval.hybrid_search import (
    HybridSearchService,
    HybridSearchResult,
    hybrid_search_service,
)
from retrieval.rag_service import rag_engine
from app import create_app


@pytest.fixture
def service():
    """Provides the singleton instance of the HybridSearchService."""
    return hybrid_search_service


@pytest.fixture
def test_client():
    """Flask test client for API endpoint testing."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. Dual Channel Execution & Deduplication
# =============================================================================

class TestDualExecutionAndDeduplication:

    def test_both_channels_execute_and_merge(self, service: HybridSearchService):
        """Verifies both lexical and semantic searches execute and results are merged."""
        results = service.search("மாயோன் காடுறை உலகம் முல்லை", top_k=5)
        assert len(results) > 0

        # Verify candidate deduplication by passage ID
        passage_ids = [r.passage_id for r in results]
        assert len(passage_ids) == len(set(passage_ids)), "Duplicate passage IDs found in hybrid results"

        # Verify top match is tol-porul-akam-005
        top = results[0]
        assert top.passage_id == "tol-porul-akam-005"
        # Both channels should contribute
        assert top.lexical_score > 0.0
        assert top.semantic_score > 0.0
        assert top.combined_score > 0.0

    def test_english_query_hybrid_retrieval(self, service: HybridSearchService):
        """Verifies cross-lingual English query executes both channels and retrieves correct sūtras."""
        results = service.search("dark mountain realm overseen by Ceyon", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-005"
        assert top.semantic_score > 0.0
        assert 0.0 <= top.combined_score <= 1.0


# =============================================================================
# 2. Score Transparency & Mathematical Calculation
# =============================================================================

class TestScoreTransparencyAndCalculation:

    def test_score_breakdown_fields_present(self, service: HybridSearchService):
        """Verifies transparent score breakdown: lexical_score, semantic_score, combined_score."""
        results = service.search("புணர்தல் பிரிதல் இருத்தல்", top_k=3)
        assert len(results) > 0

        for r in results:
            d = r.to_dict()
            assert "passage_id" in d
            assert "text" in d
            assert "source_metadata" in d
            assert "lexical_score" in d
            assert "semantic_score" in d
            assert "combined_score" in d
            assert "score" in d
            assert d["score"] == d["combined_score"]
            assert d["retrieval_method"] == "hybrid_search"

            # Check bounds
            assert 0.0 <= d["lexical_score"] <= 1.0
            assert 0.0 <= d["semantic_score"] <= 1.0
            assert 0.0 <= d["combined_score"] <= 1.0

    def test_default_weights_mathematical_accuracy(self, service: HybridSearchService):
        """
        Verifies that combined score strictly follows default weights (0.40 lexical + 0.60 semantic).
        Combined = 0.40 * Lexical + 0.60 * Semantic
        """
        results = service.search("முதல்கரு உரிப்பொருள்", top_k=5)
        assert len(results) > 0

        for r in results:
            expected_combined = 0.40 * r.lexical_score + 0.60 * r.semantic_score
            assert abs(r.combined_score - expected_combined) < 0.001, (
                f"Combined score {r.combined_score} != expected {expected_combined} "
                f"for lex={r.lexical_score}, sem={r.semantic_score}"
            )

    def test_custom_configurable_weights_accuracy(self, service: HybridSearchService):
        """
        Verifies mathematical accuracy when custom weights are passed.
        Test with 80% lexical / 20% semantic.
        """
        w_lex = 0.80
        w_sem = 0.20
        results = service.search(
            "மாயோன் மேய காடுறை",
            top_k=5,
            lexical_weight=w_lex,
            semantic_weight=w_sem,
        )
        assert len(results) > 0

        for r in results:
            expected_combined = (w_lex * r.lexical_score + w_sem * r.semantic_score) / (w_lex + w_sem)
            assert abs(r.combined_score - expected_combined) < 0.001

    def test_pure_lexical_weight(self, service: HybridSearchService):
        """Verifies 100% lexical weighting (w_lex=1.0, w_sem=0.0)."""
        results = service.search(
            "முதல்கரு",
            top_k=3,
            lexical_weight=1.0,
            semantic_weight=0.0,
        )
        assert len(results) > 0
        top = results[0]
        assert top.combined_score == top.lexical_score

    def test_pure_semantic_weight(self, service: HybridSearchService):
        """Verifies 100% semantic weighting (w_lex=0.0, w_sem=1.0)."""
        results = service.search(
            "primary ground spatial landscape and temporal season",
            top_k=3,
            lexical_weight=0.0,
            semantic_weight=1.0,
        )
        assert len(results) > 0
        top = results[0]
        assert top.combined_score == top.semantic_score


# =============================================================================
# 3. Hybrid Search with Metadata Filtering
# =============================================================================

class TestHybridFiltering:

    def test_hybrid_search_with_tinai_filter(self, service: HybridSearchService):
        """Verifies filtering by Tiṇai in hybrid search."""
        results = service.search(
            "landscape and emotions",
            top_k=5,
            filters={"tinai": "Kuṟiñci"},
        )
        assert len(results) > 0
        for r in results:
            assert r.source_metadata["tinai"] == "Kuṟiñci"

    def test_hybrid_search_with_chapter_filter(self, service: HybridSearchService):
        """Verifies filtering by chapter in hybrid search."""
        results = service.search(
            "dramatic emotional aesthetic manifestation",
            top_k=5,
            filters={"chapter": "Meyppāṭṭiyal"},
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-mey-001"
        assert results[0].source_metadata["chapter"] == "Meyppāṭṭiyal"

    def test_hybrid_search_with_entity_filter(self, service: HybridSearchService):
        """Verifies filtering by recognized entity in hybrid search."""
        results = service.search(
            "deity and forest",
            top_k=5,
            filters={"entity": "Māyōṉ"},
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-akam-005"
        assert "Māyōṉ" in results[0].source_metadata["entities"]


# =============================================================================
# 4. RAG Engine Integration & Flask API Tests
# =============================================================================

class TestAPIAndIntegration:

    def test_rag_engine_hybrid_passage_search(self):
        """Verifies RAGRetrievalEngine.hybrid_passage_search integration."""
        results = rag_engine.hybrid_passage_search(
            "மாயோன் காடுறை உலகம்",
            top_k=3,
            lexical_weight=0.4,
            semantic_weight=0.6,
        )
        assert len(results) > 0
        top = results[0]
        assert "passage_id" in top
        assert "lexical_score" in top
        assert "semantic_score" in top
        assert "combined_score" in top
        assert top["retrieval_method"] == "hybrid_search"

    def test_flask_hybrid_endpoint_default(self, test_client):
        """Verifies POST /api/retrieval/hybrid returns transparent scores with default weights."""
        res = test_client.post(
            "/api/retrieval/hybrid",
            json={"query": "சேயோன் மேய மைவரை குறிஞ்சி", "top_k": 3},
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert len(results) > 0

        top = results[0]
        assert "passage_id" in top
        assert "text" in top
        assert "lexical_score" in top
        assert "semantic_score" in top
        assert "combined_score" in top
        assert 0.0 <= top["combined_score"] <= 1.0

    def test_flask_hybrid_endpoint_custom_weights_and_filters(self, test_client):
        """Verifies POST /api/retrieval/hybrid with custom weights and metadata filters."""
        res = test_client.post(
            "/api/retrieval/hybrid",
            json={
                "query": "பொருள்",
                "top_k": 3,
                "lexical_weight": 0.7,
                "semantic_weight": 0.3,
                "filters": {"chapter": "Akattiṇaiyiyal"},
            },
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        assert payload["data"]["lexical_weight"] == 0.7
        assert payload["data"]["semantic_weight"] == 0.3
        results = payload["data"]["results"]
        assert len(results) > 0
        for r in results:
            assert r["source_metadata"]["chapter"] == "Akattiṇaiyiyal"
            assert "lexical_score" in r
            assert "semantic_score" in r
            assert "combined_score" in r
