"""
Unit and Integration Tests for Real-Time Dynamic Confidence Score Validation.
Verifies the 6-factor evaluator, strict epistemic gating, penalty deductions,
and the REST API endpoint /api/reasoning/confidence/validate.
"""
import pytest
from reasoning.confidence_evaluator import (
    ConfidenceEvaluator,
    ConfidenceEvaluationResult,
    ConfidenceFactor,
    ConfidencePenalty,
)
from reasoning.models import (
    PremiseNode,
    RuleNode,
    InferenceNode,
    ConclusionNode,
)
from app import app


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _build_mock_canonical_passages():
    """Builds a set of 3 authentic Tolkāppiyam Poruḷatikāram evidence passages."""
    return [
        {
            "passage_id": "tol-porul-akam-005",
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "sutra_number": 5,
            "reference": "Sūtra 5 • Akattiṇaiyiyal",
            "tinai": "Kuṟiñci",
            "relevance_score": 0.94,
            "confidenceScore": 0.94,
            "retrieval_methods": ["semantic", "bm25", "graph"],
            "entities": ["Kuṟiñci", "Murukan", "Valli"],
            "concepts": ["Puṇartal", "Mutalporuḷ", "Karupporuḷ"],
        },
        {
            "passage_id": "tol-porul-akam-014",
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "sutra_number": 14,
            "reference": "Sūtra 14 • Akattiṇaiyiyal",
            "tinai": "Kuṟiñci",
            "relevance_score": 0.89,
            "confidenceScore": 0.89,
            "retrieval_methods": ["semantic", "bm25"],
            "entities": ["Kuṟiñci", "Kuriñcittalai"],
            "concepts": ["Iraval", "Uripporuḷ"],
        },
        {
            "passage_id": "tol-porul-puram-018",
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Purattiṇaiyiyal",
            "sutra_number": 18,
            "reference": "Sūtra 18 • Purattiṇaiyiyal",
            "tinai": "Kuṟiñci",
            "relevance_score": 0.82,
            "confidenceScore": 0.82,
            "retrieval_methods": ["semantic", "graph"],
            "entities": ["Veriyattu", "Velan"],
            "concepts": ["Ritual", "Karupporuḷ"],
        },
    ]


def _build_mock_vyapti_rule():
    """Builds a sound Vyāpti rule grounded in Tolkāppiyam."""
    return RuleNode(
        id="R1",
        label="Universal Concomitance (Vyāpti)",
        rule_id="R-KURINJI-001",
        rule_name="Universal Concomitance (Vyāpti)",
        antecedents=["Mountainous ecology (Mutalporuḷ)", "Midnight/Winter season"],
        consequent="Erotic union sentiment (Puṇartal Uripporuḷ)",
        formal_logic="∀x (Ecology(x, Kuṟiñci) ∧ Time(x, Yamam) → Mood(x, Puṇartal))",
        exemplar_sutra="Sūtra 5 • Akattiṇaiyiyal",
        tinai="Kuṟiñci",
        vyapti_validated=True,
        vyapti_status="grounded",
        evidence_support_ids=["tol-porul-akam-005", "tol-porul-akam-014"],
        confidence=0.95,
    )


def _build_mock_conclusion():
    """Builds a verified conclusion node."""
    return ConclusionNode(
        id="C1",
        label="Synthesized Epistemic Truth (Nigamana)",
        statement="Kuṟiñci eco-semiotic affective mood is conclusively established.",
        formal_logic="Ecology(Kuṟiñci) ∧ Time(Yamam) ⊢ Mood(Puṇartal)",
        soundness_score=0.92,
        tinai="Kuṟiñci",
        supporting_evidence_ids=["tol-porul-akam-005", "tol-porul-akam-014"],
        inference_ids=["I1"],
        epistemic_verdict="Sound Canonical Invariance (தொல்காப்பிய முறைமை நெறி)",
        confidence=0.92,
    )


