"""
RAG Retrieval routes:
- POST /api/retrieval/semantic      (Dense vector similarity search via FAISS)
- POST /api/retrieval/bm25          (Lexical search via BM25Okapi)
- POST /api/retrieval/hybrid        (Fused semantic + lexical search via RRF)
- GET  /api/retrieval/by-source/<id> (Source-grounded chunk lookup by document / sūtra ID)
- GET  /api/retrieval/by-entity/<e> (Evidence retrieval by entity name)
- GET  /api/retrieval/statistics    (RAG index health and statistics)
- POST /api/retrieval/index         (Trigger corpus re-indexing)
"""
from flask import Blueprint, request
from api.responses import success_response, error_response
from retrieval.rag_service import rag_engine
from core.logger import logger

retrieval_bp = Blueprint("retrieval", __name__, url_prefix="/api/retrieval")


@retrieval_bp.route("/semantic", methods=["POST"])
def semantic_search():
    """Executes dense vector similarity search using multilingual embeddings and cosine similarity."""
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or body.get("queryText") or "").strip()
    
    if not query:
        return error_response(
            "Parameter 'query' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=400,
        )
    if len(query) > 500:
        return error_response(
            "Query length exceeds maximum limit of 500 characters",
            error_code="QUERY_TOO_LONG",
            status_code=400,
        )

    try:
        top_k = int(body.get("top_k", 5))
        top_k = min(max(top_k, 1), 50)
    except (ValueError, TypeError):
        top_k = 5

    filters = body.get("filters")
    target = body.get("target", "chunks")

    try:
        if target == "passages":
            results = rag_engine.semantic_passage_search(query, top_k=top_k, filters=filters)
            msg = f"Retrieved {len(results)} passages via semantic search"
        else:
            results = rag_engine.semantic_search(query, top_k=top_k, filters=filters)
            msg = f"Retrieved {len(results)} chunks via FAISS semantic search"

        return success_response(
            data={"results": results, "total": len(results), "query": query, "filters": filters},
            message=msg,
        )
    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        return error_response(f"Semantic search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/semantic-passages", methods=["POST"])
