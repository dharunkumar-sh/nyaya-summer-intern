"""
Dense Semantic Embedding Generator for Classical Tamil Poetics.

Supports:
1. SentenceTransformers embeddings (e.g. multilingual transformer models)
2. Dense subword/character n-gram TF-IDF embeddings (pure NumPy fallback for deterministic tests/offline mode)
3. Cosine similarity calculation over L2-normalized vectors.
"""
from __future__ import annotations

import math
import numpy as np
from typing import List, Dict, Optional, Union
from collections import Counter
from preprocessing.tamil_normalizer import TamilNormalizer
from core.logger import logger


class DenseNgramEmbeddingGenerator:
    """
    Pure NumPy & Python Dense Semantic Embedding Generator.
    Extracts character and subword n-grams with sublinear TF-IDF and L2-normalized cosine projection.
    Zero external network calls—100% deterministic and compliant with all environments.
    """

    def __init__(self, ngram_range=(3, 5), fixed_dim: Optional[int] = None):
        self.ngram_range = ngram_range
        self.fixed_dim = fixed_dim
        self.vocabulary: Dict[str, int] = {}
        self.idf: np.ndarray = np.empty(0, dtype=np.float32)
        self.is_fitted = False

    def _extract_ngrams(self, text: str) -> List[str]:
        """Extracts character n-grams with word boundary markers."""
        cleaned = TamilNormalizer.normalize(text)
        words = cleaned.split()
        ngrams = []
        min_n, max_n = self.ngram_range

        for word in words:
            w = f" {word} "
            w_len = len(w)
            for n in range(min_n, min(max_n + 1, w_len + 1)):
                for i in range(w_len - n + 1):
                    ngrams.append(w[i : i + n])

        return ngrams

    def fit(self, texts: List[str]) -> "DenseNgramEmbeddingGenerator":
        """Builds vocabulary and IDF statistics from corpus texts."""
        doc_count = len(texts)
        if doc_count == 0:
            return self

        doc_freq: Counter = Counter()
        for text in texts:
            unique_ngrams = set(self._extract_ngrams(text))
            for ng in unique_ngrams:
                doc_freq[ng] += 1

        sorted_vocab = sorted(doc_freq.keys())
        if self.fixed_dim and len(sorted_vocab) > self.fixed_dim:
            sorted_vocab = sorted_vocab[: self.fixed_dim]

        self.vocabulary = {ng: idx for idx, ng in enumerate(sorted_vocab)}
        vocab_size = len(self.vocabulary)

        idf_vals = np.zeros(vocab_size, dtype=np.float32)
        for ng, idx in self.vocabulary.items():
            df = doc_freq[ng]
            idf_vals[idx] = math.log((1.0 + doc_count) / (1.0 + df)) + 1.0

        self.idf = idf_vals
        self.is_fitted = True
        return self

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encodes texts into dense, L2-normalized feature vectors."""
        if not self.is_fitted:
            self.fit(texts)

        if not self.vocabulary:
            dim = self.fixed_dim or 64
            return np.zeros((len(texts), dim), dtype=np.float32)

        vocab_size = len(self.vocabulary)
        matrix = np.zeros((len(texts), vocab_size), dtype=np.float32)

        for doc_idx, text in enumerate(texts):
            ngrams = self._extract_ngrams(text)
            if not ngrams:
                continue

            tf_counts = Counter(ngrams)
            for ng, count in tf_counts.items():
                if ng in self.vocabulary:
                    col_idx = self.vocabulary[ng]
                    sublinear_tf = 1.0 + math.log(count)
                    matrix[doc_idx, col_idx] = sublinear_tf * self.idf[col_idx]

        # L2 unit normalization for direct dot-product cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (matrix / norms).astype(np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        """Encodes a single query string into a 1D vector."""
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        """Returns feature vector dimension."""
        return len(self.vocabulary) if self.is_fitted else (self.fixed_dim or 64)


class SentenceTransformerEmbeddingGenerator:
    """
    SentenceTransformers embedding wrapper with automatic fallback to DenseNgramEmbeddingGenerator.
    Ensures all vectors are L2-normalized float32 arrays for exact cosine similarity via inner product.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        fallback_dim: int = 384,
    ):
        self.model_name = model_name
        self.fallback_dim = fallback_dim
        self._st_model = None
        self._fallback_encoder = DenseNgramEmbeddingGenerator(fixed_dim=fallback_dim)
        self._init_model()

    def _init_model(self):
        """Attempts to load SentenceTransformer; falls back to n-gram if offline or unavailable."""
        try:
            import os
            from sentence_transformers import SentenceTransformer
            if os.getenv("TESTING_OFFLINE") == "true":
                self._st_model = None
                return

            try:
                self._st_model = SentenceTransformer(self.model_name, local_files_only=True)
                logger.info(f"Loaded SentenceTransformer from cache: {self.model_name}")
            except Exception:
                # Do not block startup with massive HuggingFace downloads if offline or slow
                if os.getenv("ENABLE_REMOTE_EMBEDDINGS") == "true":
                    self._st_model = SentenceTransformer(self.model_name)
                    logger.info(f"Loaded SentenceTransformer: {self.model_name}")
                else:
                    logger.info(f"SentenceTransformer '{self.model_name}' not cached locally. Using fast deterministic dense n-gram fallback.")
                    self._st_model = None
        except Exception as e:
            logger.info(f"SentenceTransformer '{self.model_name}' deferred or offline ({e}). Using dense n-gram fallback.")
            self._st_model = None

    def fit(self, texts: List[str]) -> "SentenceTransformerEmbeddingGenerator":
        """Fits fallback model if SentenceTransformer is not loaded."""
        if self._st_model is None:
            self._fallback_encoder.fit(texts)
        return self

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encodes texts into L2-normalized float32 dense vector representations."""
        if self._st_model is not None:
            try:
                embeddings = self._st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.astype(np.float32)
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding failed: {e}. Using fallback.")

        # Fallback encoding
        return self._fallback_encoder.encode(texts)

    def encode_one(self, text: str) -> np.ndarray:
        """Encodes a single text string."""
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        """Returns the vector dimensionality."""
        if self._st_model is not None:
            return self._st_model.get_sentence_embedding_dimension()
        return self._fallback_encoder.dimension


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D or 2D vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    dot = np.dot(vec_a, vec_b)
    sim = dot / (norm_a * norm_b)
    return float(np.clip(sim, -1.0, 1.0))


# Backward compatibility alias
EmbeddingGenerator = DenseNgramEmbeddingGenerator
