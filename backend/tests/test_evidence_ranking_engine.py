"""
Comprehensive test suite for the Evidence-Ranking Layer in Hybrid RAG.

Tests cover:
1.  EvidenceRankerConfig initialization, weight normalization, and defaults.
2.  EvidenceScoreComponents dataclass fields, ranges [0.0, 1.0], and to_dict().
3.  EvidenceRankingExplanation fields, diagnostics, and to_dict().
4.  RankedEvidenceItem dataclass, score mapping, rank order, and badge_info.
5.  compute_semantic_relevance: normalization and alignment extraction.
6.  compute_graph_relevance: ontological connectivity, seed entity overlap, path bonus.
7.  compute_source_reliability: canonical Tolkāppiyam hierarchy, section/sūtra completeness.
8.  compute_context_relevance: token coverage, transliteration/translation, tiṇai match.
9.  compute_evidence_confidence: multi-channel consensus (1, 2, 3+ channels).
10. rank_evidence: deterministic sorting, tie-breaking, configurable weights.
11. Provenance preservation: exact passage_id, source references, graph_path in every ranked item.
12. Transparent explanations: component contributions, matched terms, and human-readable summaries.
13. Backward compatibility: EvidenceRanker.format_evidence_records works as before.
14. Integration with HybridRAGPipeline.retrieve: returns ranked items with transparent score_components.
"""
import sys
import pathlib
import pytest

backend = str(pathlib.Path(__file__).resolve().parent.parent)
if backend not in sys.path:
    sys.path.insert(0, backend)

from retrieval.ranker import (
    EvidenceRanker,
    EvidenceRankingEngine,
    evidence_ranking_engine,
    EvidenceScoreComponents,
    EvidenceRankingExplanation,
    RankedEvidenceItem,
    EvidenceRankerConfig,
)


# ---------------------------------------------------------------------------
# Test 1 – EvidenceRankerConfig
# ---------------------------------------------------------------------------

def test_config_defaults_and_normalization():
    cfg = EvidenceRankerConfig()
    total = (
        cfg.semantic_weight
        + cfg.graph_weight
        + cfg.source_weight
        + cfg.context_weight
        + cfg.confidence_weight
    )
    assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"
    assert cfg.semantic_weight > 0
    assert cfg.graph_weight > 0
    assert cfg.source_weight > 0
    assert cfg.context_weight > 0
    assert cfg.confidence_weight > 0


def test_config_custom_weights_normalization():
    cfg = EvidenceRankerConfig(
        semantic_weight=2.0,
        graph_weight=1.0,
        source_weight=1.0,
        context_weight=0.0,
        confidence_weight=0.0,
    )
    total = (
        cfg.semantic_weight
        + cfg.graph_weight
        + cfg.source_weight
        + cfg.context_weight
        + cfg.confidence_weight
    )
    assert abs(total - 1.0) < 1e-6
    assert abs(cfg.semantic_weight - 0.5) < 1e-6  # 2 / 4


# ---------------------------------------------------------------------------
# Test 2 & 3 – EvidenceScoreComponents and EvidenceRankingExplanation
# ---------------------------------------------------------------------------

def test_evidence_score_components_dataclass():
    comp = EvidenceScoreComponents(
        semantic_relevance=0.85,
        graph_relevance=0.72,
        source_reliability=0.95,
        context_relevance=0.60,
        evidence_confidence=0.85,
        raw_components={"custom_val": 1.23},
    )
    d = comp.to_dict()
    assert d["semantic_relevance"] == 0.85
    assert d["graph_relevance"] == 0.72
    assert d["source_reliability"] == 0.95
    assert d["context_relevance"] == 0.60
    assert d["evidence_confidence"] == 0.85
    assert "custom_val" in d["raw_components"]


def test_evidence_ranking_explanation_dataclass():
    expl = EvidenceRankingExplanation(
        summary="High semantic alignment • Multi-channel consensus",
        matched_terms=["kurinci", "ceyon"],
        matched_entities=["Seyon"],
        matched_concepts=["Mutalporul"],
        source_pedigree="Tolkāppiyam Canonical Sūtra",
        channel_consensus=["semantic_vector", "keyword_entity"],
        component_contributions={"semantic": 0.25, "graph": 0.20},
    )
    d = expl.to_dict()
    assert "summary" in d
    assert d["matched_terms"] == ["kurinci", "ceyon"]
    assert d["source_pedigree"] == "Tolkāppiyam Canonical Sūtra"
    assert "semantic" in d["component_contributions"]


# ---------------------------------------------------------------------------
# Test 4 – RankedEvidenceItem
# ---------------------------------------------------------------------------

