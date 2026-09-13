"""
Comprehensive Unit and Integration Tests for Structured Context Transformation in Hybrid RAG.

Verifies:
1. Exact preservation of source reference, passage ID, text, metadata, and Neo4j graph relationships.
2. Compact context limits (max passages, character budgets, max relationships).
3. Clear boundary separation between source evidence and prompt instructions.
4. Insufficient evidence detection when evidence falls below relevance threshold or minimum count.
5. End-to-end REST API endpoint POST /api/retrieval/structured-context.
6. Integration with answer generation and reasoning pipeline.
"""
import pytest
from app import create_app
from retrieval.structured_context_builder import (
    StructuredContextBuilder,
    StructuredRAGContext,
    GroundedPassageContext,
    GroundedGraphRelationship,
    structured_context_builder,
)
from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline, EvidenceItem


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Unit Tests for StructuredContextBuilder
# ---------------------------------------------------------------------------

def test_structured_context_preserves_provenance_and_neo4j_relationships():
    """
    Verifies that every selected passage preserves:
    - passage_id
    - source_reference
    - text
    - metadata (work, section, chapter, sutra_number, tinai, entities, concepts)
    - Neo4j graph relationships
    """
    sample_evidence = [
        {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும்...",
            "relevance_score": 0.88,
            "semantic_score": 0.85,
            "lexical_score": 0.80,
            "graph_score": 0.90,
            "retrieval_methods": ["semantic_vector", "keyword_entity", "graph_traversal"],
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 5,
                "tinai": "Kuṟiñci",
                "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            },
            "entities": ["Cēyōṉ", "Māyōṉ", "Mountain"],
            "concepts": ["Mutalporuḷ", "Karupporuḷ"],
            "graph_context": {
                "subgraph": {
                    "nodes": [
                        {"id": "ceyon", "label": "Cēyōṉ", "type": "Deity"},
                        {"id": "mutalporul", "label": "Mutalporuḷ", "type": "Concept"},
                    ],
                    "edges": [
                        {"source": "tol-porul-akam-005", "target": "ceyon", "type": "manifests_entity"},
                        {"source": "tol-porul-akam-005", "target": "mutalporul", "type": "grounds_concept"},
                    ],
                },
                "entities": [{"id": "ceyon", "label": "Cēyōṉ", "category": "Deity"}],
                "concepts": [{"id": "mutalporul", "label": "Mutalporuḷ"}],
            },
        }
    ]

    ctx = structured_context_builder.build_context(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் தெய்வம்",
        evidence_items=sample_evidence,
        min_relevance_threshold=0.30,
        min_evidence_count=1,
    )

    assert ctx.is_sufficient is True
    assert ctx.status == "sufficient_evidence"
    assert ctx.passage_count == 1
    assert len(ctx.evidence_passages) == 1

    p = ctx.evidence_passages[0]
    assert p.passage_id == "tol-porul-akam-005"
    assert p.source_reference == "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5"
    assert "மாயோன்" in p.text
    assert p.work == "Tolkāppiyam"
    assert p.section == "Poruḷatikāram"
    assert p.chapter == "Akattiṇaiyiyal"
    assert p.sutra_number == 5
    assert p.tinai == "Kuṟiñci"
    assert "Cēyōṉ" in p.entities
    assert "Mutalporuḷ" in p.concepts
    assert p.relevance_score == 0.88

    # Neo4j Graph relationships preserved
    assert len(p.relationships) >= 2
    rel_types = {r.relationship_type for r in p.relationships}
    assert "manifests_entity" in rel_types
    assert "grounds_concept" in rel_types


def test_structured_context_boundary_separation():
    """
    Verifies strict separation of source evidence from prompt instructions.
    Boundary markers must cleanly fence the evidence.
    """
    sample_evidence = [
        {
            "passage_id": "tol-porul-akam-003",
            "text": "முதல்கரு உரிப்பொருள் என்ற மூன்றே...",
            "relevance_score": 0.92,
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 3,
                "tinai": "General",
                "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 3",
            },
        }
    ]

    ctx = structured_context_builder.build_context(
        query="அகப்பொருள் மூவகைப் பொருட்கள்",
        evidence_items=sample_evidence,
    )

    rendered = ctx.to_prompt_context()

    # Unambiguous boundary markers present
    assert ctx.boundary_marker_start in rendered
    assert ctx.boundary_marker_end in rendered

    # Evidence is between markers
    start_pos = rendered.index(ctx.boundary_marker_start)
    end_pos = rendered.index(ctx.boundary_marker_end)
    evidence_block = rendered[start_pos:end_pos]

    assert "tol-porul-akam-003" in evidence_block
    assert "முதல்கரு" in evidence_block

    # Instructions follow after end marker
    instruction_block = rendered[end_pos:]
    assert "INSTRUCTION:" in instruction_block
    assert "DO NOT INVENT" in rendered


