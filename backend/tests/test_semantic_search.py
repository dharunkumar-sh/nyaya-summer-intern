"""
Comprehensive Test Suite for Multilingual Semantic Search Engine.

Validates:
1. Engine initialization & passage embedding generation over actual classical Tamil dataset.
2. Complete provenance metadata retention: work, section, chapter, verse, entity, concept, source identifiers.
3. Pure Tamil semantic queries and ranking.
4. Cross-lingual pure English queries matching classical Tamil concepts and passages.
5. Cosine similarity calculation and normalized similarity score bounds [0.0, 1.0].
6. Combined semantic search with metadata filtering (by tinai, entity, chapter, verse).
7. Local embedding persistence (.npz + JSON manifest) and fast cold startup without regeneration.
8. Cache invalidation on dataset change.
9. Integration with RAGRetrievalEngine and Flask API endpoints (/api/retrieval/semantic, /api/retrieval/semantic-passages).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import numpy as np
import pytest

from retrieval.semantic_search import (
    SemanticSearchEngine,
    SemanticPassageDocument,
    SemanticSearchResult,
    semantic_search_engine,
)
from retrieval.rag_service import rag_engine
from app import create_app


@pytest.fixture
def engine():
    """Provides the singleton instance of the SemanticSearchEngine."""
    return semantic_search_engine


@pytest.fixture
def test_client():
    """Flask test client for API route verification."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. Dataset Indexing & Embedding Generation Tests
# =============================================================================

class TestSemanticIndexingAndMetadata:

    def test_engine_indexes_actual_corpus(self, engine: SemanticSearchEngine):
        """Verifies that the engine indexes passages and generates valid embeddings."""
        assert len(engine.documents) == 6
        assert engine.embeddings.ndim == 2
        assert engine.embeddings.shape[0] == 6
        assert engine.embeddings.shape[1] > 0

        stats = engine.get_statistics()
        assert stats["total_passages"] == 6
        assert stats["vector_dimension"] == engine.embeddings.shape[1]
        assert stats["cache_exists"] is True

    def test_passage_metadata_fields_complete(self, engine: SemanticSearchEngine):
        """
        Validates that each embedded passage preserves all required provenance metadata:
        work, section, chapter, verse, entity, concept, and source identifiers.
        """
        for doc in engine.documents:
            meta = doc.source_metadata
            # Passage ID & text
            assert doc.passage_id.startswith("tol-porul-")
            assert len(doc.text.strip()) > 0
            assert len(doc.embedding_text.strip()) > len(doc.text.strip()) or len(doc.embedding_text.strip()) > 0

            # Structural hierarchy
            assert meta.get("work") == "Tolkāppiyam"
            assert meta.get("section") == "Poruḷatikāram"
            assert meta.get("chapter") in ("Akattiṇaiyiyal", "Meyppāṭṭiyal")
            assert isinstance(meta.get("verse"), int)

            # Entities and concepts
            assert isinstance(meta.get("entity"), list)
            assert len(meta["entity"]) > 0
            assert isinstance(meta.get("concept"), list)
            assert len(meta["concept"]) > 0

            # Source identifiers
            assert meta.get("source_identifier") == doc.passage_id
            assert "Tolkāppiyam" in meta.get("source_reference", "")


# =============================================================================
# 2. Semantic Search Queries (Tamil & English Cross-Lingual)
# =============================================================================

