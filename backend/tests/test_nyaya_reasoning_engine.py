"""
Comprehensive test suite for the Nyāya-inspired Neuro-Symbolic Reasoning Layer.

Tests cover:
1.  PremiseNode dataclass attributes, to_dict(), and to_neo4j_params().
2.  RuleNode dataclass attributes, to_dict(), and to_neo4j_params().
3.  InferenceNode dataclass attributes, to_dict(), and to_neo4j_params().
4.  ConclusionNode dataclass attributes, to_dict(), and to_neo4j_params().
5.  ReasoningTrace dataclass, to_dict(), and to_neo4j_graph() persistence export.
6.  EvidenceGroundedPremiseBuilder: grounds premises directly in retrieved evidence.
7.  TinaiRuleEngine: antecedent satisfaction checking against evidence keywords/entities.
8.  TinaiRuleEngine.evaluate_multi_hop: 2-hop deduction chaining.
9.  NyayaReasoner.evidence_grounded_deduction: 5-member Pañcāvayava inference.
10. Pañcāvayava stage sequence order: Pratijñā -> Hetu -> Udāharaṇa -> Upanaya -> Nigamana.
11. DefeasibleValidator.validate_from_evidence: evidence-calibrated soundness.
12. Hetvābhāsa fallacy inspection: Asiddha detection when evidence is missing.
13. ProofTraceGenerator: 7-node DAG connected with real passage IDs and references.
14. Strict evidence grounding: premise statements contain substrings from retrieved evidence.
15. ReasoningService.execute_reasoning_pipeline: end-to-end orchestration.
"""
import sys
import pathlib
import pytest

backend = str(pathlib.Path(__file__).resolve().parent.parent)
if backend not in sys.path:
    sys.path.insert(0, backend)

from reasoning.models import (
    PremiseNode,
    RuleNode,
    InferenceNode,
    ConclusionNode,
    ReasoningTrace,
)
from reasoning.premise_builder import EvidenceGroundedPremiseBuilder, PremiseBuilder
from reasoning.rule_engine import TinaiRuleEngine
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.validator import DefeasibleValidator
from reasoning.proof_trace import ProofTraceGenerator
from services.reasoning_service import reasoning_service


# ---------------------------------------------------------------------------
# Test 1 – PremiseNode
# ---------------------------------------------------------------------------

def test_premise_node_dataclass_and_neo4j_params():
    p = PremiseNode(
        id="P1",
        label="P1",
        statement="Mountain habitat conditions human interiority.",
        formal_logic="Premise(P1) : Mountain(x) -> Affect(x)",
        pramana_mode="Śabda Pramāṇa",
        grounded_passage_ids=["tol-porul-akam-003"],
        grounded_sutra="Tolkāppiyam Sūtra 3",
        tinai="Kuṟiñci",
        concept_category="Mutalporuḷ",
        confidence=0.96,
    )
    d = p.to_dict()
    assert d["id"] == "P1"
    assert d["type"] == "Premise"
    assert d["concept_category"] == "Mutalporuḷ"
    assert d["grounded_passage_ids"] == ["tol-porul-akam-003"]

    params = p.to_neo4j_params()
    assert params["id"] == "P1"
    assert params["hierarchy_level"] == "L4"
    assert "tol-porul-akam-003" in params["metadata_json"]


# ---------------------------------------------------------------------------
# Test 2 – RuleNode
# ---------------------------------------------------------------------------

def test_rule_node_dataclass_and_neo4j_params():
    r = RuleNode(
        id="R1",
        label="R1",
        rule_id="R1_KURINCI",
        rule_name="Kuṟiñci Vyāpti",
        antecedents=["MountainTerrain", "Midnight"],
        consequent="Puṇartal (Intimate Union)",
        formal_logic="∀x [MountainTerrain(x) ∧ Midnight(x) ⇒ InvariableAffect(x, Puṇartal)]",
        exemplar_sutra="Tolkāppiyam Akattiṇaiyiyal Sūtra 5",
        tinai="Kuṟiñci",
        vyapti_validated=True,
        matched_antecedents=["MountainTerrain"],
        evidence_support_ids=["tol-porul-akam-005"],
    )
    d = r.to_dict()
    assert d["rule_id"] == "R1_KURINCI"
    assert d["consequent"] == "Puṇartal (Intimate Union)"
    assert d["vyapti_validated"] is True

    params = r.to_neo4j_params()
    assert params["type"] == "Rule"
    assert "tol-porul-akam-005" in params["metadata_json"]


# ---------------------------------------------------------------------------
# Test 3 – InferenceNode
# ---------------------------------------------------------------------------