def semantic_passage_search():
    """Executes semantic search returning passage ID, passage text, source metadata, and normalized similarity score."""
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    filters = body.get("filters")

    if not query:
        return error_response(
            "Parameter 'query' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        results = rag_engine.semantic_passage_search(query, top_k=top_k, filters=filters)
        return success_response(
            data={"results": results, "total": len(results), "query": query, "filters": filters},
            message=f"Retrieved {len(results)} passages via semantic search",
        )
    except Exception as e:
        logger.error(f"Semantic passage search error: {e}", exc_info=True)
        return error_response(f"Semantic passage search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/bm25", methods=["POST"])
def bm25_search():
    """Executes lexical keyword search using BM25 with metadata filtering."""
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    filters = body.get("filters")
    exact_terms = body.get("exact_terms")
    require_phrase = bool(body.get("require_phrase", False))

    if not query and not exact_terms and not filters:
        return error_response(
            "Parameter 'query', 'exact_terms', or 'filters' must be provided",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        results = rag_engine.bm25_search(
            query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
        )
        return success_response(
            data={"results": results, "total": len(results), "query": query, "filters": filters},
            message=f"Retrieved {len(results)} chunks via BM25 lexical search",
        )
    except Exception as e:
        logger.error(f"BM25 search error: {e}", exc_info=True)
        return error_response(f"BM25 search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/lexical", methods=["POST"])
def lexical_search():
    """
    Direct lexical search over classical Tamil literary passages.
    Returns passage ID, text, complete source metadata, and normalized BM25 score.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    filters = body.get("filters")
    exact_terms = body.get("exact_terms")
    require_phrase = bool(body.get("require_phrase", False))
    primary_passages_only = bool(body.get("primary_passages_only", False))

    if not query and not exact_terms and not filters:
        return error_response(
            "Parameter 'query', 'exact_terms', or 'filters' must be provided",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        results = rag_engine.lexical_search(
            query=query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            primary_passages_only=primary_passages_only,
        )
        return success_response(
            data={"results": results, "total": len(results), "query": query, "filters": filters},
            message=f"Retrieved {len(results)} passages via lexical search",
        )
    except Exception as e:
        logger.error(f"Lexical search error: {e}", exc_info=True)
        return error_response(f"Lexical search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/hybrid", methods=["POST"])
def hybrid_search():
    """
    Executes unified hybrid retrieval fusing BM25 lexical and dense semantic vector search.
    Returns candidates with individual lexical, semantic, and combined scores.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))

    lexical_weight = body.get("lexical_weight")
    if lexical_weight is None:
        lexical_weight = body.get("bm25_weight", 0.40)
    lexical_weight = float(lexical_weight)

    semantic_weight = float(body.get("semantic_weight", 0.60))
    filters = body.get("filters")
    exact_terms = body.get("exact_terms")
    require_phrase = bool(body.get("require_phrase", False))
    target = body.get("target", "passages")
    rerank = bool(body.get("rerank", False))
    rerank_weights = body.get("rerank_weights")
    include_graph = bool(body.get("include_graph", False))
    max_graph_depth = int(body.get("max_graph_depth", 2))
    graph_weight = body.get("graph_weight")

    if not query and not exact_terms and not filters:
        return error_response(
            "Parameter 'query', 'exact_terms', or 'filters' must be provided",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        if target == "chunks":
            results = rag_engine.hybrid_search(
                query,
                top_k=top_k,
                semantic_weight=semantic_weight,
                bm25_weight=lexical_weight,
            )
            msg = f"Retrieved {len(results)} chunks via Hybrid RRF search"
        elif include_graph:
            results = rag_engine.graph_hybrid_passage_search(
                query=query,
                top_k=top_k,
                max_graph_depth=max_graph_depth,
                lexical_weight=lexical_weight,
                semantic_weight=semantic_weight,
                graph_weight=graph_weight,
                filters=filters,
                exact_terms=exact_terms,
                require_phrase=require_phrase,
                rerank=rerank,
            )
            msg = f"Retrieved {len(results)} passages via Graph-Augmented Hybrid search"
        else:
            results = rag_engine.hybrid_passage_search(
                query=query,
                top_k=top_k,
                lexical_weight=lexical_weight,
                semantic_weight=semantic_weight,
                filters=filters,
                exact_terms=exact_terms,
                require_phrase=require_phrase,
                rerank=rerank,
                rerank_weights=rerank_weights,
            )
            msg = f"Retrieved {len(results)} passages via Unified Hybrid search"
            if rerank:
                msg += " with second-stage re-ranking"

        return success_response(
            data={
                "results": results,
                "total": len(results),
                "query": query,
                "lexical_weight": lexical_weight,
                "semantic_weight": semantic_weight,
                "graph_weight": graph_weight,
                "filters": filters,
                "rerank": rerank,
                "rerank_weights": rerank_weights,
                "include_graph": include_graph,
                "max_graph_depth": max_graph_depth,
            },
            message=msg,
        )
    except Exception as e:
        logger.error(f"Hybrid search error: {e}", exc_info=True)
        return error_response(f"Hybrid search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/graph-hybrid", methods=["POST"])
def graph_hybrid_search_endpoint():
    """
    Dedicated endpoint for Graph-Augmented Hybrid Search.
    Combines BM25 lexical relevance, dense semantic relevance, and Neo4j Aura Knowledge Graph
    topological context into a unified ranked search context with exact source provenance.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    max_graph_depth = int(body.get("max_graph_depth", 2))
    lexical_weight = body.get("lexical_weight")
    semantic_weight = body.get("semantic_weight")
    graph_weight = body.get("graph_weight")
    filters = body.get("filters")
    exact_terms = body.get("exact_terms")
    require_phrase = bool(body.get("require_phrase", False))
    rerank = bool(body.get("rerank", True))

    if not query and not exact_terms and not filters:
        return error_response(
            "Parameter 'query', 'exact_terms', or 'filters' must be provided",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        results = rag_engine.graph_hybrid_passage_search(
            query=query,
            top_k=top_k,
            max_graph_depth=max_graph_depth,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            graph_weight=graph_weight,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            rerank=rerank,
        )
        return success_response(
            data={
                "results": results,
                "total": len(results),
                "query": query,
                "top_k": top_k,
                "max_graph_depth": max_graph_depth,
                "lexical_weight": lexical_weight,
                "semantic_weight": semantic_weight,
                "graph_weight": graph_weight,
                "filters": filters,
            },
            message=f"Retrieved {len(results)} passages via Neo4j Knowledge Graph Augmented Hybrid search",
        )
    except Exception as e:
        logger.error(f"Graph-hybrid search error: {e}", exc_info=True)
        return error_response(f"Graph-hybrid search failed: {str(e)}", status_code=500)


@retrieval_bp.route("/rerank", methods=["POST"])
def rerank_passages_endpoint():
    """
    Second-stage re-ranking endpoint for literary passages.
    Evaluates candidates using semantic similarity, keyword coverage, entity/concept matching,
    source relevance, and metadata matching. Returns ranked passages with component breakdowns
    and human-readable ranking explanations.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    candidates = body.get("candidates")
    top_k = int(body.get("top_k", 5))
    weights = body.get("weights") or body.get("rerank_weights")
    filters = body.get("filters")

    if not query:
        return error_response(
            "Parameter 'query' is required for re-ranking",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        if candidates is not None and isinstance(candidates, list):
            # Direct re-ranking of provided candidate set
            results = rag_engine.rerank_passages(
                candidates=candidates,
                query=query,
                top_k=top_k,
                weights=weights,
                filters=filters,
            )
        else:
            # Generate candidate set via hybrid search and then re-rank
            results = rag_engine.hybrid_passage_search(
                query=query,
                top_k=top_k,
                filters=filters,
                rerank=True,
                rerank_weights=weights,
            )

        return success_response(
            data={
                "results": results,
                "total": len(results),
                "query": query,
                "top_k": top_k,
                "weights": weights,
                "filters": filters,
            },
            message=f"Successfully re-ranked {len(results)} passages across 5 relevance dimensions",
        )
    except Exception as e:
        logger.error(f"Re-ranking error: {e}", exc_info=True)
        return error_response(f"Re-ranking failed: {str(e)}", status_code=500)


@retrieval_bp.route("/by-source/<string:source_id>", methods=["GET"])
def retrieve_by_source(source_id: str):
    """Retrieves all evidence chunks matching a specific source ID or sūtra reference."""
    try:
        results = rag_engine.retrieve_by_source(source_id)
        if not results:
            return error_response(
                f"No evidence found for source ID '{source_id}'",
                error_code="SOURCE_NOT_FOUND",
                status_code=404,
            )
        return success_response(
            data={"results": results, "total": len(results), "source_id": source_id},
            message=f"Retrieved {len(results)} chunks for source '{source_id}'",
        )
    except Exception as e:
        logger.error(f"Source retrieval error: {e}", exc_info=True)
        return error_response(f"Source retrieval failed: {str(e)}", status_code=500)


@retrieval_bp.route("/by-entity/<string:entity>", methods=["GET"])
def retrieve_by_entity(entity: str):
    """Retrieves all evidence chunks referencing or associated with an entity."""
    try:
        results = rag_engine.retrieve_by_entity(entity)
        return success_response(
            data={"results": results, "total": len(results), "entity": entity},
            message=f"Retrieved {len(results)} chunks for entity '{entity}'",
        )
    except Exception as e:
        logger.error(f"Entity retrieval error: {e}", exc_info=True)
        return error_response(f"Entity retrieval failed: {str(e)}", status_code=500)


@retrieval_bp.route("/statistics", methods=["GET"])
def get_retrieval_statistics():
    """Returns statistics on the indexed chunks, vector dimensionality, and indices."""
    try:
        stats = rag_engine.get_statistics()
        return success_response(data=stats, message="Retrieval statistics retrieved")
    except Exception as e:
        logger.error(f"Error fetching retrieval stats: {e}", exc_info=True)
        return error_response(f"Failed to fetch stats: {str(e)}", status_code=500)


@retrieval_bp.route("/index", methods=["POST"])
def trigger_indexing():
    """Triggers re-indexing of the classical Tamil corpus."""
    try:
        stats = rag_engine.index_corpus()
        return success_response(data=stats, message="Corpus re-indexing complete")
    except Exception as e:
        logger.error(f"Error re-indexing: {e}", exc_info=True)
        return error_response(f"Re-indexing failed: {str(e)}", status_code=500)


@retrieval_bp.route("/hybrid-rag", methods=["POST"])
def hybrid_rag_retrieval_endpoint():
    """
    Dedicated endpoint executing the 3-channel Hybrid RAG pipeline:
    - Channel A: Semantic Vector Similarity Search via Neo4j Aura / FAISS
    - Channel B: Lexical BM25Okapi Search with Literary Terminology extraction
    - Channel C: Multi-Hop Knowledge Graph Traversal from seed entities
    Integrated with 5-signal deterministic Evidence Ranking Engine.
    """
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or body.get("queryText") or "").strip()

    if not query:
        return error_response(
            "Parameter 'query' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=400,
        )
    if len(query) > 500:
        return error_response(
            "Query length exceeds maximum limit of 500 characters",
            error_code="QUERY_TOO_LONG",
            status_code=400,
        )

    try:
        top_k = int(body.get("top_k", 5))
        top_k = min(max(top_k, 1), 50)
    except (ValueError, TypeError):
        top_k = 5

    filters = body.get("filters")
    if not isinstance(filters, dict):
        filters = {} if filters is None else {"raw": filters}
    else:
        filters = dict(filters)

    for param_key, filter_key in [
        ("query_type", "query_type"),
        ("queryType", "query_type"),
        ("depth", "depth"),
        ("hops", "depth"),
        ("focus", "focus"),
        ("work", "work"),
        ("section", "section"),
        ("chapter", "chapter"),
        ("tinai", "tinai"),
    ]:
        if param_key in body and filter_key not in filters and body[param_key] is not None:
            filters[filter_key] = body[param_key]

    try:
        from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline
        collection = hybrid_rag_pipeline.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
        )
        return success_response(
            data=collection.to_dict(),
            message=f"Retrieved {len(collection.items)} ranked evidence item(s) via 3-channel Hybrid RAG",
            meta={
                "query": query,
                "top_k": top_k,
                "total_retrieved": len(collection.items),
                "pipeline_version": collection.pipeline_version,
            },
        )
    except Exception as e:
        logger.error(f"Hybrid RAG retrieval error: {e}", exc_info=True)
        return error_response(f"Hybrid RAG retrieval failed: {str(e)}", status_code=500)


