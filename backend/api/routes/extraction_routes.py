"""
Extraction routes:
- POST /api/extraction/extract          Extract from a single sutra_id or raw text
- POST /api/extraction/batch            Batch extract from the full corpus
- GET  /api/extraction/relation-types   List controlled relation vocabulary
- GET  /api/extraction/entity-categories List supported entity categories
"""
from flask import Blueprint, request
from api.responses import success_response, error_response
from extraction.pipeline import extraction_pipeline
from extraction.entity_extractor import EntityExtractor
from extraction.relation_extractor import RelationExtractor
from ingestion.corpus_loader import corpus_loader
from core.logger import logger

extraction_bp = Blueprint("extraction", __name__, url_prefix="/api/extraction")


@extraction_bp.route("/extract", methods=["POST"])
def extract_single():
    """
    Extracts entities, relations, events, and context from a single sūtra.

    JSON body (one of):
        {"sutra_id": "tol-porul-akam-005"}
        {"text": "<Tamil text>", "tinai": "Kuṟiñci", "passage_id": "custom-001"}
    """
    body     = request.get_json(silent=True) or {}
    sutra_id = body.get("sutra_id")
    raw_text = body.get("text")

    try:
        if sutra_id:
            result = extraction_pipeline.extract_from_sutra_id(sutra_id)
            if result is None:
                return error_response(
                    f"Sūtra '{sutra_id}' not found",
                    error_code="SUTRA_NOT_FOUND",
                    status_code=404,
                )
            return success_response(
                data=result,
                message=f"Extraction complete for sūtra '{sutra_id}'",
            )

        if raw_text:
            passage = {
                "document_id":     body.get("passage_id", "custom"),
                "original_text":   raw_text,
                "normalized_text": raw_text,
                "tinai":           body.get("tinai", "General"),
                "triples":         [],
                "entities":        [],
            }
            result = extraction_pipeline.extract(passage).to_dict()
            return success_response(
                data=result,
                message="Extraction complete for provided text",
            )

        return error_response(
            "Provide either 'sutra_id' or 'text' in the request body",
            error_code="MISSING_INPUT",
            status_code=400,
        )

    except Exception as exc:
        logger.error(f"Extraction error: {exc}", exc_info=True)
        return error_response(
            f"Extraction failed: {str(exc)}",
            error_code="EXTRACTION_ERROR",
            status_code=500,
        )


@extraction_bp.route("/batch", methods=["POST"])
def extract_batch():
    """
    Batch-extracts knowledge from the entire loaded corpus.

    Optional JSON body:
        {"sutra_ids": ["tol-porul-akam-003", ...]}  → subset extraction
        {}                                           → full corpus
    """
    body      = request.get_json(silent=True) or {}
    sutra_ids = body.get("sutra_ids")

    try:
        if sutra_ids:
            sutras = [
                s for s in corpus_loader.get_all_sutras()
                if s.get("id") in set(sutra_ids)
            ]
        else:
            sutras = corpus_loader.get_all_sutras()

        results = extraction_pipeline.extract_batch(sutras)

        total_entities  = sum(len(r["entities"])  for r in results)
        total_relations = sum(len(r["relations"]) for r in results)
        total_events    = sum(len(r["events"])    for r in results)

        return success_response(
            data={
                "passages":         results,
                "batch_summary": {
                    "total_passages":  len(results),
                    "total_entities":  total_entities,
                    "total_relations": total_relations,
                    "total_events":    total_events,
                },
            },
            message=f"Batch extraction complete: {len(results)} passages processed",
        )

    except Exception as exc:
        logger.error(f"Batch extraction error: {exc}", exc_info=True)
        return error_response(
            f"Batch extraction failed: {str(exc)}",
            error_code="BATCH_EXTRACTION_ERROR",
            status_code=500,
        )


@extraction_bp.route("/relation-types", methods=["GET"])
def get_relation_types():
    """Returns the complete controlled relation vocabulary."""
    return success_response(
        data=RelationExtractor.get_relation_types(),
        message="Controlled relation vocabulary retrieved",
        meta={"total": len(RelationExtractor.get_relation_types())},
    )


@extraction_bp.route("/entity-categories", methods=["GET"])
def get_entity_categories():
    """Returns all supported entity categories with descriptions."""
    return success_response(
        data=EntityExtractor.get_categories(),
        message="Entity categories retrieved",
        meta={"total": len(EntityExtractor.get_categories())},
    )
