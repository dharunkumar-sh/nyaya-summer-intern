"""
V1 API Routes Blueprint Bundle.
Combines corpus and health endpoints under /api/v1.
"""
from flask import Blueprint
from routes.v1.corpus_routes import v1_corpus_bp
from routes.v1.health_routes import v1_health_bp

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1_bp.register_blueprint(v1_corpus_bp)
api_v1_bp.register_blueprint(v1_health_bp)

__all__ = ["api_v1_bp", "v1_corpus_bp", "v1_health_bp"]