@retrieval_bp.route("/structured-context", methods=["POST"])
def structured_context_endpoint():
    """
    Transforms ranked Hybrid RAG retrieval results into a compact, structured context
    for grounded answer generation:
    - Preserves exact source reference, passage ID, text, and literary metadata.
    - Extracts structured Neo4j graph relationships (entities, concepts, events, hierarchy).
    - Compacts context within configurable character budgets.
    - Demarcates source evidence strictly from instructions with boundary fences.
    - Returns an explicit 'insufficient_evidence' state when minimum criteria are not met.
    """
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or body.get("queryText") or "").strip()

    if not query:
        return error_response(
            "Parameter 'query' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=400,
        )
    if len(query) > 500:
        return error_response(
            "Query length exceeds maximum limit of 500 characters",
            error_code="QUERY_TOO_LONG",
            status_code=400,
        )

    try:
        top_k = min(max(int(body.get("top_k", 5)), 1), 50)
    except (ValueError, TypeError):
        top_k = 5

    try:
        max_passages = min(max(int(body.get("max_passages", 5)), 1), 20)
    except (ValueError, TypeError):
        max_passages = 5

    try:
        max_context_chars = min(max(int(body.get("max_context_chars", 4000)), 500), 16000)
    except (ValueError, TypeError):
        max_context_chars = 4000

    try:
        max_relationships = min(max(int(body.get("max_relationships", 8)), 1), 25)
    except (ValueError, TypeError):
        max_relationships = 8

    try:
        min_relevance_threshold = min(max(float(body.get("min_relevance_threshold", 0.30)), 0.0), 1.0)
    except (ValueError, TypeError):
        min_relevance_threshold = 0.30

    try:
        min_evidence_count = min(max(int(body.get("min_evidence_count", 1)), 1), 10)
    except (ValueError, TypeError):
        min_evidence_count = 1

    filters = body.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    for param_key in ("work", "section", "chapter", "tinai"):
        if param_key in body and param_key not in filters and body[param_key]:
            filters[param_key] = str(body[param_key]).strip()

    try:
        context_dict = rag_engine.build_structured_context(
            query=query,
            top_k=top_k,
            filters=filters,
            max_passages=max_passages,
            max_context_chars=max_context_chars,
            max_relationships_per_passage=max_relationships,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
            as_dict=True,
        )

        msg = (
            f"Structured context assembled: {context_dict['passage_count']} qualifying passage(s)"
            if context_dict["is_sufficient"]
            else "Insufficient relevant evidence retrieved for query"
        )

        return success_response(
            data=context_dict,
            message=msg,
            meta={
                "query": query,
                "is_sufficient": context_dict["is_sufficient"],
                "status": context_dict["status"],
                "passage_count": context_dict["passage_count"],
            },
        )
    except Exception as e:
        logger.error(f"Error building structured context: {e}", exc_info=True)
        return error_response(f"Structured context generation failed: {str(e)}", status_code=500)


