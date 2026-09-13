"""
Comprehensive test suite for Second-Stage Re-ranking Layer.

Verifies:
1. Individual score component calculations (semantic similarity, keyword coverage,
   entity/concept matching, source relevance, metadata matching).
2. Determinism and reproducibility across repeated executions.
3. Configurable weighting sensitivity (custom weights modifying rankings).
4. Rich transparent explanations and component contributions.
5. Integration with HybridSearchService, RAGEngine, and Flask REST endpoints.
"""
import pytest
from typing import Dict, Any, List

from retrieval.reranker import (
    PassageReranker,
    RerankerConfig,
    RerankScoreComponents,
    RerankExplanation,
    RerankedPassage,
    passage_reranker,
)
from retrieval.hybrid_search import (
    HybridSearchService,
    HybridSearchResult,
    hybrid_search_service,
)
from retrieval.rag_service import rag_engine
from app import create_app


@pytest.fixture(scope="module")
def reranker() -> PassageReranker:
    return passage_reranker


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# =============================================================================
# 1. Score Component Calculations
# =============================================================================

class TestScoreComponents:

    def test_semantic_similarity_computation(self, reranker: PassageReranker):
        """Verifies semantic similarity returns normalized [0.0, 1.0] values."""
        candidate = {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும்",
            "semantic_score": 0.85,
        }
        score = reranker.compute_semantic_similarity("forest pastoral realm", candidate)
        assert 0.0 <= score <= 1.0
        assert score == 0.85

    def test_keyword_coverage_calculation(self, reranker: PassageReranker):
        """Verifies exact token and phrase coverage across text and translation."""
        metadata = {
            "translation": "The forest world presided over by Mayon (Mullai)",
            "transliteration": "mayon meya katurai ulakamum",
            "category": "Landscape Geography",
        }
        text = "மாயோன் மேய காடுறை உலகமும்"

        # English query coverage
        cov_en, matched_en = reranker.compute_keyword_coverage("forest world Mayon Mullai", text, metadata)
        assert cov_en > 0.5
        assert "forest" in matched_en
        assert "world" in matched_en
        assert "mayon" in matched_en
        assert "mullai" in matched_en

        # Tamil query coverage
        cov_ta, matched_ta = reranker.compute_keyword_coverage("மாயோன் காடுறை உலகம்", text, metadata)
        assert cov_ta > 0.5
        assert "மாயோன்" in matched_ta

    def test_entity_concept_matching(self, reranker: PassageReranker):
        """Verifies matching against annotated entities, concepts, and tiṇai."""
        metadata = {
            "entity": ["Māyōn", "Cēyōn", "Vēntan"],
            "concept": ["Mutalporuḷ", "Tiṇai", "Landscape"],
            "tinai": "Mullai",
        }

        # Query mentioning Mayon and Mullai
        score, ents, concepts = reranker.compute_entity_concept_match("Mayon pastoral landscape in Mullai", metadata)
        assert score >= 0.85
        assert "Māyōn" in ents
        assert "Mullai" in concepts or "Landscape" in concepts

        # Query with non-matching entities
        score_none, ents_none, concepts_none = reranker.compute_entity_concept_match("quantum physics computer", metadata)
        assert score_none == 0.0
        assert len(ents_none) == 0

    def test_source_relevance_canonical_authority(self, reranker: PassageReranker):
        """Verifies canonical Tolkāppiyam source authority and explicit citation bonuses."""
        metadata = {
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "verse": 5,
            "source_identifier": "tol-porul-akam-005",
            "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
        }

        base_score, desc = reranker.compute_source_relevance("general query", "tol-porul-akam-005", metadata)
        assert base_score >= 0.85
        assert "Sūtra 5" in desc or "Akattiṇaiyiyal" in desc

        # Query explicitly mentioning source
        explicit_score, _ = reranker.compute_source_relevance("Tolkappiyam Akattinaiyiyal sutra 5", "tol-porul-akam-005", metadata)
        assert explicit_score > base_score
        assert explicit_score <= 1.0

    def test_metadata_matching_filters(self, reranker: PassageReranker):
        """Verifies metadata concordance with user filters and inferred query context."""
        metadata = {
            "tinai": "Mullai",
            "chapter": "Akattiṇaiyiyal",
            "category": "Landscape Geography",
        }

        # Matching filters
        score_match, matched = reranker.compute_metadata_match(metadata, filters={"tinai": "Mullai", "chapter": "Akattiṇaiyiyal"})
        assert score_match == 1.0
        assert matched["tinai"] == "Mullai"

        # Partial non-matching filter
        score_part, _ = reranker.compute_metadata_match(metadata, filters={"tinai": "Kuriñci"})
        assert score_part == 0.0

        # Inferred query context
        score_inferred, inferred_matched = reranker.compute_metadata_match(metadata, query="love poems in Mullai region")
        assert score_inferred == 1.0
        assert "inferred_tinai" in inferred_matched


