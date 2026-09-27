"""
Version 1 Health and Connectivity Diagnostics API.
"""
from __future__ import annotations

from flask import Blueprint
from config.settings import Config
from database.connection import get_db_manager
from services.corpus_service import get_corpus_service
from utilities.response_envelope import api_success

v1_health_bp = Blueprint("v1_health", __name__, url_prefix="/health")


@v1_health_bp.route("", methods=["GET"])
def health_status():
    """Root health check for v1 API."""
    corpus_service = get_corpus_service()
    meta = corpus_service.get_metadata()
    db_manager = get_db_manager()
    db_health = db_manager.verify_connectivity()

    return api_success(
        data={
            "status": "HEALTHY",
            "api_version": "v1",
            "corpus": meta.name,
            "canonical_sutras": meta.total_sutras,
            "database": db_health,
        },
        message="Classical Tamil Corpus and Literature API v1 is operational",
    )


@v1_health_bp.route("/neo4j", methods=["GET"])
def neo4j_health():
    """Dedicated health check for Neo4j Aura database connectivity."""
    db_manager = get_db_manager()
    db_health = db_manager.verify_connectivity()
    status_code = 200 if db_health["connected"] else 503
    return api_success(
        data=db_health,
        message="Neo4j Aura connectivity status verified",
        status_code=status_code,
    )