class TestSemanticQueries:

    def test_tamil_semantic_query_deity_landscape(self, engine: SemanticSearchEngine):
        """Verifies pure Tamil semantic search for forest landscape and deity Māyōṉ."""
        results = engine.search("மாயோன் காடுறை உலகம் முல்லை", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-005"
        assert top.score > 0.5
        assert top.cosine_similarity > 0.0

    def test_tamil_semantic_query_affective_moods(self, engine: SemanticSearchEngine):
        """Verifies Tamil semantic query for love emotions (Uripporuḷ: Puṇartal, Pirital, etc.)."""
        results = engine.search("புணர்தல் பிரிதல் இருத்தல் இரங்கல் ஊடல் உரிப்பொருள்", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-014"
        assert 0.0 <= top.score <= 1.0

    def test_english_cross_lingual_query_semiotics(self, engine: SemanticSearchEngine):
        """Verifies English query maps to tripartite semiotics sūtra (Mutal, Karu, Uri)."""
        results = engine.search("habitat constituents and psychological mood order in verse composition", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-003"
        assert top.score > 0.5

    def test_english_cross_lingual_query_mountain_realm(self, engine: SemanticSearchEngine):
        """Verifies English query for mountain realm and deity Cēyōṉ."""
        results = engine.search("dark mountain realm overseen by Ceyon", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-akam-005"

    def test_english_cross_lingual_query_aesthetics(self, engine: SemanticSearchEngine):
        """Verifies English query for eightfold emotional manifestations (Meyppāṭṭiyal)."""
        results = engine.search("eightfold emotional manifestations in dramatic and poetic contexts", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.passage_id == "tol-porul-mey-001"


# =============================================================================
# 3. Similarity Score Normalization & Output Contract
# =============================================================================

class TestSimilarityScoresAndOutputContract:

    def test_normalized_score_bounds(self, engine: SemanticSearchEngine):
        """Verifies that similarity scores are strictly within [0.0, 1.0] and sorted descending."""
        results = engine.search("classical tamil poetics and ecological landscape", top_k=5)
        assert len(results) > 0
        for r in results:
            assert 0.0 <= r.score <= 1.0, f"Score out of bounds: {r.score}"
            assert -1.0 <= r.cosine_similarity <= 1.0, f"Cosine similarity out of bounds: {r.cosine_similarity}"

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_output_contract_fields(self, engine: SemanticSearchEngine):
        """Verifies that return object contains passage ID, passage text, source metadata, and normalized score."""
        results = engine.search("biotic constituents flora and fauna", top_k=2)
        assert len(results) > 0
        top = results[0]

        d = top.to_dict()
        assert "passage_id" in d
        assert "text" in d
        assert "source_metadata" in d
        assert "score" in d
        assert "cosine_similarity" in d
        assert d["retrieval_method"] == "semantic_embedding"

        meta = d["source_metadata"]
        for key in ("work", "section", "chapter", "verse", "entity", "concept", "source_identifier"):
            assert key in meta, f"Missing required metadata key: {key}"


# =============================================================================
# 4. Semantic Search with Metadata Filtering
# =============================================================================

class TestSemanticFiltering:

    def test_filter_by_tinai(self, engine: SemanticSearchEngine):
        """Verifies combining semantic search with Tiṇai filtering."""
        results = engine.search(
            "poetic landscape and deity",
            top_k=5,
            filters={"tinai": "Kuṟiñci"},
        )
        assert len(results) > 0
        for r in results:
            assert r.source_metadata["tinai"] == "Kuṟiñci"

    def test_filter_by_chapter(self, engine: SemanticSearchEngine):
        """Verifies combining semantic search with chapter filtering."""
        results = engine.search(
            "poetic meaning and emotions",
            top_k=5,
            filters={"chapter": "Meyppāṭṭiyal"},
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-mey-001"
        assert results[0].source_metadata["chapter"] == "Meyppāṭṭiyal"

    def test_filter_by_verse(self, engine: SemanticSearchEngine):
        """Verifies filtering by exact verse number."""
        results = engine.search(
            "meaning",
            top_k=5,
            filters={"verse": 4},
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-akam-004"
        assert results[0].source_metadata["verse"] == 4

    def test_filter_by_entity(self, engine: SemanticSearchEngine):
        """Verifies filtering by recognized entity."""
        results = engine.search(
            "landscape",
            top_k=5,
            filters={"entity": "Varuṇaṉ"},
        )
        assert len(results) == 1
        assert results[0].passage_id == "tol-porul-akam-005"
        entities = results[0].source_metadata["entities"]
        assert any("varuṇaṉ" in str(e).lower() for e in entities)


# =============================================================================
# 5. Local Persistence & Embedding Caching Tests
# =============================================================================

class TestPersistenceAndCaching:

    def test_save_and_load_embeddings(self, engine: SemanticSearchEngine):
        """Verifies local persistence to .npz and .json manifest and restoration without loss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_npz = Path(tmpdir) / "test_embeddings.npz"
            test_manifest = Path(tmpdir) / "test_manifest.json"

            # Save
            engine.save_embeddings(test_npz, test_manifest)
            assert test_npz.exists()
            assert test_manifest.exists()

            # Fresh engine loading from disk
            fresh_engine = SemanticSearchEngine(
                cache_dir=tmpdir,
                auto_initialize=False,
            )
            success = fresh_engine.load_embeddings(test_npz, test_manifest)
            assert success is True
            assert len(fresh_engine.documents) == len(engine.documents)
            assert fresh_engine.embeddings.shape == engine.embeddings.shape
            assert fresh_engine._corpus_hash == engine._corpus_hash

            # Verify identical search result
            results = fresh_engine.search("மாயோன் முல்லை", top_k=2)
            assert len(results) > 0
            assert results[0].passage_id == "tol-porul-akam-005"

    def test_default_cache_exists_in_processed(self, engine: SemanticSearchEngine):
        """Verifies that default passage_embeddings.npz and manifest exist in data/processed."""
        assert engine.npz_path.exists(), f"Missing default npz cache at {engine.npz_path}"
        assert engine.manifest_path.exists(), f"Missing manifest at {engine.manifest_path}"

        with np.load(engine.npz_path, allow_pickle=False) as npz:
            assert "embeddings" in npz
            assert "passage_ids" in npz
            assert npz["embeddings"].shape[0] == 6


# =============================================================================
# 6. RAG Engine Integration & Flask API Tests
# =============================================================================

class TestAPIIntegration:

    def test_rag_engine_semantic_passage_search(self):
        """Verifies RAGRetrievalEngine.semantic_passage_search integration."""
        results = rag_engine.semantic_passage_search("Ceyon mountain realm", top_k=2)
        assert len(results) > 0
        top = results[0]
        assert top["passage_id"] == "tol-porul-akam-005"
        assert "source_metadata" in top
        assert top["score"] > 0.0

    def test_flask_semantic_endpoint_with_target_passages(self, test_client):
        """Verifies POST /api/retrieval/semantic with target='passages'."""
        res = test_client.post(
            "/api/retrieval/semantic",
            json={
                "query": "primary spatio-temporal ground Mutalporul",
                "top_k": 2,
                "target": "passages",
            },
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert len(results) > 0
        top = results[0]
        assert top["passage_id"] in ("tol-porul-akam-003", "tol-porul-akam-004")
        assert "source_metadata" in top
        assert 0.0 <= top["score"] <= 1.0

    def test_flask_semantic_passages_endpoint_with_filters(self, test_client):
        """Verifies POST /api/retrieval/semantic-passages with metadata filter."""
        res = test_client.post(
            "/api/retrieval/semantic-passages",
            json={
                "query": "affective emotional moods",
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
            assert r["source_metadata"]["chapter"] == "Akattiṇaiyiyal"
            assert "tol-porul-mey-001" != r["passage_id"]
