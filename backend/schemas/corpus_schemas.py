"""
Pydantic Request and Response Schemas for Classical Tamil Corpus and Literature APIs.
Ensures strict validation, type safety, and automatic OpenAPI schema generation.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

from models.enums import HierarchyLevel
from models.corpus import (
    KnowledgeTriple,
    NyayaMapping,
    TinaiLandscape,
    Atikaram,
)

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata describing paginated collections."""
    page: int = Field(1, description="Current page number (1-indexed)")
    page_size: int = Field(20, description="Number of items per page")
    total_items: int = Field(..., description="Total count of items matching filter")
    total_pages: int = Field(..., description="Total pages available")
    has_next: bool = Field(False, description="True if a subsequent page exists")
    has_prev: bool = Field(False, description="True if a previous page exists")


class SutraFilterParams(BaseModel):
    """Query parameter validation for sūtra retrieval."""
    atikaram: Optional[str] = Field(None, description="Filter by atikaram (e.g. 'porul', 'Poruḷatikāram')")
    iyal: Optional[str] = Field(None, description="Filter by iyal chapter name")
    tinai: Optional[str] = Field(None, description="Filter by tiṇai classification")
    category: Optional[str] = Field(None, description="Filter by category")
    search: Optional[str] = Field(None, description="Full-text query against Tamil verse, transliteration, or translation")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size limit")


class SutraResponse(BaseModel):
    """Serialized Sūtra API representation."""
    id: str
    sutra_number: int
    atikaram: str
    iyal: str
    tamil_text: str
    transliteration: Optional[str] = None
    english_translation: Optional[str] = None
    category: Optional[str] = None
    tinai: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    triples: List[KnowledgeTriple] = Field(default_factory=list)
    nyaya_mapping: Optional[NyayaMapping] = None


class PaginatedSutrasResponse(BaseModel):
    """Paginated collection of sūtras."""
    items: List[SutraResponse]
    pagination: PaginationMeta


class AtikaramSummaryResponse(BaseModel):
    """Summary representation of a major book division."""
    id: str
    name: str
    english: str
    sutra_count: int
    iyals: List[str]


class IyalSummaryResponse(BaseModel):
    """Summary of a specific iyal chapter."""
    name: str
    atikaram: str
    sutra_count: int


class CorpusInfoResponse(BaseModel):
    """Corpus overview metadata."""
    name: str
    period: str
    total_sutras: int
    books_count: int
    books: List[AtikaramSummaryResponse]


class TinaiLandscapeResponse(BaseModel):
    """Poetic landscape details."""
    tinai: str
    landscape: str
    season: str
    time_of_day: str
    deity: str
    primary_sentiment: str
    associated_sutras_count: int


class CorpusStatisticsResponse(BaseModel):
    """High-level corpus structural metrics."""
    total_sutras: int
    books_count: int
    atikaram_breakdown: Dict[str, int]
    tinai_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    indexed_sutras_count: int


class HierarchyNodeResponse(BaseModel):
    """Generic hierarchical node representation for L0 to L3 levels."""
    id: str
    name: str
    level: HierarchyLevel
    description: Optional[str] = None
    children_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LiteratureWorkResponse(BaseModel):
    """Catalog entry for classical literary treatise."""
    work_id: str
    title_tamil: str
    title_english: str
    author: Optional[str] = None
    period: str
    category: str
    total_sections: int
    total_passages: int
    description: Optional[str] = None


class ApiResponseEnvelope(BaseModel, Generic[T]):
    """Standardized API envelope conforming to project conventions."""
    success: bool
    data: Optional[T] = None
    message: str
    error: Optional[Dict[str, Any]] = None
    timestamp: str
    meta: Dict[str, Any] = Field(default_factory=dict)
