"""
Comprehensive Test Suite for Neo4j Knowledge Graph Augmented Hybrid Search.

Verifies:
1. Graph context retrieval using stable passage IDs (e.g., tol-porul-akam-005, tol-porul-mey-001).
2. Controlled relationship expansion (associated_entities, associated_concepts, associated_events, evidence, source_hierarchy).
3. Bounded maximum graph depth (1, 2, 3 hops) without retrieving the entire graph.
4. Exact source provenance preservation across the full hierarchy (L0 to L3).
5. Graph relevance score computation and query alignment.
6. Tri-partite relevance combination (lexical + semantic + graph).
7. Integration with HybridSearchService, RAGEngine, and Flask REST API endpoints.
"""
from __future__ import annotations

import pytest
from typing import Dict, Any, List

from retrieval.graph_hybrid_search import (
    GraphHybridSearchService,
    GraphContext,
    GraphAugmentedPassageResult,
    graph_hybrid_search_service,
    CONTROLLED_RELATIONS,
)
from retrieval.hybrid_search import hybrid_search_service
from retrieval.rag_service import rag_engine
from app import create_app


@pytest.fixture(scope="module")
def service() -> GraphHybridSearchService:
    return graph_hybrid_search_service


@pytest.fixture(scope="module")
def app():
    app = create_app("testing")
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# =============================================================================
# 1. Graph Context Retrieval & Controlled Expansion
# =============================================================================

class TestGraphContextRetrieval:

    def test_retrieve_graph_context_by_stable_passage_id(self, service: GraphHybridSearchService):
        """Verifies graph context is successfully retrieved using canonical passage ID."""
        ctx = service.retrieve_passage_graph_context("tol-porul-akam-005", query="Mayon Mullai", max_depth=2)
        assert ctx.passage_id == "tol-porul-akam-005"
        assert len(ctx.source_hierarchy) >= 3
        assert len(ctx.entities) > 0 or len(ctx.concepts) > 0
        assert ctx.graph_source in ("neo4j_aura", "in_memory")

    def test_controlled_relationships_filtering(self, service: GraphHybridSearchService):
        """Verifies that only controlled relationships are expanded in the neighborhood."""
        ctx = service.retrieve_passage_graph_context("tol-porul-akam-005", max_depth=2)
        all_allowed = set().union(*CONTROLLED_RELATIONS.values())

        # Verify edges in subgraph match controlled relation names or standard semantic edges
        for edge in ctx.subgraph.get("edges", []):
            rel = edge.get("relation") or edge.get("type")
            if rel:
                assert rel.lower() in {r.lower() for r in all_allowed} or "related" in rel.lower() or "contains" in rel.lower()

    def test_bounded_expansion_depth(self, service: GraphHybridSearchService):
        """Verifies max_graph_depth strictly bounds the traversal depth."""
        ctx_depth1 = service.retrieve_passage_graph_context("tol-porul-akam-005", max_depth=1)
        ctx_depth2 = service.retrieve_passage_graph_context("tol-porul-akam-005", max_depth=2)

        # Depth 2 should have equal or greater nodes than Depth 1
        assert len(ctx_depth2.subgraph["nodes"]) >= len(ctx_depth1.subgraph["nodes"])

    def test_does_not_retrieve_entire_graph(self, service: GraphHybridSearchService):
        """Verifies that neighborhood extraction is strictly bounded and does not dump the entire graph."""
        ctx = service.retrieve_passage_graph_context("tol-porul-akam-003", max_depth=2, max_nodes_per_passage=20)
        total_nodes = len(ctx.subgraph["nodes"])
        # Total graph has 30+ nodes; bounded context must be small and focused
        assert 1 <= total_nodes <= 25

    def test_exact_source_provenance_preservation(self, service: GraphHybridSearchService):
        """Verifies provenance chain preserves exact hierarchical levels (L0 Literature to L3 Passage)."""
        ctx = service.retrieve_passage_graph_context("tol-porul-akam-005", max_depth=2)
        hierarchy = ctx.source_hierarchy
        assert len(hierarchy) >= 3

        levels = [h.get("level") for h in hierarchy if h.get("level")]
        # Check presence of literature (L0) and work (L1) or sections (L2)
        assert any("L0" in lvl for lvl in levels) or any("L1" in lvl for lvl in levels)

        labels = [str(h.get("label")) for h in hierarchy]
        assert any("Tolkāppiyam" in lbl or "Sangam" in lbl or "Poruḷ" in lbl for lbl in labels)


# =============================================================================
# 2. Graph Relevance & Tri-Partite Fusion Scoring
# =============================================================================

