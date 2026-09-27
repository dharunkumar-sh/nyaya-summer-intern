"""
Configuration Package for Classical Tamil Reasoner Backend.
"""
from config.settings import (
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    config_by_name,
)
from config.neo4j_config import Neo4jConfig, sanitize_uri


def get_config(name: str = None) -> Config:
    """Returns the application config object for the specified environment."""
    import os
    if name is None:
        name = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(name, Config)


__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "Neo4jConfig",
    "config_by_name",
    "get_config",
    "sanitize_uri",
]
