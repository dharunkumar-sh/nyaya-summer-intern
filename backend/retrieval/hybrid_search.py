"""
Unified Hybrid Search Service for Classical Tamil Literature.

Combines BM25 lexical retrieval and dense semantic vector retrieval:
- Dual channel execution for every valid query.
- Score normalization to comparable [0.0, 1.0] ranges.
- Merge candidate results using canonical passage IDs with clean deduplication.
- Configurable relevance weights (default: 40% lexical, 60% semantic).
- Transparent score reporting: returns individual lexical, semantic, and combined scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.logger import logger
from .lexical_search import (
    LexicalSearchEngine,
    LexicalSearchResult,
    lexical_search_engine,
)
from .semantic_search import (
    SemanticSearchEngine,
    SemanticSearchResult,
    semantic_search_engine,
)
from .reranker import (
    PassageReranker,
    RerankedPassage,
    RerankScoreComponents,
    RerankExplanation,
    passage_reranker,
)


@dataclass
class HybridSearchResult:
    """
    Unified hybrid search candidate result preserving individual and combined relevance scores,
    with optional second-stage re-ranking scores, components, and explanations.
    """
    passage_id: str
    text: str
    source_metadata: Dict[str, Any]
    lexical_score: float
    semantic_score: float
    combined_score: float
    score: float = field(init=False)
    cosine_similarity: float = 0.0
    matched_terms: List[str] = field(default_factory=list)
    phrase_matched: bool = False
    retrieval_method: str = "hybrid_search"
    final_score: Optional[float] = None
    rank: Optional[int] = None
    score_components: Optional[Dict[str, float]] = None
    explanation: Optional[Dict[str, Any]] = None
    graph_score: Optional[float] = None
    graph_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.final_score is not None:
            self.score = self.final_score
        else:
            self.score = self.combined_score

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary with transparent score breakdown."""
        data: Dict[str, Any] = {
            "passage_id": self.passage_id,
            "text": self.text,
            "source_metadata": self.source_metadata,
            "lexical_score": round(self.lexical_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "combined_score": round(self.combined_score, 4),
            "score": round(self.score, 4),
            "cosine_similarity": round(self.cosine_similarity, 4),
            "matched_terms": self.matched_terms,
            "phrase_matched": self.phrase_matched,
            "retrieval_method": self.retrieval_method,
        }
        if self.final_score is not None:
            data["final_score"] = round(self.final_score, 4)
        if self.graph_score is not None:
            data["graph_score"] = round(self.graph_score, 4)
        if self.rank is not None:
            data["rank"] = self.rank
        if self.score_components is not None:
            data["score_components"] = self.score_components
        if self.explanation is not None:
            data["explanation"] = self.explanation
        if self.graph_context is not None:
            data["graph_context"] = self.graph_context
        return data


class HybridSearchService:
    """
    Orchestrates unified lexical (BM25) and semantic (dense vector) retrieval
    with configurable weighted fusion and transparent ranking diagnostics.
    """

    def __init__(
        self,
        lexical_engine: Optional[LexicalSearchEngine] = None,
        semantic_engine: Optional[SemanticSearchEngine] = None,
        default_lexical_weight: float = 0.40,
        default_semantic_weight: float = 0.60,
    ):
        self.lexical_engine = lexical_engine or lexical_search_engine
        self.semantic_engine = semantic_engine or semantic_search_engine
        self.default_lexical_weight = float(default_lexical_weight)
        self.default_semantic_weight = float(default_semantic_weight)

    def search(
        self,
        query: str,
        top_k: int = 5,
        lexical_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        primary_passages_only: bool = True,
        candidate_pool_factor: int = 4,
        rerank: bool = False,
        rerank_weights: Optional[Dict[str, float]] = None,
        include_graph_context: bool = False,
        max_graph_depth: int = 2,
        graph_weight: Optional[float] = None,
    ) -> List[HybridSearchResult]:
        """
        Executes unified hybrid retrieval:
        1. Runs BM25 lexical search.
        2. Runs dense semantic vector search.
        3. Merges and deduplicates candidates by passage ID.
        4. Calculates weighted combined relevance scores.
        5. Optionally applies second-stage re-ranking (semantic similarity, keyword coverage,
           entity/concept matching, source relevance, metadata matching).
        6. Optionally integrates Neo4j Aura Knowledge Graph context (bounded controlled expansion,
           tri-partite relevance fusion).
        7. Returns top-K candidates with individual, combined, and re-ranked scores.

        Args:
            query: Search query in Tamil or English.
            top_k: Number of highest ranking results to return.
            lexical_weight: Optional override for BM25 lexical relevance weight.
            semantic_weight: Optional override for dense semantic relevance weight.
            filters: Optional metadata filtering criteria.
            exact_terms: Optional list of required terms for lexical matching.
            require_phrase: Whether lexical search strictly enforces exact phrase.
            primary_passages_only: Whether to constrain retrieval to passage level.
            candidate_pool_factor: Multiplier for candidate retrieval depth.
            rerank: Whether to execute second-stage re-ranking layer.
            rerank_weights: Optional dictionary of weights for second-stage re-ranker.
            include_graph_context: Whether to enrich candidates with Neo4j Knowledge Graph context.
            max_graph_depth: Max hops for controlled graph relationship expansion (default: 2).
            graph_weight: Optional weight for graph relevance in tri-partite score combination.

        Returns:
            List of HybridSearchResult instances sorted descending by score.
        """
        clean_query = query.strip()
        if not clean_query and not exact_terms and not filters:
            return []

        if include_graph_context:
            from .graph_hybrid_search import graph_hybrid_search_service
            graph_results = graph_hybrid_search_service.search(
                query=clean_query,
                top_k=top_k,
                max_graph_depth=max_graph_depth,
                lexical_weight=lexical_weight,
                semantic_weight=semantic_weight,
                graph_weight=graph_weight,
                filters=filters,
                exact_terms=exact_terms,
                require_phrase=require_phrase,
                rerank_first_stage=rerank,
            )
            mapped_results: List[HybridSearchResult] = []
            for gr in graph_results:
                mapped_results.append(
                    HybridSearchResult(
                        passage_id=gr.passage_id,
                        text=gr.text,
                        source_metadata=gr.source_metadata,
                        lexical_score=gr.lexical_score,
                        semantic_score=gr.semantic_score,
                        combined_score=gr.final_score,
                        cosine_similarity=gr.semantic_score,
                        matched_terms=[],
                        phrase_matched=False,
                        retrieval_method="graph_hybrid_search",
                        final_score=gr.final_score,
                        rank=gr.rank,
                        graph_score=gr.graph_score,
                        graph_context=gr.graph_context.to_dict(),
                    )
                )
            return mapped_results

        # 1. Resolve configurable weights
        w_lex = float(lexical_weight if lexical_weight is not None else self.default_lexical_weight)
        w_sem = float(semantic_weight if semantic_weight is not None else self.default_semantic_weight)

        total_weight = w_lex + w_sem
        if total_weight <= 0.0:
            logger.warning("HybridSearchService: Total weight <= 0; resetting to defaults (0.4 / 0.6)")
            w_lex = 0.40
            w_sem = 0.60
            total_weight = 1.0

        # Normalized weights
        norm_w_lex = w_lex / total_weight
        norm_w_sem = w_sem / total_weight

        # 2. Execute both retrieval methods for candidate generation
        pool_size = max(top_k * candidate_pool_factor, 10)

        # Lexical Retrieval Channel
        lexical_results: List[LexicalSearchResult] = []
        if w_lex > 0.0 or not clean_query:
            try:
                lexical_results = self.lexical_engine.search(
                    query=clean_query,
                    top_k=pool_size,
                    filters=filters,
                    exact_terms=exact_terms,
                    require_phrase=require_phrase,
                    primary_passages_only=primary_passages_only,
                )
            except Exception as e:
                logger.error(f"HybridSearchService: Lexical search error: {e}")

        # Semantic Retrieval Channel
        semantic_results: List[SemanticSearchResult] = []
        if w_sem > 0.0 and clean_query:
            try:
                semantic_results = self.semantic_engine.search(
                    query=clean_query,
                    top_k=pool_size,
                    filters=filters,
                )
            except Exception as e:
                logger.error(f"HybridSearchService: Semantic search error: {e}")

        # 3. Merge candidates using passage ID and deduplicate
        lex_map: Dict[str, LexicalSearchResult] = {r.passage_id: r for r in lexical_results}
        sem_map: Dict[str, SemanticSearchResult] = {r.passage_id: r for r in semantic_results}

        all_passage_ids: Set[str] = set(lex_map.keys()) | set(sem_map.keys())
        if not all_passage_ids:
            return []

        merged_candidates: List[HybridSearchResult] = []

        for pid in all_passage_ids:
            lex_item = lex_map.get(pid)
            sem_item = sem_map.get(pid)

            # Individual scores
            lex_score = float(lex_item.score) if lex_item else 0.0
            sem_score = float(sem_item.score) if sem_item else 0.0
            cos_sim = float(sem_item.cosine_similarity) if sem_item else 0.0
            matched_terms = lex_item.matched_terms if lex_item else []
            phrase_matched = lex_item.phrase_matched if lex_item else False

            # Passage text & metadata
            if lex_item:
                text = lex_item.text
                metadata = lex_item.source_metadata
            elif sem_item:
                text = sem_item.text
                metadata = sem_item.source_metadata
            else:
                continue

            # 4. Calculate combined hybrid relevance score
            combined_score = (norm_w_lex * lex_score) + (norm_w_sem * sem_score)
            clamped_combined = min(1.0, max(0.0, combined_score))

            candidate = HybridSearchResult(
                passage_id=pid,
                text=text,
                source_metadata=metadata,
                lexical_score=round(lex_score, 4),
                semantic_score=round(sem_score, 4),
                combined_score=round(clamped_combined, 4),
                cosine_similarity=round(cos_sim, 4),
                matched_terms=matched_terms,
                phrase_matched=phrase_matched,
            )
            merged_candidates.append(candidate)

        # 5. Sort descending by combined_score, with passage_id as deterministic tie-breaker
        merged_candidates.sort(key=lambda r: (-r.combined_score, -r.semantic_score, r.passage_id))

        # 6. Apply Second-Stage Re-ranking if requested
        if rerank:
            reranked = passage_reranker.rerank(
                candidates=merged_candidates,
                query=clean_query,
                top_k=top_k,
                weights=rerank_weights,
                filters=filters,
            )
            final_results: List[HybridSearchResult] = []
            for item in reranked:
                res = HybridSearchResult(
                    passage_id=item.passage_id,
                    text=item.text,
                    source_metadata=item.source_metadata,
                    lexical_score=item.score_components.lexical_score,
                    semantic_score=item.score_components.semantic_score,
                    combined_score=item.score_components.initial_combined_score,
                    cosine_similarity=item.score_components.semantic_similarity,
                    matched_terms=item.explanation.matched_keywords,
                    phrase_matched=False,
                    retrieval_method="hybrid_with_rerank",
                    final_score=item.final_score,
                    rank=item.rank,
                    score_components=item.score_components.to_dict(),
                    explanation=item.explanation.to_dict(),
                )
                final_results.append(res)
            return final_results

        return merged_candidates[:top_k]

    def search_with_rerank(
        self,
        query: str,
        top_k: int = 5,
        lexical_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        rerank_weights: Optional[Dict[str, float]] = None,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
    ) -> List[HybridSearchResult]:
        """Convenience method that always executes second-stage re-ranking."""
        return self.search(
            query=query,
            top_k=top_k,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            rerank=True,
            rerank_weights=rerank_weights,
        )

    def search_with_graph(
        self,
        query: str,
        top_k: int = 5,
        max_graph_depth: int = 2,
        lexical_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        rerank: bool = True,
    ) -> List[HybridSearchResult]:
        """Convenience method that retrieves graph-augmented hybrid search results."""
        return self.search(
            query=query,
            top_k=top_k,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            graph_weight=graph_weight,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            rerank=rerank,
            include_graph_context=True,
            max_graph_depth=max_graph_depth,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Returns diagnostic statistics of the hybrid search service."""
        return {
            "default_lexical_weight": self.default_lexical_weight,
            "default_semantic_weight": self.default_semantic_weight,
            "lexical_engine_stats": self.lexical_engine.get_statistics(),
            "semantic_engine_stats": self.semantic_engine.get_statistics(),
            "reranker_weights": {
                "semantic_similarity": passage_reranker.config.semantic_similarity_weight,
                "keyword_coverage": passage_reranker.config.keyword_coverage_weight,
                "entity_concept": passage_reranker.config.entity_concept_weight,
                "source_relevance": passage_reranker.config.source_relevance_weight,
                "metadata_match": passage_reranker.config.metadata_match_weight,
            },
            "service_status": "ready",
        }


# Global singleton instance with 40% lexical / 60% semantic defaults
hybrid_search_service = HybridSearchService()
