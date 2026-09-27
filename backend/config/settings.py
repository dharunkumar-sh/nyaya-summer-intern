"""
Application Settings and Configuration Loader for Classical Tamil Literature Reasoner.
Reads settings from environment variables with safe defaults.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""

    # Server settings
    SECRET_KEY = os.getenv("SECRET_KEY", "nyaya-tolkappiyam-secret-key-default")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    TESTING = False
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    API_PREFIX = os.getenv("API_PREFIX", "/api")
    API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")

    # CORS origins
    CORS_ORIGINS: List[str] = [
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
    DATA_DIR = BASE_DIR / "data"
    PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
    INDEXES_DIR = BASE_DIR / "data" / "indexes"

    # Default Search & Graph Parameters
    DEFAULT_TOP_K = int(os.getenv("DEFAULT_SEARCH_TOP_K", 5))
    DEFAULT_KG_DEPTH = int(os.getenv("DEFAULT_KG_DEPTH", 2))

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
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
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
    NEO4J_VECTOR_INDEX_NAME = os.getenv("NEO4J_VECTOR_INDEX_NAME", "passage_embeddings_index")
    NEO4J_VECTOR_SIMILARITY_FUNCTION = os.getenv("NEO4J_VECTOR_SIMILARITY_FUNCTION", "cosine")


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
