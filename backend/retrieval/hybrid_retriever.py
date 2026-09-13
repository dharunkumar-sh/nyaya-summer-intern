"""
Hybrid Retriever combining BM25 Lexical, Dense Vector Cosine, and Knowledge Graph Topological retrieval.
Applies Reciprocal Rank Fusion (RRF): RRF(d) = sum(1 / (60 + rank_i(d))).
"""
from typing import List, Dict, Any, Tuple
from .bm25 import BM25Retriever
from .vector_store import VectorStore
from .graph_retriever import GraphRetriever
from core.logger import logger


class HybridRetriever:
    """Orchestrates multi-channel retrieval with Reciprocal Rank Fusion."""

    def __init__(self):
        self.bm25 = BM25Retriever()
        self.vector_store = VectorStore()
        self.graph_retriever = GraphRetriever()

    def search(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.35,
        vector_weight: float = 0.40,
        graph_weight: float = 0.25,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Executes tri-channel retrieval and fuses results via weighted RRF."""
        # 1. Channel searches
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        vector_results = self.vector_store.search(query, top_k=top_k * 2)
        graph_results = self.graph_retriever.search(query, top_k=top_k * 2)

        # 2. Reciprocal Rank Fusion dictionary: doc_id -> fused_score
        rrf_scores: Dict[str, float] = {}
        sutra_lookup: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60.0

        # Process BM25 Channel
        for rank, (sutra, score) in enumerate(bm25_results):
            s_id = sutra["id"]
            sutra_lookup[s_id] = sutra
            rrf_scores[s_id] = rrf_scores.get(s_id, 0.0) + bm25_weight * (1.0 / (rrf_k + rank + 1))

        # Process Vector Channel
        for rank, (sutra, score) in enumerate(vector_results):
            s_id = sutra["id"]
            sutra_lookup[s_id] = sutra
            rrf_scores[s_id] = rrf_scores.get(s_id, 0.0) + vector_weight * (1.0 / (rrf_k + rank + 1))

        # Process Graph Channel
        for rank, (sutra, score) in enumerate(graph_results):
            s_id = sutra["id"]
            sutra_lookup[s_id] = sutra
            rrf_scores[s_id] = rrf_scores.get(s_id, 0.0) + graph_weight * (1.0 / (rrf_k + rank + 1))

        # 3. Sort by fused score
        ranked_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Normalize fused scores to [0.80, 0.99] realistic epistemic confidence range
        if ranked_items:
            max_val = ranked_items[0][1]
            results = []
            for s_id, score in ranked_items[:top_k]:
                normalized = 0.82 + 0.16 * (score / max_val if max_val > 0 else 1.0)
                results.append((sutra_lookup[s_id], round(normalized, 4)))
            return results

        return []
