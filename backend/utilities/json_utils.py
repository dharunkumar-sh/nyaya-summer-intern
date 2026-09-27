"""
JSON Serialization and Type Coercion Helpers.
Converts Pydantic models, dates, and sets into JSON-safe dictionaries.
"""
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel


def to_json_safe(obj: Any) -> Any:
    """Recursively converts arbitrary Python objects to JSON-serializable primitives."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    return str(obj)