# =============================================================================
# 2. Determinism and Configurability
# =============================================================================

class TestDeterminismAndConfigurability:

    def test_deterministic_reproducibility(self, reranker: PassageReranker):
        """Verifies that executing re-ranking multiple times yields identical results."""
        candidates = hybrid_search_service.search("முல்லை மாயோன் காடு", top_k=5, rerank=False)
        assert len(candidates) > 0

        run1 = reranker.rerank(candidates, "முல்லை மாயோன் காடு", top_k=3)
        run2 = reranker.rerank(candidates, "முல்லை மாயோன் காடு", top_k=3)

        assert len(run1) == len(run2)
        for r1, r2 in zip(run1, run2):
            assert r1.passage_id == r2.passage_id
            assert abs(r1.final_score - r2.final_score) < 1e-9
            assert r1.rank == r2.rank
            assert r1.explanation.summary == r2.explanation.summary

    def test_custom_configurable_weights_sensitivity(self, reranker: PassageReranker):
        """Verifies that changing component weights predictably affects final scores."""
        candidates = hybrid_search_service.search("pastoral forest landscape", top_k=5, rerank=False)
        assert len(candidates) > 0

        # High keyword weight vs High semantic weight
        weights_kw = {
            "semantic_similarity": 0.0,
            "keyword_coverage": 1.0,
            "entity_concept": 0.0,
            "source_relevance": 0.0,
            "metadata_match": 0.0,
        }
        res_kw = reranker.rerank(candidates, "pastoral forest landscape", top_k=3, weights=weights_kw)

        weights_sem = {
            "semantic_similarity": 1.0,
            "keyword_coverage": 0.0,
            "entity_concept": 0.0,
            "source_relevance": 0.0,
            "metadata_match": 0.0,
        }
        res_sem = reranker.rerank(candidates, "pastoral forest landscape", top_k=3, weights=weights_sem)

        assert len(res_kw) > 0
        assert len(res_sem) > 0
        # Check component scores reflect pure weights
        assert abs(res_kw[0].final_score - res_kw[0].score_components.keyword_coverage) < 1e-4
        assert abs(res_sem[0].final_score - res_sem[0].score_components.semantic_similarity) < 1e-4

    def test_deterministic_tie_breaking(self, reranker: PassageReranker):
        """Verifies tie-breaking handles identical scores deterministically by passage_id."""
        dummy_candidates = [
            {
                "passage_id": "tol-porul-akam-014",
                "text": "dummy verse b",
                "source_metadata": {"work": "Tolkāppiyam", "verse": 14},
                "semantic_score": 0.5,
            },
            {
                "passage_id": "tol-porul-akam-003",
                "text": "dummy verse a",
                "source_metadata": {"work": "Tolkāppiyam", "verse": 3},
                "semantic_score": 0.5,
            },
        ]
        res = reranker.rerank(dummy_candidates, "dummy query", top_k=2)
        assert len(res) == 2
        # Lexicographical tie-breaker should place tol-porul-akam-003 before 014
        assert res[0].passage_id == "tol-porul-akam-003"
        assert res[1].passage_id == "tol-porul-akam-014"