class TestConfidenceEvaluator:
    """Test suite for ConfidenceEvaluator algorithm."""

    def test_high_confidence_with_canonical_evidence(self):
        """Authentic Tolkāppiyam passages with multi-channel consensus produce HIGH / VERY_HIGH confidence."""
        evidence = _build_mock_canonical_passages()
        vyapti = _build_mock_vyapti_rule()
        conclusion = _build_mock_conclusion()

        eval_result = ConfidenceEvaluator.evaluate(
            query="How does Kurinji landscape signify union?",
            evidence_records=evidence,
            vyapti_rule=vyapti,
            conclusion=conclusion,
            tinai="Kuṟiñci",
        )

        assert isinstance(eval_result, ConfidenceEvaluationResult)
        assert eval_result.confidence_score >= 0.70
        assert eval_result.confidence_level in ["HIGH", "VERY_HIGH"]
        assert eval_result.is_sufficient is True
        assert eval_result.confidence_stars >= 3.5

        # Check all 6 factors exist and have positive weighted scores
        assert len(eval_result.factors) == 6
        for factor_key in [
            "evidence_relevance",
            "source_provenance",
            "retrieval_strength",
            "premise_support",
            "reasoning_consistency",
            "validation_status",
        ]:
            factor = eval_result.factors[factor_key]
            assert isinstance(factor, ConfidenceFactor)
            assert factor.weighted_score > 0.0

        # Weights must sum to 1.0
        total_weight = sum(f.weight for f in eval_result.factors.values())
        assert pytest.approx(total_weight, 0.001) == 1.0

        # Zero penalties for fully canonical sound proof
        assert len(eval_result.penalties) == 0

    def test_insufficient_evidence_gating(self):
        """Fewer than 2 canonical passages strictly gates confidence to <= 0.25."""
        single_evidence = [_build_mock_canonical_passages()[0]]
        vyapti = _build_mock_vyapti_rule()

        eval_result = ConfidenceEvaluator.evaluate(
            query="Kurinji poetics",
            evidence_records=single_evidence,
            vyapti_rule=vyapti,
            tinai="Kuṟiñci",
        )

        # Must be strictly gated to <= 0.25
        assert eval_result.confidence_score <= 0.25
        assert eval_result.confidence_level in ["LOW", "INSUFFICIENT"]
        assert eval_result.is_sufficient is False

        # Penalty must be registered
        penalty_names = [p.penalty_name for p in eval_result.penalties]
        assert "P_INSUFFICIENT_EVIDENCE" in penalty_names

    def test_zero_evidence_returns_absolute_zero(self):
        """Zero evidence passages produces confidence score of 0.0 and INSUFFICIENT status."""
        eval_result = ConfidenceEvaluator.evaluate(
            query="Random query with zero evidence",
            evidence_records=[],
            vyapti_rule=None,
            conclusion=None,
        )

        assert eval_result.confidence_score == 0.0
        assert eval_result.confidence_percentage == 0
        assert eval_result.confidence_stars == 0.0
        assert eval_result.confidence_level == "INSUFFICIENT"
        assert eval_result.is_sufficient is False

    def test_ungrounded_vyapti_gating(self):
        """Missing or ungrounded Vyāpti rule strictly gates confidence to <= 0.30."""
        evidence = _build_mock_canonical_passages()

        # No vyāpti rule provided
        eval_result = ConfidenceEvaluator.evaluate(
            query="Inquiry without universal invariable rule",
            evidence_records=evidence,
            vyapti_rule=None,
            conclusion=None,
        )

        assert eval_result.confidence_score <= 0.30
        penalty_names = [p.penalty_name for p in eval_result.penalties]
        assert "P_UNGROUNDED_VYAPTI" in penalty_names

    def test_unsupported_conclusion_penalty(self):
        """Conclusion lacking supporting passage IDs triggers penalty and is gated to <= 0.25."""
        evidence = _build_mock_canonical_passages()
        vyapti = _build_mock_vyapti_rule()

        unsupported_conclusion = ConclusionNode(
            id="C1",
            label="Unsupported Conclusion",
            statement="Speculative assertion without grounded passage IDs",
            formal_logic="⊥",
            soundness_score=0.99,
            tinai="Kuṟiñci",
            supporting_evidence_ids=[],  # Empty! Lacks supporting citations
            inference_ids=[],
            confidence=0.99,
        )

        eval_result = ConfidenceEvaluator.evaluate(
            query="Inquiry with ungrounded conclusion",
            evidence_records=evidence,
            vyapti_rule=vyapti,
            conclusion=unsupported_conclusion,
        )

        assert eval_result.confidence_score <= 0.25
        penalty_names = [p.penalty_name for p in eval_result.penalties]
        assert "P_UNSUPPORTED_CONCLUSION" in penalty_names

    def test_conflicting_cross_tinai_evidence_penalty(self):
        """Cross-habitat discordance across 3+ tinais triggers P_CONFLICTING_EVIDENCE."""
        conflicting_evidence = [
            {
                "passage_id": "P1",
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "tinai": "Kuṟiñci",
                "relevance_score": 0.85,
            },
            {
                "passage_id": "P2",
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "tinai": "Neytal",
                "relevance_score": 0.82,
            },
            {
                "passage_id": "P3",
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "tinai": "Marutam",
                "relevance_score": 0.80,
            },
        ]
        vyapti = _build_mock_vyapti_rule()

        eval_result = ConfidenceEvaluator.evaluate(
            query="Contradictory inquiry spanning 3 habitats",
            evidence_records=conflicting_evidence,
            vyapti_rule=vyapti,
            tinai="Kuṟiñci",
        )

        penalty_names = [p.penalty_name for p in eval_result.penalties]
        assert "P_CONFLICTING_EVIDENCE" in penalty_names

    def test_weak_relevance_penalty(self):
        """Passages with mean relevance below 0.45 trigger P_WEAK_RELEVANCE."""
        weak_evidence = [
            {
                "passage_id": "P1",
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "tinai": "Kuṟiñci",
                "relevance_score": 0.32,
            },
            {
                "passage_id": "P2",
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "tinai": "Kuṟiñci",
                "relevance_score": 0.28,
            },
        ]
        vyapti = _build_mock_vyapti_rule()

        eval_result = ConfidenceEvaluator.evaluate(
            query="Query with weak semantic relevance",
            evidence_records=weak_evidence,
            vyapti_rule=vyapti,
            tinai="Kuṟiñci",
        )

        penalty_names = [p.penalty_name for p in eval_result.penalties]
        assert "P_WEAK_RELEVANCE" in penalty_names


