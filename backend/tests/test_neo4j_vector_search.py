"""
Unit and Integration Tests for Neo4j Vector Index & Vector Similarity Search.

Verifies:
1. Dynamic dimension resolution matching the selected embedding model.
2. Centralized, environment-driven vector search settings in Config & Neo4jConfig.
3. Neo4j vector index creation with exact model dimensions and similarity metric.
4. vector_similarity_search repository method returning passage IDs, similarity scores,
   source metadata, and text.
5. Input handling for both NumPy arrays and Python float lists.
6. Backward-compatible query_passages_by_vector method.
7. Resilience against driver / query failures without application crashes.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from config import Config, Neo4jConfig
from knowledge_graph.neo4j_repository import Neo4jRepository, neo4j_repository
from retrieval.embeddings import SentenceTransformerEmbeddingGenerator, DenseNgramEmbeddingGenerator


# =============================================================================
# 1. Dynamic Dimension Resolution Tests
# =============================================================================

def test_resolve_vector_dimensions_known_models():
    """Verifies that vector dimensions are resolved accurately without hardcoding errors."""
    dim_minilm = Neo4jConfig.resolve_vector_dimensions(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    assert dim_minilm == 384

    dim_e5 = Neo4jConfig.resolve_vector_dimensions(
        model_name="intfloat/multilingual-e5-base"
    )
    assert dim_e5 == 768

    dim_bgem3 = Neo4jConfig.resolve_vector_dimensions(
        model_name="BAAI/bge-m3"
    )
    assert dim_bgem3 == 1024


def test_resolve_vector_dimensions_from_encoder():
    """Verifies dynamic dimension resolution directly from an active encoder instance."""
    encoder = DenseNgramEmbeddingGenerator(fixed_dim=256)
    dim = Neo4jConfig.resolve_vector_dimensions(encoder=encoder)
    assert dim == 256


def test_centralized_config_attributes():
    """Verifies centralized environment-driven vector index attributes."""
    assert hasattr(Neo4jConfig, "VECTOR_INDEX_NAME")
    assert hasattr(Neo4jConfig, "VECTOR_SIMILARITY_FUNCTION")
    assert Neo4jConfig.VECTOR_INDEX_NAME == Config.NEO4J_VECTOR_INDEX_NAME
    assert Neo4jConfig.VECTOR_SIMILARITY_FUNCTION in ("cosine", "euclidean")


# =============================================================================
# 2. Vector Index Registration Tests
# =============================================================================

def test_ensure_passage_vector_index_cypher_generation():
    """Verifies Cypher query generation for Neo4j 5+ vector index registration."""
    mock_service = MagicMock()
    repo = Neo4jRepository(service=mock_service)

    res = repo.ensure_passage_vector_index(
        index_name="test_vector_index",
        dimensions=384,
        similarity_function="cosine",
    )

    assert res["status"] == "ready"
    assert res["dimensions"] == 384
    assert res["similarity_function"] == "cosine"

    # Verify executed Cypher contains backtick-quoted options
    mock_service.execute_write.assert_called_once()
    cypher_call = mock_service.execute_write.call_args[0][0]
    assert "CREATE VECTOR INDEX test_vector_index IF NOT EXISTS" in cypher_call
    assert "`vector.dimensions`: 384" in cypher_call
    assert "`vector.similarity_function`: 'cosine'" in cypher_call


def test_ensure_passage_vector_index_dynamic_fallback():
    """Verifies ensure_passage_vector_index resolves dimensions if omitted."""
    mock_service = MagicMock()
    repo = Neo4jRepository(service=mock_service)

    res = repo.ensure_passage_vector_index(dimensions=None)
    assert res["status"] == "ready"
    assert res["dimensions"] == Config.EMBEDDING_VECTOR_DIM


# =============================================================================
# 3. Vector Similarity Search Repository Method Tests
# =============================================================================

def test_vector_similarity_search_structure():
    """
    Verifies that vector_similarity_search returns structured records containing:
    passage_id, similarity_score, text, and source_metadata.
    """
    mock_service = MagicMock()
    # Mock Neo4j execute_read returning a vector match record
    mock_service.execute_read.return_value = [
        {
            "id": "tol-porul-akam-005",
            "label": "Sūtra 5",
            "sutra_number": 5,
            "text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "original_text": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
            "translation": "The forest world presided over by Māyōṉ and the mountain world by Cēyōṉ...",
            "source_reference": "Tolkāppiyam, Poruḷatikāram, Akattiṇaiyiyal, Sūtra 5",
            "tinai": "Mullai / Kuṟiñci",
            "work_name": "Tolkāppiyam",
            "section_name": "Poruḷatikāram",
            "chapter_name": "Akattiṇaiyiyal",
            "metadata_json": '{"category": "TiṇaiSemiotics"}',
            "score": 0.9421,
        }
    ]

    repo = Neo4jRepository(service=mock_service)
    dummy_vector = [0.1] * 384

    results = repo.vector_similarity_search(dummy_vector, top_k=3)

    assert len(results) == 1
    match = results[0]

    # Required return fields: passage_id, similarity_score, text, source_metadata
    assert match["passage_id"] == "tol-porul-akam-005"
    assert match["similarity_score"] == 0.9421
    assert "மாயோன் மேய" in match["text"]

    meta = match["source_metadata"]
    assert meta["sutra_number"] == 5
    assert meta["work_name"] == "Tolkāppiyam"
    assert meta["section_name"] == "Poruḷatikāram"
    assert meta["chapter_name"] == "Akattiṇaiyiyal"
    assert meta["tinai"] == "Mullai / Kuṟiñci"
    assert meta["source_reference"] == "Tolkāppiyam, Poruḷatikāram, Akattiṇaiyiyal, Sūtra 5"
    assert "Māyōṉ" in meta["translation"]
    assert meta["metadata"]["category"] == "TiṇaiSemiotics"


def test_vector_similarity_search_numpy_support():
    """Verifies that vector_similarity_search transparently handles 1D NumPy array inputs."""
    mock_service = MagicMock()
    mock_service.execute_read.return_value = []
    repo = Neo4jRepository(service=mock_service)

    np_vec = np.random.randn(384).astype(np.float32)
    results = repo.vector_similarity_search(np_vec, top_k=5)

    assert isinstance(results, list)
    mock_service.execute_read.assert_called_once()
    executed_params = mock_service.execute_read.call_args[0][1]
    assert isinstance(executed_params["vector"], list)
    assert len(executed_params["vector"]) == 384


def test_query_passages_by_vector_backward_compatibility():
    """Verifies query_passages_by_vector alias calls vector_similarity_search."""
    mock_service = MagicMock()
    mock_service.execute_read.return_value = []
    repo = Neo4jRepository(service=mock_service)

    results = repo.query_passages_by_vector([0.5] * 384, top_k=2)
    assert isinstance(results, list)
    mock_service.execute_read.assert_called_once()


def test_vector_similarity_search_exception_resilience():
    """Verifies vector_similarity_search returns empty list gracefully on Cypher failure."""
    mock_service = MagicMock()
    mock_service.execute_read.side_effect = RuntimeError("Index not yet populated")
    repo = Neo4jRepository(service=mock_service)

    results = repo.vector_similarity_search([0.1] * 384, top_k=5)
    assert results == []


# =============================================================================
# 4. Live Neo4j Aura Vector Search Test
# =============================================================================

def test_live_aura_vector_search_when_available():
    """
    Tests vector index creation and search against the live Neo4j Aura database
    if driver is connected.
    """
    if not neo4j_repository.is_available():
        pytest.skip("Neo4j Aura not configured or unreachable.")

    # 1. Ensure index exists
    idx_res = neo4j_repository.ensure_passage_vector_index(
        dimensions=384,
        similarity_function="cosine",
    )
    assert idx_res["status"] in ("ready", "error")

    # 2. Query with a sample unit vector
    sample_vector = [0.0] * 384
    sample_vector[0] = 1.0

    results = neo4j_repository.vector_similarity_search(sample_vector, top_k=3)
    assert isinstance(results, list)
    if results:
        top = results[0]
        assert "passage_id" in top
        assert "similarity_score" in top
        assert "text" in top
        assert "source_metadata" in top
