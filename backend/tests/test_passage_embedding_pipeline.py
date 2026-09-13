"""
Unit and Integration Tests for PassageEmbeddingPipeline.

Verifies:
1. Configurable multilingual embedding model and provider via environment variables / constructor.
2. Filtering and skipping of empty, whitespace-only, and invalid passages.
3. Strict preservation of original passage text, translations, transliterations, and metadata.
4. Deterministic passage ID generation ensuring idempotent updates without duplicates.
5. Batch vectorization with retry handling and exponential backoff.
6. Neo4j vector indexing and batch embedding storage.
7. Local .npz and JSON manifest persistence.
8. Flask API route POST /api/search/embeddings/rebuild.
"""
import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from config import Config
from retrieval.passage_embedding_pipeline import (
    PassageEmbeddingPipeline,
    ValidatedPassage,
    SkippedPassage,
    PipelineReport,
    passage_embedding_pipeline,
)
from knowledge_graph.neo4j_repository import Neo4jRepository


# =============================================================================
# 1. Configuration & Model Selection Tests
# =============================================================================

def test_pipeline_configuration_defaults():
    """Verifies that the pipeline adopts default environment configurations."""
    pipeline = PassageEmbeddingPipeline()
    assert pipeline.model_name == Config.EMBEDDING_MODEL_NAME
    assert pipeline.provider in ("sentence-transformers", "huggingface", "dense-ngram", "fallback")
    assert pipeline.batch_size == Config.EMBEDDING_BATCH_SIZE
    assert pipeline.vector_dim == Config.EMBEDDING_VECTOR_DIM


def test_custom_provider_selection():
    """Verifies switching provider to pure deterministic dense n-gram fallback."""
    pipeline = PassageEmbeddingPipeline(provider="dense-ngram", vector_dim=128)
    assert pipeline.provider == "dense-ngram"
    assert pipeline.vector_dim == 128


# =============================================================================
# 2. Validation & Invalid Passage Rejection Tests
# =============================================================================

def test_validate_valid_passage():
    """Tests validation of a complete, well-formed Classical Tamil passage."""
    pipeline = PassageEmbeddingPipeline(provider="dense-ngram")
    raw = {
        "id": "tol-porul-akam-003",
        "sutra_number": 3,
        "tamil_text": "முதல்கரு உரிப்பொருள் என்ற மூன்றே...",
        "english_translation": "Primary ground, biotic elements, and interior mood are the three...",
        "transliteration": "mutalkaru uripporuḷ eṉṟa mūṉṟē...",
        "atikaram": "பொருளதிகாரம்",
        "iyal": "அகத்திணையியல்",
        "tinai": "General",
        "metadata": {"category": "TripartiteSemiotics"},
    }
    val, skip = pipeline.validate_passage(raw)
    assert skip is None
    assert val is not None
    assert val.passage_id == "tol-porul-akam-003"
    assert val.original_text == "முதல்கரு உரிப்பொருள் என்ற மூன்றே..."
    assert len(val.normalized_text) > 0
    # Verified: original text & translation preserved
    assert val.translation == "Primary ground, biotic elements, and interior mood are the three..."
    assert val.metadata["category"] == "TripartiteSemiotics"


def test_reject_empty_and_whitespace_passages():
    """Tests that empty or whitespace-only passages are strictly rejected and skipped."""
    pipeline = PassageEmbeddingPipeline(provider="dense-ngram")

    # Empty text
    raw_empty = {"id": "p-1", "tamil_text": ""}
    val, skip = pipeline.validate_passage(raw_empty)
    assert val is None
    assert skip is not None
    assert "empty" in skip.reason.lower()

    # Whitespace only
    raw_ws = {"id": "p-2", "tamil_text": "   \t\n  "}
    val, skip = pipeline.validate_passage(raw_ws)
    assert val is None
    assert skip is not None
    assert "whitespace" in skip.reason.lower()

    # Text too short (< 3 chars)
    raw_short = {"id": "p-3", "tamil_text": "அ"}
    val, skip = pipeline.validate_passage(raw_short)
    assert val is None
    assert skip is not None
    assert "too short" in skip.reason.lower()

    # Null dictionary
    val, skip = pipeline.validate_passage(None)
    assert val is None
    assert skip is not None


# =============================================================================
# 3. Deterministic Passage IDs & Idempotency Tests
# =============================================================================

def test_deterministic_id_generation():
    """Tests that deterministic, canonical IDs are generated consistently."""
    pipeline = PassageEmbeddingPipeline(provider="dense-ngram")

    # Canonical sūtra in Akattinaiyiyal
    raw_1 = {"sutra_number": 5, "iyal": "அகத்திணையியல்", "text": "மாயோன் மேய காடுறை உலகமும்..."}
    val_1, _ = pipeline.validate_passage(raw_1)
    assert val_1.passage_id == "tol-porul-akam-005"

    # Canonical sūtra in Meyppattiyal
    raw_2 = {"sutra_number": 1, "iyal": "மெய்ப்பாட்டியல்", "text": "பண்ணைத் தோன்றிய எண்வகைப் பொருளும்..."}
    val_2, _ = pipeline.validate_passage(raw_2)
    assert val_2.passage_id == "tol-porul-mey-001"

    # Repeated validation yields identical IDs (zero duplicates)
    val_1_again, _ = pipeline.validate_passage(raw_1)
    assert val_1_again.passage_id == val_1.passage_id


