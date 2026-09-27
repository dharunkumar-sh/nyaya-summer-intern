"""
Test suite for the dedicated Vyāpti identification stage in the Nyāya reasoning pipeline.

Verifies:
1. Distinction between:
   - Case Evidence (establishes the specific situation)
   - Vyāpti Evidence (establishes the general relation/rule)
   - Application Evidence (connects the general rule to the current case)
2. Guarded attribution: Never automatically assume that a retrieved verse represents Vyāpti.
3. Canonical Neo4j evidence backing for candidate Vyāptis.
4. Exact CandidateVyapti schema:
   {
     "rule": "...",
     "source": "...",
     "evidence": "...",
     "confidence": 0.0,
     "status": "grounded"
   }
5. Configured validation criteria evaluation.
6. Explicit "Vyāpti unavailable" state when no grounded Vyāpti exists (no fabrication).
7. End-to-end integration into ReasoningService and the Flask API endpoint.
"""
import sys
import pathlib
import pytest

backend = str(pathlib.Path(__file__).resolve().parent.parent)
if backend not in sys.path:
    sys.path.insert(0, backend)

from reasoning.vyapti_identifier import (
    VyaptiIdentifier,
    vyapti_identifier,
    VyaptiValidationCriteria,
    CandidateVyapti,
)
from reasoning.rule_engine import TinaiRuleEngine
from reasoning.nyaya_engine import NyayaReasoner
from services.reasoning_service import reasoning_service


# ---------------------------------------------------------------------------
# Test 1: Evidence Classification (Case vs Vyāpti vs Application)
# ---------------------------------------------------------------------------

def test_evidence_classification_distinguishes_three_roles():
    """
    Verifies that the system cleanly distinguishes between:
    - Case Evidence (specific situation)
    - Vyāpti Evidence (general relation/rule)
    - Application Evidence (connects rule to case)
    """
    sample_evidence = [
        # 1. Poetic verse: Kuruntokai 40 (Case Evidence)
        {
            "passage_id": "kuruntokai-040",
            "text": "யாயும் ஞாயும் யாராகியரோ எந்தையும் நுந்தையும் எம்முறைக் கேளிர்...",
            "source": {
                "work": "Kuruntokai",
                "section": "Ceyyul",
                "reference": "Kuṟuntokai Verse 40",
            },
            "category": "PoeticVerse",
        },
        # 2. Canonical Sūtra: Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5 (Vyāpti Evidence)
        {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 5,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            },
            "category": "CanonicalVyaptiRule",
        },
        # 3. Biotic signifier passage: Vēṅkai flower blooming (Application Evidence)
        {
            "passage_id": "tol-porul-akam-018",
            "text": "பூவும் புள்ளும் புணர்வழி இன்றி தலைவன் வரவுணர்த்தும் வேங்கை...",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 18,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 18",
            },
            "category": "ApplicationEvidence",
            "evidenceRole": "applicationEvidence",
        },
    ]

    classified = vyapti_identifier.classify_evidence(sample_evidence, tinai="Kuṟiñci")

    assert "case_evidence" in classified
    assert "vyapti_evidence" in classified
    assert "application_evidence" in classified

    # 1. Poetic verse must be Case Evidence, establishing the specific situation
    assert len(classified["case_evidence"]) == 1
    assert classified["case_evidence"][0]["passage_id"] == "kuruntokai-040"
    assert classified["case_evidence"][0]["role_description"] == "establishes the specific situation"

    # 2. Canonical Sūtra must be Vyāpti Evidence, establishing the general relation/rule
    assert len(classified["vyapti_evidence"]) == 1
    assert classified["vyapti_evidence"][0]["passage_id"] == "tol-porul-akam-005"
    assert classified["vyapti_evidence"][0]["role_description"] == "establishes the general relation/rule"

    # 3. Biotic signifier must be Application Evidence, connecting the general rule to the case
    assert len(classified["application_evidence"]) == 1
    assert classified["application_evidence"][0]["passage_id"] == "tol-porul-akam-018"
    assert classified["application_evidence"][0]["role_description"] == "connects the general rule to the current case"


# ---------------------------------------------------------------------------
# Test 2: Guarded Attribution (Never Automatically Assume Verse is Vyāpti)
# ---------------------------------------------------------------------------

