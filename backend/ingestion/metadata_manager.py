"""
Metadata manager tracking Atikāram breakdown, sūtra indexing, and corpus health.
"""
from typing import Dict, Any
from .corpus_loader import corpus_loader


class MetadataManager:
    """Provides high-level corpus metrics and status report."""

    @staticmethod
    def get_summary() -> Dict[str, Any]:
        """Calculates live corpus stats."""
        meta = corpus_loader.get_metadata()
        sutras = corpus_loader.get_all_sutras()
        triples = corpus_loader.get_all_triples()

        unique_subjects = {t["subject"] for t in triples}
        unique_objects = {t["object"] for t in triples}
        unique_entities = unique_subjects.union(unique_objects)

        active_counts = {"eluttu": 0, "col": 0, "porul": 0}
        for s in sutras:
            at = str(s.get("atikaram", "")).lower()
            if "eluttu" in at or "eḻuttu" in at:
                active_counts["eluttu"] += 1
            elif "col" in at:
                active_counts["col"] += 1
            elif "porul" in at or "poruḷ" in at:
                active_counts["porul"] += 1

        books = []
        for b in meta.get("books", []):
            book_id = b.get("id")
            active_cnt = active_counts.get(book_id, 0)
            canonical_cnt = b.get("sutra_count", 0)
            books.append({
                **b,
                "sutra_count": canonical_cnt,
                "canonical_sutras_count": canonical_cnt,
                "active_sutras_count": active_cnt,
            })

        return {
            "corpus_name": meta.get("name", "Tolkāppiyam"),
            "period": meta.get("period", "Classical Sangam"),
            "total_sutras_canonical": meta.get("total_sutras", 1610),
            "indexed_sutras_active": len(sutras),
            "books_count": meta.get("books_count", 3),
            "books": books,
            "total_relations": len(triples),
            "total_named_entities": len(unique_entities),
            "status": "Ready",
        }
