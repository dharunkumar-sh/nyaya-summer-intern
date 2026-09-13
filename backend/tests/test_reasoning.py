"""
Unit tests for Pañcāvayava syllogistic deduction and Hetvābhāsa fallacy validation.
"""
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.validator import DefeasibleValidator
from reasoning.proof_trace import ProofTraceGenerator
from services.reasoning_service import reasoning_service


def test_pancavayava_deduction_generation():
    """Verifies that all 5 stages of the Nyāya syllogism are synthesized."""
    stages = NyayaReasoner.synthesize_deduction(
        query_text="குறிஞ்சி நில ஒழுக்கம்",
        tinai="Kuṟiñci",
    )
    assert len(stages) == 5
    stage_names = [s["sanskritName"] for s in stages]
    assert stage_names == ["Pratijñā", "Hetu", "Udāharaṇa", "Upanaya", "Nigamana"]


def test_proof_trace_generation():
    """Verifies that the 7-node connected proof DAG is created."""
    nodes = ProofTraceGenerator.generate_trace_nodes(tinai="Kuṟiñci")
    assert len(nodes) == 7
    labels = [n["label"] for n in nodes]
    assert labels == ["E1", "P1", "E2", "P2", "R1", "I1", "C1"]


def test_hetvabhasa_fallacy_validation():
    """Verifies that the 5 Hetvābhāsa fallacies are tested and return zero violations."""
    validation = DefeasibleValidator.validate_deduction(tinai="Kuṟiñci", evidence_count=5)
    assert validation["soundnessScore"] >= 0.95
    assert validation["fallacies"]["savyabhicara"] == 0.0
    assert validation["fallacies"]["viruddha"] == 0.0
    assert len(validation["checks"]) == 5


def test_full_reasoning_pipeline():
    """Tests end-to-end execution of ReasoningService."""
    result = reasoning_service.execute_reasoning_pipeline(
        query_text="குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?",
        depth=3,
        focus="Relationship",
    )

    assert result["detectedTinai"] == "Kuṟiñci"
    assert len(result["evidenceRecords"]) > 0
    assert len(result["reasoningStages"]) == 5
    assert len(result["proofNodes"]) == 7
    assert "tamilAnswer" in result["finalAnswer"]
    assert "englishAnswer" in result["finalAnswer"]
    assert result["validationResults"]["soundnessScore"] > 0.9
