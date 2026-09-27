"""
Base Parser Interface and Data Transfer Classes for Classical Tamil Literature Ingestion.
"""
from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from models.corpus import LiteratureWork, LiterarySection, LiteraryPassage, Commentary, VerseLine


def generate_stable_slug(text: str, fallback: str = "item") -> str:
    """
    Generates deterministic, URL-friendly slug supporting Latin transliterations and clean IDs.
    """
    if not text:
        return fallback
    # Strip parenthetical descriptions e.g. 'Tolkāppiyam (தொல்காப்பியம்)' -> 'Tolkāppiyam'
    text_clean = re.sub(r"\(.*?\)", "", text).strip()
    cleaned = unicodedata.normalize("NFKD", text_clean).strip().lower()
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", cleaned).strip("-")
    return slug or fallback


@dataclass
class ParsedLiteratureData:
    """Encapsulates parsed literary entities ready for ingestion validation and persistence."""
    work: Optional[LiteratureWork] = None
    sections: List[LiterarySection] = field(default_factory=list)
    passages: List[LiteraryPassage] = field(default_factory=list)
    commentaries: List[Commentary] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and (self.work is not None or len(self.passages) > 0)


class BaseLiteratureParser(ABC):
    """Abstract base class for all file format literature parsers."""

    @abstractmethod
    def parse(
        self,
        content: str | bytes,
        filename: Optional[str] = None,
        default_work_id: Optional[str] = None,
        default_section_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ParsedLiteratureData:
        """
        Parses raw text or byte stream into structured ParsedLiteratureData.
        Must preserve original text without destructive transformation.
        """
        pass
