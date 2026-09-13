"""
Unit and integration tests for RAG Retrieval Infrastructure.

Tests:
- RetrievalChunk schema and PassageChunker
- SentenceTransformer & DenseNgram embedding generation
- FAISS Vector Index exact cosine similarity search
- BM25 lexical keyword retrieval over chunks
- RAGRetrievalEngine: semantic_search, bm25_search, retrieve_by_source, retrieve_by_entity, hybrid_search
- Source traceability preservation in all results
- REST API endpoints under /api/retrieval
"""
import pytest
import numpy as np
from app import create_app
from retrieval.chunker import RetrievalChunk, PassageChunker
from retrieval.embeddings import (
    DenseNgramEmbeddingGenerator,
    SentenceTransformerEmbeddingGenerator,
    cosine_similarity,
)
from retrieval.faiss_index import FAISSVectorIndex
from retrieval.bm25 import BM25Retriever
from retrieval.rag_service import RAGRetrievalEngine, rag_engine


SAMPLE_PASSAGE = {
    "document_id": "tol-porul-akam-005",
    "work": "Tolkāppiyam",
    "section": "Poruḷatikāram",
    "chapter": "Akattiṇaiyiyal",
    "passage_id": "tol-porul-akam-005",
    "original_text": (
        "மாயோன் மேய காடுறை உலகமும்\n"
        "சேயோன் மேய மைவரை உலகமும்\n"
        "வேந்தன் மேய தீம்புனல் உலகமும்\n"
        "வருணன் மேய பெருமணல் உலகமும்\n"
        "முல்லை குறிஞ்சி மருதம் நெய்தல்எனச்\n"
        "சொல்லிய முறையால் சொல்லவும் படுமே."
    ),
    "normalized_text": (
        "மாயோன் மேய காடுறை உலகமும்\n"
        "சேயோன் மேய மைவரை உலகமும்\n"
        "வேந்தன் மேய தீம்புனல் உலகமும்\n"
        "வருணன் மேய பெருமணல் உலகமும்\n"
        "முல்லை குறிஞ்சி மருதம் நெய்தல்எனச்\n"
        "சொல்லிய முறையால் சொல்லவும் படுமே."
    ),
    "verse_lines": [
        "மாயோன் மேய காடுறை உலகமும்",
        "சேயோன் மேய மைவரை உலகமும்",
        "வேந்தன் மேய தீம்புனல் உலகமும்",
        "வருணன் மேய பெருமணல் உலகமும்",
        "முல்லை குறிஞ்சி மருதம் நெய்தல்எனச்",
        "சொல்லிய முறையால் சொல்லவும் படுமே.",
    ],
    "metadata": {
        "sutra_number": 5,
        "tinai": "Kuṟiñci",
        "category": "Ecological Deity & Habitat Concordance",
        "entities": ["Māyōṉ", "Cēyōṉ", "Vēntan", "Varuṇaṉ", "Kuṟiñci", "Mullai"],
        "english_translation": "The forested realm overseen by Māyōṉ (Mullai)...",
    },
}


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


# ===========================================================================
# 1. Chunking & RetrievalChunk Schema
# ===========================================================================

class TestChunking:

    def test_chunk_schema(self):
        chunk = RetrievalChunk(
            chunk_id="chk-001",
            document_id="doc-001",
            work="Tolkāppiyam",
            section="Poruḷatikāram",
            passage_id="pass-001",
            text="குறிஞ்சி நிலம்",
            source="Tolkāppiyam Akattiṇaiyiyal Sūtra 5",
            metadata={"tinai": "Kuṟiñci"},
        )
        d = chunk.to_dict()
        required_keys = {
            "chunk_id", "document_id", "work", "section",
            "passage_id", "text", "source", "metadata",
        }
        assert required_keys.issubset(d.keys())

    def test_passage_chunker_primary(self):
        chunks = PassageChunker.chunk_passage(SAMPLE_PASSAGE, chunk_by_verse_lines=False)
        assert len(chunks) == 1
        c = chunks[0]
        assert c.document_id == "tol-porul-akam-005"
        assert c.work == "Tolkāppiyam"
        assert "Akattiṇaiyiyal" in c.section
        assert "Sūtra 5" in c.source
        assert "சேயோன்" in c.text

    def test_passage_chunker_verse_lines(self):
        chunks = PassageChunker.chunk_passage(SAMPLE_PASSAGE, chunk_by_verse_lines=True)
        # 1 primary + 6 line chunks = 7 chunks
        assert len(chunks) == 7
        line_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "line"]
        assert len(line_chunks) == 6
        assert all("Line" in c.source for c in line_chunks)

    def test_chunk_corpus(self):
        chunks = PassageChunker.chunk_corpus([SAMPLE_PASSAGE], chunk_by_verse_lines=True)
        assert len(chunks) >= 7


