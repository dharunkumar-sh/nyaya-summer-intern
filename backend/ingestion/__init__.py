"""Ingestion package for loading, validating, and managing Tolkāppiyam corpus."""
from .corpus_loader import CorpusLoader
from .dataset_validator import DatasetValidator
from .metadata_manager import MetadataManager
from .dataset_ingestion_service import DatasetIngestionService, ingestion_service
from .kg_ingestion_pipeline import KGIngestionPipeline, kg_ingestion_pipeline

__all__ = [
    "CorpusLoader",
    "DatasetValidator",
    "MetadataManager",
    "DatasetIngestionService",
    "ingestion_service",
    "KGIngestionPipeline",
    "kg_ingestion_pipeline",
]
