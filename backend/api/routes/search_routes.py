"""
Clean, Production-Grade Flask REST API for Search Functionality.

Endpoints:
- POST /api/search : Primary search endpoint accepting JSON payload.
- GET  /api/search : Query parameter search endpoint for testing and lightweight queries.

Supports:
- Modes: 'hybrid' (default), 'keyword' (BM25Plus), 'semantic' (Dense Vector).
- Query Normalization: Unicode NFC, Tamil orthography, literary terminology extraction.
- Relevance Scores: Transparent normalized lexical, semantic, graph, and combined scores.
- Source Metadata: Complete provenance (work, section, chapter, sutra, tinai, entities).
- Graph Context: Controlled Knowledge Graph neighborhood via Neo4j Aura (with in-memory fallback).
- Pagination: 1-indexed page and page_size parameters with accurate metadata.
- Validation: 1-500 character query limit, parameter bounds, safe defaults, zero implementation leakage.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from flask import Blueprint, request

from api.responses import success_response, error_response
from core.logger import logger
from query.query_preprocessor import query_preprocessor
from retrieval.rag_service import rag_engine
from retrieval.graph_hybrid_search import graph_hybrid_search_service
from retrieval.passage_embedding_pipeline import passage_embedding_pipeline

search_bp = Blueprint("search", __name__, url_prefix="/api/search")

MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 1
DEFAULT_TOP_K = 5
MAX_TOP_K = 50
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 50

VALID_MODES = {
    "hybrid": "hybrid",
    "unified": "hybrid",
    "fused": "hybrid",
    "keyword": "keyword",
    "lexical": "keyword",
    "bm25": "keyword",
    "semantic": "semantic",
    "vector": "semantic",
}


def _extract_request_params() -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Extracts and standardizes parameters from either JSON body (POST) or query string (GET).
    Returns (params_dict, error_message_or_none).
    """
    if request.method == "POST":
        payload = request.get_json(silent=True)
        if payload is None and request.data:
            return {}, "Malformed JSON in request body"
        data = payload or {}
    else:
        # GET request
        data = request.args.to_dict()

    return data, None


def _format_relevance_scores(item: Dict[str, Any], mode: str) -> Dict[str, float]:
    """
    Constructs a standardized, transparent dictionary of relevance scores.
    """
    scores: Dict[str, float] = {}

    # Combined / final / relevance score
    final_val = (
        item.get("relevance_score")
        or item.get("final_score")
        or item.get("combined_score")
        or item.get("score")
    )
    if final_val is not None:
        scores["combined_score"] = round(float(final_val), 4)
        scores["relevance_score"] = round(float(final_val), 4)

    # Lexical score
    lex_val = (
        item.get("lexical_score")
        or item.get("bm25_score")
        or item.get("normalized_score")
    )
    if lex_val is not None:
        scores["lexical_score"] = round(float(lex_val), 4)
    elif mode == "keyword" and "score" in item:
        scores["lexical_score"] = round(float(item["score"]), 4)

    # Semantic score
    sem_val = (
        item.get("semantic_score")
        or item.get("cosine_similarity")
        or (item.get("score") if mode == "semantic" else None)
    )
    if sem_val is not None:
        scores["semantic_score"] = round(float(sem_val), 4)

    # Graph score
    if "graph_score" in item and item["graph_score"] is not None:
        scores["graph_score"] = round(float(item["graph_score"]), 4)

    # Rerank score
    if "rerank_score" in item and item["rerank_score"] is not None:
        scores["rerank_score"] = round(float(item["rerank_score"]), 4)
    elif "score_components" in item and isinstance(item["score_components"], dict):
        comp = item["score_components"]
        if "final_score" in comp and comp["final_score"] is not None:
            scores["rerank_score"] = round(float(comp["final_score"]), 4)

    return scores


