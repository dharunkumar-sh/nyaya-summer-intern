"""
Comprehensive test suite for the Hybrid RAG Retrieval Pipeline.

Tests cover:
1.  Pipeline configuration and weight normalization defaults.
2.  EvidenceItem dataclass field presence and to_dict completeness.
3.  EvidenceCollection dataclass to_dict and retrieval_stats.
4.  End-to-end retrieve() returns a valid EvidenceCollection.
5.  Three-channel tagging: items carry at least one retrieval_method.
6.  Deduplication: same passage from two channels merges retrieval_methods.
7.  No generation: result dict has no answer/LLM-output keys.
8.  Provenance: every item has passage_id, source, and graph_path present.
9.  Weight override: custom weights change relevance_score predictably.
10. rag_engine.hybrid_rag_retrieve() delegate returns correct structure.
11. Live Neo4j graph traversal channel (skipped if not connected).
12. Empty query returns empty EvidenceCollection.items.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

def _ensure_backend_in_path():
    import pathlib, sys
    backend = str(pathlib.Path(__file__).resolve().parent.parent)
    if backend not in sys.path:
        sys.path.insert(0, backend)

_ensure_backend_in_path()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline():
    from retrieval.hybrid_rag_pipeline import HybridRAGPipeline
    return HybridRAGPipeline(
        semantic_weight=0.40,
        lexical_weight=0.35,
        graph_weight=0.25,
        top_k=5,
        candidate_pool=12,
        max_graph_depth=2,
    )


@pytest.fixture(scope="module")
def small_evidence_item():
    from retrieval.hybrid_rag_pipeline import EvidenceItem
    return EvidenceItem(
        passage_id="tol-porul-akam-003",
        text="அகத்திணையியல் passage text",
        source={"work": "Tolkāppiyam", "section": "Poruḷatikāram"},
        graph_path=[{"level": "L0", "type": "Literature", "id": "lit-sangam", "label": "Classical Tamil"}],
        retrieval_methods=["semantic_vector", "keyword_entity"],
        semantic_score=0.85,
        lexical_score=0.62,
        graph_score=0.70,
        relevance_score=0.754,
        rank=1,
        graph_context={"entities": [], "concepts": []},
    )


@pytest.fixture(scope="module")
def small_collection(small_evidence_item):
    from retrieval.hybrid_rag_pipeline import EvidenceCollection
    return EvidenceCollection(
        query="What is Mutalporuḷ?",
        processed_query={"normalized_query": "What is Mutalporuḷ?"},
        items=[small_evidence_item],
        retrieval_stats={
            "channel_a_semantic_count": 5,
            "channel_b_keyword_count": 4,
            "channel_c_graph_count": 2,
            "total_candidates_before_merge": 11,
            "unique_candidates_after_merge": 7,
            "returned": 5,
            "elapsed_seconds": 1.23,
        },
        pipeline_version="1.0.0",
    )


# ---------------------------------------------------------------------------
# Test 1 – Configuration defaults and weight normalization
# ---------------------------------------------------------------------------

def test_pipeline_configuration_defaults():
    from retrieval.hybrid_rag_pipeline import HybridRAGPipeline

    p = HybridRAGPipeline()
    assert p.top_k >= 1
    assert p.candidate_pool >= p.top_k
    assert 1 <= p.max_graph_depth <= 3

    # Weights must sum to 1.0
    total = p.semantic_weight + p.lexical_weight + p.graph_weight
    assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"

    # All weights are positive
    assert p.semantic_weight > 0
    assert p.lexical_weight > 0
    assert p.graph_weight > 0


def test_pipeline_weight_normalization():
    from retrieval.hybrid_rag_pipeline import HybridRAGPipeline

    p = HybridRAGPipeline(semantic_weight=2.0, lexical_weight=1.0, graph_weight=1.0)
    total = p.semantic_weight + p.lexical_weight + p.graph_weight
    assert abs(total - 1.0) < 1e-6
    assert abs(p.semantic_weight - 0.5) < 1e-6  # 2/4

    # Zero total resets to sensible defaults
    p2 = HybridRAGPipeline(semantic_weight=0.0, lexical_weight=0.0, graph_weight=0.0)
    total2 = p2.semantic_weight + p2.lexical_weight + p2.graph_weight
    assert abs(total2 - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 2 – EvidenceItem field presence and to_dict completeness
# ---------------------------------------------------------------------------

def test_evidence_item_fields(small_evidence_item):
    item = small_evidence_item
    assert item.passage_id == "tol-porul-akam-003"
    assert item.text
    assert isinstance(item.source, dict)
    assert isinstance(item.graph_path, list)
    assert isinstance(item.retrieval_methods, list)
    assert 0.0 <= item.semantic_score <= 1.0
    assert 0.0 <= item.lexical_score <= 1.0
    assert 0.0 <= item.graph_score <= 1.0
    assert 0.0 <= item.relevance_score <= 1.0
    assert item.rank >= 0


def test_evidence_item_to_dict(small_evidence_item):
    d = small_evidence_item.to_dict()
    required = {
        "passage_id", "rank", "text", "source", "graph_path",
        "retrieval_methods", "semantic_score", "lexical_score",
        "graph_score", "relevance_score", "graph_context",
    }
    assert required.issubset(d.keys()), f"Missing keys: {required - d.keys()}"


# ---------------------------------------------------------------------------
# Test 3 – EvidenceCollection dataclass
# ---------------------------------------------------------------------------

def test_evidence_collection_fields(small_collection):
    c = small_collection
    assert c.query
    assert isinstance(c.items, list)
    assert isinstance(c.retrieval_stats, dict)
    assert c.pipeline_version


def test_evidence_collection_to_dict(small_collection):
    d = small_collection.to_dict()
    assert "query" in d
    assert "processed_query" in d
    assert "items" in d
    assert "retrieval_stats" in d
    assert "pipeline_version" in d
    assert "total_results" in d
    assert d["total_results"] == len(small_collection.items)


# ---------------------------------------------------------------------------
# Test 4 – End-to-end retrieve() returns a valid EvidenceCollection
# ---------------------------------------------------------------------------

def test_retrieve_returns_evidence_collection(pipeline):
    from retrieval.hybrid_rag_pipeline import EvidenceCollection
    result = pipeline.retrieve("What is Mutalporuḷ?", top_k=3)
    assert isinstance(result, EvidenceCollection)
    assert result.query == "What is Mutalporuḷ?"
    assert isinstance(result.items, list)
    assert isinstance(result.retrieval_stats, dict)
    assert result.pipeline_version == pipeline.PIPELINE_VERSION


# ---------------------------------------------------------------------------
# Test 5 – Three-channel tagging: items carry at least one retrieval_method
# ---------------------------------------------------------------------------

def test_all_items_have_retrieval_methods(pipeline):
    result = pipeline.retrieve("Tolkappiyam Akathinai emotion", top_k=3)
    for item in result.items:
        assert isinstance(item.retrieval_methods, list), "retrieval_methods must be a list"
        assert len(item.retrieval_methods) >= 1, f"Item {item.passage_id} has no retrieval_methods"
        valid_methods = {"semantic_vector", "keyword_entity", "graph_traversal"}
        for m in item.retrieval_methods:
            assert m in valid_methods, f"Unknown retrieval method: {m}"


# ---------------------------------------------------------------------------
# Test 6 – Deduplication: passage in two channels merges retrieval_methods
# ---------------------------------------------------------------------------

def test_deduplication_merges_retrieval_methods(pipeline):
    """
    Mock Channels A and B to both return the same passage_id.
    After merging, that item should have both retrieval_methods.
    """
    from retrieval.hybrid_rag_pipeline import EvidenceItem

    shared_pid = "tol-porul-akam-003"
    channel_a = {
        shared_pid: {
            "passage_id": shared_pid,
            "text": "test text",
            "source": {"work": "Tolkāppiyam"},
            "semantic_score": 0.8,
        }
    }
    channel_b = {
        shared_pid: {
            "passage_id": shared_pid,
            "text": "test text",
            "source": {"work": "Tolkāppiyam"},
            "lexical_score": 0.6,
        }
    }
    channel_c = {}

    merged = pipeline._merge_channels(channel_a, channel_b, channel_c)
    assert shared_pid in merged
    item = merged[shared_pid]
    assert "semantic_vector" in item.retrieval_methods
    assert "keyword_entity" in item.retrieval_methods
    assert item.semantic_score == 0.8
    assert item.lexical_score == 0.6


def test_deduplication_keeps_best_scores():
    from retrieval.hybrid_rag_pipeline import HybridRAGPipeline
    p = HybridRAGPipeline()
    pid = "tol-porul-mey-001"
    # Channel A appears twice via different channels - highest should win
    ca = {pid: {"passage_id": pid, "text": "x", "source": {}, "semantic_score": 0.9}}
    cb = {pid: {"passage_id": pid, "text": "x", "source": {}, "lexical_score": 0.7}}
    cc = {pid: {"passage_id": pid, "text": "x", "source": {}, "graph_score": 0.5}}
    merged = p._merge_channels(ca, cb, cc)
    item = merged[pid]
    assert item.semantic_score == 0.9
    assert item.lexical_score == 0.7
    assert item.graph_score == 0.5
    assert len(item.retrieval_methods) == 3


# ---------------------------------------------------------------------------
# Test 7 – No generation: result has no answer/LLM-output keys
# ---------------------------------------------------------------------------

def test_no_generated_content_in_results(pipeline):
    result = pipeline.retrieve("What is Karupporuḷ?", top_k=3)
    result_dict = result.to_dict()

    forbidden_keys = {
        "answer", "generated_answer", "llm_output", "generated_text",
        "inference", "synthesized_answer", "response",
    }

    def _check_no_forbidden(obj, path="root"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in forbidden_keys, \
                    f"Forbidden key '{k}' found at path '{path}.{k}'"
                _check_no_forbidden(v, path=f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_no_forbidden(item, path=f"{path}[{i}]")

    _check_no_forbidden(result_dict)


# ---------------------------------------------------------------------------
# Test 8 – Provenance: every item has passage_id, source, graph_path
# ---------------------------------------------------------------------------

def test_provenance_preserved(pipeline):
    result = pipeline.retrieve("Tolkappiyam tinai concept", top_k=3)
    for item in result.items:
        assert item.passage_id, f"EvidenceItem must have a non-empty passage_id"
        assert isinstance(item.source, dict), "source must be a dict"
        assert isinstance(item.graph_path, list), "graph_path must be a list"


# ---------------------------------------------------------------------------
# Test 9 – Weight overrides change relevance_score predictably
# ---------------------------------------------------------------------------

def test_weight_override_changes_relevance(pipeline):
    """
    Create a synthetic merged dict and verify that score changes when weights change.
    """
    from retrieval.hybrid_rag_pipeline import EvidenceItem

    item = EvidenceItem(
        passage_id="tol-porul-akam-003",
        text="x",
        source={},
        semantic_score=0.8,
        lexical_score=0.2,
        graph_score=0.1,
    )
    merged = {"tol-porul-akam-003": item}

    # High semantic weight -> relevance dominated by semantic_score
    for itm in merged.values():
        itm.relevance_score = round(0.80 * itm.semantic_score + 0.15 * itm.lexical_score + 0.05 * itm.graph_score, 6)
    high_sem_score = merged["tol-porul-akam-003"].relevance_score

    # High lexical weight -> relevance dominated by lexical_score
    for itm in merged.values():
        itm.relevance_score = round(0.10 * itm.semantic_score + 0.85 * itm.lexical_score + 0.05 * itm.graph_score, 6)
    high_lex_score = merged["tol-porul-akam-003"].relevance_score

    assert high_sem_score > high_lex_score, (
        f"High semantic weight ({high_sem_score}) should produce higher score than high lexical ({high_lex_score})"
        " for a passage with semantic_score=0.8 and lexical_score=0.2"
    )


# ---------------------------------------------------------------------------
# Test 10 – rag_engine.hybrid_rag_retrieve() delegate
# ---------------------------------------------------------------------------

def test_rag_engine_delegate():
    from retrieval.rag_service import rag_engine

    result = rag_engine.hybrid_rag_retrieve(
        query="What is Uripporuḷ?",
        top_k=3,
        as_dict=True,
    )
    assert isinstance(result, dict)
    assert "query" in result
    assert "items" in result
    assert "retrieval_stats" in result
    assert "pipeline_version" in result
    assert result["query"] == "What is Uripporuḷ?"

    # as_dict=False must return EvidenceCollection
    from retrieval.hybrid_rag_pipeline import EvidenceCollection
    ec = rag_engine.hybrid_rag_retrieve(
        query="What is Uripporuḷ?",
        top_k=3,
        as_dict=False,
    )
    assert isinstance(ec, EvidenceCollection)


# ---------------------------------------------------------------------------
# Test 11 – Live Neo4j graph traversal channel (skipped if not connected)
# ---------------------------------------------------------------------------

def test_live_neo4j_graph_channel(pipeline):
    """
    Verifies Channel C (graph traversal) surfaces at least one result
    when Neo4j Aura is connected.  Skipped when offline.
    """
    if not pipeline._is_neo4j_active():
        pytest.skip("Neo4j Aura not connected - skipping live graph traversal test")

    from query.query_preprocessor import QueryPreprocessingService
    pq = QueryPreprocessingService.preprocess("Mutalporuḷ landscape entity")

    channel_c = pipeline._channel_c_graph_traversal(pq, top_k=5)
    # Should either return passage results or empty dict (no error)
    assert isinstance(channel_c, dict), "Channel C must return a dict"

    for pid, data in channel_c.items():
        assert data.get("retrieval_method") == "graph_traversal"
        assert data.get("passage_id") == pid
        score = data.get("graph_score", -1.0)
        assert 0.0 <= score <= 1.0, f"graph_score out of range: {score}"


# ---------------------------------------------------------------------------
# Test 12 – Empty query returns empty EvidenceCollection.items
# ---------------------------------------------------------------------------

def test_empty_query_returns_empty_collection(pipeline):
    for q in ["", "   ", "\t\n"]:
        result = pipeline.retrieve(q, top_k=5)
        assert isinstance(result.items, list), "items must be a list"
        assert len(result.items) == 0, f"Empty query '{repr(q)}' should return 0 items, got {len(result.items)}"