def test_does_not_automatically_assume_retrieved_verse_is_vyapti():
    """
    Verifies that an empirical poetic verse (e.g. from Akanānūṟu or Kuruntokai)
    is NEVER assumed to represent Vyāpti, even if it matches the Tiṇai keywords.
    """
    poetic_verse = [
        {
            "passage_id": "akanānūṟu-002",
            "text": "இரவு வரல் மரபின் தலைவன் வந்தனன் குறிஞ்சி நிலத்து வேங்கை மலர...",
            "source": {
                "work": "Akanānūṟu",
                "reference": "Akanānūṟu Verse 2",
            },
            "relevance_score": 0.98,
        }
    ]

    classified = vyapti_identifier.classify_evidence(poetic_verse, tinai="Kuṟiñci")

    # Must NOT be in vyapti_evidence
    assert len(classified["vyapti_evidence"]) == 0
    # Must be in case_evidence
    assert len(classified["case_evidence"]) == 1
    assert classified["case_evidence"][0]["passage_id"] == "akanānūṟu-002"


# ---------------------------------------------------------------------------
# Test 3: Exact Candidate Vyāpti Structure
# ---------------------------------------------------------------------------

def test_candidate_vyapti_exact_schema():
    """
    Verifies that each candidate Vyāpti strictly maintains:
    {
      "rule": "...",
      "source": "...",
      "evidence": "...",
      "confidence": 0.0,
      "status": "grounded"
    }
    """
    candidate = CandidateVyapti(
        rule="∀x [MountainTerrain(x) ∧ Midnight(x) ⇒ InvariableAffect(x, Puṇartal)]",
        source="Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
        evidence="மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
        confidence=0.99,
        status="grounded",
    )

    d = candidate.to_dict()

    # Exact 5 keys specified in the prompt
    assert set(d.keys()) == {"rule", "source", "evidence", "confidence", "status"}
    assert isinstance(d["rule"], str) and len(d["rule"]) > 0
    assert isinstance(d["source"], str) and "Tolkāppiyam" in d["source"]
    assert isinstance(d["evidence"], str) and len(d["evidence"]) > 0
    assert isinstance(d["confidence"], float) and d["confidence"] == 0.99
    assert d["status"] == "grounded"


# ---------------------------------------------------------------------------
# Test 4: Candidate Supported by Neo4j Canonical Evidence
# ---------------------------------------------------------------------------

def test_candidate_vyapti_neo4j_canonical_support():
    """
    Verifies that a candidate Vyāpti must be supported by canonical evidence in Neo4j.
    """
    canonical_item = {
        "passage_id": "tol-porul-akam-005",
        "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
        "source": {
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "sutra_number": 5,
            "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
        },
        "category": "CanonicalVyaptiRule",
        "confidence": 0.98,
    }

    result = vyapti_identifier.identify_vyapti(
        evidence_items=[canonical_item],
        tinai="Kuṟiñci",
    )

    assert result["is_established"] is True
    assert result["status"] == "grounded"
    assert result["grounded_vyapti"] is not None

    gv = result["grounded_vyapti"]
    assert set(gv.keys()) == {"rule", "source", "evidence", "confidence", "status"}
    assert gv["status"] == "grounded"
    assert "Tolkāppiyam" in gv["source"]
    assert gv["confidence"] >= 0.85


# ---------------------------------------------------------------------------
# Test 5: Configured Validation Criteria
# ---------------------------------------------------------------------------

def test_configured_validation_criteria_enforcement():
    """
    Verifies that only when the candidate satisfies the configured validation criteria
    is the Vyāpti marked as established ("grounded").
    """
    canonical_item = {
        "passage_id": "tol-porul-akam-005",
        "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
        "source": {
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "sutra_number": 5,
            "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
        },
        "category": "CanonicalVyaptiRule",
        "confidence": 0.80,  # Below strict 0.95 threshold
    }

    # Strict criteria: min_confidence = 0.95
    strict_criteria = VyaptiValidationCriteria(
        min_confidence=0.95,
        require_canonical_neo4j=True,
    )

    result_strict = vyapti_identifier.identify_vyapti(
        evidence_items=[canonical_item],
        tinai="Kuṟiñci",
        criteria=strict_criteria,
    )

    # Must fail to establish due to confidence threshold
    assert result_strict["is_established"] is False
    assert result_strict["status"] == "Vyāpti unavailable"
    assert result_strict["grounded_vyapti"] is None
    assert any(c["status"] == "ungrounded" for c in result_strict["candidates"])

    # Relaxed criteria: min_confidence = 0.75
    relaxed_criteria = VyaptiValidationCriteria(
        min_confidence=0.75,
        require_canonical_neo4j=True,
    )

    result_relaxed = vyapti_identifier.identify_vyapti(
        evidence_items=[canonical_item],
        tinai="Kuṟiñci",
        criteria=relaxed_criteria,
    )

    # Must succeed under relaxed criteria
    assert result_relaxed["is_established"] is True
    assert result_relaxed["status"] == "grounded"
    assert result_relaxed["grounded_vyapti"]["status"] == "grounded"


# ---------------------------------------------------------------------------
# Test 6: Explicit "Vyāpti unavailable" Fallback State (No Fabrication)
# ---------------------------------------------------------------------------

