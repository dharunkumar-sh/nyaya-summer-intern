"""
Comprehensive Test Suite for the Lightweight BM25 Lexical Search Engine.

Validates:
1. Engine initialization & indexing with the project's actual literary passage dataset.
2. Complete provenance metadata retention: work, section, chapter, verse, entity, concept, source identifiers.
3. Exact term matching and Tamil Unicode normalization.
4. Multiple keywords search with coordination scoring.
5. Phrase-like matching (quoted phrases and contiguous token sequences).
6. Metadata filtering by work, section, chapter, verse, entity, concept, source_id, and tinai.
7. Normalized BM25 score guarantees (0.0 <= score <= 1.0) and sort ordering.
8. Local index persistence, disk caching, and fast startup loading without request-time re-indexing.
9. Integration with BM25Retriever and Flask API endpoints (/api/retrieval/bm25, /api/retrieval/lexical).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from retrieval.lexical_search import (
    LexicalSearchEngine,
    PassageDocument,
    LexicalSearchResult,
    lexical_search_engine,
)
from retrieval.bm25 import BM25Retriever
from app import create_app


@pytest.fixture
def engine():
    """Provides a ready instance of the LexicalSearchEngine."""
    return lexical_search_engine


@pytest.fixture
def test_client():
    """Flask test client for API route verification."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. Dataset Indexing & Provenance Metadata Tests
# =============================================================================

class TestDatasetIndexingAndMetadata:

    def test_engine_indexes_actual_corpus(self, engine: LexicalSearchEngine):
        """Verifies that the engine indexes the actual literary dataset."""
        assert len(engine.documents) > 0
        stats = engine.get_statistics()
        assert stats["total_documents"] >= 6
        assert stats["primary_passages"] == 6
        assert stats["unique_works"] >= 1
        assert stats["unique_sections"] >= 1
        assert stats["unique_chapters"] >= 1
        assert stats["unique_entities"] > 0
        assert stats["unique_concepts"] > 0

    def test_passage_metadata_fields_complete(self, engine: LexicalSearchEngine):
        """
        Validates that indexed passage text is stored together with all required metadata:
        work, section, chapter, verse, entity, concept, and source identifiers.
        """
        primary_docs = [
            d for d in engine.documents
            if d.source_metadata.get("document_level") == "passage"
        ]
        assert len(primary_docs) >= 6

        for doc in primary_docs:
            meta = doc.source_metadata
            # 1. Passage ID
            assert doc.passage_id.startswith("tol-porul-"), f"Invalid passage ID: {doc.passage_id}"

            # 2. Text
            assert len(doc.text.strip()) > 0, f"Empty text for {doc.passage_id}"

            # 3. Work
            assert meta.get("work") == "Tolkāppiyam"

            # 4. Section
            assert meta.get("section") == "Poruḷatikāram"

            # 5. Chapter
            assert meta.get("chapter") in ("Akattiṇaiyiyal", "Meyppāṭṭiyal")

            # 6. Verse (sūtra number)
            assert meta.get("verse") is not None
            assert isinstance(meta.get("verse"), int)

            # 7. Entity
            assert "entity" in meta
            assert isinstance(meta["entity"], list)
            assert len(meta["entity"]) > 0

            # 8. Concept
            assert "concept" in meta
            assert isinstance(meta["concept"], list)
            assert len(meta["concept"]) > 0

            # 9. Source identifiers
            assert meta.get("source_identifier") == doc.passage_id
            assert "Tolkāppiyam" in meta.get("source_reference", "")


# =============================================================================
# 2. Search Capabilities: Exact Terms, Multiple Keywords, Phrase Matching
# =============================================================================