# ===========================================================================
# 2. Embeddings & Cosine Similarity
# ===========================================================================

class TestEmbeddings:

    def test_dense_ngram_embedding_normalized(self):
        encoder = DenseNgramEmbeddingGenerator()
        texts = ["குறிஞ்சி நிலம்", "முல்லை நிலம் காடு"]
        vecs = encoder.encode(texts)
        assert vecs.shape[0] == 2
        # Check L2 unit normalization
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, [1.0, 1.0], atol=1e-5)

    def test_sentence_transformer_generator(self):
        st_encoder = SentenceTransformerEmbeddingGenerator()
        texts = ["மாயோன் மேய காடுறை", "சேயோன் மேய மைவரை"]
        vecs = st_encoder.encode(texts)
        assert vecs.shape[0] == 2
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, [1.0, 1.0], atol=1e-5)

    def test_cosine_similarity_identity(self):
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert pytest.approx(cosine_similarity(v1, v1), 0.001) == 1.0

    def test_cosine_similarity_orthogonal(self):
        v1 = np.array([1.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0], dtype=np.float32)
        assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 0.0


# ===========================================================================
# 3. FAISS Vector Index
# ===========================================================================

class TestFAISSIndex:

    def test_faiss_add_and_search(self):
        dim = 32
        index = FAISSVectorIndex(dimension=dim)
        chunks = [
            RetrievalChunk(
                chunk_id=f"chk-{i}",
                document_id=f"doc-{i}",
                work="Tolkāppiyam",
                section="Poruḷ",
                passage_id=f"doc-{i}",
                text=f"Text {i}",
                source=f"Source {i}",
            )
            for i in range(5)
        ]
        # Random L2-normalized embeddings
        rng = np.random.default_rng(42)
        raw_vecs = rng.standard_normal((5, dim)).astype(np.float32)
        norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
        vecs = raw_vecs / norms

        index.add_chunks(chunks, vecs)
        assert index.size() == 5

        # Query with first vector
        results = index.search(vecs[0], top_k=3)
        assert len(results) == 3
        top_chunk, score = results[0]
        assert top_chunk.chunk_id == "chk-0"
        assert pytest.approx(score, 0.01) == 1.0

    def test_faiss_get_chunk_by_id(self):
        dim = 8
        index = FAISSVectorIndex(dimension=dim)
        chunk = RetrievalChunk(
            chunk_id="test-chunk-xyz",
            document_id="doc-xyz",
            work="Tolkāppiyam",
            section="Poruḷ",
            passage_id="doc-xyz",
            text="Sample",
            source="Citation",
        )
        vec = np.ones((1, dim), dtype=np.float32)
        index.add_chunks([chunk], vec)

        found = index.get_chunk_by_id("test-chunk-xyz")
        assert found is not None
        assert found.text == "Sample"


# ===========================================================================
# 4. BM25 Lexical Index
# ===========================================================================

class TestBM25Retriever:

    def test_bm25_index_chunks(self):
        retriever = BM25Retriever()
        chunks = [
            RetrievalChunk(
                chunk_id="c1",
                document_id="d1",
                work="Tolkāppiyam",
                section="Poruḷ",
                passage_id="p1",
                text="சேயோன் மேய மைவரை குறிஞ்சி",
                source="Sūtra 5",
            ),
            RetrievalChunk(
                chunk_id="c2",
                document_id="d2",
                work="Tolkāppiyam",
                section="Poruḷ",
                passage_id="p2",
                text="மாயோன் மேய காடுறை முல்லை",
                source="Sūtra 5",
            ),
        ]
        retriever.index_chunks(chunks)
        results = retriever.search_chunks("சேயோன்", top_k=2)
        assert len(results) > 0
        top_chunk, score = results[0]
        assert top_chunk.chunk_id == "c1"
        assert 0.0 < score <= 1.0


