"""
System Routes:
- GET /api/system/status  (Comprehensive live diagnostics across Flask, Neo4j Aura, RAG, KG, and Corpus)
- GET /api/system/ping    (Lightweight liveness probe)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from flask import Blueprint, jsonify

from api.responses import success_response
from core.logger import logger
from services.neo4j_service import neo4j_service
from ingestion.metadata_manager import MetadataManager

system_bp = Blueprint("system", __name__, url_prefix="/api/system")
_START_TIME = time.time()


@system_bp.route("/ping", methods=["GET"])
def ping():
    """Lightweight ping probe."""
    return jsonify({
        "pong": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


@system_bp.route("/status", methods=["GET"])
def get_system_status():
    """
    Returns unified, structured system health and operational metrics.
    Strictly sanitizes internal credentials and catches service-specific
    failures so the caller receives granular diagnostics.
    """
    probe_start = time.perf_counter()

    # 1. Probe Neo4j Aura
    neo4j_health = neo4j_service.get_safe_connection_health()
    db_connected = neo4j_health.get("connected", False)

    database_diag = {
        "name": "Neo4j Aura Graph Database",
        "status": "connected" if db_connected else "disconnected",
        "connected": db_connected,
        "database": neo4j_health.get("database"),
        "server_agent": neo4j_health.get("server_agent"),
        "protocol_version": neo4j_health.get("protocol_version"),
        "latency_ms": neo4j_health.get("latency_ms"),
        "message": neo4j_health.get("message", ""),
    }

    # 2. Probe Hybrid RAG Engine (FAISS + BM25)
    retrieval_diag = {
        "name": "Hybrid RAG Engine (FAISS + BM25)",
        "status": "initializing",
        "healthy": False,
        "faiss_indexed_chunks": 0,
        "bm25_indexed_records": 0,
        "total_chunks": 0,
    }
    try:
        from retrieval.rag_service import rag_engine
        faiss_size = rag_engine.faiss_index.size() if rag_engine.faiss_index else 0
        bm25_size = len(rag_engine.bm25_retriever.records) if hasattr(rag_engine, "bm25_retriever") and rag_engine.bm25_retriever else 0
        chunk_count = len(rag_engine.chunks) if hasattr(rag_engine, "chunks") else 0

        retrieval_diag.update({
            "status": "ready" if (faiss_size > 0 or chunk_count > 0) else "empty",
            "healthy": bool(faiss_size > 0 or chunk_count > 0),
            "faiss_indexed_chunks": faiss_size,
            "bm25_indexed_records": bm25_size,
            "total_chunks": chunk_count,
        })
    except Exception as e:
        logger.warning(f"Error probing RAG retrieval status: {e}")
        retrieval_diag["status"] = "degraded"
        retrieval_diag["message"] = str(e)

    # 3. Probe Hierarchical Knowledge Graph
    kg_diag = {
        "name": "Hierarchical Knowledge Graph Store",
        "status": "inactive",
        "healthy": False,
        "total_nodes": 0,
        "total_edges": 0,
        "is_connected": False,
        "density": 0.0,
    }
    try:
        from knowledge_graph.graph_builder import kg_instance
        from knowledge_graph.graph_validator import KnowledgeGraphValidator
        store = kg_instance.store
        validator_summary = KnowledgeGraphValidator.validate()

        kg_diag.update({
            "status": "active",
            "healthy": True,
            "total_nodes": validator_summary.get("node_count", store.node_count()),
            "total_edges": validator_summary.get("edge_count", store.edge_count()),
            "is_connected": validator_summary.get("is_connected", False),
            "density": validator_summary.get("density", 0.0),
        })
    except Exception as e:
        logger.warning(f"Error probing Knowledge Graph store status: {e}")
        kg_diag["status"] = "degraded"
        kg_diag["message"] = str(e)

    # 4. Probe Corpus Engine
    corpus_summary = MetadataManager.get_summary()
    corpus_diag = {
        "name": "Canonical Classical Tamil Corpus",
        "status": "loaded",
        "corpus_name": corpus_summary.get("corpus_name", "Tolkāppiyam"),
        "canonical_sutras": corpus_summary.get("total_sutras_canonical", 1610),
        "active_indexed_sutras": corpus_summary.get("indexed_sutras_active", 0),
        "sections": ["Eḻuttatikāram", "Collatikāram", "Poruḷatikāram"],
    }

    # 5. Measure Application Response Latency & System Status
    app_latency_ms = round((time.perf_counter() - probe_start) * 1000, 2)
    uptime_sec = round(time.time() - _START_TIME, 1)

    # Overall Status:
    # - "healthy": Core app is running, Neo4j Aura is connected, RAG and KG are healthy
    # - "degraded": Core app is running, but Neo4j is offline or retrieval index is partial
    # - "unhealthy": Core components failed
    if db_connected and retrieval_diag["healthy"] and kg_diag["healthy"]:
        system_overall = "healthy"
    elif retrieval_diag["healthy"] or kg_diag["healthy"]:
        system_overall = "degraded"
    else:
        system_overall = "unhealthy"

    data = {
        "status": system_overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_sec,
        "services": {
            "application": {
                "name": "Nyāya Neuro-Symbolic Reasoner Core",
                "status": "online",
                "version": "2.6.0",
                "latency_ms": app_latency_ms,
            },
            "database": database_diag,
            "retrieval": retrieval_diag,
            "knowledge_graph": kg_diag,
            "corpus": corpus_diag,
        },
    }

    return success_response(data=data, message=f"System status: {system_overall.upper()}")


@system_bp.route("/clear-cache", methods=["POST"])
def clear_system_cache():
    """Flushes transient system and retrieval runtime caches."""
    try:
        from retrieval.rag_service import rag_engine
        rag_engine.clear_runtime_cache()
        return success_response(
            data={"cleared": True},
            message="System runtime caches cleared successfully",
        )
    except Exception as e:
        logger.error(f"Error clearing system caches: {e}", exc_info=True)
        return error_response(f"System cache clearance failed: {str(e)}", status_code=500)