def test_ranked_evidence_item_structure():
    comp = EvidenceScoreComponents(0.8, 0.7, 0.9, 0.6, 0.85)
    expl = EvidenceRankingExplanation("summary", [], [], [], "pedigree", ["ch1"], {})
    item = RankedEvidenceItem(
        passage_id="tol-porul-akam-003",
        text="verse text",
        source={"work": "Tolkāppiyam", "sutra_number": 3},
        final_score=0.785,
        score_components=comp,
        explanation=expl,
        rank=1,
        graph_path=[{"level": "L0", "label": "Sangam"}],
        retrieval_methods=["semantic_vector"],
    )
    assert item.score == 0.785
    d = item.to_dict()
    assert d["passage_id"] == "tol-porul-akam-003"
    assert d["final_score"] == 0.785
    assert d["rank"] == 1
    assert "score_components" in d
    assert "explanation" in d
    assert len(d["graph_path"]) == 1


# ---------------------------------------------------------------------------
# Test 5 – compute_semantic_relevance
# ---------------------------------------------------------------------------

def test_compute_semantic_relevance():
    engine = EvidenceRankingEngine()
    item = {"semantic_score": 0.88}
    score, raw = engine.compute_semantic_relevance(item, "any query")
    assert 0.0 <= score <= 1.0
    assert abs(score - 0.88) < 1e-4

    # Negative cosine should clamp to 0.0
    item_neg = {"semantic_score": -0.5}
    score_neg, _ = engine.compute_semantic_relevance(item_neg, "any query")
    assert score_neg == 0.0


# ---------------------------------------------------------------------------
# Test 6 – compute_graph_relevance
# ---------------------------------------------------------------------------

def test_compute_graph_relevance():
    engine = EvidenceRankingEngine()
    item = {
        "graph_score": 0.75,
        "graph_context": {
            "entities": [{"label": "Seyon"}, {"label": "Murugan"}],
            "concepts": [{"label": "Kurinci"}],
        },
        "graph_path": [{"id": "L0"}, {"id": "L1"}],
    }
    score, matched_ents, matched_concs = engine.compute_graph_relevance(
        item, "Where does Seyon dwell in Kurinci?"
    )
    assert 0.0 <= score <= 1.0
    assert "Seyon" in matched_ents
    assert "Kurinci" in matched_concs
    assert score >= 0.50


# ---------------------------------------------------------------------------
# Test 7 – compute_source_reliability
# ---------------------------------------------------------------------------

def test_compute_source_reliability_canonical_tolkappiyam():
    engine = EvidenceRankingEngine()
    canonical_item = {
        "passage_id": "tol-porul-akam-003",
        "source": {
            "work": "Tolkāppiyam",
            "section": "Poruḷatikāram",
            "chapter": "Akattiṇaiyiyal",
            "sutra_number": 3,
        },
    }
    score, pedigree = engine.compute_source_reliability(canonical_item)
    assert score >= 0.90, f"Canonical Tolkāppiyam should score >= 0.90, got {score}"
    assert "Tolkāppiyam" in pedigree


def test_compute_source_reliability_generic():
    engine = EvidenceRankingEngine()
    generic_item = {
        "passage_id": "other-text-01",
        "source": {"work": "Commentary"},
    }
    score, pedigree = engine.compute_source_reliability(generic_item)
    assert score < 0.90
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Test 8 – compute_context_relevance
# ---------------------------------------------------------------------------

def test_compute_context_relevance():
    engine = EvidenceRankingEngine()
    item = {
        "text": "மாயோன் மேய காடுறை உலகமும்",
        "source": {
            "translation": "The forest world presided over by Mayon",
            "tinai": "Mullai",
        },
        "lexical_score": 0.70,
    }
    score, matched = engine.compute_context_relevance(item, "Mayon forest Mullai world")
    assert 0.0 <= score <= 1.0
    assert len(matched) >= 2
    assert score >= 0.50


# ---------------------------------------------------------------------------
# Test 9 – compute_evidence_confidence
# ---------------------------------------------------------------------------

def test_compute_evidence_confidence():
    engine = EvidenceRankingEngine()
    item_3ch = {"retrieval_methods": ["semantic_vector", "keyword_entity", "graph_traversal"]}
    score_3ch, _ = engine.compute_evidence_confidence(item_3ch)

    item_1ch = {"retrieval_methods": ["keyword_entity"]}
    score_1ch, _ = engine.compute_evidence_confidence(item_1ch)

    assert score_3ch > score_1ch
    assert score_3ch >= 0.90
    assert score_1ch >= 0.65


# ---------------------------------------------------------------------------
# Test 10 – rank_evidence deterministic sorting
# ---------------------------------------------------------------------------

def test_rank_evidence_deterministic():
    engine = EvidenceRankingEngine()
    items = [
        {
            "passage_id": "tol-porul-akam-004",
            "text": "Item B",
            "semantic_score": 0.60,
            "graph_score": 0.50,
            "retrieval_methods": ["semantic_vector"],
            "source": {"work": "Tolkāppiyam"},
        },
        {
            "passage_id": "tol-porul-akam-003",
            "text": "Item A",
            "semantic_score": 0.95,
            "graph_score": 0.85,
            "retrieval_methods": ["semantic_vector", "keyword_entity", "graph_traversal"],
            "source": {"work": "Tolkāppiyam", "sutra_number": 3},
        },
    ]
    ranked = engine.rank_evidence(items, query="Akam love poetics", top_k=2)
    assert len(ranked) == 2
    assert ranked[0].passage_id == "tol-porul-akam-003"
    assert ranked[0].rank == 1
    assert ranked[1].passage_id == "tol-porul-akam-004"
    assert ranked[1].rank == 2
    assert ranked[0].final_score >= ranked[1].final_score


