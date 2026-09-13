"""
FAISS Vector Index for dense semantic retrieval.

Uses faiss.IndexFlatIP for exact cosine similarity search over L2-normalized vectors.
Maintains a bidirectional mapping between FAISS internal integer IDs and RetrievalChunks.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    _FAISS_AVAILABLE = False

from core.logger import logger
from .chunker import RetrievalChunk


class FAISSVectorIndex:
    """
    FAISS-powered vector similarity index executing exact inner-product (cosine) search,
    with an exact NumPy dot-product fallback if FAISS native binaries are not installed.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        if _FAISS_AVAILABLE and faiss is not None:
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.index = None
            self._vectors: Optional[np.ndarray] = None
        self.chunks: List[RetrievalChunk] = []
        self._chunk_id_to_idx: Dict[str, int] = {}

    def add_chunks(
        self,
        chunks: List[RetrievalChunk],
        embeddings: np.ndarray,
    ) -> None:
        """
        Adds chunks and their corresponding L2-normalized embeddings to the FAISS index.
        """
        if len(chunks) == 0 or embeddings.shape[0] == 0:
            return

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} does not match index dimension {self.dimension}"
            )

        # Ensure float32 format
        vectors = embeddings.astype(np.float32)

        # Ensure vectors are L2-normalized for exact cosine similarity via inner product
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms

        start_idx = len(self.chunks)
        if _FAISS_AVAILABLE and self.index is not None:
            self.index.add(vectors)
        else:
            if self._vectors is None:
                self._vectors = vectors
            else:
                self._vectors = np.vstack([self._vectors, vectors])

        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self._chunk_id_to_idx[chunk.chunk_id] = start_idx + i

        total = self.size()
        logger.info(f"Vector index added {len(chunks)} chunks (total: {total})")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> List[Tuple[RetrievalChunk, float]]:
        """
        Searches index using query vector and returns top_k (chunk, cosine_similarity) pairs.
        """
        total = self.size()
        if total == 0 or len(self.chunks) == 0:
            return []

        # Format query vector as 2D float32 array
        q_vec = query_vector.astype(np.float32)
        if q_vec.ndim == 1:
            q_vec = np.expand_dims(q_vec, axis=0)

        # L2-normalize query vector
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        k = min(top_k, total)

        if _FAISS_AVAILABLE and self.index is not None:
            scores, indices = self.index.search(q_vec, k)
            scores_row = scores[0]
            indices_row = indices[0]
        else:
            if self._vectors is None or len(self._vectors) == 0:
                return []
            dot_products = np.dot(self._vectors, q_vec.T).squeeze(axis=-1)
            top_indices = np.argsort(-dot_products)[:k]
            scores_row = dot_products[top_indices]
            indices_row = top_indices

        results: List[Tuple[RetrievalChunk, float]] = []
        for score, idx in zip(scores_row, indices_row):
            if 0 <= idx < len(self.chunks):
                # Clamp cosine similarity to [-1.0, 1.0] and round
                cos_sim = float(np.clip(score, -1.0, 1.0))
                results.append((self.chunks[idx], round(cos_sim, 4)))

        return results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[RetrievalChunk]:
        """Lookup chunk by unique chunk_id."""
        idx = self._chunk_id_to_idx.get(chunk_id)
        if idx is not None and idx < len(self.chunks):
            return self.chunks[idx]
        return None

    def size(self) -> int:
        """Returns number of indexed vectors."""
        if _FAISS_AVAILABLE and self.index is not None:
            return self.index.ntotal
        return len(self.chunks)

    def clear(self) -> None:
        """Resets the index."""
        if _FAISS_AVAILABLE and self.index is not None:
            self.index.reset()
        self._vectors = None
        self.chunks.clear()
        self._chunk_id_to_idx.clear()

    def save(self, filepath: str) -> None:
        """Saves vector index to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if _FAISS_AVAILABLE and faiss is not None and self.index is not None:
            faiss.write_index(self.index, filepath)
            logger.info(f"Saved FAISS index to {filepath}")
        elif self._vectors is not None:
            np.save(filepath, self._vectors)
            logger.info(f"Saved NumPy vector index to {filepath}")

    def load(self, filepath: str) -> None:
        """Loads vector index from disk."""
        if os.path.exists(filepath):
            if _FAISS_AVAILABLE and faiss is not None:
                try:
                    self.index = faiss.read_index(filepath)
                    self.dimension = self.index.d
                    logger.info(f"Loaded FAISS index from {filepath} (dim: {self.dimension}, total: {self.index.ntotal})")
                    return
                except Exception as e:
                    logger.warning(f"Could not load via FAISS: {e}")
            try:
                self._vectors = np.load(filepath)
                self.dimension = self._vectors.shape[1]
                logger.info(f"Loaded NumPy vectors from {filepath} (dim: {self.dimension}, total: {len(self._vectors)})")
            except Exception as e:
                logger.error(f"Failed to load vector file: {e}")