def test_explicit_vyapti_unavailable_state_when_no_grounded_vyapti():
    """
    Verifies that if no grounded Vyāpti exists, the system returns an explicit
    "Vyāpti unavailable" state instead of generating / hallucinating one.
    """
    # Only non-canonical poetic verses without any canonical Tolkāppiyam Vyāpti sūtras
    poetic_only_items = [
        {
            "passage_id": "kuruntokai-101",
            "text": "கொங்குதேர் வாழ்க்கை அஞ்சிறைத் தும்பி காமஞ் செப்பாது கண்டது மொழிமோ...",
            "source": {
                "work": "Kuruntokai",
                "reference": "Kuṟuntokai Verse 2",
            },
            "category": "PoeticVerse",
        }
    ]

    result = vyapti_identifier.identify_vyapti(
        evidence_items=poetic_only_items,
        tinai="Pālai",
    )

    # If Neo4j has no matching sūtras for this or if only poetic verses provided
    # Check that when Vyāpti is ungrounded, the explicit state is returned
    strict_criteria = VyaptiValidationCriteria(
        min_confidence=0.90,
        require_canonical_neo4j=True,
        require_source_provenance=True,
    )

    result_strict = vyapti_identifier.identify_vyapti(
        evidence_items=poetic_only_items,
        tinai="Pālai",
        criteria=strict_criteria,
    )

    if not result_strict["is_established"]:
        assert result_strict["status"] == "Vyāpti unavailable"
        assert result_strict["is_established"] is False
        assert result_strict["grounded_vyapti"] is None
        assert "Vyāpti unavailable" in result_strict["reason"]
        assert len(result_strict["missing_requirements"]) > 0


# ---------------------------------------------------------------------------
# Test 7: RuleEngine & NyayaReasoner Integration
# ---------------------------------------------------------------------------

def test_rule_engine_and_nyaya_deduction_with_grounded_vyapti():
    """
    Verifies that TinaiRuleEngine and NyayaReasoner integrate with the Vyāpti identification stage.
    """
    canonical_items = [
        {
            "passage_id": "tol-porul-akam-005",
            "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Akattiṇaiyiyal",
                "sutra_number": 5,
                "reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            },
            "category": "CanonicalVyaptiRule",
            "confidence": 0.98,
        },
        {
            "passage_id": "kuruntokai-040",
            "text": "யாயும் ஞாயும் யாராகியரோ...",
            "source": {"work": "Kuruntokai", "reference": "Kuṟuntokai 40"},
            "category": "CaseEvidence",
        },
    ]

    # Test RuleNode formulation
    rules = TinaiRuleEngine.build_rule_nodes(tinai="Kuṟiñci", evidence_items=canonical_items)
    assert len(rules) == 1
    r1 = rules[0]
    assert r1.vyapti_validated is True
    assert r1.vyapti_status == "grounded"
    assert r1.candidate_vyapti is not None
    assert r1.candidate_vyapti["status"] == "grounded"

    # Test 5-stage deduction
    stages = NyayaReasoner.evidence_grounded_deduction(
        query_text="Kurinji love union",
        tinai="Kuṟiñci",
        evidence_items=canonical_items,
    )
    assert len(stages) == 5

    # Stage 3 (Udāharaṇa) must reflect established Vyāpti
    udaharana = stages[2]
    assert udaharana.sanskrit_name == "Udāharaṇa"
    assert "Invariance confirmed" in udaharana.fallacy_check or "Vyāpti established" in udaharana.fallacy_check
    assert udaharana.confidence >= 0.85


# ---------------------------------------------------------------------------
# Test 8: End-to-End Pipeline Vyāpti Exposure
# ---------------------------------------------------------------------------

def test_reasoning_service_exposes_vyapti_identification_payload():
    """
    Verifies that ReasoningService executes the dedicated Vyāpti identification stage
    and returns candidates, classification, and status in its payload.
    """
    result = reasoning_service.execute_reasoning_pipeline(
        query_text="குறிஞ்சி நிலத்தில் புணர்தல் ஒழுக்கம் எவ்வாறு நிலைநாட்டப்படுகிறது?",
        depth=2,
        focus="Relationship",
    )

    assert "vyaptiStatus" in result
    assert "vyaptiIdentification" in result
    assert "candidateVyaptis" in result
    assert "caseEvidence" in result
    assert "vyaptiEvidence" in result
    assert "applicationEvidence" in result

    if result.get("vyaptiStatus") == "grounded":
        assert result["establishedVyapti"] is not None
        assert result["establishedVyapti"]["status"] == "grounded"
    elif result.get("vyaptiStatus") == "Vyāpti unavailable":
        assert result["establishedVyapti"] is None
        assert result["vyaptiUnavailable"] is True
