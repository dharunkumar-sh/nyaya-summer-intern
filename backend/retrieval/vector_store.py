"""
Dense Vector Store executing high-performance Cosine similarity indexing over Tolkāppiyam sūtras.
"""
import numpy as np
from typing import List, Dict, Any, Tuple
from .embeddings import EmbeddingGenerator
from core.logger import logger


class VectorStore:
    """Stores vectors and executes fast top-K cosine similarity retrieval."""

    def __init__(self, embedding_generator: EmbeddingGenerator = None):
        self.encoder = embedding_generator or EmbeddingGenerator()
        self.records: List[Dict[str, Any]] = []
        self.matrix: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self.build_index()

    def build_index(self) -> None:
        """Indexes all sūtras from corpus_loader."""
        from ingestion.corpus_loader import corpus_loader
        sutras = corpus_loader.get_all_sutras()
        if not sutras:
            return

        texts = [s["tamil_text"] + " " + s.get("english_translation", "") for s in sutras]
        self.encoder.fit(texts)
        self.matrix = self.encoder.encode(texts)
        self.records = sutras
        logger.info(f"Vector Store indexed {len(self.records)} sūtras (dim: {self.matrix.shape[1]})")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Computes cosine similarity of query against all stored vectors."""
        if len(self.records) == 0:
            return []

        query_vec = self.encoder.encode_one(query)
        # Cosine similarity is dot product because vectors are L2-normalized
        scores = np.dot(self.matrix, query_vec)

        # Get top-K indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((self.records[idx], float(scores[idx])))

        return results
