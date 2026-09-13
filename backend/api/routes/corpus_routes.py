"""
Corpus routes:
- GET  /api/corpus/info           (Metadata and Atikāram breakdown)
- GET  /api/corpus/statistics     (Dataset profiling and distributions)
- GET  /api/corpus/literature     (Literature corpus level information L0)
- GET  /api/corpus/works          (Canonical treatises / works L1)
- GET  /api/corpus/works/<id>     (Work details by identifier)
- GET  /api/corpus/sections       (Sections / Atikārams / Iyals L2)
- GET  /api/corpus/sections/<id>  (Section details by identifier)
- GET  /api/corpus/passages       (Paginated canonical literary passages / sūtras L3)
- GET  /api/corpus/passages/<id>  (Single passage details by ID L3)
- GET  /api/corpus/sutras         (Backward-compatible sūtra listing)
- GET  /api/corpus/sutras/<id>    (Backward-compatible single sūtra retrieval)
- POST /api/corpus/validate       (Dataset validation)
- POST /api/corpus/preprocess     (Tamil literary text preprocessing)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from flask import Blueprint, request

from api.responses import success_response, error_response
from ingestion.corpus_loader import corpus_loader
from ingestion.metadata_manager import MetadataManager
from ingestion.dataset_ingestion_service import ingestion_service
from preprocessing.pipeline import preprocessing_pipeline
from core.logger import logger

corpus_bp = Blueprint("corpus", __name__, url_prefix="/api/corpus")


@corpus_bp.route("/info", methods=["GET"])
def get_corpus_info():
    """Returns metadata and Atikāram breakdown of the indexed corpus."""
    summary = MetadataManager.get_summary()
    return success_response(data=summary, message="Corpus metadata retrieved")


@corpus_bp.route("/statistics", methods=["GET"])
def get_dataset_statistics():
    """Returns dataset profiling statistics for Ontology and Query_Mapping."""
    try:
        stats = ingestion_service.get_statistics()
        return success_response(
            data=stats,
            message="Dataset profiling statistics retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error computing dataset statistics: {e}", exc_info=True)
        return error_response(
            message=f"Failed to retrieve dataset statistics: {str(e)}",
            error_code="STATISTICS_ERROR",
            status_code=500,
        )


@corpus_bp.route("/literature", methods=["GET"])
def get_literature_info():
    """Returns top-level literature corpus metadata (Hierarchy Level L0)."""
    meta = corpus_loader.get_metadata()
    data = {
        "id": "sangam-literature",
        "hierarchy_level": "L0",
        "title": "Classical Tamil Literature (சங்க இலக்கியமும் தொல்காப்பியமும்)",
        "language": "Classical Tamil (தமிழ்)",
        "script": "Tamil (தமிழ் எழுத்து)",
        "period": "Early Historic / Sangam Era (கி.மு. 300 - கி.பி. 300)",
        "primary_treatise": meta.get("name", "Tolkāppiyam"),
        "total_works": 1,
        "description": "Foundational corpus of Classical Tamil grammar, poetics, semiotics, and prosody.",
    }
    return success_response(data=data, message="Literature corpus information retrieved")


@corpus_bp.route("/works", methods=["GET"])
def list_works():
    """Lists canonical literary treatises / monographs (Hierarchy Level L1)."""
    meta = corpus_loader.get_metadata()
    all_sutras = corpus_loader.get_all_sutras()

    works = [
        {
            "id": "tolkappiyam",
            "hierarchy_level": "L1",
            "name": meta.get("name", "Tolkāppiyam"),
            "tamil_name": "தொல்காப்பியம்",
            "author": meta.get("author", "Tolkāppiyar (தொல்காப்பியர்)"),
            "sections_count": 3,
            "canonical_sutras_count": len(all_sutras),
            "primary_subject": "Tamil Grammar, Semiotics, Poetics, and Ontology",
            "structure": ["Eḻuttatikāram (Phonology)", "Collatikāram (Morphology/Syntax)", "Poruḷatikāram (Poetics/Semiotics)"],
            "active_section": "Poruḷatikāram (பொருளதிகாரம்)",
        }
    ]
    return success_response(data=works, message=f"Retrieved {len(works)} canonical work(s)")


@corpus_bp.route("/works/<string:work_id>", methods=["GET"])
def get_work_detail(work_id: str):
    """Retrieves single canonical work details."""
    norm_id = work_id.lower().strip()
    if norm_id not in ["tolkappiyam", "tol", "work-tolkappiyam"]:
        return error_response(
            message=f"Work '{work_id}' not found in canonical corpus",
            error_code="WORK_NOT_FOUND",
            status_code=404,
        )

    meta = corpus_loader.get_metadata()
    all_sutras = corpus_loader.get_all_sutras()
    work = {
        "id": "tolkappiyam",
        "hierarchy_level": "L1",
        "name": meta.get("name", "Tolkāppiyam"),
        "tamil_name": "தொல்காப்பியம்",
        "author": meta.get("author", "Tolkāppiyar (தொல்காப்பியர்)"),
        "sections_count": 3,
        "canonical_sutras_count": len(all_sutras),
        "primary_subject": "Tamil Grammar, Semiotics, Poetics, and Ontology",
        "sections": [
            {"name": "Eḻuttatikāram", "focus": "Phonetics & Phonology"},
            {"name": "Collatikāram", "focus": "Morphology & Syntax"},
            {"name": "Poruḷatikāram", "focus": "Poetics, Tiṇai Semiotics & Psychology"},
        ],
    }
    return success_response(data=work, message="Retrieved canonical work details")


@corpus_bp.route("/sections", methods=["GET"])
def list_sections():
    """Lists sections / Atikārams / Iyals (Hierarchy Level L2)."""
    all_sutras = corpus_loader.get_all_sutras()
    meta = corpus_loader.get_metadata()
    books = meta.get("books", [])
    parent_filter = request.args.get("parent_atikaram") or request.args.get("atikaram") or request.args.get("book")

    # Aggregate chapters/iyals from active sūtras
    active_chapter_counts: Dict[str, int] = {}
    for s in all_sutras:
        ch = s.get("chapter") or s.get("iyal") or s.get("atikaram", "Poruḷatikāram")
        active_chapter_counts[ch] = active_chapter_counts.get(ch, 0) + 1

    sections = []
    seen_ids = set()

    # First add from canonical books definition if available
    for b in books:
        b_name = b.get("name", "")
        b_clean = b_name.split(" ")[0] if " " in b_name else b_name
        b_iyals = b.get("iyals", [])
        for iyal in b_iyals:
            norm_id = "sec-" + iyal.lower().replace(" ", "-").replace("ḷ", "l").replace("ā", "a").replace("ṭ", "t").replace("ṟ", "r").replace("ṉ", "n").replace("ṅ", "ng")
            count = active_chapter_counts.get(iyal, 0)
            seen_ids.add(norm_id)
            sections.append({
                "id": norm_id,
                "hierarchy_level": "L2",
                "name": iyal,
                "work": "Tolkāppiyam",
                "parent_atikaram": b_clean,
                "parent_book_id": b.get("id", ""),
                "sutras_count": count,
                "focus": b.get("english", "Canonical Chapter"),
            })

    # Add any remaining chapters from active sūtras not in books
    for ch_name, count in sorted(active_chapter_counts.items()):
        norm_id = "sec-" + ch_name.lower().replace(" ", "-").replace("ḷ", "l").replace("ā", "a").replace("ṭ", "t").replace("ṟ", "r").replace("ṉ", "n").replace("ṅ", "ng")
        if norm_id not in seen_ids:
            seen_ids.add(norm_id)
            sections.append({
                "id": norm_id,
                "hierarchy_level": "L2",
                "name": ch_name,
                "work": "Tolkāppiyam",
                "parent_atikaram": "Poruḷatikāram",
                "parent_book_id": "porul",
                "sutras_count": count,
                "focus": "Akattiṇai (Interior Poetics)" if "aka" in ch_name.lower() else "Meyppāṭu (Aesthetic Sentiment)",
            })

    if parent_filter and parent_filter.lower() != "all":
        p_lower = parent_filter.lower()
        sections = [
            sec for sec in sections
            if p_lower in sec["parent_atikaram"].lower() or p_lower in sec.get("parent_book_id", "").lower()
        ]

    return success_response(
        data=sections,
        message=f"Retrieved {len(sections)} sections/chapters",
        meta={"total": len(sections)},
    )


@corpus_bp.route("/sections/<string:section_id>", methods=["GET"])
def get_section_detail(section_id: str):
    """Retrieves single section details by identifier."""
    all_sutras = corpus_loader.get_all_sutras()
    norm_id = section_id.lower().strip()

    matching_sutras = []
    sec_name = None
    for s in all_sutras:
        ch = s.get("chapter") or s.get("iyal") or s.get("atikaram", "")
        ch_norm = ch.lower().replace(" ", "-").replace("ḷ", "l").replace("ā", "a").replace("ṭ", "t")
        if norm_id in ch_norm or ch_norm in norm_id or norm_id == s.get("atikaram", "").lower():
            matching_sutras.append(s)
            sec_name = ch

    if not matching_sutras:
        return error_response(
            message=f"Section '{section_id}' not found",
            error_code="SECTION_NOT_FOUND",
            status_code=404,
        )

    data = {
        "id": section_id,
        "hierarchy_level": "L2",
        "name": sec_name or section_id,
        "work": "Tolkāppiyam",
        "parent_atikaram": "Poruḷatikāram",
        "sutras_count": len(matching_sutras),
        "sutra_ids": [s["id"] for s in matching_sutras],
    }
    return success_response(data=data, message=f"Retrieved section details for '{section_id}'")


@corpus_bp.route("/passages", methods=["GET"])
def list_passages():
    """
    Lists canonical passages / sūtras (Hierarchy Level L3) with filtering and pagination.

    Query parameters:
      tinai: string (optional, e.g. 'Kuṟiñci', 'Mullai')
      section: string (optional Atikāram filter)
      chapter: string (optional Iyal filter)
      work: string (optional work filter)
      q / query / search: string (optional search query across text, translations, transliteration, id)
      page: integer (optional, default: 1, min: 1)
      page_size / pageSize: integer (optional, default: 10, min: 1, max: 50)
    """
    tinai_filter = request.args.get("tinai")
    section_filter = request.args.get("section") or request.args.get("atikaram")
    chapter_filter = request.args.get("chapter") or request.args.get("iyal")
    work_filter = request.args.get("work")
    query_filter = request.args.get("q") or request.args.get("query") or request.args.get("search")

    try:
        page_arg = request.args.get("page", 1)
        page_size_arg = request.args.get("page_size") or request.args.get("pageSize") or 10
        page = max(1, int(page_arg))
        page_size = min(50, max(1, int(page_size_arg)))
    except (ValueError, TypeError):
        return error_response("Parameters 'page' and 'page_size' must be valid integers", error_code="INVALID_PAGINATION", status_code=400)

    all_sutras = corpus_loader.get_all_sutras()
    filtered = all_sutras

    if work_filter and work_filter.lower() != "all":
        filtered = [s for s in filtered if work_filter.lower() in s.get("work", "Tolkāppiyam").lower()]

    if tinai_filter and tinai_filter.lower() != "all":
        filtered = [s for s in filtered if s.get("tinai", "").lower() == tinai_filter.lower()]

    if section_filter and section_filter.lower() != "all":
        filtered = [
            s for s in filtered
            if section_filter.lower() in s.get("atikaram", "").lower()
            or section_filter.lower() in s.get("section", "").lower()
            or section_filter.lower() in s.get("chapter", "").lower()
        ]

    if chapter_filter and chapter_filter.lower() != "all":
        filtered = [
            s for s in filtered
            if chapter_filter.lower() in s.get("chapter", "").lower()
            or chapter_filter.lower() in s.get("iyal", "").lower()
        ]

    if query_filter:
        q_norm = query_filter.lower().strip()
        filtered = [
            s for s in filtered
            if q_norm in s.get("tamil_text", "").lower()
            or q_norm in s.get("english_translation", "").lower()
            or q_norm in s.get("translation", "").lower()
            or q_norm in s.get("transliteration", "").lower()
            or q_norm in s.get("id", "").lower()
            or str(s.get("sutra_number", "")) == q_norm
            or any(q_norm in str(e).lower() for e in s.get("entities", []))
            or any(q_norm in str(c).lower() for c in s.get("concepts", []))
        ]

    total = len(filtered)
    total_pages = max(1, math.ceil(total / page_size))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_items = filtered[start_idx:end_idx]

    pagination = {
        "page": page,
        "page_size": page_size,
        "pageSize": page_size,
        "total": total,
        "total_pages": total_pages,
        "totalPages": total_pages,
        "hasMore": page < total_pages,
    }

    return success_response(
        data=paged_items,
        message=f"Retrieved {len(paged_items)} passage(s) (page {page} of {total_pages})",
        meta={
            **pagination,
            "tinai_filter": tinai_filter,
            "section_filter": section_filter,
            "chapter_filter": chapter_filter,
            "query_filter": query_filter,
            "work_filter": work_filter,
        },
    )


@corpus_bp.route("/passages/<string:passage_id>", methods=["GET"])
def get_passage_detail(passage_id: str):
    """Retrieves single canonical passage by its deterministic identifier (e.g. tol-porul-akam-003)."""
    sutra = corpus_loader.get_sutra_by_id(passage_id)
    if not sutra:
        return error_response(
            f"Passage '{passage_id}' not found in canonical corpus",
            error_code="PASSAGE_NOT_FOUND",
            status_code=404,
        )

    return success_response(data=sutra, message=f"Retrieved passage '{passage_id}'")


@corpus_bp.route("/sutras", methods=["GET"])
def list_sutras():
    """Backward-compatible alias for /passages."""
    return list_passages()


@corpus_bp.route("/sutras/<string:sutra_id>", methods=["GET"])
def get_sutra_detail(sutra_id: str):
    """Backward-compatible alias for /passages/<id>."""
    return get_passage_detail(sutra_id)


@corpus_bp.route("/validate", methods=["POST"])
def validate_datasets():
    """Executes on-demand validation on Ontology and/or Query_Mapping datasets."""
    body = request.get_json(silent=True) or {}
    dataset_name = body.get("dataset_name", "all").lower().strip()

    valid_names = {"all", "ontology", "query_mapping"}
    if dataset_name not in valid_names:
        return error_response(
            message=f"Invalid dataset '{dataset_name}'. Supported: 'all', 'ontology', 'query_mapping'",
            error_code="INVALID_DATASET_NAME",
            status_code=400,
        )

    try:
        result = ingestion_service.validate_datasets(dataset_name=dataset_name)
        return success_response(
            data=result,
            message=f"Dataset validation completed ({dataset_name})",
        )
    except Exception as e:
        logger.error(f"Error executing dataset validation: {e}", exc_info=True)
        return error_response(
            message=f"Dataset validation failed: {str(e)}",
            error_code="VALIDATION_ERROR",
            status_code=500,
        )


@corpus_bp.route("/preprocess", methods=["POST"])
def preprocess_corpus():
    """
    Triggers the Tamil literary text preprocessing pipeline.
    """
    body = request.get_json(silent=True) or {}
    sutra_id = body.get("sutra_id")

    try:
        if sutra_id:
            sutra = corpus_loader.get_sutra_by_id(sutra_id)
            if not sutra:
                return error_response(
                    f"Sūtra '{sutra_id}' not found",
                    error_code="SUTRA_NOT_FOUND",
                    status_code=404,
                )
            result = preprocessing_pipeline.run_single(sutra)
            return success_response(
                data=result,
                message=f"Sūtra '{sutra_id}' preprocessed successfully",
            )

        all_sutras = corpus_loader.get_all_sutras()
        stats = preprocessing_pipeline.run(all_sutras)
        return success_response(
            data=stats,
            message=(
                f"Preprocessing pipeline complete: "
                f"{stats['processed_count']}/{stats['total_sutras']} sūtras "
                f"processed in {stats['processing_time_ms']} ms"
            ),
        )

    except Exception as exc:
        logger.error(f"Preprocessing pipeline error: {exc}", exc_info=True)
        return error_response(
            message=f"Preprocessing failed: {str(exc)}",
            error_code="PREPROCESSING_ERROR",
            status_code=500,
        )