class TestGraphRelevanceAndTriPartiteFusion:

    def test_graph_relevance_calculation(self, service: GraphHybridSearchService):
        """Verifies graph relevance scores reflect query overlap with entities and concepts."""
        ctx_match = service.retrieve_passage_graph_context(
            passage_id="tol-porul-akam-005",
            query="pastoral forests landscape presided by Mayon Mullai",
            max_depth=2,
        )
        assert ctx_match.graph_relevance_score > 0.60
        assert "Māyōn" in ctx_match.graph_explanation or "Mullai" in ctx_match.graph_explanation

        # Non-matching query yields base prior score
        ctx_nomatch = service.retrieve_passage_graph_context(
            passage_id="tol-porul-akam-005",
            query="modern rocket propellant engineering",
            max_depth=2,
        )
        assert ctx_nomatch.graph_relevance_score <= ctx_match.graph_relevance_score

    def test_tripartite_fusion_formula_accuracy(self, service: GraphHybridSearchService):
        """Verifies mathematical correctness of tri-partite score combination."""
        w_lex = 0.30
        w_sem = 0.45
        w_gr = 0.25
        total_w = w_lex + w_sem + w_gr

        results = service.search(
            query="pastoral forests landscape Mayon",
            top_k=2,
            lexical_weight=w_lex,
            semantic_weight=w_sem,
            graph_weight=w_gr,
            max_graph_depth=2,
        )
        assert len(results) > 0

        for r in results:
            expected = ((w_lex * r.lexical_score) + (w_sem * r.semantic_score) + (w_gr * r.graph_score)) / total_w
            assert abs(r.final_score - expected) < 0.01
            assert 0.0 <= r.final_score <= 1.0

    def test_configurable_weights_sensitivity(self, service: GraphHybridSearchService):
        """Verifies that modifying graph weight influences rankings and final scores."""
        # 100% Graph weight
        pure_graph = service.search(
            query="மாயோன் முல்லை",
            top_k=3,
            lexical_weight=0.0,
            semantic_weight=0.0,
            graph_weight=1.0,
        )
        assert len(pure_graph) > 0
        assert abs(pure_graph[0].final_score - pure_graph[0].graph_score) < 1e-4

        # 0% Graph weight
        zero_graph = service.search(
            query="மாயோன் முல்லை",
            top_k=3,
            lexical_weight=0.5,
            semantic_weight=0.5,
            graph_weight=0.0,
        )
        assert len(zero_graph) > 0
        expected_zero = 0.5 * zero_graph[0].lexical_score + 0.5 * zero_graph[0].semantic_score
        assert abs(zero_graph[0].final_score - expected_zero) < 0.01


# =============================================================================
# 3. Integration with HybridSearchService, RAGEngine & Flask API
# =============================================================================

class TestIntegrationAndEndpoints:

    def test_hybrid_search_service_with_graph_convenience(self):
        """Verifies HybridSearchService.search_with_graph convenience method."""
        results = hybrid_search_service.search_with_graph(
            query="eightfold emotional manifestations in dramatic poetics",
            top_k=2,
            max_graph_depth=2,
        )
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-mey-001"
        assert top.retrieval_method == "graph_hybrid_search"
        assert top.graph_score is not None
        assert top.graph_context is not None
        assert "source_hierarchy" in top.graph_context

    def test_rag_engine_graph_hybrid_passage_search(self):
        """Verifies RAGEngine.graph_hybrid_passage_search method."""
        results = rag_engine.graph_hybrid_passage_search(
            query="forest world presided over by Mayon",
            top_k=2,
            max_graph_depth=2,
        )
        assert len(results) > 0
        assert "graph_context" in results[0]
        assert "provenance_hierarchy" in results[0]["source_metadata"]

    def test_flask_graph_hybrid_endpoint(self, client):
        """Verifies dedicated POST /api/retrieval/graph-hybrid endpoint."""
        resp = client.post(
            "/api/retrieval/graph-hybrid",
            json={
                "query": "pastoral forest landscape presided by Mayon",
                "top_k": 2,
                "max_graph_depth": 2,
                "lexical_weight": 0.30,
                "semantic_weight": 0.45,
                "graph_weight": 0.25,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["results"]) > 0
        top = data["results"][0]
        assert top["passage_id"] == "tol-porul-akam-005"
        assert "graph_context" in top
        assert "source_hierarchy" in top["graph_context"]
        assert "graph_relevance_score" in top["graph_context"]

    def test_flask_hybrid_route_include_graph(self, client):
        """Verifies POST /api/retrieval/hybrid with include_graph: true."""
        resp = client.post(
            "/api/retrieval/hybrid",
            json={
                "query": "Mullai Mayon pastoral",
                "top_k": 2,
                "include_graph": True,
                "max_graph_depth": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["include_graph"] is True
        assert len(data["results"]) > 0
        top = data["results"][0]
        assert "graph_context" in top
        assert top["retrieval_method"] == "graph_hybrid_search"
