"""
Unit and Integration Tests for GraphRetrievalService.

Verifies:
1. Query normalization and canonical seed resolution for entities, concepts, and citations.
2. Configurable hop depth clamping (safe bounds between 1 and 4).
3. Grounded subgraph extraction, node/edge structure, and relationship endpoints validity.
4. Evidence path tracing with cumulative confidence calculations.
5. 4-tier source provenance hierarchy (Literature -> Work -> Section -> Passage).
6. Non-generative verification: Strictly grounded epistemic context with zero answer generation.
7. Dual-mode execution (Neo4j Aura execution and in-memory fallback resilience).
8. Flask API route POST /api/query/graph-retrieval.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.graph_retrieval_service import (
    GraphRetrievalService,
    GraphRetrievalResult,
    EvidencePath,
    graph_retrieval_service,
)
from query.query_preprocessor import query_preprocessor, ProcessedQuery
from knowledge_graph.neo4j_repository import Neo4jRepository


# =============================================================================
# 1. Seed Resolution & Input Normalization Tests
# =============================================================================

def test_resolve_seed_nodes_from_processed_query():
    """Tests resolving seeds from a ProcessedQuery object."""
    pq = query_preprocessor.preprocess("குறிஞ்சி நிலத்தின் சேயோன் மற்றும் புணர்தல் ஒழுக்கம்")
    meta, seeds, passages = graph_retrieval_service.resolve_seed_nodes(pq)

    assert "ceyon" in seeds or "kurinci" in seeds
    assert meta["detected_tinai"] == "Kuṟiñci"
    assert meta["original_query"] == "குறிஞ்சி நிலத்தின் சேயோன் மற்றும் புணர்தல் ஒழுக்கம்"


def test_resolve_seed_nodes_from_dict():
    """Tests resolving seeds from a raw dictionary with structured entities and concepts."""
    query_dict = {
        "entities": ["சேயோன்", "வேங்கை"],
        "concepts": ["முதற்பொருள்", "புணர்தல்"],
        "source_references": ["Sūtra 5", "tol-porul-akam-003"],
        "tinai": "Kuṟiñci",
    }
    meta, seeds, passages = graph_retrieval_service.resolve_seed_nodes(query_dict)

    assert "ceyon" in seeds
    assert "mutalporul" in seeds
    assert "punartal" in seeds
    assert "tol-porul-akam-005" in passages or "tol-porul-akam-003" in passages


def test_resolve_seed_nodes_from_raw_string():
    """Tests resolving seeds from a string input with implicit sūtra citation."""
    raw_query = "What does Sūtra 5 say about Māyōṉ and Cēyōṉ in Mullai and Kuṟiñci?"
    meta, seeds, passages = graph_retrieval_service.resolve_seed_nodes(raw_query)

    assert "tol-porul-akam-005" in passages
    assert any(s in seeds for s in ["mayon", "ceyon", "kurinci", "mullai"])


def test_hop_depth_clamping():
    """Tests that hop depth is safely clamped between 1 and 4."""
    # Test depth 0 clamped to 1
    res_min = graph_retrieval_service.retrieve_grounded_graph(
        query_input={"entities": ["ceyon"], "concepts": ["kurinci"]},
        hop_depth=0,
    )
    assert res_min.query_summary["hop_depth"] == 1

    # Test depth 10 clamped to 4
    res_max = graph_retrieval_service.retrieve_grounded_graph(
        query_input={"entities": ["ceyon"], "concepts": ["kurinci"]},
        hop_depth=10,
    )
    assert res_max.query_summary["hop_depth"] == 4


# =============================================================================
# 2. In-Memory Fallback Grounded Retrieval Tests
# =============================================================================

def test_in_memory_retrieval_structure():
    """Verifies complete structure of GraphRetrievalResult from in-memory engine."""
    result = graph_retrieval_service.retrieve_grounded_graph(
        query_input={
            "query": "முல்லை நிலத்தில் மாயோன்",
            "entities": ["மாயோன்"],
            "concepts": ["முல்லை", "முதற்பொருள்"],
            "sources": ["Sūtra 5"],
        },
        hop_depth=2,
    )

    assert isinstance(result, GraphRetrievalResult)
    data = result.to_dict()

    # Verify query summary
    assert "seed_node_ids" in data["query_summary"]
    assert data["query_summary"]["hop_depth"] == 2
    assert data["query_summary"]["retrieval_source"] in ("in_memory_fallback", "neo4j_aura")

    # Verify passages
    assert len(data["passages"]) > 0
    first_passage = data["passages"][0]
    assert "id" in first_passage
    assert "text" in first_passage
    assert "translation" in first_passage
    assert "source_reference" in first_passage

    # Verify nodes & relationships in subgraph
    subgraph = data["subgraph"]
    assert "nodes" in subgraph and len(subgraph["nodes"]) > 0
    assert "edges" in subgraph

    # Verify edge endpoint integrity
    node_ids = {n["id"] for n in subgraph["nodes"]}
    for edge in subgraph["edges"]:
        assert edge["source"] in node_ids, f"Edge source {edge['source']} not in node IDs"
        assert edge["target"] in node_ids, f"Edge target {edge['target']} not in node IDs"
        assert "confidence" in edge
        assert 0.0 <= edge["confidence"] <= 1.0


def test_provenance_hierarchy():
    """Verifies that 4-tier provenance is constructed for each returned passage."""
    result = graph_retrieval_service.retrieve_grounded_graph(
        query_input={"source_references": ["tol-porul-akam-005"]},
        hop_depth=2,
    )

    prov = result.provenance
    assert "tol-porul-akam-005" in prov
    p_rec = prov["tol-porul-akam-005"]

    assert p_rec["literature"]["level"] == "L0"
    assert p_rec["work"]["level"] == "L1"
    assert p_rec["section"]["level"] == "L2"
    assert p_rec["passage"]["level"] == "L3"
    assert len(p_rec["chain"]) == 4


def test_strictly_non_generative():
    """
    Verifies that the epistemic context is strictly grounded and NO synthetic
    natural language answers are generated by this service.
    """
    result = graph_retrieval_service.retrieve_grounded_graph(
        query_input="குறிஞ்சி நிலத்தின் உரிப்பொருள் புணர்தல் ஒழுக்கம் விளக்குக",
        hop_depth=2,
    )

    epistemic = result.epistemic_context
    assert epistemic["strictly_grounded"] is True
    assert epistemic["answer_generated"] is False
    assert "answer" not in epistemic
    assert "summary" not in epistemic
    assert isinstance(epistemic["premises"], list)
    assert isinstance(epistemic["grounded_axioms"], list)


def test_evidence_paths_confidence():
    """Tests evidence paths discovery and cumulative confidence propagation."""
    result = graph_retrieval_service.retrieve_grounded_graph(
        query_input={"entities": ["ceyon"], "concepts": ["kurinci"]},
        hop_depth=2,
    )

    paths = result.evidence_paths
    if paths:
        first_path = paths[0]
        assert "start_id" in first_path
        assert "target_id" in first_path
        assert "cumulative_confidence" in first_path
        assert 0.0 <= first_path["cumulative_confidence"] <= 1.0
        assert "nodes" in first_path
        assert "edges" in first_path


# =============================================================================
# 3. Neo4j Mocked Execution & Fallback Recovery Tests
# =============================================================================

def test_neo4j_aura_retrieval_when_available():
    """Tests retrieval path when Neo4j Aura repository is available."""
    mock_repo = MagicMock(spec=Neo4jRepository)
    mock_repo.is_available.return_value = True

    mock_repo.traverse_multi_hop.return_value = [
        {
            "start_id": "ceyon",
            "target_id": "kurinci",
            "length": 1,
            "propagated_confidence": 0.95,
            "nodes": [
                {"id": "ceyon", "label": "Cēyōṉ", "type": "Entity", "hierarchy_level": "L5"},
                {"id": "kurinci", "label": "Kuṟiñci", "type": "Concept", "hierarchy_level": "L4"},
            ],
            "relationships": [
                {"type": "GROUNDS_LANDSCAPE", "confidence": 0.95}
            ],
        }
    ]
    mock_repo.get_evidence_paths.return_value = [
        {
            "start_id": "ceyon",
            "target_id": "tol-porul-akam-005",
            "ground_id": "tol-porul-akam-005",
            "ground_type": "Passage",
            "length": 1,
            "confidence": 0.95,
            "nodes": [
                {"id": "ceyon", "label": "Cēyōṉ", "type": "Entity"},
                {"id": "tol-porul-akam-005", "label": "Sūtra 5", "type": "Passage"},
            ],
            "edges": [{"type": "MENTIONS", "confidence": 0.95}],
        }
    ]
    mock_repo.get_literary_context_for_passage.return_value = {
        "passage": {
            "id": "tol-porul-akam-005",
            "sutra_number": 5,
            "chapter_name": "Akattiṇaiyiyal",
            "work_name": "Tolkāppiyam",
            "source_reference": "Tolkāppiyam, Akattiṇaiyiyal, Sūtra 5",
            "original_text": "மாயோன் மேய காடுறை உலகமும்...",
            "translation": "The forest world presided over by Māyōṉ...",
            "tinai": "Mullai / Kuṟiñci",
        },
        "provenance_path": [
            {"id": "lit-sangam", "label": "Classical Tamil Sangam Literature", "type": "Literature", "hierarchy_level": "L0"},
            {"id": "work-tolkappiyam", "label": "Tolkāppiyam", "type": "Work", "hierarchy_level": "L1"},
            {"id": "sec-porul-akam", "label": "Akattiṇaiyiyal", "type": "Section", "hierarchy_level": "L2"},
            {"id": "tol-porul-akam-005", "label": "Sūtra 5", "type": "Passage", "hierarchy_level": "L3"},
        ],
        "concepts": [{"id": "kurinci", "label": "Kuṟiñci"}],
        "entities": [{"id": "ceyon", "label": "Cēyōṉ"}],
    }

    service = GraphRetrievalService(neo4j_repo=mock_repo)
    result = service.retrieve_grounded_graph(
        query_input={"entities": ["ceyon"], "sources": ["tol-porul-akam-005"]},
        hop_depth=2,
    )

    assert result.query_summary["retrieval_source"] == "neo4j_aura"
    assert "tol-porul-akam-005" in result.passage_ids
    assert len(result.nodes) >= 2
    mock_repo.traverse_multi_hop.assert_called()


def test_neo4j_error_graceful_fallback():
    """Tests that if Neo4j raises an exception, the service recovers via in-memory fallback."""
    mock_repo = MagicMock(spec=Neo4jRepository)
    mock_repo.is_available.return_value = True
    mock_repo.traverse_multi_hop.side_effect = RuntimeError("Neo4j Aura Connection Timeout")

    service = GraphRetrievalService(neo4j_repo=mock_repo)
    result = service.retrieve_grounded_graph(
        query_input={"entities": ["ceyon"], "concepts": ["kurinci"]},
        hop_depth=2,
    )

    # Should recover gracefully rather than failing
    assert result is not None
    assert "recovery" in result.query_summary["retrieval_source"] or result.query_summary["retrieval_source"] == "in_memory_fallback"
    assert len(result.nodes) > 0


# =============================================================================
# 4. REST API Endpoint Tests (/api/query/graph-retrieval)
# =============================================================================

def test_api_graph_retrieval_endpoint():
    """Tests the Flask REST endpoint POST /api/query/graph-retrieval."""
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        payload = {
            "query": "குறிஞ்சி நிலத்தின் சேயோன் ஒழுக்கம்",
            "entities": ["சேயோன்"],
            "concepts": ["முதற்பொருள்", "உரிப்பொருள்"],
            "sources": ["Sūtra 5"],
            "hopDepth": 2,
        }
        res = client.post("/api/query/graph-retrieval", json=payload)
        assert res.status_code == 200

        data = res.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "query_summary" in data["data"]
        assert "passage_ids" in data["data"]
        assert "passages" in data["data"]
        assert "nodes" in data["data"]
        assert "relationships" in data["data"]
        assert "provenance" in data["data"]
        assert "epistemic_context" in data["data"]
        assert data["data"]["epistemic_context"]["strictly_grounded"] is True
        assert data["data"]["epistemic_context"]["answer_generated"] is False