def _format_source_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts and cleanses source metadata ensuring all canonical attributes exist."""
    meta = item.get("source_metadata")
    if not isinstance(meta, dict):
        meta = item.get("metadata")
    if not isinstance(meta, dict):
        meta = item.get("source")
    if not isinstance(meta, dict):
        meta = {}

    inner_meta = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}

    work = (
        meta.get("work")
        or meta.get("work_name")
        or inner_meta.get("work")
        or inner_meta.get("work_name")
        or item.get("work")
        or item.get("work_name")
        or "Tolkappiyam"
    )
    section = (
        meta.get("section")
        or meta.get("section_name")
        or meta.get("atikaram")
        or inner_meta.get("section")
        or inner_meta.get("section_name")
        or inner_meta.get("atikaram")
        or item.get("section")
        or item.get("section_name")
        or ""
    )
    chapter = (
        meta.get("chapter")
        or meta.get("chapter_name")
        or meta.get("iyal")
        or inner_meta.get("chapter")
        or inner_meta.get("chapter_name")
        or inner_meta.get("iyal")
        or item.get("chapter")
        or item.get("chapter_name")
        or ""
    )
    sutra_number = meta.get("sutra_number") or inner_meta.get("sutra_number") or item.get("sutra_number")
    source_id = (
        meta.get("source_id")
        or meta.get("source_reference")
        or meta.get("source")
        or inner_meta.get("source_reference")
        or item.get("passage_id")
        or ""
    )
    if isinstance(source_id, dict):
        source_id = source_id.get("source_id") or source_id.get("source_reference") or item.get("passage_id") or ""
    tinai = meta.get("tinai") or inner_meta.get("tinai") or item.get("tinai") or "General"
    entities = meta.get("entities") or inner_meta.get("entities") or item.get("entities") or []
    concepts = meta.get("concepts") or inner_meta.get("concepts") or item.get("concepts") or []

    return {
        "work": str(work),
        "section": str(section),
        "chapter": str(chapter),
        "sutra_number": sutra_number,
        "source_id": str(source_id),
        "tinai": str(tinai),
        "entities": list(entities) if isinstance(entities, (list, tuple, set)) else [],
        "concepts": list(concepts) if isinstance(concepts, (list, tuple, set)) else [],
    }


def _execute_search(
    query: str,
    normalized_query: str,
    mode: str,
    top_k: int,
    page: int,
    page_size: int,
    filters: Optional[Dict[str, Any]],
    include_graph: bool,
    max_graph_depth: int,
    rerank: bool,
    lexical_weight: float,
    semantic_weight: float,
    graph_weight: Optional[float],
    exact_terms: Optional[List[str]],
    require_phrase: bool,
) -> Dict[str, Any]:
    """
    Executes search according to validated mode, applies pagination,
    and constructs standardized JSON output.
    """
    # Determine candidate pool size needed to fulfill pagination page
    fetch_k = max(top_k, page * page_size, 10)
    fetch_k = min(fetch_k, 50)

    raw_results: List[Dict[str, Any]] = []
    retrieval_stats: Optional[Dict[str, Any]] = None

    if mode == "hybrid":
        from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline

        # Execute 3-channel Hybrid RAG retrieval pipeline:
        # Channel A: Semantic vector retrieval (Neo4j Aura vector similarity search with FAISS fallback)
        # Channel B: BM25/keyword retrieval (LexicalSearchEngine with query terms + entity/concept terms)
        # Channel C: Neo4j graph retrieval (multi-hop traversal from seed entities)
        # Deduplicates candidates using stable passage IDs, fuses and normalizes scores,
        # and applies the deterministic 5-signal evidence ranking layer.
        evidence_col = hybrid_rag_pipeline.retrieve(
            query=query,
            top_k=fetch_k,
            filters=filters,
            max_graph_depth=max_graph_depth if include_graph else 1,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            graph_weight=graph_weight if include_graph else 0.0,
            enrich_graph_context=include_graph,
        )
        raw_results = [item.to_dict() for item in evidence_col.items]
        retrieval_stats = evidence_col.retrieval_stats

    elif mode == "keyword":
        raw_results = rag_engine.lexical_search(
            query=query,
            top_k=fetch_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
        )

    elif mode == "semantic":
        raw_results = rag_engine.semantic_passage_search(
            query=query,
            top_k=fetch_k,
            filters=filters,
        )

    total_results = len(raw_results)
    total_pages = max(1, math.ceil(total_results / page_size)) if total_results > 0 else 1

    # Apply 1-indexed pagination slicing
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    sliced_items = raw_results[start_idx:end_idx] if start_idx < total_results else []

    ranked_results: List[Dict[str, Any]] = []
    for idx, item in enumerate(sliced_items):
        passage_id = str(item.get("passage_id") or item.get("id") or f"passage-{idx+1}")
        text = str(item.get("text") or item.get("passage_text") or "")
        rel_scores = _format_relevance_scores(item, mode)
        src_meta = _format_source_metadata(item)

        # Graph Context extraction
        graph_ctx: Optional[Dict[str, Any]] = None
        if item.get("graph_context"):
            raw_ctx = item["graph_context"]
            graph_ctx = raw_ctx if isinstance(raw_ctx, dict) else (raw_ctx.to_dict() if hasattr(raw_ctx, "to_dict") else None)
        elif include_graph and passage_id:
            try:
                g_context = graph_hybrid_search_service.retrieve_passage_graph_context(
                    passage_id=passage_id,
                    query=query,
                    max_depth=max_graph_depth,
                )
                if g_context:
                    graph_ctx = g_context.to_dict()
            except Exception as e:
                logger.debug(f"Could not retrieve graph context for {passage_id}: {e}")
                graph_ctx = None

        # Determine retrieval method / methods
        retrieval_methods = item.get("retrieval_methods")
        if not isinstance(retrieval_methods, list):
            if item.get("retrieval_method"):
                retrieval_methods = [str(item["retrieval_method"])]
            elif mode == "hybrid":
                retrieval_methods = ["semantic_vector", "keyword_entity", "graph_traversal"]
            elif mode == "keyword":
                retrieval_methods = ["keyword_bm25"]
            elif mode == "semantic":
                retrieval_methods = ["semantic_vector"]
            else:
                retrieval_methods = [mode]

        primary_retrieval_method = item.get("retrieval_method") or (retrieval_methods[0] if retrieval_methods else mode)

        ranked_results.append({
            "rank": start_idx + idx + 1,
            "passage_id": passage_id,
            "text": text,
            "source": item.get("source") or src_meta.get("source_id") or passage_id,
            "source_metadata": src_meta,
            "work": src_meta["work"],
            "section": src_meta["section"],
            "chapter": src_meta["chapter"],
            "sutra_number": src_meta["sutra_number"],
            "tinai": src_meta["tinai"],
            "entities": src_meta["entities"],
            "concepts": src_meta["concepts"],
            "entity_metadata": {
                "entities": src_meta["entities"],
                "concepts": src_meta["concepts"],
            },
            "retrieval_method": primary_retrieval_method,
            "retrieval_methods": retrieval_methods,
            "relevance_scores": rel_scores,
            "graph_context": graph_ctx,
            "graph_path": item.get("graph_path") or (graph_ctx.get("source_hierarchy") if graph_ctx else []),
            "score_components": item.get("score_components"),
            "badge_info": item.get("badge_info"),
            "explanation": item.get("explanation"),
        })

    response_payload: Dict[str, Any] = {
        "original_query": query,
        "normalized_query": normalized_query,
        "mode": mode,
        "result_count": len(ranked_results),
        "total_results": total_results,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "filters_applied": filters or {},
        "ranked_results": ranked_results,
    }
    if retrieval_stats:
        response_payload["retrieval_stats"] = retrieval_stats

    return response_payload


@search_bp.route("", methods=["GET", "POST"])
@search_bp.route("/", methods=["GET", "POST"])
def search():
    """
    Unified search endpoint accepting GET or POST requests.
    Validates inputs, normalizes queries, dispatches retrieval, and formats responses.
    """
    raw_data, parse_err = _extract_request_params()
    if parse_err:
        return error_response(
            message=parse_err,
            error_code="BAD_REQUEST",
            status_code=400,
        )

    # 1. Query Extraction and Validation
    query = raw_data.get("query") or raw_data.get("q")
    if query is None or not isinstance(query, str) or not query.strip():
        return error_response(
            message="Parameter 'query' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    query = query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        return error_response(
            message=f"Query exceeds maximum permitted length of {MAX_QUERY_LENGTH} characters",
            error_code="QUERY_TOO_LONG",
            status_code=400,
        )

    # 2. Search Mode Extraction and Validation
    raw_mode = raw_data.get("mode") or raw_data.get("search_mode") or "hybrid"
    if not isinstance(raw_mode, str) or raw_mode.strip().lower() not in VALID_MODES:
        supported_modes_str = ", ".join(sorted(list(set(VALID_MODES.values()))))
        return error_response(
            message=f"Invalid search mode '{raw_mode}'. Supported modes: {supported_modes_str}",
            error_code="INVALID_SEARCH_MODE",
            status_code=400,
        )
    mode = VALID_MODES[raw_mode.strip().lower()]

    # 3. Numeric & Pagination Parameters Validation
    try:
        top_k = int(raw_data.get("top_k", DEFAULT_TOP_K))
        top_k = max(1, min(top_k, MAX_TOP_K))
    except (ValueError, TypeError):
        return error_response("Parameter 'top_k' must be a valid integer", error_code="VALIDATION_ERROR", status_code=400)

    try:
        page = int(raw_data.get("page", DEFAULT_PAGE))
        if page < 1:
            return error_response("Parameter 'page' must be greater than or equal to 1", error_code="VALIDATION_ERROR", status_code=400)
    except (ValueError, TypeError):
        return error_response("Parameter 'page' must be a valid integer", error_code="VALIDATION_ERROR", status_code=400)

    try:
        page_size = int(raw_data.get("page_size", top_k or DEFAULT_PAGE_SIZE))
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    except (ValueError, TypeError):
        return error_response("Parameter 'page_size' must be a valid integer", error_code="VALIDATION_ERROR", status_code=400)

    # 4. Weights Validation
    try:
        lexical_weight = float(raw_data.get("lexical_weight", 0.40))
        semantic_weight = float(raw_data.get("semantic_weight", 0.60))
        raw_graph_weight = raw_data.get("graph_weight")
        graph_weight = float(raw_graph_weight) if raw_graph_weight is not None else None

        if not (0.0 <= lexical_weight <= 1.0) or not (0.0 <= semantic_weight <= 1.0):
            return error_response("Relevance weights must be between 0.0 and 1.0", error_code="VALIDATION_ERROR", status_code=400)
        if graph_weight is not None and not (0.0 <= graph_weight <= 1.0):
            return error_response("Parameter 'graph_weight' must be between 0.0 and 1.0", error_code="VALIDATION_ERROR", status_code=400)
    except (ValueError, TypeError):
        return error_response("Relevance weights must be valid numbers", error_code="VALIDATION_ERROR", status_code=400)

    # 5. Metadata Filters Consolidation
    filters: Dict[str, Any] = {}
    raw_filters = raw_data.get("filters")
    if isinstance(raw_filters, dict):
        filters.update(raw_filters)

    for field_name in ("work", "section", "chapter", "source", "tinai"):
        val = raw_data.get(field_name)
        if val is not None and isinstance(val, str) and val.strip():
            filters[field_name] = val.strip()

    # 6. Additional Flags & Exact Terms
    include_graph = raw_data.get("include_graph")
    if include_graph is None:
        include_graph = True if mode == "hybrid" else False
    elif isinstance(include_graph, str):
        include_graph = include_graph.lower() in ("true", "1", "yes")
    else:
        include_graph = bool(include_graph)

    try:
        max_graph_depth = int(raw_data.get("max_graph_depth", 2))
        max_graph_depth = max(1, min(max_graph_depth, 3))
    except (ValueError, TypeError):
        max_graph_depth = 2

    rerank = raw_data.get("rerank", True)
    if isinstance(rerank, str):
        rerank = rerank.lower() in ("true", "1", "yes")
    else:
        rerank = bool(rerank)

    require_phrase = raw_data.get("require_phrase", False)
    if isinstance(require_phrase, str):
        require_phrase = require_phrase.lower() in ("true", "1", "yes")
    else:
        require_phrase = bool(require_phrase)

    exact_terms_raw = raw_data.get("exact_terms")
    exact_terms: Optional[List[str]] = None
    if isinstance(exact_terms_raw, list):
        exact_terms = [str(t).strip() for t in exact_terms_raw if str(t).strip()]
    elif isinstance(exact_terms_raw, str) and exact_terms_raw.strip():
        exact_terms = [t.strip() for t in exact_terms_raw.split(",") if t.strip()]

    # 7. Query Preprocessing & Normalization
    try:
        processed_query = query_preprocessor.preprocess(query)
        normalized_query = processed_query.normalized_query
    except Exception as e:
        logger.warning(f"Query preprocessor warning for '{query}': {e}")
        normalized_query = query.strip()

    # 8. Execution & Safe Error Handling
    try:
        search_data = _execute_search(
            query=query,
            normalized_query=normalized_query,
            mode=mode,
            top_k=top_k,
            page=page,
            page_size=page_size,
            filters=filters if filters else None,
            include_graph=include_graph,
            max_graph_depth=max_graph_depth,
            rerank=rerank,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            graph_weight=graph_weight,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
        )

        msg = (
            f"Retrieved {search_data['result_count']} passages via {mode} search "
            f"(page {search_data['page']} of {search_data['total_pages']})"
        )
        return success_response(data=search_data, message=msg)

    except Exception as e:
        # Log complete internal exception details with traceback securely on server
        logger.error(f"Search API error processing query '{query}': {e}", exc_info=True)
        # Client-facing error message is sanitized with no internal implementation leakage
        return error_response(
            message="A server error occurred during search processing. Please try again later.",
            error_code="SEARCH_PROCESSING_ERROR",
            status_code=500,
        )


@search_bp.route("/embeddings/rebuild", methods=["POST"])
def rebuild_embeddings():
    """
    Triggers the Passage node embedding pipeline:
    - Validates passages (skipping empty/invalid ones).
    - Encodes normalized text with configurable model in batches.
    - Idempotently updates Neo4j Passage nodes & registers vector index.
    - Persists local .npz and JSON manifest cache.
    """
    try:
        data = request.get_json(silent=True) or {}
        batch_size = int(data.get("batch_size") or data.get("batchSize") or 32)
        update_neo4j = bool(data.get("update_neo4j", True))
        save_local_cache = bool(data.get("save_local_cache", True))
        custom_passages = data.get("passages")

        pipeline = passage_embedding_pipeline
        if batch_size > 0:
            pipeline.batch_size = batch_size

        report = pipeline.run_pipeline(
            passages=custom_passages,
            update_neo4j=update_neo4j,
            save_local_cache=save_local_cache,
        )

        return success_response(
            data=report.to_dict(),
            message=f"Passage embedding pipeline completed: {report.valid_passages} embedded, {report.skipped_passages} skipped",
        )
    except Exception as e:
        logger.error(f"Error rebuilding passage embeddings: {e}", exc_info=True)
        return error_response(str(e), error_code="EMBEDDING_PIPELINE_ERROR", status_code=500)

