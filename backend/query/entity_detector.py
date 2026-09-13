"""
Query entity detector extracting Tiṇai concepts, deities, and sūtra references from prompt.
"""
from typing import List, Dict, Any
from extraction.entity_extractor import EntityExtractor


class QueryEntityDetector:
    """Extracts Tiṇai keywords, deities, and poetics concepts from inquiry."""

    @classmethod
    def detect(cls, query: str) -> List[Dict[str, Any]]:
        """Delegates to EntityExtractor and returns entity dicts for downstream use."""
        entities = EntityExtractor.extract(query, source_id="query")
        # Return dicts compatible with downstream consumers (term, tinai, category)
        return [
            {
                "term":           e.canonical_form,
                "transliteration": e.transliteration,
                "category":       e.category.value,
                "tinai":          e.tinai,
            }
            for e in entities
        ]

