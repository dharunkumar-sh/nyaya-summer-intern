"""
Comprehensive test suite for the Proof-Trace Service.

Tests cover:
1.  ProofTracePayload, ProofTraceStep, and ProofTraceEdge dataclass fields and serialization.
2.  Insufficient-evidence state detection when 0 evidence items are provided.
3.  Insufficient-evidence state detection when only 1 evidence item is provided (threshold=2).
4.  Valid proof trace generation when >= 2 evidence items are provided.
5.  Traceability verification: unbroken directed path from C1 back to E1 and E2.
6.  Step-by-step chaining: valid relationship_to_next and target_step_id for intermediate steps.
7.  Explanation and source citation completeness on every proof step.
8.  Frontend compatibility: proofNodes and proofEdges structure matching React expectations.
9.  ReasoningService integration with insufficient evidence: no conclusion fabricated.
10. ReasoningService integration with sufficient evidence: complete proof trace and edges returned.
11. Flask API endpoints: POST /api/reasoning/proof-trace and POST /api/reasoning/deduce.
"""
import sys
import pathlib
import pytest

backend = str(pathlib.Path(__file__).resolve().parent.parent)
if backend not in sys.path:
    sys.path.insert(0, backend)

from reasoning.models import (
    ProofTraceStep,
    ProofTraceEdge,
    ProofTracePayload,
)
from reasoning.proof_trace import ProofTraceGenerator
from services.proof_trace_service import ProofTraceService, proof_trace_service
from services.reasoning_service import reasoning_service


# ---------------------------------------------------------------------------
# Test 1 – ProofTrace Dataclasses Structure
# ---------------------------------------------------------------------------

def test_proof_trace_dataclass_structure():
    step = ProofTraceStep(
        id="E1",
        type="Evidence",
        name="Canonical Sūtra",
        source_reference="Tolkāppiyam Sūtra 3",
        passage_id="tol-porul-akam-003",
        relationship_to_next="GROUNDS_PREMISE",
        relationship_label="grounds premise",
        target_step_id="P1",
        explanation="Canonical verse grounding terrestrial habitat.",
        formal_logic="Evidence(E1) : Verse(x)",
        confidence=0.98,
    )
    d_step = step.to_dict()
    assert d_step["id"] == "E1"
    assert d_step["relationshipToNext"] == "GROUNDS_PREMISE"
    assert d_step["targetStepId"] == "P1"
    assert d_step["passageId"] == "tol-porul-akam-003"

    edge = ProofTraceEdge(
        id="pe_E1_P1",
        source="E1",
        target="P1",
        label="grounds premise",
        type="GROUNDS_PREMISE",
        relation="GROUNDS_PREMISE",
        confidence=0.98,
        isProofTraceEdge=True,
    )
    d_edge = edge.to_dict()
    assert d_edge["id"] == "pe_E1_P1"
    assert d_edge["isProofTraceEdge"] is True


# ---------------------------------------------------------------------------
# Test 2 & 3 – Insufficient Evidence State
# ---------------------------------------------------------------------------

def test_insufficient_evidence_state_when_empty():
    payload = proof_trace_service.generate_proof_trace(
        query_text="What is this obscure concept?",
        evidence_items=[],
        min_evidence_threshold=2,
    )
    assert payload.status == "INSUFFICIENT_EVIDENCE"
    assert payload.is_valid is False
    assert payload.insufficient_evidence is True
    assert payload.conclusion_id is None
    assert len(payload.nodes) == 0
    assert len(payload.edges) == 0
    assert len(payload.steps) == 0
    assert len(payload.missing_requirements) >= 1
    assert "At least 2" in payload.reason

    d = payload.to_dict()
    assert d["insufficientEvidence"] is True
    assert d["conclusionId"] is None


def test_insufficient_evidence_state_when_single_item():
    single_item = [{"passage_id": "tol-single-01", "text": "Only one verse retrieved"}]
    payload = proof_trace_service.generate_proof_trace(
        query_text="Partial query",
        evidence_items=single_item,
        min_evidence_threshold=2,
    )
    assert payload.status == "INSUFFICIENT_EVIDENCE"
    assert payload.insufficient_evidence is True
    assert payload.evidence_count == 1
    assert payload.conclusion_id is None


# ---------------------------------------------------------------------------
# Test 4 – Valid Proof Trace with Sufficient Evidence
# ---------------------------------------------------------------------------

