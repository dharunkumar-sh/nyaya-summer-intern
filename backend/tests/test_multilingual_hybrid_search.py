"""
Comprehensive test suite for the Multilingual Hybrid Search Pipeline.

Verifies:
1. Pure Tamil queries retrieve relevant Classical Tamil passages with high lexical and semantic scores.
2. English queries retrieve semantically equivalent Tamil passages using multilingual embeddings.
3. Mixed-language queries seamlessly combine lexical and semantic channels.
4. Candidate deduplication using stable canonical passage IDs.
5. Separate and transparent scoring: lexical_score, semantic_score, and hybrid_score [0.0, 1.0].
6. Complete preservation of source, work, section, passage, entity, concept, and relevance metadata.
7. End-to-end integration across HybridSearchService and HybridRAGPipeline without external search databases (no Valkey).
"""
import pytest
from retrieval.hybrid_search import HybridSearchService, hybrid_search_service, HybridSearchResult
from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline, EvidenceCollection, EvidenceItem


@pytest.fixture
def service() -> HybridSearchService:
    """Provides the singleton instance of the HybridSearchService."""
    return hybrid_search_service


class TestTamilQueryRetrieval:
    """Verify that pure Tamil queries retrieve relevant Classical Tamil passages."""

    def test_pure_tamil_landscape_and_deity_query(self, service: HybridSearchService):
        query = "மாயோன் காடுறை உலகம் முல்லை"
        results = service.search(query=query, top_k=5)

        assert len(results) > 0
        top = results[0]

        # Sūtra 5 is Mayon / Mullai / Ceyon / Kurinji landscape definition
        assert top.passage_id == "tol-porul-akam-005"
        assert top.lexical_score > 0.0
        assert top.semantic_score > 0.0
        assert top.hybrid_score > 0.0
        assert 0.0 <= top.hybrid_score <= 1.0

    def test_pure_tamil_tripartite_semiotics_query(self, service: HybridSearchService):
        query = "குறிஞ்சி நிலத்தின் உரிப்பொருள் யாது?"
        results = service.search(query=query, top_k=5)

        assert len(results) > 0
        pids = [r.passage_id for r in results]
        assert "tol-porul-akam-003" in pids or "tol-porul-akam-005" in pids


class TestEnglishQueryRetrieval:
    """Verify that English queries retrieve semantically equivalent Tamil passages."""

    def test_english_poetic_landscape_query(self, service: HybridSearchService):
        query = "dark mountain realm overseen by Ceyon"
        results = service.search(query=query, top_k=5)

        assert len(results) > 0
        top = results[0]
        # Should retrieve the Kurinji / Ceyon sutra tol-porul-akam-005
        assert top.passage_id == "tol-porul-akam-005"
        assert top.semantic_score > 0.0
        assert 0.0 <= top.hybrid_score <= 1.0

    def test_english_affective_interiority_query(self, service: HybridSearchService):
        query = "What is the affective mood of the Kurinji landscape?"
        results = service.search(query=query, top_k=5)

        assert len(results) > 0
        pids = [r.passage_id for r in results]
        # Should find Uripporul / Kurinji passages
        assert any(pid in ("tol-porul-akam-003", "tol-porul-akam-005") for pid in pids)
        top = results[0]
        assert top.semantic_score > 0.0
        assert top.hybrid_score > 0.0


class TestMixedLanguageQueryRetrieval:
    """Verify that mixed-language queries seamlessly fuse Tamil and English representations."""

    def test_mixed_language_query_fusion(self, service: HybridSearchService):
        query = "Explain உரிப்பொருள் in Kurinji landscape according to Tolkāppiyam"
        results = service.search(query=query, top_k=5)

        assert len(results) > 0
        top = results[0]

        # Both channels should contribute to the hybrid result
        assert top.semantic_score > 0.0
        assert top.hybrid_score > 0.0
        pids = [r.passage_id for r in results]
        assert "tol-porul-akam-003" in pids or "tol-porul-akam-005" in pids


class TestDeduplicationAndStablePassageIds:
    """Verify deduplication by stable canonical passage ID."""

    def test_results_are_deduplicated_by_passage_id(self, service: HybridSearchService):
        queries = [
            "மாயோன் காடுறை உலகம்",
            "What is the affective mood of the Kurinji landscape?",
            "Explain உரிப்பொருள் and Mutalporuḷ",
        ]
        for q in queries:
            results = service.search(query=q, top_k=10)
            passage_ids = [r.passage_id for r in results]
            # No duplicate passage IDs allowed
            assert len(passage_ids) == len(set(passage_ids)), f"Duplicate passage IDs found for query: {q}"


class TestScoreTransparencyAndMetadataPreservation:
    """Verify separate lexical, semantic, hybrid scores and complete metadata preservation."""

    def test_transparent_scores_and_metadata_in_result(self, service: HybridSearchService):
        query = "Explain Varuṉaṉ deity of Neytal landscape in Tolkāppiyam"
        results = service.search(query=query, top_k=3)

        assert len(results) > 0
        for r in results:
            d = r.to_dict()

            # Separate scores
            assert "lexical_score" in d
            assert "semantic_score" in d
            assert "hybrid_score" in d
            assert "combined_score" in d
            assert "score" in d
            assert 0.0 <= d["lexical_score"] <= 1.0
            assert 0.0 <= d["semantic_score"] <= 1.0
            assert 0.0 <= d["hybrid_score"] <= 1.0
            assert d["hybrid_score"] == d["combined_score"]

            # Required metadata fields
            assert "passage_id" in d and len(d["passage_id"]) > 0
            assert "passage" in d and len(d["passage"]) > 0
            assert "text" in d
            assert "work" in d and d["work"] == "Tolkāppiyam"
            assert "section" in d
            assert "chapter" in d
            assert "source" in d and len(d["source"]) > 0
            assert "entities" in d and isinstance(d["entities"], list)
            assert "concepts" in d and isinstance(d["concepts"], list)
            assert "source_metadata" in d and isinstance(d["source_metadata"], dict)
            assert "relevance_metadata" in d and isinstance(d["relevance_metadata"], dict)

            # Relevance metadata internals
            rel = d["relevance_metadata"]
            assert "lexical_score" in rel
            assert "semantic_score" in rel
            assert "hybrid_score" in rel
            assert "weights" in rel


class TestHybridRAGPipelineMultilingualIntegration:
    """Verify that the HybridRAGPipeline end-to-end retrieve() handles multilingual queries."""

    def test_hybrid_rag_pipeline_tamil_and_english(self):
        # 1. Tamil inquiry
        ta_col = hybrid_rag_pipeline.retrieve("மாயோன் காடுறை உலகம்", top_k=3)
        assert isinstance(ta_col, EvidenceCollection)
        assert len(ta_col.items) > 0
        ta_item = ta_col.items[0].to_dict()
        assert ta_item["passage_id"] == "tol-porul-akam-005"
        assert "hybrid_score" in ta_item
        assert "work" in ta_item
        assert "section" in ta_item
        assert "entities" in ta_item

        # 2. English inquiry
        en_col = hybrid_rag_pipeline.retrieve("What is the affective mood of the Kurinji landscape?", top_k=3)
        assert isinstance(en_col, EvidenceCollection)
        assert len(en_col.items) > 0
        en_item = en_col.items[0].to_dict()
        assert "hybrid_score" in en_item
        assert "lexical_score" in en_item
        assert "semantic_score" in en_item
        assert "passage" in en_item
        assert "source" in en_item