@retrieval_bp.route("/answer", methods=["POST"])
def answer_query():
    """
    Generate an evidence-grounded final answer for a query using the OpenRouter LLM.
    Ensures that the LLM operates strictly on validated retrieved context.
    Returns final answer, retrieved evidence, source references, confidence info,
    and reasoning metadata.
    """
    body = request.get_json(silent=True) or {}
    query = (
        body.get("query")
        or body.get("queryText")
        or body.get("question")
        or ""
    ).strip()

    if not query:
        return error_response(
            "Query cannot be empty. Please provide 'query' or 'queryText'.",
            error_code="INVALID_QUERY",
            status_code=400,
        )

    try:
        top_k = min(max(int(body.get("top_k", 5)), 1), 20)
    except (ValueError, TypeError):
        top_k = 5

    try:
        max_graph_depth = min(max(int(body.get("max_graph_depth", 2)), 1), 4)
    except (ValueError, TypeError):
        max_graph_depth = 2

    try:
        max_context_chars = min(max(int(body.get("max_context_chars", 4000)), 500), 12000)
    except (ValueError, TypeError):
        max_context_chars = 4000

    try:
        max_relationships = min(max(int(body.get("max_relationships", 8)), 1), 25)
    except (ValueError, TypeError):
        max_relationships = 8

    try:
        min_relevance_threshold = min(max(float(body.get("min_relevance_threshold", 0.30)), 0.0), 1.0)
    except (ValueError, TypeError):
        min_relevance_threshold = 0.30

    try:
        min_evidence_count = min(max(int(body.get("min_evidence_count", 1)), 1), 10)
    except (ValueError, TypeError):
        min_evidence_count = 1

    filters = body.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    for param_key in ("work", "section", "chapter", "tinai"):
        if param_key in body and param_key not in filters and body[param_key]:
            filters[param_key] = str(body[param_key]).strip()

    try:
        answer_result = rag_engine.answer_query(
            query=query,
            top_k=top_k,
            filters=filters,
            max_graph_depth=max_graph_depth,
            max_context_chars=max_context_chars,
            max_relationships=max_relationships,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
        )

        is_sufficient = not answer_result.get("insufficient_evidence", False)
        msg = (
            "Evidence-grounded answer successfully synthesized"
            if is_sufficient
            else "Insufficient relevant evidence retrieved to answer query"
        )

        return success_response(
            data=answer_result,
            message=msg,
            meta={
                "query": query,
                "is_sufficient": is_sufficient,
                "provider": answer_result.get("reasoning_metadata", {}).get("provider", "openrouter"),
                "model": answer_result.get("reasoning_metadata", {}).get("model", "unknown"),
                "retrieved_count": len(answer_result.get("retrieved_evidence", [])),
            },
        )
    except Exception as e:
        logger.error(f"Error synthesizing grounded answer: {e}", exc_info=True)
        return error_response(f"Answer synthesis failed: {str(e)}", status_code=500)


