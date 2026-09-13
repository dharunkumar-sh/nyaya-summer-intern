"""
Standardized JSON response formatting helpers for REST API.
Guarantees consistent payload envelopes across all endpoints.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from flask import jsonify, Response


def success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> tuple[Response, int]:
    """Formats a successful JSON API response."""
    payload = {
        "success": True,
        "data": data,
        "message": message,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    return jsonify(payload), status_code


def error_response(
    message: str = "An unexpected error occurred",
    error_code: str = "SERVER_ERROR",
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> tuple[Response, int]:
    """Formats an error JSON API response."""
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
    }
    return jsonify(payload), status_code