def test_inference_node_dataclass_and_neo4j_params():
    inf = InferenceNode(
        id="I1_PRATIJNA",
        label="Stage 1: Pratijñā",
        stage_number=1,
        sanskrit_name="Pratijñā",
        tamil_name="பிரதிஞ்ஞா",
        english_role="Target Proposition",
        full_title="1. பிரதிஞ்ஞா (Pratijñā) — Target Proposition",
        tamil_reasoning_text="குறிஞ்சி நில முதற்பொருள் உரிப்பொருளை நிலைநாட்டுகிறது.",
        english_interpretation="Kuṟiñci terrain grounds intimate love.",
        formal_logic="H(x) : Terrain(Kuṟiñci) -> Affect(Puṇartal)",
        epistemic_grounding="Tolkāppiyam Sūtra 3",
        pramana_mode="Śabda Pramāṇa",
        fallacy_check="Pakṣa-dharmatā: Validated.",
        linked_evidence_ids=["tol-porul-akam-003"],
        premise_ids=["P1"],
        rule_ids=["R1"],
        hop_depth=0,
    )
    d = inf.to_dict()
    assert d["stageNumber"] == 1
    assert d["sanskritName"] == "Pratijñā"
    assert d["linkedEvidenceIds"] == ["tol-porul-akam-003"]

    params = inf.to_neo4j_params()
    assert params["stage_number"] == 1
    assert params["sanskrit_name"] == "Pratijñā"


# ---------------------------------------------------------------------------
# Test 4 – ConclusionNode
# ---------------------------------------------------------------------------

def test_conclusion_node_dataclass_and_neo4j_params():
    concl = ConclusionNode(
        id="CONCL_01",
        label="Conclusion",
        statement="Aesthetic signification conclusively established as Kuṟiñci Uripporuḷ.",
        formal_logic="∴ Conclusion(C1) : EpistemicSoundness = 0.98",
        soundness_score=0.98,
        tinai="Kuṟiñci",
        supporting_evidence_ids=["tol-porul-akam-003", "tol-porul-akam-005"],
        inference_ids=["I1_PRATIJNA", "I5_NIGAMANA"],
    )
    d = concl.to_dict()
    assert d["soundness_score"] == 0.98
    assert len(d["supporting_evidence_ids"]) == 2

    params = concl.to_neo4j_params()
    assert params["type"] == "Conclusion"
    assert params["soundness_score"] == 0.98


# ---------------------------------------------------------------------------
# Test 5 – ReasoningTrace and Neo4j Graph Export
# ---------------------------------------------------------------------------

def test_reasoning_trace_dataclass_and_neo4j_graph():
    p = PremiseNode("P1", "P1", "stmt", "logic", "pramana", ["p-1"], "ref", "Kuṟiñci")
    r = RuleNode("R1", "R1", "R1_K", "rule", ["ant"], "conseq", "logic", "sutra", "Kuṟiñci", evidence_support_ids=["p-1"])
    inf = InferenceNode(
        id="I1", label="I1", stage_number=1, sanskrit_name="Pratijñā", tamil_name="பிரதிஞ்ஞா",
        english_role="Proposition", full_title="Title", tamil_reasoning_text="ta",
        english_interpretation="en", formal_logic="logic", epistemic_grounding="ref",
        pramana_mode="pramana", fallacy_check="check", linked_evidence_ids=["p-1"],
        premise_ids=["P1"], rule_ids=["R1"]
    )
    concl = ConclusionNode("C1", "C1", "statement", "logic", 0.98, "Kuṟiñci", ["p-1"], ["I1"])

    trace = ReasoningTrace(
        query="Kuṟiñci poetics",
        session_id="sess-01",
        tinai="Kuṟiñci",
        premises=[p],
        rules=[r],
        inferences=[inf],
        conclusion=concl,
        hop_count=2,
        evidence_ids_used=["p-1"],
    )

    d = trace.to_dict()
    assert d["detectedTinai"] == "Kuṟiñci"
    assert len(d["premises"]) == 1
    assert len(d["reasoningStages"]) == 1

    graph = trace.to_neo4j_graph()
    assert "nodes" in graph
    assert "relationships" in graph
    assert len(graph["nodes"]) == 4  # Premise, Rule, Inference, Conclusion
    # Check relationships exist
    rel_types = [rel["rel_type"] for rel in graph["relationships"]]
    assert "SUPPORTED_BY" in rel_types
    assert "DERIVED_FROM" in rel_types
    assert "SUB_SUMES" in rel_types


