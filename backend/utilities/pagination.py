"""
Pagination Utility for Collections and Query Results.
Provides consistent slice calculations and metadata generation.
"""
from __future__ import annotations

import math
from typing import Sequence, TypeVar, Tuple, List
from schemas.corpus_schemas import PaginationMeta

T = TypeVar("T")


def paginate_items(
    items: Sequence[T],
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[T], PaginationMeta]:
    """
    Slices an in-memory sequence of items according to 1-indexed pagination parameters
    and generates standardized PaginationMeta.
    """
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / page_size))

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    sliced_items = list(items[start_idx:end_idx])

    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return sliced_items, meta