# =============================================================================
# 3. Explanations and Transparency
# =============================================================================

class TestExplanationsAndTransparency:

    def test_explanation_structure_and_components(self, reranker: PassageReranker):
        """Verifies that every reranked passage provides transparent diagnostics."""
        candidates = hybrid_search_service.search("Māyōn Mullai forest", top_k=3, rerank=False)
        reranked = reranker.rerank(candidates, "Māyōn Mullai forest", top_k=2)

        for p in reranked:
            d = p.to_dict()
            assert "score_components" in d
            assert "explanation" in d
            assert "final_score" in d
            assert "rank" in d

            comps = d["score_components"]
            assert "semantic_similarity" in comps
            assert "keyword_coverage" in comps
            assert "entity_concept_match" in comps
            assert "source_relevance" in comps
            assert "metadata_match" in comps

            expl = d["explanation"]
            assert "summary" in expl
            assert len(expl["summary"]) > 10
            assert "component_contributions" in expl
            assert "source_authority" in expl


# =============================================================================
# 4. Service and API Integration
# =============================================================================

class TestServiceAndAPIIntegration:

    def test_hybrid_search_service_rerank_flag(self):
        """Verifies HybridSearchService.search(rerank=True) re-ranks and attaches explanations."""
        results = hybrid_search_service.search("காடுறை உலகம் மாயோன்", top_k=3, rerank=True)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-005"
        assert top.retrieval_method == "hybrid_with_rerank"
        assert top.final_score is not None
        assert top.score == top.final_score
        assert top.score_components is not None
        assert top.explanation is not None
        assert top.rank == 1

    def test_search_with_rerank_method(self):
        """Verifies hybrid_search_service.search_with_rerank convenience method."""
        results = hybrid_search_service.search_with_rerank(
            query="mountain realm overseen by Ceyon",
            top_k=2,
        )
        assert len(results) > 0
        assert results[0].retrieval_method == "hybrid_with_rerank"
        assert results[0].score_components is not None

    def test_rag_engine_hybrid_passage_search_with_rerank(self):
        """Verifies RAGEngine.hybrid_passage_search with rerank=True."""
        results = rag_engine.hybrid_passage_search("எண்வகை மெய்ப்பாடு", top_k=2, rerank=True)
        assert len(results) > 0
        assert "score_components" in results[0]
        assert "explanation" in results[0]
        assert results[0]["retrieval_method"] == "hybrid_with_rerank"

    def test_flask_hybrid_route_with_rerank(self, client):
        """Verifies POST /api/retrieval/hybrid with rerank: true."""
        resp = client.post(
            "/api/retrieval/hybrid",
            json={
                "query": "pastoral forest landscape presided by Mayon",
                "top_k": 2,
                "rerank": True,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["rerank"] is True
        assert len(data["results"]) > 0
        top = data["results"][0]
        assert "score_components" in top
        assert "explanation" in top
        assert top["retrieval_method"] == "hybrid_with_rerank"

    def test_flask_rerank_endpoint(self, client):
        """Verifies dedicated POST /api/retrieval/rerank endpoint."""
        resp = client.post(
            "/api/retrieval/rerank",
            json={
                "query": "Aesthetic realization and eight emotional rasas",
                "top_k": 2,
                "weights": {
                    "semantic_similarity": 0.40,
                    "keyword_coverage": 0.20,
                    "entity_concept": 0.20,
                    "source_relevance": 0.10,
                    "metadata_match": 0.10,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["results"]) > 0
        top = data["results"][0]
        assert top["passage_id"] == "tol-porul-mey-001"
        assert "score_components" in top
        assert "explanation" in top