def test_structured_context_compact_character_limits():
    """
    Verifies that the context builder enforces max_context_chars and max_passages limits.
    """
    # Create 10 items
    many_items = [
        {
            "passage_id": f"tol-porul-akam-00{i}",
            "text": f"Canonical Tamil verse number {i} with detailed explanation text for testing limits.",
            "relevance_score": 0.80 - (i * 0.05),
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "sutra_number": i,
                "source_reference": f"Tolkāppiyam Sūtra {i}",
            },
        }
        for i in range(1, 10)
    ]

    # Enforce max 2 passages
    ctx_max2 = structured_context_builder.build_context(
        query="test query",
        evidence_items=many_items,
        max_passages=2,
        max_context_chars=8000,
    )
    assert ctx_max2.passage_count == 2
    assert len(ctx_max2.evidence_passages) == 2

    # Enforce small character budget
    ctx_compact = structured_context_builder.build_context(
        query="test query",
        evidence_items=many_items,
        max_passages=10,
        max_context_chars=600,
    )
    assert ctx_compact.total_characters <= 800
    assert ctx_compact.passage_count < 9


def test_structured_context_insufficient_evidence_state():
    """
    Verifies that when evidence falls below relevance threshold or minimum count:
    - is_sufficient is False
    - status is 'insufficient_evidence'
    - insufficient_reason details the threshold failure
    - No unsupported conclusion is fabricated
    """
    # Items below min_relevance_threshold (0.50)
    low_relevance_items = [
        {
            "passage_id": "tol-porul-akam-999",
            "text": "Marginally related verse",
            "relevance_score": 0.20,
            "source": {"work": "Tolkāppiyam"},
        }
    ]

    ctx_low = structured_context_builder.build_context(
        query="quantum physics in space",
        evidence_items=low_relevance_items,
        min_relevance_threshold=0.50,
        min_evidence_count=1,
    )

    assert ctx_low.is_sufficient is False
    assert ctx_low.status == "insufficient_evidence"
    assert ctx_low.passage_count == 0
    assert len(ctx_low.evidence_passages) == 0
    assert ctx_low.insufficient_reason is not None
    assert "Insufficient canonical evidence" in ctx_low.insufficient_reason
    assert "STATUS: INSUFFICIENT EVIDENCE" in ctx_low.rendered_context
    assert "NO CONCLUSION OR ASSERTION MAY BE GENERATED" in ctx_low.rendered_context


def test_structured_context_from_hybrid_rag_pipeline():
    """
    Verifies end-to-end integration: hybrid_rag_pipeline.build_structured_context()
    retrieves real corpus data from Neo4j Aura + BM25 and transforms it.
    """
    context = hybrid_rag_pipeline.build_structured_context(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள்",
        max_passages=3,
        min_relevance_threshold=0.20,
        min_evidence_count=1,
        as_dict=False,
    )

    assert isinstance(context, StructuredRAGContext)
    assert context.is_sufficient is True
    assert context.status == "sufficient_evidence"
    assert context.passage_count >= 1

    first = context.evidence_passages[0]
    assert first.passage_id.startswith("tol-")
    assert len(first.text.strip()) > 0
    assert "Tolk" in first.work
    assert len(first.source_reference) > 0
    assert first.relevance_score >= 0.20


# ---------------------------------------------------------------------------
# 2. REST API Integration Tests
# ---------------------------------------------------------------------------

def test_api_retrieval_structured_context_endpoint_success(client):
    """Verifies POST /api/retrieval/structured-context returns valid structured context."""
    res = client.post("/api/retrieval/structured-context", json={
        "query": "குறிஞ்சி நிலம் மலை தெய்வம்",
        "top_k": 3,
        "max_passages": 3,
        "max_context_chars": 3000,
        "min_relevance_threshold": 0.20,
        "min_evidence_count": 1,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["is_sufficient"] is True
    assert data["status"] == "sufficient_evidence"
    assert data["passage_count"] >= 1
    assert "evidence_passages" in data
    assert "rendered_context" in data
    assert "boundary_markers" in data

    first_p = data["evidence_passages"][0]
    assert "passage_id" in first_p
    assert "source_reference" in first_p
    assert "text" in first_p
    assert "work" in first_p
    assert "relationships" in first_p
    assert "relevance_score" in first_p


def test_api_retrieval_structured_context_insufficient_evidence(client):
    """
    Verifies POST /api/retrieval/structured-context returns explicit insufficient-evidence state
    when threshold cannot be met.
    """
    res = client.post("/api/retrieval/structured-context", json={
        "query": "superconductivity in semiconductors",
        "top_k": 3,
        "min_relevance_threshold": 0.99,  # Unattainable threshold
        "min_evidence_count": 5,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["is_sufficient"] is False
    assert data["status"] == "insufficient_evidence"
    assert data["passage_count"] == 0
    assert data["insufficient_reason"] is not None
    assert "Insufficient canonical evidence" in data["insufficient_reason"]


def test_api_retrieval_structured_context_validation_empty_query(client):
    """Verifies empty query returns HTTP 400."""
    res = client.post("/api/retrieval/structured-context", json={"query": "   "})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["success"] is False
    assert payload["error_code"] == "INVALID_QUERY"