# ---------------------------------------------------------------------------
# Test 6 – EvidenceGroundedPremiseBuilder
# ---------------------------------------------------------------------------

def test_evidence_grounded_premise_builder():
    evidence_items = [
        {
            "passage_id": "tol-porul-akam-003",
            "text": "முதலும் கருவும் உரிப்பொருளோடு இணையும் செய்யுள் நெறி.",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 3,
                "category": "Mutalporuḷ",
                "tinai": "Kuṟiñci",
            },
            "relevance_score": 0.96,
        },
        {
            "passage_id": "tol-porul-akam-005",
            "text": "சேயோன் மேய மைவரை உலகமும் காடமர் உலகமும்.",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "sutra_number": 5,
                "category": "Karupporuḷ",
                "tinai": "Kuṟiñci",
            },
            "relevance_score": 0.92,
        },
    ]

    premises = EvidenceGroundedPremiseBuilder.build_premise_nodes(evidence_items, tinai="Kuṟiñci")
    assert len(premises) == 2
    assert premises[0].id == "P1"
    assert premises[0].concept_category == "Mutalporuḷ"
    assert premises[0].grounded_passage_ids == ["tol-porul-akam-003"]
    assert "Akattiṇaiyiyal" in premises[0].grounded_sutra or "Poruḷ" in premises[0].grounded_sutra

    assert premises[1].id == "P2"
    assert premises[1].concept_category == "Karupporuḷ"
    assert premises[1].grounded_passage_ids == ["tol-porul-akam-005"]


# ---------------------------------------------------------------------------
# Test 7 – TinaiRuleEngine Antecedent Satisfaction
# ---------------------------------------------------------------------------

def test_rule_engine_antecedent_satisfaction():
    evidence_items = [
        {
            "passage_id": "tol-porul-akam-005",
            "text": "சேயோன் மேய மைவரை உலகம் குறிஞ்சி நிலமாகும்.",
            "graph_context": {
                "entities": [{"label": "Cēyōṉ"}, {"label": "Mountain"}],
                "concepts": [{"label": "Kuṟiñci"}],
            },
        }
    ]
    subsumption = TinaiRuleEngine.evaluate_subsumption("Kuṟiñci", evidence_items=evidence_items)
    assert subsumption["rule_applied"] == "R1_KURINCI"
    assert subsumption["is_satisfied"] is True
    assert subsumption["deduced_affect"] == "Puṇartal (Intimate Union)"
    assert "tol-porul-akam-005" in subsumption["evidence_support_ids"]


# ---------------------------------------------------------------------------
# Test 8 – Multi-Hop Rule Chaining
# ---------------------------------------------------------------------------

def test_multi_hop_rule_chaining():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "text": "Mutalporuḷ verse"},
        {"passage_id": "tol-porul-akam-005", "text": "Karupporuḷ verse"},
    ]
    hops = TinaiRuleEngine.evaluate_multi_hop(tinai="Kuṟiñci", evidence_items=evidence_items, max_hops=2)
    assert len(hops) == 2
    assert hops[0]["hop_number"] == 1
    assert hops[0]["stage"] == "Locus Grounding"
    assert hops[0]["matched_evidence_id"] == "tol-porul-akam-003"

    assert hops[1]["hop_number"] == 2
    assert hops[1]["stage"] == "Affective Deduction"
    assert hops[1]["matched_evidence_id"] == "tol-porul-akam-005"


# ---------------------------------------------------------------------------
# Test 9 & 10 – Five-Stage Pañcāvayava Deduction & Sequence Order
# ---------------------------------------------------------------------------

def test_five_stage_deduction_grounded_in_evidence():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "text": "Axiom 3", "source": {"reference": "Sūtra 3"}},
        {"passage_id": "tol-porul-akam-005", "text": "Axiom 5", "source": {"reference": "Sūtra 5"}},
    ]
    inferences = NyayaReasoner.evidence_grounded_deduction(
        query_text="Kuṟiñci love poetics",
        tinai="Kuṟiñci",
        evidence_items=evidence_items,
    )
    assert len(inferences) == 5

    # Check correct Nyāya sequence order
    expected_stages = ["Pratijñā", "Hetu", "Udāharaṇa", "Upanaya", "Nigamana"]
    for idx, expected in enumerate(expected_stages):
        assert inferences[idx].sanskrit_name == expected
        assert inferences[idx].stage_number == idx + 1
        assert len(inferences[idx].linked_evidence_ids) >= 1

    # Check stage 1 is anchored to primary passage
    assert inferences[0].linked_evidence_ids == ["tol-porul-akam-003"]
    # Check stage 4 (Upanaya) has hop_depth >= 1
    assert inferences[3].hop_depth >= 1


