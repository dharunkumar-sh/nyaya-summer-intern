"""
Schemas Package for Classical Tamil Corpus and Literature APIs.
"""
from schemas.corpus_schemas import (
    PaginationMeta,
    SutraFilterParams,
    SutraResponse,
    PaginatedSutrasResponse,
    AtikaramSummaryResponse,
    IyalSummaryResponse,
    CorpusInfoResponse,
    TinaiLandscapeResponse,
    CorpusStatisticsResponse,
    HierarchyNodeResponse,
    LiteratureWorkResponse,
    ApiResponseEnvelope,
)

__all__ = [
    "PaginationMeta",
    "SutraFilterParams",
    "SutraResponse",
    "PaginatedSutrasResponse",
    "AtikaramSummaryResponse",
    "IyalSummaryResponse",
    "CorpusInfoResponse",
    "TinaiLandscapeResponse",
    "CorpusStatisticsResponse",
    "HierarchyNodeResponse",
    "LiteratureWorkResponse",
    "ApiResponseEnvelope",
]
