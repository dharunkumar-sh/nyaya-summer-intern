"""
Standardized JSON Response Formatting Utilities.
Guarantees consistent schema payloads across all endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Sequence
from flask import jsonify, Response

from utilities.json_utils import to_json_safe
from schemas.corpus_schemas import PaginationMeta


def api_success(
    data: Any = None,
    message: str = "Operation completed successfully",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> Tuple[Response, int]:
    """Formats a successful JSON API response conforming to standard envelope."""
    payload = {
        "success": True,
        "data": to_json_safe(data),
        "message": message,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    return jsonify(payload), status_code


def api_error(
    message: str = "An unexpected error occurred",
    error_code: str = "SERVER_ERROR",
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> Tuple[Response, int]:
    """Formats an error JSON API response conforming to standard envelope."""
    payload = {
        "success": False,
        "data": None,
        "message": message,
        "error": {
            "code": error_code,
            "details": details or {},
        },
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {},
    }
    return jsonify(payload), status_code


def api_paginated(
    items: Sequence[Any],
    pagination_meta: PaginationMeta,
    message: str = "Items retrieved successfully",
    extra_meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> Tuple[Response, int]:
    """Formats a paginated JSON API response with standard pagination metadata."""
    meta = pagination_meta.model_dump()
    if extra_meta:
        meta.update(extra_meta)

    payload = {
        "success": True,
        "data": {
            "items": to_json_safe(items),
            "pagination": pagination_meta.model_dump(),
        },
        "message": message,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
    }
    return jsonify(payload), status_code