# ---------------------------------------------------------------------------
# Test 11 – DefeasibleValidator Calibrated by Evidence
# ---------------------------------------------------------------------------

def test_validator_calibrated_by_evidence():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "relevance_score": 0.96},
        {"passage_id": "tol-porul-akam-005", "relevance_score": 0.94},
        {"passage_id": "tol-porul-mey-001", "relevance_score": 0.90},
    ]
    val = DefeasibleValidator.validate_from_evidence(evidence_items=evidence_items, tinai="Kuṟiñci")
    assert val["soundnessScore"] >= 0.90
    assert val["symbolicValidity"] == "Sound (Valid Epistemic Deduction)"
    assert val["hetvabhasaCheck"] == "Passed (Zero Fallacies Detected)"
    assert val["fallacies"]["asiddha"] == 0.0
    assert val["fallacies"]["savyabhicara"] == 0.0
    assert len(val["checks"]) == 5


# ---------------------------------------------------------------------------
# Test 12 – Hetvābhāsa Asiddha Fallacy when Evidence is Empty
# ---------------------------------------------------------------------------

def test_hetvabhasa_asiddha_when_empty_evidence():
    val = DefeasibleValidator.validate_from_evidence(evidence_items=[], tinai="Kuṟiñci")
    assert val["fallacies"]["asiddha"] == 1.0
    assert val["soundnessScore"] < 0.85
    assert "Defeasible" in val["symbolicValidity"]


# ---------------------------------------------------------------------------
# Test 13 – ProofTraceGenerator Real Evidence IDs
# ---------------------------------------------------------------------------

def test_proof_trace_links_real_evidence_ids():
    evidence_items = [
        {"passage_id": "tol-porul-akam-003", "text": "Text 3", "source": {"reference": "Tolkāppiyam Sūtra 3"}},
        {"passage_id": "tol-porul-akam-005", "text": "Text 5", "source": {"reference": "Tolkāppiyam Sūtra 5"}},
    ]
    nodes = ProofTraceGenerator.generate_trace_nodes(tinai="Kuṟiñci", evidence_items=evidence_items)
    assert len(nodes) == 7
    labels = [n["label"] for n in nodes]
    assert labels == ["E1", "P1", "E2", "P2", "R1", "I1", "C1"]

    e1_node = next(n for n in nodes if n["id"] == "E1")
    assert e1_node["passageId"] == "tol-porul-akam-003"
    assert "Sūtra 3" in e1_node["citation"]

    e2_node = next(n for n in nodes if n["id"] == "E2")
    assert e2_node["passageId"] == "tol-porul-akam-005"


# ---------------------------------------------------------------------------
# Test 14 – Strict Evidence Grounding in Premises
# ---------------------------------------------------------------------------

def test_no_hallucinated_facts_in_premises():
    unique_text = "வேங்கை மலர்ந்தது தலைவன் வருகை குறித்த குறியீடு"
    evidence_items = [
        {
            "passage_id": "custom-sutra-99",
            "text": unique_text,
            "source": {"work": "Tolkāppiyam", "sutra_number": 99},
        }
    ]
    premises = EvidenceGroundedPremiseBuilder.build_premise_nodes(evidence_items, tinai="Kuṟiñci")
    assert len(premises) >= 1
    # Check that the snippet of unique_text appears in the premise statement
    assert "வேங்கை" in premises[0].statement or "வேங்கை" in premises[0].tamil_statement or "custom-sutra-99" in premises[0].formal_logic


# ---------------------------------------------------------------------------
# Test 15 – ReasoningService End-to-End Orchestration
# ---------------------------------------------------------------------------

def test_reasoning_service_full_pipeline():
    result = reasoning_service.execute_reasoning_pipeline(
        query_text="குறிஞ்சி நிலத்தின் புணர்தல் ஒழுக்கம்",
        depth=2,
        focus="Relationship",
    )
    assert result["detectedTinai"] == "Kuṟiñci"
    assert len(result["reasoningStages"]) == 5
    assert len(result["premises"]) >= 1
    assert len(result["rules"]) >= 1
    assert "conclusion" in result
    assert "reasoningTrace" in result
    assert "proofNodes" in result
    assert len(result["proofNodes"]) == 7
    assert "neo4jGraph" in result
    assert "nodes" in result["neo4jGraph"]
    assert "relationships" in result["neo4jGraph"]
    assert result["validationResults"]["soundnessScore"] > 0.85