# ---------------------------------------------------------------------------
# Test 11 – Provenance preservation
# ---------------------------------------------------------------------------

def test_rank_evidence_preserves_provenance():
    engine = EvidenceRankingEngine()
    items = [
        {
            "passage_id": "tol-porul-mey-001",
            "text": "Meyppattiyal verse",
            "source": {
                "work": "Tolkāppiyam",
                "section": "Poruḷatikāram",
                "chapter": "Meyppāṭṭiyal",
                "sutra_number": 248,
            },
            "graph_path": [
                {"level": "L0", "label": "Sangam"},
                {"level": "L1", "label": "Tolkāppiyam"},
                {"level": "L2", "label": "Poruḷatikāram"},
            ],
            "semantic_score": 0.80,
            "retrieval_methods": ["semantic_vector", "keyword_entity"],
        }
    ]
    ranked = engine.rank_evidence(items, "eight rasas of meyppadu")
    assert len(ranked) == 1
    r = ranked[0]
    assert r.passage_id == "tol-porul-mey-001"
    assert r.source["chapter"] == "Meyppāṭṭiyal"
    assert r.source["sutra_number"] == 248
    assert len(r.graph_path) == 3
    assert r.badge_info["code"] == "E1"
    assert "Meyppāṭṭiyal" in r.badge_info["badges"][0]["label"] or "Poruḷ" in r.badge_info["badges"][0]["label"]


# ---------------------------------------------------------------------------
# Test 12 – Backward compatibility with EvidenceRanker.format_evidence_records
# ---------------------------------------------------------------------------

def test_evidence_ranker_legacy_format():
    sutras = [
        (
            {
                "id": "sutra-1",
                "atikaram": "Poruḷ",
                "iyal": "Akattiṇaiyiyal",
                "sutra_number": 1,
                "tamil_text": "முதலெனப்படுவது",
                "english_translation": "What is called mutal...",
                "tinai": "Kuṟiñci",
                "category": "Mutalporuḷ",
            },
            0.92,
        )
    ]
    formatted = EvidenceRanker.format_evidence_records(sutras)
    assert len(formatted) == 1
    card = formatted[0]
    assert card["id"] == "E1"
    assert card["code"] == "E1"
    assert card["confidenceFormatted"] == "92%"
    assert card["confidenceScore"] == 0.92
    assert "Akattiṇaiyiyal" in card["reference"]
    assert card["badges"][0]["label"] == "Mutalporuḷ"
    assert card["badges"][1]["label"] == "Kuṟiñci Tiṇai"


# ---------------------------------------------------------------------------
# Test 13 – EvidenceRanker.rank_evidence delegation
# ---------------------------------------------------------------------------

def test_evidence_ranker_class_method_delegation():
    items = [
        {
            "passage_id": "tol-01",
            "text": "Sample",
            "semantic_score": 0.8,
            "source": {"work": "Tolkāppiyam"},
        }
    ]
    ranked = EvidenceRanker.rank_evidence(items, "Sample query")
    assert len(ranked) == 1
    assert ranked[0].passage_id == "tol-01"
    assert isinstance(ranked[0].score_components, EvidenceScoreComponents)


# ---------------------------------------------------------------------------
# Test 14 – Integration with HybridRAGPipeline.retrieve
# ---------------------------------------------------------------------------

def test_hybrid_rag_pipeline_evidence_ranking_integration():
    from retrieval.hybrid_rag_pipeline import HybridRAGPipeline
    pipeline = HybridRAGPipeline(top_k=3)
    collection = pipeline.retrieve("What is Mutalporuḷ in Tolkappiyam?", top_k=3)

    assert len(collection.items) > 0
    top_item = collection.items[0]

    # Check that score_components and explanation are populated
    assert top_item.score_components is not None, "score_components must be populated by EvidenceRankingEngine"
    assert "semantic_relevance" in top_item.score_components
    assert "graph_relevance" in top_item.score_components
    assert "source_reliability" in top_item.score_components
    assert "context_relevance" in top_item.score_components
    assert "evidence_confidence" in top_item.score_components

    assert top_item.explanation is not None, "explanation must be populated"
    assert "summary" in top_item.explanation
    assert "component_contributions" in top_item.explanation

    # Check to_dict serialization completeness
    d = top_item.to_dict()
    assert "score_components" in d
    assert "explanation" in d
    assert "badge_info" in d
    assert d["badge_info"]["code"] == "E1"