def test_valid_proof_trace_with_sufficient_evidence():
    evidence_items = [
        {
            "passage_id": "tol-porul-akam-003",
            "text": "முதலும் கருவும் உரிப்பொருளோடு இணையும் செய்யுள் நெறி.",
            "source": {"reference": "Tolkāppiyam Sūtra 3", "tinai": "Kuṟiñci"},
        },
        {
            "passage_id": "tol-porul-akam-005",
            "text": "சேயோன் மேய மைவரை உலகம் குறிஞ்சி நிலமாகும்.",
            "source": {"reference": "Tolkāppiyam Sūtra 5", "tinai": "Kuṟiñci"},
        },
    ]

    payload = proof_trace_service.generate_proof_trace(
        query_text="Kuṟiñci love poetics",
        tinai="Kuṟiñci",
        evidence_items=evidence_items,
        min_evidence_threshold=2,
    )

    assert payload.status == "VALID_PROOF"
    assert payload.is_valid is True
    assert payload.insufficient_evidence is False
    assert payload.conclusion_id == "C1"
    assert payload.evidence_count == 2
    assert len(payload.nodes) == 7
    assert len(payload.edges) >= 6
    assert len(payload.steps) == 7


# ---------------------------------------------------------------------------
# Test 5 – Traceability from Conclusion to Source Evidence
# ---------------------------------------------------------------------------

def test_traceability_from_conclusion_to_source_evidence():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "text": "Text 3"},
        {"passage_id": "tol-porul-akam-005", "text": "Text 5"},
    ]

    payload = proof_trace_service.generate_proof_trace(
        query_text="Kuṟiñci poetics",
        evidence_items=evidence_items,
    )

    assert payload.is_valid is True
    assert len(payload.traceable_paths) > 0

    # Ensure path goes from E1 -> P1 -> E2 -> P2 -> R1 -> I1 -> C1
    path_found = False
    for p in payload.traceable_paths:
        if p[0] == "E1" and p[-1] == "C1":
            path_found = True
            break
    assert path_found, f"Expected path from E1 to C1, got {payload.traceable_paths}"


# ---------------------------------------------------------------------------
# Test 6 & 7 – Step-by-Step Chaining and Explanations
# ---------------------------------------------------------------------------

def test_step_relationship_to_next_and_explanations():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "text": "Text 3", "source": {"reference": "Tolkāppiyam Sūtra 3"}},
        {"passage_id": "tol-porul-akam-005", "text": "Text 5", "source": {"reference": "Tolkāppiyam Sūtra 5"}},
    ]

    payload = proof_trace_service.generate_proof_trace(
        query_text="Kuṟiñci poetics",
        evidence_items=evidence_items,
    )

    step_dict = {s.id: s for s in payload.steps}

    # E1 connects to P1
    assert step_dict["E1"].target_step_id == "P1"
    assert step_dict["E1"].relationship_to_next == "GROUNDS_PREMISE"
    assert step_dict["E1"].passage_id == "tol-porul-akam-003"
    assert len(step_dict["E1"].explanation) > 0

    # P1 connects to E2
    assert step_dict["P1"].target_step_id == "E2"
    assert step_dict["P1"].relationship_to_next == "CORROBORATED_BY"

    # E2 connects to P2
    assert step_dict["E2"].target_step_id == "P2"
    assert step_dict["E2"].passage_id == "tol-porul-akam-005"

    # P2 connects to R1
    assert step_dict["P2"].target_step_id == "R1"

    # R1 connects to I1
    assert step_dict["R1"].target_step_id == "I1"

    # I1 connects to C1
    assert step_dict["I1"].target_step_id == "C1"
    assert step_dict["I1"].relationship_to_next == "ENTAILS_CONCLUSION"

    # C1 is the terminal conclusion
    assert step_dict["C1"].target_step_id is None
    assert step_dict["C1"].relationship_to_next is None


# ---------------------------------------------------------------------------
# Test 8 – Frontend Compatibility (Cytoscape & SVG Layout)
# ---------------------------------------------------------------------------

