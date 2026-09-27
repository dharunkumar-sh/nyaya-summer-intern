"""
Neo4j Aura Configuration and Credential Validation.
Guarantees secure connection handling without credential leakage.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
from config.settings import Config


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

    VECTOR_INDEX_NAME = Config.NEO4J_VECTOR_INDEX_NAME
    VECTOR_SIMILARITY_FUNCTION = Config.NEO4J_VECTOR_SIMILARITY_FUNCTION
    DEFAULT_VECTOR_DIMENSIONS = Config.EMBEDDING_VECTOR_DIM

    VALID_SCHEMES = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")

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

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if minimum required credentials and URI are populated."""
        return bool(cls.URI and cls.USERNAME and cls.PASSWORD)

    @classmethod
    def validate(cls) -> Dict[str, Any]:
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
    def get_masked_config(cls) -> Dict[str, Any]:
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
