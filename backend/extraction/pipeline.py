"""
Semantic Extraction Pipeline for Classical Tamil Literary Knowledge.

Orchestrates EntityExtractor, RelationExtractor, EventExtractor,
and ContextExtractor into a single cohesive pipeline that produces
fully-provenance-tagged ExtractionResult objects.

Usage
-----
    from extraction.pipeline import extraction_pipeline

    result = extraction_pipeline.extract(passage)
    results = extraction_pipeline.extract_batch(passages)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.logger import logger
from .entity_extractor import EntityExtractor
from .relation_extractor import RelationExtractor
from .event_extractor import EventExtractor
from .context_extractor import ContextExtractor
from .models import ExtractionResult


class SemanticExtractionPipeline:
    """
    Orchestrates the four extraction stages in sequence.

    Stage order
    -----------
    1. EntityExtractor  — lexicon scan + corpus entity promotion
    2. RelationExtractor — corpus triples + co-occurrence + pattern rules
    3. EventExtractor   — poetic situation + structured Event
    4. ContextExtractor — genre, speaker, situation, temporal markers

    Every extracted fact retains:
        source_id, source_text, confidence, extraction_method,
        validation_status
    """

    # ------------------------------------------------------------------
    # Single passage extraction
    # ------------------------------------------------------------------

    def extract(self, passage: Dict[str, Any]) -> ExtractionResult:
        """
        Extract knowledge from a single ProcessedPassage dict.

        Accepts either:
        - A full ProcessedPassage (from preprocessing pipeline)
        - A raw corpus sūtra dict (from CorpusLoader)

        Returns an ExtractionResult with entities, relations, events,
        context, and extraction_summary.
        """
        # ---- Resolve passage fields ----
        passage_id  = passage.get("document_id") or passage.get("id", "")
        original    = passage.get("original_text") or passage.get("tamil_text", "")
        normalized  = passage.get("normalized_text") or original
        tinai       = (
            passage.get("metadata", {}).get("tinai")
            or passage.get("tinai", "General")
        )
        corpus_triples = (
            passage.get("metadata", {}).get("triples")
            or passage.get("triples", [])
        )
        corpus_entities = (
            passage.get("metadata", {}).get("entities")
            or passage.get("entities", [])
        )

        text_for_extraction = normalized or original

        # ---- Stage 1: Entities ----
        raw_entities = EntityExtractor.extract(
            text=text_for_extraction,
            source_id=passage_id,
            source_text=original,
            supplemental_entities=corpus_entities,
        )
        entity_dicts = [e.to_dict() for e in raw_entities]

        # ---- Stage 2: Relations ----
        raw_relations = RelationExtractor.extract(
            text=text_for_extraction,
            entities=entity_dicts,
            corpus_triples=corpus_triples,
            source_id=passage_id,
            source_text=original,
        )

        # ---- Stage 3: Events ----
        raw_events = EventExtractor.extract(
            text=text_for_extraction,
            tinai=tinai,
            source_id=passage_id,
            source_text=original,
        )

        # ---- Stage 4: Context ----
        context = ContextExtractor.extract_context(
            text=text_for_extraction,
            tinai=tinai,
        )

        result = ExtractionResult(
            passage_id=passage_id,
            source_text=original,
            entities=raw_entities,
            relations=raw_relations,
            events=raw_events,
            context=context,
        )

        logger.debug(
            f"Extracted passage '{passage_id}': "
            f"{len(raw_entities)} entities, {len(raw_relations)} relations, "
            f"{len(raw_events)} events"
        )
        return result

    # ------------------------------------------------------------------
    # Batch extraction
    # ------------------------------------------------------------------

    def extract_batch(
        self,
        passages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Processes a list of passages (ProcessedPassage or sūtra dicts).
        Returns a list of ExtractionResult dicts with a summary appended.
        """
        results = []
        failed  = 0

        for passage in passages:
            pid = passage.get("document_id") or passage.get("id", "<unknown>")
            try:
                result = self.extract(passage)
                results.append(result.to_dict())
            except Exception as exc:
                logger.warning(f"Extraction failed for passage '{pid}': {exc}")
                failed += 1

        logger.info(
            f"Batch extraction: {len(results)} succeeded, {failed} failed"
        )
        return results

    # ------------------------------------------------------------------
    # Convenience: extract by sūtra ID using CorpusLoader
    # ------------------------------------------------------------------

    def extract_from_sutra_id(self, sutra_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads a sūtra by ID from the corpus and runs full extraction.
        Returns None if the sūtra is not found.
        """
        from ingestion.corpus_loader import corpus_loader
        sutra = corpus_loader.get_sutra_by_id(sutra_id)
        if not sutra:
            return None
        return self.extract(sutra).to_dict()


# Singleton pipeline instance
extraction_pipeline = SemanticExtractionPipeline()