def test_proof_nodes_and_edges_frontend_schema():
    evidence_items = [
        {"passage_id": "tol-01", "text": "Verse 1"},
        {"passage_id": "tol-02", "text": "Verse 2"},
    ]
    payload = proof_trace_service.generate_proof_trace(
        query_text="Kuṟiñci",
        evidence_items=evidence_items,
    )

    # Check SVG coordinates on nodes
    cx_values = [n["cx"] for n in payload.nodes]
    assert cx_values == [32, 112, 192, 272, 352, 432, 508]

    # Check color badges on nodes
    for n in payload.nodes:
        assert "color" in n
        assert "bg" in n
        assert "lightBg" in n
        assert "border" in n
        assert "text" in n

    # Check proofEdges schema
    trace_edges = [e for e in payload.edges if e["isProofTraceEdge"]]
    assert len(trace_edges) == 6
    edge_ids = [e["id"] for e in trace_edges]
    assert edge_ids == [
        "pe_E1_P1", "pe_P1_E2", "pe_E2_P2", "pe_P2_R1", "pe_R1_I1", "pe_I1_C1"
    ]


# ---------------------------------------------------------------------------
# Test 9 – ReasoningService Insufficient Evidence Handling
# ---------------------------------------------------------------------------

def test_reasoning_service_insufficient_evidence():
    # Patch query_service to return 0 evidence items
    from unittest.mock import patch

    with patch("services.reasoning_service.query_service.process_query") as mock_query, \
         patch("retrieval.hybrid_rag_pipeline.hybrid_rag_pipeline.retrieve") as mock_retrieval:
        mock_query.return_value = {
            "query_text": "Non-existent inquiry",
            "detected_tinai": "Kuṟiñci",
            "evidence_records": [],
            "knowledge_graph": {"nodes": [], "edges": []},
        }
        mock_retrieval.return_value = None

        result = reasoning_service.execute_reasoning_pipeline("Non-existent inquiry")

        assert result["insufficientEvidence"] is True
        assert result["conclusion"] is None
        assert result["reasoningTrace"] is None
        assert result["validationResults"]["soundnessScore"] == 0.0
        assert result["validationResults"]["fallacies"]["asiddha"] == 1.0
        assert len(result["proofNodes"]) == 0
        assert len(result["proofEdges"]) == 0
        assert result["proofTrace"]["insufficientEvidence"] is True


# ---------------------------------------------------------------------------
# Test 10 – ReasoningService Sufficient Evidence
# ---------------------------------------------------------------------------

def test_reasoning_service_sufficient_evidence():
    result = reasoning_service.execute_reasoning_pipeline(
        query_text="குறிஞ்சி நிலத்து புணர்தல் ஒழுக்கம்",
        depth=2,
    )
    assert result["insufficientEvidence"] is False
    assert result["conclusion"] is not None
    assert len(result["proofNodes"]) == 7
    assert len(result["proofEdges"]) >= 6
    assert "proofTrace" in result
    assert result["proofTrace"]["isValid"] is True
    assert len(result["traceSteps"]) == 7


# ---------------------------------------------------------------------------
# Test 11 – Flask API Endpoints
# ---------------------------------------------------------------------------

def test_proof_trace_api_endpoint():
    from app import app
    client = app.test_client()

    # Test POST /api/reasoning/proof-trace with insufficient evidence
    resp_insufficient = client.post(
        "/api/reasoning/proof-trace",
        json={"queryText": "Empty test", "evidenceItems": []},
    )
    assert resp_insufficient.status_code == 200
    data_insufficient = resp_insufficient.get_json()["data"]
    assert data_insufficient["insufficientEvidence"] is True
    assert data_insufficient["status"] == "INSUFFICIENT_EVIDENCE"

    # Test POST /api/reasoning/proof-trace with sufficient evidence
    evidence_payload = [
        {"passage_id": "tol-porul-akam-003", "text": "Passage 1"},
        {"passage_id": "tol-porul-akam-005", "text": "Passage 2"},
    ]
    resp_valid = client.post(
        "/api/reasoning/proof-trace",
        json={"queryText": "Valid test", "evidenceItems": evidence_payload},
    )
    assert resp_valid.status_code == 200
    data_valid = resp_valid.get_json()["data"]
    assert data_valid["insufficientEvidence"] is False
    assert data_valid["status"] == "VALID_PROOF"
    assert len(data_valid["nodes"]) == 7
    assert len(data_valid["edges"]) >= 6
    assert len(data_valid["steps"]) == 7

    # Test POST /api/reasoning/deduce
    resp_deduce = client.post(
        "/api/reasoning/deduce",
        json={"queryText": "Deduce test", "tinai": "Kuṟiñci", "evidenceItems": evidence_payload},
    )
    assert resp_deduce.status_code == 200
    data_deduce = resp_deduce.get_json()["data"]
    assert "proofNodes" in data_deduce
    assert "proofEdges" in data_deduce
    assert "traceSteps" in data_deduce