class TestSearchQueries:

    def test_exact_term_search(self, engine: LexicalSearchEngine):
        """Verifies searching with exact classical Tamil terms."""
        results = engine.search("முதல்கரு", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert "முதல்கரு" in top.text
        assert 0.0 < top.score <= 1.0
        assert top.passage_id == "tol-porul-akam-003"

    def test_deity_exact_terms(self, engine: LexicalSearchEngine):
        """Verifies finding specific ecological deities in Sūtra 5."""
        for deity in ["மாயோன்", "சேயோன்", "வேந்தன்", "வருணன்"]:
            results = engine.search(deity, top_k=2)
            assert len(results) > 0
            assert any(deity in r.text for r in results)
            # Should match tol-porul-akam-005
            matching_ids = [r.source_metadata.get("source_identifier") for r in results]
            assert any("tol-porul-akam-005" in mid for mid in matching_ids)

    def test_multiple_keywords_search(self, engine: LexicalSearchEngine):
        """Verifies multi-keyword search with term coordination."""
        results = engine.search("மாயோன் காடுறை உலகம் முல்லை", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert "tol-porul-akam-005" in top.passage_id
        assert top.score == 1.0
        assert len(top.matched_terms) >= 3

    def test_phrase_like_matching_with_quotes(self, engine: LexicalSearchEngine):
        """Verifies quoted phrase matching boosts or matches exact text."""
        results = engine.search('"முதல்கரு உரிப்பொருள் என்ற மூன்றே"', top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-003"
        assert top.phrase_matched is True
        assert top.score == 1.0

    def test_strict_phrase_matching_filtering(self, engine: LexicalSearchEngine):
        """Verifies require_phrase=True filters out non-contiguous matches."""
        # Exact phrase that exists in sutra 4
        phrase = "நிலம்பொழுது இரண்டின்"
        results = engine.search(phrase, top_k=5, require_phrase=True)
        assert len(results) > 0
        for r in results:
            assert "நிலம்பொழுது" in r.text and "இரண்டின்" in r.text
            assert r.phrase_matched is True

        # Non-existent phrase sequence
        no_results = engine.search('"நிலம்பொழுது மூன்றே"', top_k=5, require_phrase=True)
        assert len(no_results) == 0

    def test_exact_terms_parameter_enforcement(self, engine: LexicalSearchEngine):
        """Verifies that exact_terms must strictly appear in matched documents."""
        # Sutra 5 has both சேயோன் and மாயோன்
        results = engine.search(
            "உலகம்",
            top_k=5,
            exact_terms=["சேயோன்"],
        )
        assert len(results) > 0
        for r in results:
            assert "சேயோன்" in r.text

        # Sutra 3 does NOT have சேயோன்
        sutra_3_results = [r for r in results if r.passage_id == "tol-porul-akam-003"]
        assert len(sutra_3_results) == 0


# =============================================================================
# 3. Metadata Filtering Tests
# =============================================================================

class TestMetadataFiltering:

    def test_filter_by_work_and_section(self, engine: LexicalSearchEngine):
        """Verifies filtering by work and section names."""
        results = engine.search(
            "பொருள்",
            top_k=5,
            filters={"work": "Tolkāppiyam", "section": "Poruḷatikāram"},
        )
        assert len(results) > 0
        for r in results:
            assert r.source_metadata["work"] == "Tolkāppiyam"
            assert r.source_metadata["section"] == "Poruḷatikāram"

    def test_filter_by_chapter(self, engine: LexicalSearchEngine):
        """Verifies filtering by specific chapter (iyal)."""
        # Filter for Meyppāṭṭiyal
        results = engine.search(
            "பொருள்",
            top_k=5,
            filters={"chapter": "Meyppāṭṭiyal"},
        )
        assert len(results) > 0
        for r in results:
            assert r.source_metadata["chapter"] == "Meyppāṭṭiyal"
            assert "tol-porul-mey-001" in r.passage_id

        # Verify Akattiṇaiyiyal filter does not return Meyppāṭṭiyal
        results_akam = engine.search(
            "பொருள்",
            top_k=5,
            filters={"chapter": "Akattiṇaiyiyal"},
        )
        for r in results_akam:
            assert r.source_metadata["chapter"] == "Akattiṇaiyiyal"
            assert "tol-porul-mey-001" not in r.passage_id

    def test_filter_by_verse(self, engine: LexicalSearchEngine):
        """Verifies filtering by verse / sūtra number."""
        results = engine.search(
            "பொருள்",
            top_k=5,
            filters={"verse": 3},
            primary_passages_only=True,
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-akam-003"
        assert results[0].source_metadata["verse"] == 3

    def test_filter_by_entity(self, engine: LexicalSearchEngine):
        """Verifies filtering by entity membership."""
        # Filter by entity Cēyōṉ
        results = engine.search(
            "உலகம்",
            top_k=5,
            filters={"entity": "Cēyōṉ"},
        )
        assert len(results) > 0
        for r in results:
            entities = r.source_metadata["entities"]
            assert any("cēyōṉ" in str(e).lower() for e in entities)

    def test_filter_by_concept(self, engine: LexicalSearchEngine):
        """Verifies filtering by concept membership."""
        results = engine.search(
            "பொருள்",
            top_k=5,
            filters={"concept": "Epistemic Tripartite Semioc"},
        )
        assert len(results) > 0
        for r in results:
            concepts = r.source_metadata["concepts"]
            assert any("Epistemic Tripartite Semioc" in str(c) for c in concepts)

    def test_filter_by_source_identifier(self, engine: LexicalSearchEngine):
        """Verifies filtering by exact source identifier."""
        results = engine.search(
            "",
            top_k=5,
            filters={"source_id": "tol-porul-akam-005"},
            primary_passages_only=True,
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-akam-005"

    def test_filter_by_tinai(self, engine: LexicalSearchEngine):
        """Verifies filtering by ecological Tiṇai."""
        results = engine.search(
            "உலகம்",
            top_k=5,
            filters={"tinai": "Kuṟiñci"},
        )
        assert len(results) > 0
        for r in results:
            assert r.source_metadata["tinai"] == "Kuṟiñci"


# =============================================================================
# 4. Result Structure and Normalized Score Guarantees
# =============================================================================

class TestResultStructureAndScores:

    def test_normalized_score_bounds(self, engine: LexicalSearchEngine):
        """Verifies that returned scores are strictly between 0.0 and 1.0."""
        results = engine.search("புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல்", top_k=5)
        assert len(results) > 0
        for r in results:
            assert 0.0 <= r.score <= 1.0, f"Score out of bounds: {r.score}"

        # Scores must be in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_result_contract_fields(self, engine: LexicalSearchEngine):
        """Verifies that every result returns passage ID, text, source metadata, and normalized score."""
        results = engine.search("தெய்வம் உணாவே மாமரம்", top_k=2)
        assert len(results) > 0
        top = results[0]

        d = top.to_dict()
        assert "passage_id" in d
        assert "text" in d
        assert "source_metadata" in d
        assert "score" in d
        assert "raw_score" in d
        assert "matched_terms" in d
        assert "phrase_matched" in d
        assert d["retrieval_method"] == "lexical_bm25"

        meta = d["source_metadata"]
        for required_meta in ("work", "section", "chapter", "verse", "entity", "concept", "source_identifier"):
            assert required_meta in meta, f"Missing required metadata: {required_meta}"


# =============================================================================
# 5. Persistence, Cache Validation, and Fast Startup Tests
# =============================================================================

class TestPersistenceAndStartup:

    def test_save_and_load_index(self, engine: LexicalSearchEngine):
        """Verifies saving index to disk and restoring without loss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_bm25_cache.json"

            # Save
            saved_path = engine.save_index(cache_file)
            assert saved_path.exists()

            # Load into fresh engine
            new_engine = LexicalSearchEngine(
                cache_dir=tmpdir,
                auto_initialize=False,
            )
            success = new_engine.load_index(cache_file)
            assert success is True
            assert len(new_engine.documents) == len(engine.documents)
            assert new_engine._corpus_hash == engine._corpus_hash

            # Search on loaded engine
            results = new_engine.search("முதல்கரு", top_k=2)
            assert len(results) > 0
            assert results[0].passage_id == "tol-porul-akam-003"

    def test_persistent_cache_file_exists_in_processed(self, engine: LexicalSearchEngine):
        """Verifies that the default persistent cache file exists on disk."""
        assert engine.cache_path.exists(), f"Cache file not found at {engine.cache_path}"
        with open(engine.cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "documents" in data
        assert "corpus_hash" in data
        assert len(data["documents"]) > 0


# =============================================================================
# 6. Backward Compatibility & API Integration Tests
# =============================================================================

class TestAPIAndBackwardCompatibility:

    def test_bm25_retriever_compatibility(self):
        """Verifies BM25Retriever methods remain functional and backward compatible."""
        retriever = BM25Retriever()
        results = retriever.search("முதல்கரு உரிப்பொருள்", top_k=2)
        assert len(results) > 0
        top_rec, score = results[0]
        assert 0.0 < score <= 1.0

        # Test search_passages
        passage_results = retriever.search_passages("முதல்கரு", top_k=2)
        assert len(passage_results) > 0
        assert passage_results[0].passage_id == "tol-porul-akam-003"

    def test_flask_bm25_endpoint_with_filters(self, test_client):
        """Verifies POST /api/retrieval/bm25 with query and filters."""
        res = test_client.post(
            "/api/retrieval/bm25",
            json={
                "query": "பொருள்",
                "top_k": 3,
                "filters": {"chapter": "Akattiṇaiyiyal"},
            },
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert len(results) > 0
        for r in results:
            assert "source" in r
            assert "text" in r

    def test_flask_lexical_endpoint_returns_passage_metadata(self, test_client):
        """Verifies POST /api/retrieval/lexical returns passage ID, text, source metadata, and score."""
        res = test_client.post(
            "/api/retrieval/lexical",
            json={
                "query": "சேயோன் மேய மைவரை குறிஞ்சி",
                "top_k": 3,
                "filters": {"entity": "Cēyōṉ"},
            },
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert len(results) > 0

        top = results[0]
        assert "passage_id" in top
        assert "text" in top
        assert "source_metadata" in top
        assert "score" in top
        assert 0.0 < top["score"] <= 1.0

        meta = top["source_metadata"]
        assert meta["work"] == "Tolkāppiyam"
        assert meta["section"] == "Poruḷatikāram"
        assert meta["chapter"] == "Akattiṇaiyiyal"
        assert meta["verse"] == 5
        assert "Cēyōṉ" in meta["entities"]
        assert meta["source_identifier"] == "tol-porul-akam-005"
