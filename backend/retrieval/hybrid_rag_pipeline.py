"""
Hybrid RAG Retrieval Pipeline for Classical Tamil Literary Knowledge.

Orchestrates three complementary retrieval strategies for every valid query:

Channel A - Semantic Vector Retrieval:
    Uses Neo4j Aura vector_similarity_search (384-dim cosine) with an automatic
    fallback to the local SemanticSearchEngine / FAISS index.

Channel B - Keyword / Entity Retrieval:
    Uses LexicalSearchEngine (BM25Plus) with extracted query entities and concepts
    injected as supplementary exact-match terms.

Channel C - Graph Traversal Retrieval:
    Seeds from query KG node IDs produced by QueryPreprocessingService, performs
    bounded multi-hop traversal via Neo4j (depth 1-3) to surface passage IDs
    connected to queried entities/concepts, then resolves text locally.

Post-retrieval pipeline:
    - Merges all channel candidates by canonical passage_id.
    - Deduplicated results record every contributing retrieval_method.
    - Computes composite relevance_score from configurable per-channel weights.
    - Enriches top candidates with full graph context (entities, concepts, graph_path).
    - Returns a typed EvidenceCollection - strictly retrieve-only, no answer generation.

Provenance is preserved at every stage:
    passage_id -> source (work/section/chapter/sutra) -> graph_path -> retrieval_methods.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.logger import logger
from query.query_preprocessor import QueryPreprocessingService, ProcessedQuery


# ---------------------------------------------------------------------------
# Typed Output Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    """
    A single grounded evidence unit returned by the Hybrid RAG Pipeline.

    Every field is populated from actual corpus data.  No generated content
    is ever placed in this object.
    """
    # Identity
    passage_id: str
    text: str

    # Full source provenance
    source: Dict[str, Any]

    # Ordered hierarchy chain (L0 Literature -> L1 Work -> L2 Section -> L3 Passage)
    graph_path: List[Dict[str, Any]] = field(default_factory=list)

    # Which retrieval channels found this passage
    retrieval_methods: List[str] = field(default_factory=list)

    # Per-channel normalized scores [0.0, 1.0]
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    graph_score: float = 0.0

    # Composite weighted relevance score [0.0, 1.0]
    relevance_score: float = 0.0

    # Final rank position
    rank: int = 0

    # Rich graph neighborhood (entities, concepts, events, evidence)
    graph_context: Optional[Dict[str, Any]] = None

    # Transparent evidence-ranking score components and explanations
    score_components: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None
    badge_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable evidence item."""
        data: Dict[str, Any] = {
            "passage_id": self.passage_id,
            "rank": self.rank,
            "text": self.text,
            "source": self.source,
            "graph_path": self.graph_path,
            "retrieval_methods": self.retrieval_methods,
            "semantic_score": round(self.semantic_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "graph_score": round(self.graph_score, 4),
            "relevance_score": round(self.relevance_score, 4),
            "graph_context": self.graph_context,
        }
        if self.score_components is not None:
            data["score_components"] = self.score_components
        if self.explanation is not None:
            data["explanation"] = self.explanation
        if self.badge_info is not None:
            data["badge_info"] = self.badge_info
        return data


@dataclass
class EvidenceCollection:
    """
    Unified, deduplicated evidence collection produced by the Hybrid RAG Pipeline.

    This is the sole output of HybridRAGPipeline.retrieve().
    It must not contain generated answers, hallucinated content, or inferences.
    """
    query: str
    processed_query: Dict[str, Any]
    items: List[EvidenceItem] = field(default_factory=list)
    retrieval_stats: Dict[str, Any] = field(default_factory=dict)
    pipeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable evidence collection."""
        return {
            "query": self.query,
            "processed_query": self.processed_query,
            "items": [item.to_dict() for item in self.items],
            "retrieval_stats": self.retrieval_stats,
            "pipeline_version": self.pipeline_version,
            "total_results": len(self.items),
        }


# ---------------------------------------------------------------------------
# Hybrid RAG Pipeline
# ---------------------------------------------------------------------------

class HybridRAGPipeline:
    """
    Hybrid RAG retrieval pipeline combining three complementary retrieval channels.

    All constructor parameters are configurable with sensible defaults.
    The pipeline is retrieve-only: it never generates, infers, or synthesizes answers.
    """

    PIPELINE_VERSION = "1.0.0"

    def __init__(
        self,
        semantic_weight: float = 0.40,
        lexical_weight: float = 0.35,
        graph_weight: float = 0.25,
        top_k: int = 5,
        candidate_pool: int = 15,
        max_graph_depth: int = 2,
        use_neo4j_vector: bool = True,
    ):
        """
        Args:
            semantic_weight: Weight applied to Channel A (Neo4j vector / FAISS) scores.
            lexical_weight:  Weight applied to Channel B (BM25 keyword/entity) scores.
            graph_weight:    Weight applied to Channel C (graph traversal) scores.
            top_k:           Number of top evidence items to return.
            candidate_pool:  Candidates gathered per channel before merging.
            max_graph_depth: Graph traversal hop depth.  Clamped to [1, 3].
            use_neo4j_vector: Prefer Neo4j vector_similarity_search when Neo4j is live.
        """
        # Normalize weights so they always sum to 1.0
        total = semantic_weight + lexical_weight + graph_weight
        if total <= 0.0:
            semantic_weight, lexical_weight, graph_weight = 0.40, 0.35, 0.25
            total = 1.0
        self.semantic_weight = semantic_weight / total
        self.lexical_weight = lexical_weight / total
        self.graph_weight = graph_weight / total

        self.top_k = max(1, int(top_k))
        self.candidate_pool = max(self.top_k, int(candidate_pool))
        self.max_graph_depth = min(3, max(1, int(max_graph_depth)))
        self.use_neo4j_vector = bool(use_neo4j_vector)

    # ------------------------------------------------------------------
    # Neo4j availability helper
    # ------------------------------------------------------------------

    def _is_neo4j_active(self) -> bool:
        """Returns True when Neo4j Aura driver is connected."""
        try:
            from services.neo4j_service import neo4j_service
            return neo4j_service.is_connected()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Channel A - Semantic Vector Retrieval
    # ------------------------------------------------------------------

    def _channel_a_semantic(
        self,
        processed_query: ProcessedQuery,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Executes semantic vector retrieval.

        Priority: Neo4j vector_similarity_search -> local SemanticSearchEngine fallback.
        Returns a dict keyed by passage_id, each value containing the raw result dict.
        """
        results: Dict[str, Dict[str, Any]] = {}
        vector_query = processed_query.vector_query or processed_query.normalized_query

        if not vector_query:
            return results

        # Attempt Neo4j native vector search first
        neo4j_ok = self.use_neo4j_vector and self._is_neo4j_active()
        if neo4j_ok:
            try:
                from knowledge_graph.neo4j_repository import neo4j_repository
                from retrieval.semantic_search import semantic_search_engine

                # Generate query embedding using the same encoder as the persisted index
                q_vec = semantic_search_engine.encoder.encode_one(vector_query)
                neo4j_hits = neo4j_repository.vector_similarity_search(
                    embedding=q_vec,
                    top_k=top_k,
                )
                for hit in neo4j_hits:
                    pid = hit.get("passage_id") or hit.get("id", "")
                    if not pid:
                        continue
                    source_meta = hit.get("source_metadata") or {}
                    if filters:
                        match = True
                        for fk, fv in filters.items():
                            if fk in source_meta and fv:
                                if str(source_meta[fk]).strip().lower() != str(fv).strip().lower():
                                    match = False
                                    break
                        if not match:
                            continue
                    score = float(hit.get("similarity_score") or hit.get("score", 0.0))
                    # Normalize from [-1,1] or [0,1] cosine to [0,1]
                    norm_score = float(max(0.0, min(1.0, (score + 1.0) / 2.0 if score < 0 else score)))
                    results[pid] = {
                        "passage_id": pid,
                        "text": hit.get("text", ""),
                        "source": source_meta,
                        "semantic_score": norm_score,
                        "retrieval_method": "semantic_vector",
                        "channel": "A_neo4j_vector",
                    }
                logger.debug(f"HybridRAG Channel A (Neo4j vector): {len(results)} results")
                return results
            except Exception as e:
                logger.warning(f"HybridRAG Channel A Neo4j vector failed, falling back: {e}")

        # Fallback: local SemanticSearchEngine
        try:
            from retrieval.semantic_search import semantic_search_engine
            sem_results = semantic_search_engine.search(
                query=vector_query, top_k=top_k, filters=filters
            )
            for r in sem_results:
                pid = r.passage_id
                results[pid] = {
                    "passage_id": pid,
                    "text": r.text,
                    "source": r.source_metadata,
                    "semantic_score": float(r.score),
                    "retrieval_method": "semantic_vector",
                    "channel": "A_local_faiss",
                }
            logger.debug(f"HybridRAG Channel A (local FAISS): {len(results)} results")
        except Exception as e:
            logger.warning(f"HybridRAG Channel A local fallback failed: {e}")

        return results

    # ------------------------------------------------------------------
    # Channel B - Keyword / Entity Retrieval
    # ------------------------------------------------------------------

    def _channel_b_keyword_entity(
        self,
        processed_query: ProcessedQuery,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Executes BM25 keyword retrieval enriched with extracted entities and concepts
        as additional exact-match terms.
        """
        results: Dict[str, Dict[str, Any]] = {}
        bm25_query = processed_query.bm25_query or processed_query.normalized_query

        if not bm25_query and not processed_query.entities and not processed_query.concepts:
            return results

        # Collect exact entity/concept labels for BM25 term boosting
        exact_terms: List[str] = []
        for item in (processed_query.entities or []) + (processed_query.concepts or []):
            label = item.get("canonical") or item.get("english") or item.get("label", "")
            if label:
                exact_terms.append(label)
        exact_terms = list(dict.fromkeys(exact_terms))  # deduplicate preserving order

        try:
            from retrieval.lexical_search import lexical_search_engine
            lex_results = lexical_search_engine.search(
                query=bm25_query,
                top_k=top_k,
                filters=filters,
                exact_terms=exact_terms or None,
            )
            for r in lex_results:
                pid = r.passage_id
                results[pid] = {
                    "passage_id": pid,
                    "text": r.text,
                    "source": r.source_metadata,
                    "lexical_score": float(r.score),
                    "matched_terms": r.matched_terms,
                    "retrieval_method": "keyword_entity",
                    "channel": "B_bm25",
                }
            logger.debug(f"HybridRAG Channel B (BM25+entity): {len(results)} results")
        except Exception as e:
            logger.warning(f"HybridRAG Channel B keyword/entity retrieval failed: {e}")

        return results

    # ------------------------------------------------------------------
    # Channel C - Graph Traversal Retrieval
    # ------------------------------------------------------------------

    def _channel_c_graph_traversal(
        self,
        processed_query: ProcessedQuery,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieves passages reachable from query KG seed nodes via bounded graph traversal.

        Seeds come from ProcessedQuery.kg_seed_node_ids (up to 3).
        Passages are resolved from the local lexical/semantic index by passage_id.
        """
        results: Dict[str, Dict[str, Any]] = {}

        if not self._is_neo4j_active():
            logger.debug("HybridRAG Channel C: Neo4j not active, skipping graph traversal")
            return results

        seed_ids = (processed_query.kg_seed_node_ids or [])[:3]
        if not seed_ids:
            return results

        try:
            from knowledge_graph.neo4j_repository import neo4j_repository
            from retrieval.lexical_search import lexical_search_engine
            from retrieval.semantic_search import semantic_search_engine

            discovered_pids: Dict[str, float] = {}  # passage_id -> confidence

            for seed_id in seed_ids:
                try:
                    paths = neo4j_repository.traverse_multi_hop(
                        start_id=seed_id,
                        max_hops=self.max_graph_depth,
                        target_labels=["Passage", "Evidence"],
                    )
                    for path in paths[:top_k * 2]:
                        for node in path.get("path_nodes", []):
                            ntype = node.get("type", "")
                            nid = node.get("id", "")
                            if ntype in ("Passage", "Evidence") and nid:
                                conf = float(node.get("confidence", 1.0))
                                # Keep highest confidence among traversal paths
                                if nid not in discovered_pids or conf > discovered_pids[nid]:
                                    discovered_pids[nid] = conf
                except Exception as e:
                    logger.debug(f"HybridRAG Channel C traversal from seed '{seed_id}': {e}")

            if not discovered_pids:
                return results

            # Resolve text for each discovered passage_id from local indexes
            max_graph_score = max(discovered_pids.values()) if discovered_pids else 1.0

            for pid, confidence in list(discovered_pids.items()):
                if len(results) >= top_k:
                    break
                # Try lexical index first (has source metadata)
                doc = lexical_search_engine._doc_id_map.get(pid)
                if doc:
                    text = doc.text
                    source = doc.source_metadata
                else:
                    # Try semantic index
                    sem_doc = semantic_search_engine._doc_id_map.get(pid)
                    if sem_doc:
                        text = sem_doc.text
                        source = sem_doc.source_metadata
                    else:
                        # Fall back to Neo4j passage lookup
                        try:
                            neo4j_passage = neo4j_repository.get_passage_by_id(pid)
                            if neo4j_passage:
                                text = neo4j_passage.get("text", "")
                                source = {
                                    k: v for k, v in neo4j_passage.items()
                                    if k not in ("text", "embedding")
                                }
                            else:
                                continue  # passage not resolvable
                        except Exception:
                            continue

                if filters and isinstance(source, dict):
                    match = True
                    for fk, fv in filters.items():
                        if fk in source and fv:
                            if str(source[fk]).strip().lower() != str(fv).strip().lower():
                                match = False
                                break
                    if not match:
                        continue

                # Normalize graph traversal score: confidence / max_confidence -> [0, 1]
                norm_score = float(confidence / max_graph_score) if max_graph_score > 0 else 0.5

                results[pid] = {
                    "passage_id": pid,
                    "text": text,
                    "source": source,
                    "graph_score": norm_score,
                    "retrieval_method": "graph_traversal",
                    "channel": "C_graph",
                }

            logger.debug(f"HybridRAG Channel C (graph traversal): {len(results)} results")
        except Exception as e:
            logger.warning(f"HybridRAG Channel C graph traversal failed: {e}")

        return results

    # ------------------------------------------------------------------
    # Merge & Score
    # ------------------------------------------------------------------

    def _merge_channels(
        self,
        channel_a: Dict[str, Dict[str, Any]],
        channel_b: Dict[str, Dict[str, Any]],
        channel_c: Dict[str, Dict[str, Any]],
    ) -> Dict[str, "EvidenceItem"]:
        """
        Merges all three channel result dicts into a single EvidenceItem dict by passage_id.

        When the same passage appears in multiple channels:
        - retrieval_methods accumulates all contributing channel tags.
        - Per-channel scores keep the best (highest) value seen.
        - Source provenance is taken from the first channel that provided it.
        """
        merged: Dict[str, EvidenceItem] = {}

        all_channels = [
            ("semantic_vector", channel_a),
            ("keyword_entity", channel_b),
            ("graph_traversal", channel_c),
        ]

        for method_tag, channel_results in all_channels:
            for pid, data in channel_results.items():
                if pid not in merged:
                    # Create new entry
                    text = data.get("text", "")
                    source = data.get("source") or {}
                    merged[pid] = EvidenceItem(
                        passage_id=pid,
                        text=text,
                        source=source,
                        retrieval_methods=[method_tag],
                        semantic_score=float(data.get("semantic_score", 0.0)),
                        lexical_score=float(data.get("lexical_score", 0.0)),
                        graph_score=float(data.get("graph_score", 0.0)),
                    )
                else:
                    item = merged[pid]
                    # Merge retrieval methods
                    if method_tag not in item.retrieval_methods:
                        item.retrieval_methods.append(method_tag)
                    # Keep best per-channel score
                    if method_tag == "semantic_vector":
                        item.semantic_score = max(item.semantic_score, float(data.get("semantic_score", 0.0)))
                    elif method_tag == "keyword_entity":
                        item.lexical_score = max(item.lexical_score, float(data.get("lexical_score", 0.0)))
                    elif method_tag == "graph_traversal":
                        item.graph_score = max(item.graph_score, float(data.get("graph_score", 0.0)))
                    # Fill in missing text/source if current entry has empty values
                    if not item.text and data.get("text"):
                        item.text = data["text"]
                    if not item.source and data.get("source"):
                        item.source = data["source"]

        return merged

    # ------------------------------------------------------------------
    # Graph Context Enrichment
    # ------------------------------------------------------------------

    def _enrich_graph_context(
        self,
        items: List["EvidenceItem"],
        query: str,
        max_depth: int,
    ) -> None:
        """
        Fetches bounded graph context for each item and populates graph_path and graph_context.
        Operates in-place on the supplied items list.
        """
        try:
            from retrieval.graph_hybrid_search import graph_hybrid_search_service
            for item in items:
                try:
                    ctx = graph_hybrid_search_service.retrieve_passage_graph_context(
                        passage_id=item.passage_id,
                        query=query,
                        max_depth=max_depth,
                    )
                    item.graph_path = ctx.source_hierarchy or []
                    item.graph_context = ctx.to_dict()
                    # Promote graph relevance score from context if it improves the item
                    if ctx.graph_relevance_score > item.graph_score:
                        item.graph_score = round(ctx.graph_relevance_score, 4)
                        # Recompute composite score
                        item.relevance_score = round(min(1.0, max(0.0,
                            self.semantic_weight * item.semantic_score
                            + self.lexical_weight * item.lexical_score
                            + self.graph_weight * item.graph_score
                        )), 6)
                except Exception as e:
                    logger.debug(f"HybridRAG graph context enrichment for '{item.passage_id}': {e}")
        except Exception as e:
            logger.warning(f"HybridRAG graph context enrichment failed: {e}")

    # ------------------------------------------------------------------
    # Main Entry Points
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: Optional[int] = None,
        semantic_weight: Optional[float] = None,
        lexical_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        enrich_graph_context: bool = True,
    ) -> EvidenceCollection:
        """
        Executes the full Hybrid RAG retrieval pipeline for a user query.

        Steps:
        1. Preprocess query -> entities, concepts, KG seeds, BM25 tokens, vector query.
        2. Run Channel A (semantic vector), B (keyword/entity), C (graph traversal).
        3. Merge candidates by passage_id, deduplicating and tracking retrieval_methods.
        4. Compute composite relevance_score with configurable weights.
        5. Enrich top candidates with graph context (graph_path, entities, concepts).
        6. Return EvidenceCollection - no generated content.

        Args:
            query: Raw user query (Tamil, English, or mixed).
            top_k: Override the number of top results to return.
            filters: Optional metadata filters (work, section, chapter, sutra_number).
            max_graph_depth: Override graph traversal depth (1-3).
            semantic_weight: Per-call weight override for semantic channel.
            lexical_weight: Per-call weight override for lexical channel.
            graph_weight: Per-call weight override for graph channel.
            enrich_graph_context: Whether to call graph_hybrid_search for context.

        Returns:
            EvidenceCollection with ranked EvidenceItem list and retrieval statistics.
            The collection never contains generated answers or inferred content.
        """
        t_start = time.monotonic()

        resolved_top_k = int(top_k) if top_k is not None else self.top_k
        resolved_depth = min(3, max(1, int(max_graph_depth))) if max_graph_depth is not None else self.max_graph_depth
        pool = max(resolved_top_k * 2, self.candidate_pool)

        # Resolve per-call weight overrides
        w_sem = float(semantic_weight) if semantic_weight is not None else self.semantic_weight
        w_lex = float(lexical_weight) if lexical_weight is not None else self.lexical_weight
        w_gr = float(graph_weight) if graph_weight is not None else self.graph_weight
        total_w = w_sem + w_lex + w_gr
        if total_w <= 0.0:
            w_sem, w_lex, w_gr = self.semantic_weight, self.lexical_weight, self.graph_weight
            total_w = w_sem + w_lex + w_gr
        w_sem /= total_w
        w_lex /= total_w
        w_gr /= total_w

        # 1. Query Preprocessing
        try:
            pq: ProcessedQuery = QueryPreprocessingService.preprocess(query)
        except Exception as e:
            logger.error(f"HybridRAG query preprocessing failed: {e}")
            return EvidenceCollection(
                query=query,
                processed_query={"error": str(e), "original_query": query},
                items=[],
                retrieval_stats={"error": str(e)},
                pipeline_version=self.PIPELINE_VERSION,
            )

        # Return immediately for empty queries
        if not pq.normalized_query and not pq.bm25_tokens and not pq.kg_seed_node_ids:
            return EvidenceCollection(
                query=query,
                processed_query=pq.to_dict(),
                items=[],
                retrieval_stats={"total_candidates": 0, "elapsed_seconds": 0.0},
                pipeline_version=self.PIPELINE_VERSION,
            )

        # 2. Run three retrieval channels
        channel_a = self._channel_a_semantic(pq, pool, filters)
        channel_b = self._channel_b_keyword_entity(pq, pool, filters)
        channel_c = self._channel_c_graph_traversal(pq, resolved_top_k, filters)

        stats_channels = {
            "channel_a_semantic_count": len(channel_a),
            "channel_b_keyword_count": len(channel_b),
            "channel_c_graph_count": len(channel_c),
        }

        # 3. Merge by passage_id
        merged = self._merge_channels(channel_a, channel_b, channel_c)

        # 4. Compute composite scores with per-call weights
        for item in merged.values():
            item.relevance_score = round(min(1.0, max(0.0,
                w_sem * item.semantic_score
                + w_lex * item.lexical_score
                + w_gr * item.graph_score
            )), 6)

        # 5. Sort: primary key relevance_score desc, ties by graph, semantic, passage_id
        ranked = sorted(
            merged.values(),
            key=lambda it: (
                -round(it.relevance_score, 6),
                -round(it.graph_score, 6),
                -round(it.semantic_score, 6),
                it.passage_id,
            ),
        )

        # 6. Graph context enrichment for top candidates
        top_candidates = ranked[:resolved_top_k]
        if enrich_graph_context and top_candidates:
            enrich_pool = top_candidates[:min(resolved_top_k * 2, pool)]
            self._enrich_graph_context(enrich_pool, query, resolved_depth)
            # Re-sort after potential graph score improvements from enrichment
            enrich_pool.sort(
                key=lambda it: (
                    -round(it.relevance_score, 6),
                    -round(it.graph_score, 6),
                    -round(it.semantic_score, 6),
                    it.passage_id,
                ),
            )
        # 7. Apply deterministic Evidence-Ranking Layer (Signal 1: Semantic, Signal 2: Graph,
        # Signal 3: Source Reliability, Signal 4: Context, Signal 5: Multi-Channel Confidence)
        try:
            from retrieval.ranker import evidence_ranking_engine
            ranked_evidence = evidence_ranking_engine.rank_evidence(
                items=top_candidates,
                query=query,
                top_k=resolved_top_k,
            )
            # Map ranked items back into EvidenceItem instances with full components
            final_items: List[EvidenceItem] = []
            for r_item in ranked_evidence:
                final_items.append(
                    EvidenceItem(
                        passage_id=r_item.passage_id,
                        text=r_item.text,
                        source=r_item.source,
                        graph_path=r_item.graph_path,
                        retrieval_methods=r_item.retrieval_methods,
                        semantic_score=r_item.score_components.semantic_relevance,
                        lexical_score=r_item.score_components.context_relevance,
                        graph_score=r_item.score_components.graph_relevance,
                        relevance_score=r_item.final_score,
                        rank=r_item.rank,
                        graph_context=r_item.graph_context,
                        score_components=r_item.score_components.to_dict(),
                        explanation=r_item.explanation.to_dict(),
                        badge_info=r_item.badge_info,
                    )
                )
            top_candidates = final_items
        except Exception as rank_err:
            logger.warning(f"HybridRAG evidence ranking fallback: {rank_err}")
            for idx, item in enumerate(top_candidates):
                item.rank = idx + 1

        elapsed = round(time.monotonic() - t_start, 3)

        retrieval_stats = {
            **stats_channels,
            "total_candidates_before_merge": len(channel_a) + len(channel_b) + len(channel_c),
            "unique_candidates_after_merge": len(merged),
            "returned": len(top_candidates),
            "weights_used": {
                "semantic": round(w_sem, 4),
                "lexical": round(w_lex, 4),
                "graph": round(w_gr, 4),
            },
            "graph_depth": resolved_depth,
            "neo4j_active": self._is_neo4j_active(),
            "elapsed_seconds": elapsed,
        }

        return EvidenceCollection(
            query=query,
            processed_query=pq.to_dict(),
            items=top_candidates,
            retrieval_stats=retrieval_stats,
            pipeline_version=self.PIPELINE_VERSION,
        )

    def retrieve_from_processed(
        self,
        processed_query: ProcessedQuery,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: Optional[int] = None,
        enrich_graph_context: bool = True,
    ) -> EvidenceCollection:
        """
        Convenience overload for callers that have already run QueryPreprocessingService.

        Runs channels B and C directly from the ProcessedQuery.
        Channel A runs using processed_query.vector_query.
        """
        return self.retrieve(
            query=processed_query.original_query,
            top_k=top_k,
            filters=filters,
            max_graph_depth=max_graph_depth,
            enrich_graph_context=enrich_graph_context,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Returns diagnostic information about the pipeline configuration."""
        try:
            from retrieval.lexical_search import lexical_search_engine
            lex_docs = len(lexical_search_engine.documents)
        except Exception:
            lex_docs = -1

        try:
            from retrieval.semantic_search import semantic_search_engine
            sem_docs = len(semantic_search_engine.documents)
            sem_dim = int(semantic_search_engine.embeddings.shape[1]) \
                if semantic_search_engine.embeddings.ndim == 2 \
                and semantic_search_engine.embeddings.shape[0] > 0 else 0
        except Exception:
            sem_docs = -1
            sem_dim = 0

        return {
            "pipeline_version": self.PIPELINE_VERSION,
            "weights": {
                "semantic": round(self.semantic_weight, 4),
                "lexical": round(self.lexical_weight, 4),
                "graph": round(self.graph_weight, 4),
            },
            "top_k": self.top_k,
            "candidate_pool": self.candidate_pool,
            "max_graph_depth": self.max_graph_depth,
            "use_neo4j_vector": self.use_neo4j_vector,
            "neo4j_active": self._is_neo4j_active(),
            "lexical_index_size": lex_docs,
            "semantic_index_size": sem_docs,
            "semantic_vector_dim": sem_dim,
        }

    def build_structured_context(
        self,
        query: str,
        evidence_items: Optional[Union[List[Any], Any]] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: Optional[int] = None,
        max_passages: int = 5,
        max_context_chars: int = 4000,
        max_relationships_per_passage: int = 8,
        min_relevance_threshold: float = 0.30,
        min_evidence_count: int = 1,
        as_dict: bool = True,
    ) -> Any:
        """
        Transforms ranked retrieval results into a compact, structured context
        tailored for answer generation with exact source citations and Neo4j relationships.
        If evidence is insufficient, returns an explicit insufficient-evidence state.
        """
        from .structured_context_builder import structured_context_builder

        if evidence_items is None:
            collection = self.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                max_graph_depth=max_graph_depth,
            )
            evidence_items = collection.items

        context = structured_context_builder.build_context(
            query=query,
            evidence_items=evidence_items,
            max_passages=max_passages,
            max_context_chars=max_context_chars,
            max_relationships_per_passage=max_relationships_per_passage,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
        )
        return context.to_dict() if as_dict else context

    def answer_query(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: Optional[int] = None,
        max_context_chars: int = 4000,
        max_relationships: int = 8,
        min_relevance_threshold: float = 0.25,
        min_evidence_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end grounded QA:
        1. 3-channel retrieval (Semantic Vector + BM25 + Neo4j Graph Traversal).
        2. Deduplication & 5-signal deterministic evidence ranking.
        3. Structured context construction with exact provenance and Neo4j graph edges.
        4. Strict sufficiency evaluation (returns explicit insufficient_evidence state if ungrounded).
        5. Grounded synthesis through OpenRouter LLM (or deterministic fallback).
        6. Returns structured response with final_answer, evidence, sources, confidence, and metadata.
        """
        from config import Config
        from .structured_context_builder import structured_context_builder
        from llm.client import llm_client

        # 1. 3-channel retrieval
        collection = self.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
            max_graph_depth=max_graph_depth,
        )

        # 2. Extract detected tiṇai if present
        detected_tinai = "Kuṟiñci"
        if collection.items:
            first_src = collection.items[0].source or {}
            detected_tinai = first_src.get("tinai") or "Kuṟiñci"

        # 3. Transform into compact structured context
        structured_ctx = structured_context_builder.build_context(
            query=query,
            evidence_items=collection.items,
            max_passages=top_k,
            max_context_chars=max_context_chars,
            max_relationships_per_passage=max_relationships,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
        )

        evidence_dicts = [item.to_dict() for item in collection.items]
        top_score = float(collection.items[0].relevance_score) if collection.items else 0.0

        # 4. Strict Retrieval Gate:
        # The LLM must not generate an answer before retrieval succeeds,
        # and insufficient retrieval must produce an explicit insufficient-evidence response.
        if not structured_ctx.is_sufficient or not collection.items:
            reason = structured_ctx.insufficient_reason or "Insufficient canonical evidence retrieved."
            final_answer = {
                "tamilAnswer": "தீர்மானிக்கப் போதுமான தொல்காப்பியச் சான்றுகள் கிடைக்கவில்லை.",
                "englishAnswer": "Insufficient canonical evidence retrieved to answer query without speculation.",
                "subtitle": f"Evidence threshold unmet: {reason}",
                "confidenceScore": 0.0,
                "starsCount": 0.0,
                "verdictStatus": "Insufficient Canonical Evidence (போதிய சான்றுகள் இல்லை)",
                "justificationTamil": f"வினாவிற்குரிய மூலச் சான்றுகளின் பொருத்தம் அல்லது எண்ணிக்கை போதாமையால் முடிவு நிறுவப்படவில்லை ({reason}).",
                "justificationEnglish": f"Retrieved canonical evidence did not meet the required relevance or count criteria ({reason}). Speculative answer generation was blocked.",
                "keySources": [],
            }
        else:
            # 5. Synthesize final answer via LLM strictly on validated retrieved context
            final_answer_obj = llm_client.synthesize_final_answer(
                query=query,
                tinai=detected_tinai,
                evidence_items=evidence_dicts,
                structured_context=structured_ctx,
            )
            final_answer = final_answer_obj.model_dump()

        return {
            "query": query,
            "final_answer": final_answer,
            "retrieved_evidence": evidence_dicts,
            "sources": final_answer.get("keySources", []),
            "confidence_info": {
                "confidenceScore": final_answer.get("confidenceScore", 0.0),
                "verdictStatus": final_answer.get("verdictStatus", ""),
                "topRelevanceScore": round(top_score, 4),
                "weightsUsed": collection.retrieval_stats.get("weights_used", {}),
            },
            "reasoning_metadata": {
                "detectedTinai": detected_tinai,
                "is_sufficient": structured_ctx.is_sufficient,
                "status": structured_ctx.status,
                "insufficient_reason": structured_ctx.insufficient_reason,
                "pipeline_version": collection.pipeline_version,
                "provider": Config.LLM_PROVIDER,
                "llm_provider": Config.LLM_PROVIDER,
                "model": Config.OPENROUTER_MODEL if Config.LLM_PROVIDER == "openrouter" else "deterministic_nyaya",
                "llm_model": Config.OPENROUTER_MODEL if Config.LLM_PROVIDER == "openrouter" else "deterministic_nyaya",
                "total_passages_retrieved": len(collection.items),
                "qualifying_passages": structured_ctx.passage_count,
                "retrieval_stats": collection.retrieval_stats,
            },
            "structured_context": structured_ctx.to_dict(),
            "insufficient_evidence": not structured_ctx.is_sufficient,
        }



# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

hybrid_rag_pipeline = HybridRAGPipeline()
