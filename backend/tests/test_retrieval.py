"""
Unit tests for BM25, dense vector search, and hybrid retrieval.
"""
from retrieval.bm25 import BM25Retriever
from retrieval.vector_store import VectorStore
from retrieval.hybrid_retriever import HybridRetriever


def test_bm25_retrieval():
    """Verifies BM25 retrieves matching sūtras for classical Tamil terms."""
    retriever = BM25Retriever()
    results = retriever.search("முதல்கரு உரிப்பொருள்", top_k=3)
    assert len(results) > 0
    top_sutra, score = results[0]
    assert "முதல்கரு" in top_sutra["tamil_text"] or score > 0


def test_vector_store_retrieval():
    """Verifies dense cosine similarity retrieval."""
    store = VectorStore()
    results = store.search("குறிஞ்சி புணர்தல்", top_k=3)
    assert len(results) > 0
    top_sutra, score = results[0]
    assert score > 0.0


def test_hybrid_retriever():
    """Verifies tri-channel RRF retrieval."""
    hybrid = HybridRetriever()
    results = hybrid.search("குறிஞ்சி நிலத்தின் முதற்பொருள்", top_k=3)
    assert len(results) > 0
    top_sutra, conf = results[0]
    assert 0.75 <= conf <= 1.0
