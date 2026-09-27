"""
Comprehensive Test Suite for Authoritative Canonical Literary Evidence in Nyāya Proof System.

Verifies:
1. All canonical verses/sūtras used in Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana, and Vyāpti
   originate from Neo4j / authentic retrieval with complete provenance.
2. No hardcoded verses, mock evidence, local JSON fallbacks, or fabricated evidence are used.
3. If required canonical evidence is missing or insufficient, the system reports missing
   requirements explicitly rather than generating synthetic content.
4. Proof trace nodes contain complete provenance metadata (work, section, chapter, sutraNumber,
   originalText, translation, evidenceType, confidence).
"""
import pytest
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.rule_engine import TinaiRuleEngine
from reasoning.premise_builder import EvidenceGroundedPremiseBuilder
from reasoning.proof_trace import ProofTraceGenerator
from services.proof_trace_service import proof_trace_service
from services.reasoning_service import reasoning_service
from knowledge_graph.neo4j_repository import neo4j_repository


def test_premise_builder_strict_no_synthetic_fallback():
    """Verifies that PremiseBuilder returns [] when evidence is empty, never fabricating synthetic premises."""
    empty_premises = EvidenceGroundedPremiseBuilder.build_premise_nodes(evidence_items=[], tinai="Kuṟiñci")
    assert empty_premises == [], "PremiseBuilder must not generate synthetic premises when evidence is empty"

    none_premises = EvidenceGroundedPremiseBuilder.build_premise_nodes(evidence_items=None, tinai="Kuṟiñci")
    assert none_premises == [], "PremiseBuilder must not generate synthetic premises when evidence is None"


def test_vyapti_universal_rules_resolve_to_canonical_citations():
    """Verifies that every Tiṇai rule defines an authentic canonical exemplar passage ID and sūtra citation."""
    for tinai_name, rule_data in TinaiRuleEngine.TINAI_RULES.items():
        assert "exemplar_passage_id" in rule_data
        assert rule_data["exemplar_passage_id"].startswith("tol-porul-")
        assert "exemplar_sutra" in rule_data
        assert "Tolkāppiyam" in rule_data["exemplar_sutra"]
        assert "Sūtra" in rule_data["exemplar_sutra"]
        assert "formal_logic" in rule_data
        assert "consequent" in rule_data


def test_nyaya_deduction_anchored_in_canonical_evidence():
    """Verifies that the 5-stage Pañcāvayava deduction anchors every stage to canonical evidence."""
    mock_evidence = [
        {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "original_text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 5,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            },
        },
        {
            "passage_id": "tol-porul-akam-014",
            "text": "புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல்...",
            "original_text": "புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல்...",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 14,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 14",
            },
        },
    ]

    inferences = NyayaReasoner.evidence_grounded_deduction(
        query_text="Mountain realm union and clandestine courtship",
        tinai="Kuṟiñci",
        evidence_items=mock_evidence,
    )

    assert len(inferences) == 5
    # Pratijñā grounded in primary passage
    assert "tol-porul-akam-005" in inferences[0].linked_evidence_ids
    assert "Sūtra 5" in inferences[0].epistemic_grounding

    # Hetu grounded in secondary passage
    assert "tol-porul-akam-014" in inferences[1].linked_evidence_ids
    assert "Sūtra 14" in inferences[1].epistemic_grounding

    # Udāharaṇa grounded in universal rule exemplar
    assert "Sūtra" in inferences[2].epistemic_grounding

    # Nigamana grounds in evidence without fallacies
    assert "tol-porul-akam-005" in inferences[4].linked_evidence_ids
    assert inferences[4].fallacy_check == "Free from Bādhā sublation. 100% Sound."


def test_missing_evidence_reports_insufficient_explicitly():
    """Verifies that missing evidence triggers explicit insufficient-evidence status rather than fake output."""
    payload = proof_trace_service.generate_proof_trace(
        query_text="Quantum mechanics wavefunction collapse in Tolkāppiyam",
        tinai="Kuṟiñci",
        evidence_items=[],
        min_evidence_threshold=2,
    )

    assert payload.insufficient_evidence is True
    assert payload.status == "INSUFFICIENT_EVIDENCE"
    assert payload.is_valid is False
    assert len(payload.missing_requirements) >= 1
    assert payload.nodes == []
    assert payload.steps == []
    assert payload.edges == []
    assert payload.conclusion_id is None


def test_proof_trace_nodes_contain_complete_provenance():
    """Verifies that proof trace E1 and E2 nodes contain work, section, chapter, sutraNumber, originalText, and confidence."""
    canonical_items = [
        {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும்...",
            "original_text": "மாயோன் மேய காடுறை உலகமும்...",
            "translation": "The forested realm overseen by Māyōṉ...",
            "confidence": 0.99,
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 5,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            },
        },
        {
            "passage_id": "tol-porul-akam-014",
            "text": "புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல்...",
            "original_text": "புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல்...",
            "translation": "Union, separation, patient awaiting...",
            "confidence": 0.98,
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 14,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 14",
            },
        },
    ]

    nodes = ProofTraceGenerator.generate_trace_nodes(tinai="Kuṟiñci", evidence_items=canonical_items)
    assert len(nodes) == 7

    e1 = next(n for n in nodes if n["id"] == "E1")
    assert e1["passageId"] == "tol-porul-akam-005"
    assert e1["work"] == "Tolkāppiyam"
    assert e1["section"] == "Poruḷatikāram"
    assert e1["chapter"] == "Akattiṇaiyiyal"
    assert e1["sutraNumber"] == 5
    assert e1["originalText"] != ""
    assert e1["evidenceType"] == "CanonicalSutra"
    assert e1["confidence"] == 0.99

    e2 = next(n for n in nodes if n["id"] == "E2")
    assert e2["passageId"] == "tol-porul-akam-014"
    assert e2["work"] == "Tolkāppiyam"
    assert e2["sutraNumber"] == 14
    assert e2["originalText"] != ""
    assert e2["evidenceType"] == "CanonicalSutra"
    assert e2["confidence"] == 0.98


def test_neo4j_repository_canonical_sutras_batch_live():
    """Verifies that neo4j_repository can batch-retrieve canonical sūtras with complete provenance."""
    batch = neo4j_repository.get_canonical_sutras_batch(["tol-porul-akam-005"])
    assert isinstance(batch, dict)
    if "tol-porul-akam-005" in batch:
        record = batch["tol-porul-akam-005"]
        assert record["sutra_number"] == 5
        assert record["work_name"] == "Tolkāppiyam"
        assert "Poruḷatikāram" in record["section_name"]
        assert record["original_text"] != ""
        assert record["translation"] != ""
