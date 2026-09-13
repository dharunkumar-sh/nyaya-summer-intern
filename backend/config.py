"""
Application-wide configuration loader.
Reads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "nyaya-tolkappiyam-secret-key-default")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    # CORS origins allowed to communicate with Flask backend
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]

    # Corpus Configuration
    CORPUS_NAME = os.getenv("CORPUS_NAME", "Tolkāppiyam")
    CORPUS_FILE = BASE_DIR / os.getenv("CORPUS_PATH", "data/raw/tolkappiyam_canonical.json")
    PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
    INDEXES_DIR = BASE_DIR / "data" / "indexes"

    # Default parameters
    DEFAULT_TOP_K = int(os.getenv("DEFAULT_SEARCH_TOP_K", 5))
    DEFAULT_KG_DEPTH = int(os.getenv("DEFAULT_KG_DEPTH", 1))

    # Epistemic Reasoning Constants
    MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", 0.75))
    MAX_HETVABHASA_TOLERANCE = float(os.getenv("MAX_HETVABHASA_TOLERANCE", 0.05))

    # Multilingual Embedding Configuration
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers").lower()
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    EMBEDDING_VECTOR_DIM = int(os.getenv("EMBEDDING_VECTOR_DIM", 384))
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 32))
    EMBEDDING_MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", 3))
    EMBEDDING_RETRY_BACKOFF = float(os.getenv("EMBEDDING_RETRY_BACKOFF", 1.5))

    # LLM Provider Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", None)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)

    # OpenRouter LLM Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1024))
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", 30.0))


    # Neo4j Aura Configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    NEO4J_MAX_CONNECTION_LIFETIME = int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", 3600))
    NEO4J_MAX_CONNECTION_POOL_SIZE = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", 50))
    NEO4J_CONNECTION_TIMEOUT = float(os.getenv("NEO4J_CONNECTION_TIMEOUT", 10.0))
    NEO4J_CONNECTION_ACQUISITION_TIMEOUT = float(os.getenv("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", 60.0))
    GRAPH_STORE_BACKEND = os.getenv("GRAPH_STORE_BACKEND", "networkx").lower()

    # Centralized Neo4j Vector Index Configuration
    NEO4J_VECTOR_INDEX_NAME = os.getenv("NEO4J_VECTOR_INDEX_NAME", "passage_embeddings_index")
    NEO4J_VECTOR_SIMILARITY_FUNCTION = os.getenv("NEO4J_VECTOR_SIMILARITY_FUNCTION", "cosine")


import re
from typing import Any, Optional


def sanitize_uri(uri: str) -> str:
    """Removes embedded credentials from URI for safe logging and display."""
    if not uri:
        return ""
    return re.sub(r"://([^@/]+)@", r"://***@", uri)


class Neo4jConfig:
    """Dedicated configuration namespace for Neo4j Aura driver with validation."""

    URI = Config.NEO4J_URI
    USERNAME = Config.NEO4J_USERNAME
    PASSWORD = Config.NEO4J_PASSWORD
    DATABASE = Config.NEO4J_DATABASE
    MAX_CONNECTION_LIFETIME = Config.NEO4J_MAX_CONNECTION_LIFETIME
    MAX_CONNECTION_POOL_SIZE = Config.NEO4J_MAX_CONNECTION_POOL_SIZE
    CONNECTION_TIMEOUT = Config.NEO4J_CONNECTION_TIMEOUT
    CONNECTION_ACQUISITION_TIMEOUT = Config.NEO4J_CONNECTION_ACQUISITION_TIMEOUT
    ENABLED = bool(Config.NEO4J_URI and Config.NEO4J_USERNAME and Config.NEO4J_PASSWORD)

    # Centralized Vector Index Settings
    VECTOR_INDEX_NAME = Config.NEO4J_VECTOR_INDEX_NAME
    VECTOR_SIMILARITY_FUNCTION = Config.NEO4J_VECTOR_SIMILARITY_FUNCTION
    DEFAULT_VECTOR_DIMENSIONS = Config.EMBEDDING_VECTOR_DIM

    @classmethod
    def resolve_vector_dimensions(cls, model_name: Optional[str] = None, encoder: Optional[Any] = None) -> int:
        """
        Dynamically resolves the exact output dimensionality of the selected embedding model.
        Guarantees that Neo4j vector index dimensions match the embedding vectors without hardcoding errors.
        """
        if encoder is not None:
            if hasattr(encoder, "dimension"):
                return int(encoder.dimension)
            if hasattr(encoder, "get_sentence_embedding_dimension"):
                return int(encoder.get_sentence_embedding_dimension())

        target_model = model_name or Config.EMBEDDING_MODEL_NAME

        KNOWN_DIMS = {
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "intfloat/multilingual-e5-base": 768,
            "intfloat/multilingual-e5-large": 1024,
            "intfloat/multilingual-e5-small": 384,
            "sentence-transformers/LaBSE": 768,
            "BAAI/bge-m3": 1024,
            "BAAI/bge-large-en-v1.5": 1024,
        }
        if target_model in KNOWN_DIMS:
            return KNOWN_DIMS[target_model]

        try:
            from sentence_transformers import SentenceTransformer
            st = SentenceTransformer(target_model, local_files_only=True)
            dim = st.get_sentence_embedding_dimension()
            if dim and int(dim) > 0:
                return int(dim)
        except Exception:
            pass

        return int(Config.EMBEDDING_VECTOR_DIM)

    VALID_SCHEMES = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if all minimum required credentials and URI are populated."""
        return bool(cls.URI and cls.USERNAME and cls.PASSWORD)

    @classmethod
    def validate(cls) -> dict:
        """
        Validates Neo4j configuration without exposing raw credentials.
        Returns a dictionary containing validation status and sanitized diagnostics.
        """
        errors = []

        if not cls.URI:
            errors.append("NEO4J_URI is missing or empty.")
        elif not any(cls.URI.startswith(scheme) for scheme in cls.VALID_SCHEMES):
            errors.append(f"NEO4J_URI has invalid scheme: '{cls.URI[:10]}...'. Expected one of {cls.VALID_SCHEMES}.")

        if not cls.USERNAME:
            errors.append("NEO4J_USERNAME is missing or empty.")

        if not cls.PASSWORD:
            errors.append("NEO4J_PASSWORD is missing or empty.")

        if cls.MAX_CONNECTION_POOL_SIZE <= 0:
            errors.append("NEO4J_MAX_CONNECTION_POOL_SIZE must be greater than 0.")

        if cls.MAX_CONNECTION_LIFETIME <= 0:
            errors.append("NEO4J_MAX_CONNECTION_LIFETIME must be greater than 0.")

        if cls.CONNECTION_TIMEOUT <= 0:
            errors.append("NEO4J_CONNECTION_TIMEOUT must be greater than 0.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "uri": sanitize_uri(cls.URI),
            "username": cls.USERNAME,
            "database": cls.DATABASE,
            "password_set": bool(cls.PASSWORD),
            "max_connection_pool_size": cls.MAX_CONNECTION_POOL_SIZE,
            "max_connection_lifetime": cls.MAX_CONNECTION_LIFETIME,
            "connection_timeout": cls.CONNECTION_TIMEOUT,
        }

    @classmethod
    def get_masked_config(cls) -> dict:
        """Returns safe configuration metadata for health checks, APIs, and logging."""
        return {
            "uri": sanitize_uri(cls.URI),
            "username": cls.USERNAME,
            "database": cls.DATABASE,
            "is_configured": cls.is_configured(),
            "password_set": bool(cls.PASSWORD),
            "max_connection_pool_size": cls.MAX_CONNECTION_POOL_SIZE,
            "max_connection_lifetime": cls.MAX_CONNECTION_LIFETIME,
            "connection_timeout": cls.CONNECTION_TIMEOUT,
        }


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