# ===========================================================================
# 5. RAG Retrieval Engine Operations
# ===========================================================================

class TestRAGRetrievalEngine:

    def test_semantic_search_returns_source_reference(self):
        results = rag_engine.semantic_search("குறிஞ்சி நிலத்து தெய்வம் சேயோன்", top_k=3)
        assert len(results) > 0
        top = results[0]
        for field in ("chunk_id", "document_id", "work", "section", "passage_id", "text", "source", "score"):
            assert field in top, f"Missing field {field} in semantic search result"
            assert top[field] != ""
        assert top["retrieval_method"] == "semantic_faiss"

    def test_bm25_search_returns_source_reference(self):
        results = rag_engine.bm25_search("சேயோன்", top_k=3)
        assert len(results) > 0
        top = results[0]
        for field in ("chunk_id", "document_id", "work", "section", "passage_id", "text", "source", "score"):
            assert field in top, f"Missing field {field} in BM25 search result"
        assert top["retrieval_method"] == "lexical_bm25"

    def test_retrieve_by_source(self):
        results = rag_engine.retrieve_by_source("tol-porul-akam-005")
        assert len(results) > 0
        for r in results:
            assert r["document_id"] == "tol-porul-akam-005"
            assert "source" in r
            assert "text" in r

    def test_retrieve_by_entity(self):
        results = rag_engine.retrieve_by_entity("Cēyōṉ")
        assert len(results) > 0
        for r in results:
            assert "source" in r
            assert "text" in r

    def test_hybrid_search(self):
        results = rag_engine.hybrid_search("முல்லை நிலம் காடு", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert "score" in top
        assert top["retrieval_method"] == "hybrid_rrf"
        assert "source" in top

    def test_get_statistics(self):
        stats = rag_engine.get_statistics()
        assert stats["total_chunks"] > 0
        assert stats["vector_dimension"] > 0
        assert stats["faiss_total_vectors"] > 0


# ===========================================================================
# 6. REST API Endpoints
# ===========================================================================

class TestRetrievalApiEndpoints:

    def test_post_semantic_search_valid(self, client):
        resp = client.post(
            "/api/retrieval/semantic",
            json={"query": "குறிஞ்சி நிலம்", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        results = data["data"]["results"]
        assert len(results) > 0
        assert "source" in results[0]

    def test_post_semantic_search_empty_query(self, client):
        resp = client.post("/api/retrieval/semantic", json={"query": ""})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_QUERY"

    def test_post_bm25_search_valid(self, client):
        resp = client.post(
            "/api/retrieval/bm25",
            json={"query": "சேயோன்", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        results = data["data"]["results"]
        assert len(results) > 0
        assert "source" in results[0]

    def test_post_bm25_search_empty_query(self, client):
        resp = client.post("/api/retrieval/bm25", json={"query": ""})
        assert resp.status_code == 400

    def test_post_hybrid_search_valid(self, client):
        resp = client.post(
            "/api/retrieval/hybrid",
            json={"query": "மாயோன் முல்லை", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["results"]) > 0

    def test_get_by_source_valid(self, client):
        resp = client.get("/api/retrieval/by-source/tol-porul-akam-005")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["results"]) > 0

    def test_get_by_source_not_found(self, client):
        resp = client.get("/api/retrieval/by-source/non_existent_id_999")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "SOURCE_NOT_FOUND"

    def test_get_by_entity_valid(self, client):
        resp = client.get("/api/retrieval/by-entity/Cēyōṉ")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["results"]) > 0

    def test_get_statistics_endpoint(self, client):
        resp = client.get("/api/retrieval/statistics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["total_chunks"] > 0
        assert data["data"]["faiss_total_vectors"] > 0

    def test_trigger_indexing_endpoint(self, client):
        resp = client.post("/api/retrieval/index")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["total_chunks"] > 0
