"""
Pydantic-based configuration model for strict environment validation.
"""
import os
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SystemSettings(BaseModel):
    """Core settings validation."""

    app_name: str = "Nyāya Neuro-Symbolic Reasoner"
    version: str = "2.6.0"
    corpus_name: str = "Tolkāppiyam"
    total_sutras: int = 1610
    total_atikarams: int = 3
    supported_languages: List[str] = Field(default_factory=lambda: ["ta", "en", "iso15919"])
    enable_fallacy_check: bool = True
    default_top_k: int = 5
    default_hops: int = 3

    # Fallacy thresholds
    savyabhicara_max: float = 0.05
    viruddha_max: float = 0.05
    satpratipaksa_max: float = 0.05
    asiddha_max: float = 0.05
    badhita_max: float = 0.05


class Neo4jSettings(BaseModel):
    """Neo4j Aura connectivity and session settings validated via Pydantic."""

    uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", ""))
    username: str = Field(default_factory=lambda: os.getenv("NEO4J_USERNAME", ""))
    password: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))
    database: str = Field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))
    max_connection_lifetime: int = Field(default_factory=lambda: int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", 3600)))
    max_connection_pool_size: int = Field(default_factory=lambda: int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", 50)))
    connection_timeout: float = Field(default_factory=lambda: float(os.getenv("NEO4J_CONNECTION_TIMEOUT", 10.0)))
    connection_acquisition_timeout: float = Field(default_factory=lambda: float(os.getenv("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", 60.0)))
    auto_sync: bool = False

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        if v:
            valid_schemes = ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")
            if not any(v.startswith(scheme) for scheme in valid_schemes):
                raise ValueError(f"Invalid Neo4j URI scheme. Expected one of {valid_schemes}")
        return v

    def is_configured(self) -> bool:
        """Returns True if minimum required connection parameters exist."""
        return bool(self.uri and self.username and self.password)

    def masked_dict(self) -> dict:
        """Returns safe settings representation with password excluded."""
        data = self.model_dump(exclude={"password"})
        data["password_configured"] = bool(self.password)
        return data


system_settings = SystemSettings()
neo4j_settings = Neo4jSettings()

