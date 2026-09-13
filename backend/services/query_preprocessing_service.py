"""
Query Preprocessing Service re-export for service layer convenience.
"""
from query.query_preprocessor import (
    QueryPreprocessingService,
    query_preprocessor,
    ProcessedQuery,
    LITERARY_TERMINOLOGY,
)

__all__ = [
    "QueryPreprocessingService",
    "query_preprocessor",
    "ProcessedQuery",
    "LITERARY_TERMINOLOGY",
]
