"""
Flask Application Factory for Nyāya Neuro-Symbolic Reasoner Backend.
Registers blueprints, configures CORS, handles exceptions, and provides /api/health.
"""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# Add backend directory to sys.path so modules can import cleanly
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import atexit
from config import Config, config_by_name
from core.logger import logger
from core.exceptions import ReasonerException
from api.responses import success_response, error_response
from ingestion.metadata_manager import MetadataManager
from services.neo4j_service import neo4j_service

# Ensure graceful connection pool shutdown on application exit
atexit.register(neo4j_service.close)

# Import route blueprints
from api.routes.query_routes import query_bp
from api.routes.corpus_routes import corpus_bp
from api.routes.kg_routes import kg_bp
from api.routes.reasoning_routes import reasoning_bp
from api.routes.analytics_routes import analytics_bp
from api.routes.docs_routes import docs_bp
from api.routes.extraction_routes import extraction_bp
from api.routes.retrieval_routes import retrieval_bp
from api.routes.search_routes import search_bp
from api.routes.system_routes import system_bp


def create_app(config_name: str = None) -> Flask:
    """Application factory initializing Flask with all middleware and routes."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app_config = config_by_name.get(config_name, Config)
    app.config.from_object(app_config)

    # 1. Configure CORS
    CORS(
        app,
        resources={
            r"/api/*": {"origins": app_config.CORS_ORIGINS},
            r"/docs*": {"origins": "*"},
        },
        supports_credentials=True,
    )

    # 2. System Health Check Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Root health check validating backend readiness and integrated subsystem status."""
        summary = MetadataManager.get_summary()
        neo4j_health = neo4j_service.get_safe_connection_health()
        return success_response(
            data={
                "status": "HEALTHY",
                "service": "Nyāya-Inspired Neuro-Symbolic Reasoner for Classical Tamil Literary Knowledge",
                "version": "2.6.0",
                "corpus": summary["corpus_name"],
                "indexed_sutras": summary["indexed_sutras_active"],
                "total_sutras": summary["total_sutras_canonical"],
                "knowledge_graph": "Active (NetworkX)",
                "reasoning_engine": "Pañcāvayava Syllogism (5-Stage Nyāya)",
                "validation_engine": "Hetvābhāsa Defeasible Logic",
                "neo4j": {
                    "connected": neo4j_health["connected"],
                    "connection_status": neo4j_health["connection_status"],
                    "database_status": neo4j_health["database_status"],
                    "database": neo4j_health.get("database"),
                    "message": neo4j_health["message"],
                },
            },
            message="Backend service is fully operational",
        )

    # Dedicated Neo4j Connectivity Health Endpoint
    @app.route("/api/health/neo4j", methods=["GET"])
    def neo4j_health_endpoint():
        """Dedicated health check verifying communication with configured Neo4j Aura database."""
        health = neo4j_service.get_safe_connection_health()
        status_code = 200 if health["connected"] else 503
        payload = {
            "success": health["connected"],
            "connection_status": health["connection_status"],
            "database_status": health["database_status"],
            "message": health["message"],
            "database": health.get("database"),
            "latency_ms": health.get("latency_ms"),
            "server_agent": health.get("server_agent"),
            "protocol_version": health.get("protocol_version"),
        }
        return jsonify(payload), status_code


    # 3. Register Blueprints
    app.register_blueprint(query_bp)
    app.register_blueprint(corpus_bp)
    app.register_blueprint(kg_bp)
    app.register_blueprint(reasoning_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(extraction_bp)
    app.register_blueprint(retrieval_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(system_bp)

    # 4. Global Exception Handlers
    @app.errorhandler(ReasonerException)
    def handle_reasoner_exception(error: ReasonerException):
        logger.warning(f"Reasoner error: {error.message} (status: {error.status_code})")
        return error_response(
            message=error.message,
            error_code=error.__class__.__name__,
            details=error.details,
            status_code=error.status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        return error_response(
            message="The requested API endpoint does not exist",
            error_code="NOT_FOUND",
            status_code=404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return error_response(
            message="Method not allowed for this endpoint",
            error_code="METHOD_NOT_ALLOWED",
            status_code=405,
        )

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return error_response(
            message="An internal server error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )

    # 5. Startup Connectivity Check for Neo4j Aura
    if config_name != "testing":
        try:
            neo4j_service.startup_check(raise_on_failure=False)
        except Exception as e:
            logger.warning(f"Non-fatal error during Neo4j startup check: {e}")

    logger.info(f"Initialized Nyāya Reasoner Flask Application in [{config_name}] mode")
    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server at http://{host}:{port}")
    app.run(host=host, port=port, debug=Config.DEBUG)
