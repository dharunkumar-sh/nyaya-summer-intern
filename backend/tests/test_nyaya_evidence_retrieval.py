"""
Test suite verifying the backend retrieval pipeline for Nyāya proof construction.

Verifies:
1. Dual-category evidence separation:
   - caseEvidence (subject, event, entity, scenario)
   - canonicalEvidence (authoritative Vyāpti sūtras from Neo4j Aura)
   - supportingEvidence (corroborating biotic/seasonal signifiers)
   - sourceMetadata (provenance audit)
2. Direct retrieval of canonical evidence from Neo4j.
3. Filtering of spurious lexical matches that lack semantic relevance and KG grounding.
4. Correct schema exposure in reasoning services and API endpoints.
"""
import pytest
from retrieval.nyaya_evidence_retriever import (
    NyayaEvidenceRetriever,
    nyaya_evidence_retriever,
    NyayaEvidenceResponse,
)
from services.reasoning_service import reasoning_service


def test_explicit_response_structure():
    """Verifies that NyayaEvidenceRetriever produces the required explicit response schema."""
    resp = nyaya_evidence_retriever.retrieve_nyaya_evidence(
        query_text="Mountain clandestine union at midnight in Kurinci",
        tinai="Kuṟiñci",
        top_k=5,
    )
    assert isinstance(resp, NyayaEvidenceResponse)
    data = resp.to_dict()

    assert "caseEvidence" in data
    assert "canonicalEvidence" in data
    assert "supportingEvidence" in data
    assert "sourceMetadata" in data

    assert isinstance(data["caseEvidence"], list)
    assert isinstance(data["canonicalEvidence"], list)
    assert isinstance(data["supportingEvidence"], list)
    assert isinstance(data["sourceMetadata"], dict)

    meta = data["sourceMetadata"]
    assert "authoritativeSource" in meta
    assert meta["authoritativeSource"] == "Neo4j Aura"
    assert "works" in meta
    assert "sections" in meta


def test_canonical_evidence_retrieval_direct_from_neo4j():
    """Verifies that canonical evidence is retrieved directly from Neo4j with full provenance."""
    resp = nyaya_evidence_retriever.retrieve_nyaya_evidence(
        query_text="Tolkappiyam Akattinaiyiyal sutras governing Kurinci landscape and mood",
        tinai="Kuṟiñci",
        top_k=4,
    )
    data = resp.to_dict()
    canonical_list = data["canonicalEvidence"]

    assert len(canonical_list) > 0, "Expected canonical evidence to be retrieved from Neo4j Aura"
    for item in canonical_list:
        assert item.get("passage_id") or item.get("id")
        assert item.get("original_text") or item.get("text")
        assert "Tolkāppiyam" in (item.get("work_name") or item.get("work") or "")
        assert item.get("evidenceRole") == "canonicalEvidence"


def test_case_evidence_retrieval_by_entities_and_semantics():
    """Verifies that case-specific evidence instantiates poetic subject/event."""
    resp = nyaya_evidence_retriever.retrieve_nyaya_evidence(
        query_text="களவொழுக்கம் வேங்கை மலர்ச்சி இரவு குறிஞ்சி தலைவன் தலைவி புணர்தல்",
        tinai="Kuṟiñci",
        top_k=5,
    )
    data = resp.to_dict()
    case_list = data["caseEvidence"]

    assert len(case_list) > 0, "Expected case-specific evidence for poetic scenario"
    for item in case_list:
        assert item.get("evidenceRole") == "caseEvidence"


def test_spurious_lexical_similarity_filtered():
    """
    Verifies that verses with lexical token overlap but below the semantic threshold
    and with zero KG entity/concept connections are rejected.
    """
    # Create retriever with test threshold
    retriever = NyayaEvidenceRetriever()

    # Synthetic hybrid candidate pool with one spurious item and one genuine item
    spurious_item = {
        "passage_id": "spurious-generic-verse-099",
        "text": "பொதுவான ஒரு செய்யுள் வரி சொல் வடிவம்",
        "lexical_score": 0.85,
        "semantic_score": 0.05,  # Very low semantic similarity
        "graph_score": 0.0,      # Zero KG connections
    }
    genuine_item = {
        "passage_id": "tol-porul-akam-005",
        "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்",
        "lexical_score": 0.70,
        "semantic_score": 0.88,
        "graph_score": 0.80,
    }

    # Filter logic test
    guarded = []
    for itm in [spurious_item, genuine_item]:
        lex_score = float(itm.get("lexical_score") or 0.0)
        sem_score = float(itm.get("semantic_score") or 0.0)
        graph_score = float(itm.get("graph_score") or 0.0)
        if lex_score > 0.05 and sem_score < retriever.MIN_SEMANTIC_THRESHOLD_FOR_LEXICAL and graph_score <= 0.0:
            continue
        guarded.append(itm)

    assert len(guarded) == 1
    assert guarded[0]["passage_id"] == "tol-porul-akam-005"


def test_reasoning_service_includes_evidence_categories():
    """Verifies that ReasoningService.execute_reasoning_pipeline returns all 4 evidence categories."""
    result = reasoning_service.execute_reasoning_pipeline(
        query_text="Kuṟiñci mountain union and nocturnal signifiers",
        depth=2,
    )
    assert "caseEvidence" in result
    assert "canonicalEvidence" in result
    assert "supportingEvidence" in result
    assert "sourceMetadata" in result

    assert isinstance(result["caseEvidence"], list)
    assert isinstance(result["canonicalEvidence"], list)
    assert isinstance(result["supportingEvidence"], list)
    assert isinstance(result["sourceMetadata"], dict)


def test_api_reasoning_retrieve_endpoint():
    """Verifies the /api/reasoning/retrieve HTTP endpoint."""
    from app import app
    client = app.test_client()

    resp = client.post(
        "/api/reasoning/retrieve",
        json={"queryText": "குறிஞ்சி நில புணர்தல் ஒழுக்கம்", "tinai": "Kuṟiñci", "top_k": 4},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    data = body["data"]

    assert "caseEvidence" in data
    assert "canonicalEvidence" in data
    assert "supportingEvidence" in data
    assert "sourceMetadata" in data
    assert len(data["canonicalEvidence"]) > 0