class TestConfidenceValidationEndpoint:
    """Tests for the Flask API route /api/reasoning/confidence/validate."""

    def test_api_validate_confidence_success(self, client):
        """Endpoint accepts evidence records and returns structured confidence evaluation."""
        evidence = _build_mock_canonical_passages()
        payload = {
            "query": "How does Kurinji landscape evoke union?",
            "evidenceRecords": evidence,
            "tinai": "Kuṟiñci",
            "reasoningStages": [
                {
                    "stageNumber": 1,
                    "sanskritName": "Pratijñā",
                    "linkedEvidenceId": "tol-porul-akam-005",
                },
                {
                    "stageNumber": 3,
                    "sanskritName": "Udāharaṇa",
                    "formalLogic": "∀x (Ecology(x) → Mood(x))",
                    "linkedEvidenceId": "tol-porul-akam-014",
                },
            ],
        }

        resp = client.post("/api/reasoning/confidence/validate", json=payload)
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["success"] is True
        assert "data" in data

        res = data["data"]
        assert "confidenceScore" in res
        assert "confidencePercentage" in res
        assert "confidenceStars" in res
        assert "confidenceLevel" in res
        assert "factors" in res
        assert isinstance(res["factors"], dict)
        assert len(res["factors"]) == 6

    def test_api_validate_confidence_insufficient(self, client):
        """Endpoint accurately evaluates insufficient evidence."""
        payload = {
            "query": "Query with empty evidence",
            "evidenceRecords": [],
            "tinai": "Kuṟiñci",
        }

        resp = client.post("/api/reasoning/confidence/validate", json=payload)
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["success"] is True
        res = data["data"]
        assert res["confidenceScore"] == 0.0
        assert res["confidenceLevel"] == "INSUFFICIENT"
        assert res["isSufficient"] is False