# =============================================================================
# 4. Batching & Retry Handling Tests
# =============================================================================

def test_batching_and_retry_with_backoff():
    """Tests that passages are processed in batches and transient errors trigger retry."""
    pipeline = PassageEmbeddingPipeline(provider="dense-ngram", batch_size=2, max_retries=3, retry_backoff=0.01)

    passages = [
        ValidatedPassage(
            passage_id=f"p-{i}",
            original_text=f"பாடல் வரிகள் எண் {i}",
            normalized_text=f"பாடல் வரிகள் எண் {i}",
            embedding_input_text=f"பாடல் வரிகள் எண் {i}",
        )
        for i in range(5)
    ]

    # Mock encoder that fails on the first attempt of a batch, then succeeds
    call_count = {"val": 0}
    original_encode = pipeline.encoder.encode

    def flaky_encode(texts):
        call_count["val"] += 1
        if call_count["val"] == 1:
            raise RuntimeError("Transient network hiccup")
        return original_encode(texts)

    pipeline.encoder.encode = flaky_encode

    embeddings = pipeline.generate_embeddings_with_retry(passages)
    assert embeddings.shape[0] == 5
    assert call_count["val"] > 1  # Verify that retry occurred


# =============================================================================
# 5. Neo4j Vector Storage & Vector Indexing Tests
# =============================================================================

def test_neo4j_vector_storage_mock():
    """Tests storing embeddings in Neo4j and verifying vector index creation."""
    mock_repo = MagicMock(spec=Neo4jRepository)
    mock_repo.is_available.return_value = True
    mock_repo.ensure_passage_vector_index.return_value = {
        "status": "ready",
        "index_name": "passage_embeddings_index",
        "dimensions": 384,
        "similarity_function": "cosine",
    }
    mock_repo.batch_set_passage_embeddings.return_value = {
        "total_items": 2,
        "updated": 2,
    }

    pipeline = PassageEmbeddingPipeline(
        provider="dense-ngram",
        vector_dim=384,
        neo4j_repo=mock_repo,
    )

    test_passages = [
        {
            "id": "tol-porul-akam-003",
            "tamil_text": "முதல்கரு உரிப்பொருள் என்ற மூன்றே",
            "english_translation": "Primary ground, biotic signifiers, and affective mood",
        },
        {
            "id": "tol-porul-akam-004",
            "tamil_text": "மாயோன் மேய காடுறை உலகமும்",
            "english_translation": "The forest world presided over by Mayon",
        },
    ]

    report = pipeline.run_pipeline(
        passages=test_passages,
        update_neo4j=True,
        save_local_cache=False,
    )

    assert report.status == "completed"
    assert report.valid_passages == 2
    assert report.skipped_passages == 0
    assert report.neo4j_updated == 2
    mock_repo.ensure_passage_vector_index.assert_called_once()
    mock_repo.batch_set_passage_embeddings.assert_called_once()


# =============================================================================
# 6. End-to-End Pipeline Execution with Local Persistence
# =============================================================================

def test_pipeline_run_end_to_end(tmp_path):
    """Executes end-to-end pipeline run on canonical corpus with local cache saving."""
    pipeline = PassageEmbeddingPipeline(
        provider="dense-ngram",
        vector_dim=64,
        batch_size=3,
        cache_dir=tmp_path,
    )

    report = pipeline.run_pipeline(update_neo4j=False, save_local_cache=True)

    assert report.status == "completed"
    assert report.valid_passages > 0
    assert report.batch_count >= 1
    assert report.local_cache_path is not None
    assert os.path.exists(report.local_cache_path)

    # Verify saved .npz structure
    data = np.load(report.local_cache_path)
    assert "passage_ids" in data
    assert "embeddings" in data
    assert len(data["passage_ids"]) == report.valid_passages
    assert data["embeddings"].shape[0] == report.valid_passages


# =============================================================================
# 7. Flask REST API Route Test (/api/search/embeddings/rebuild)
# =============================================================================

def test_api_rebuild_embeddings_endpoint():
    """Tests POST /api/search/embeddings/rebuild."""
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        payload = {
            "batch_size": 10,
            "update_neo4j": False,
            "passages": [
                {
                    "id": "tol-porul-akam-003",
                    "tamil_text": "முதல்கரு உரிப்பொருள் என்ற மூன்றே",
                    "english_translation": "Threefold semiotics of Tolkappiyam",
                },
                {
                    "id": "invalid-blank",
                    "tamil_text": "   ",  # Should be skipped
                },
            ],
        }
        res = client.post("/api/search/embeddings/rebuild", json=payload)
        assert res.status_code == 200

        data = res.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["valid_passages"] == 1
        assert data["data"]["skipped_passages"] == 1
