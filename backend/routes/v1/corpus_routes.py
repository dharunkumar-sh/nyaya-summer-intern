"""
Version 1 API Endpoints for Classical Tamil Corpus (Tolkāppiyam).
Provides REST endpoints for exploring atikārams, iyals, sūtras, tiṇai poetics, and statistics.
"""
from __future__ import annotations

from flask import Blueprint, request

from schemas.corpus_schemas import SutraFilterParams
from services.corpus_service import get_corpus_service
from utilities.response_envelope import api_success, api_paginated

v1_corpus_bp = Blueprint("v1_corpus", __name__, url_prefix="/corpus")


@v1_corpus_bp.route("/info", methods=["GET"])
def get_corpus_info():
    """Returns canonical Tolkāppiyam metadata, book counts, and editions."""
    service = get_corpus_service()
    metadata = service.get_metadata()
    return api_success(
        data=metadata,
        message="Corpus metadata retrieved successfully",
        meta={"corpus_name": metadata.name, "total_sutras": metadata.total_sutras},
    )


@v1_corpus_bp.route("/atikarams", methods=["GET"])
def get_atikarams():
    """Lists the three canonical atikārams (books) of Tolkāppiyam."""
    service = get_corpus_service()
    atikarams = service.get_atikarams()
    return api_success(
        data=atikarams,
        message="Atikārams retrieved successfully",
        meta={"count": len(atikarams)},
    )


@v1_corpus_bp.route("/atikarams/<atikaram_id>", methods=["GET"])
def get_atikaram_detail(atikaram_id: str):
    """Retrieves specific atikāram book details by ID or canonical name."""
    service = get_corpus_service()
    atikaram = service.get_atikaram(atikaram_id)
    return api_success(
        data=atikaram,
        message=f"Atikāram '{atikaram.name}' details retrieved successfully",
    )


@v1_corpus_bp.route("/iyals", methods=["GET"])
def get_iyals():
    """Lists iyals (chapters), optionally filtered by atikāram."""
    atikaram_filter = request.args.get("atikaram")
    service = get_corpus_service()
    iyals = service.get_iyals(atikaram_id=atikaram_filter)
    return api_success(
        data=iyals,
        message="Iyals retrieved successfully",
        meta={"count": len(iyals), "filter": atikaram_filter},
    )


@v1_corpus_bp.route("/sutras", methods=["GET"])
def get_sutras():
    """
    Retrieves paginated sūtras with optional filtering by atikāram, iyal,
    tiṇai landscape, category, and free-text search.
    """
    params = SutraFilterParams(
        atikaram=request.args.get("atikaram"),
        iyal=request.args.get("iyal"),
        tinai=request.args.get("tinai"),
        category=request.args.get("category"),
        search=request.args.get("search") or request.args.get("q"),
        page=int(request.args.get("page", 1)),
        page_size=int(request.args.get("page_size", 20)),
    )

    service = get_corpus_service()
    sutras, pagination_meta = service.get_sutras(
        atikaram=params.atikaram,
        iyal=params.iyal,
        tinai=params.tinai,
        category=params.category,
        search=params.search,
        page=params.page,
        page_size=params.page_size,
    )

    return api_paginated(
        items=sutras,
        pagination_meta=pagination_meta,
        message="Sūtras retrieved successfully",
        extra_meta={
            "filters": {
                "atikaram": params.atikaram,
                "iyal": params.iyal,
                "tinai": params.tinai,
                "category": params.category,
                "search": params.search,
            }
        },
    )


@v1_corpus_bp.route("/sutras/<sutra_id>", methods=["GET"])
def get_sutra_by_id(sutra_id: str):
    """Retrieves an individual sūtra by unique identifier."""
    service = get_corpus_service()
    sutra = service.get_sutra_by_id(sutra_id)
    return api_success(
        data=sutra,
        message=f"Sūtra '{sutra.id}' retrieved successfully",
    )


@v1_corpus_bp.route("/tinai", methods=["GET"])
def get_tinai_landscapes():
    """Returns the five Classical Tamil Tiṇai landscapes and associated counts."""
    service = get_corpus_service()
    landscapes = service.get_tinai_landscapes()
    return api_success(
        data=landscapes,
        message="Tiṇai landscapes retrieved successfully",
        meta={"count": len(landscapes)},
    )


@v1_corpus_bp.route("/statistics", methods=["GET"])
def get_corpus_statistics():
    """Returns structural breakdowns and analytics across the corpus."""
    service = get_corpus_service()
    stats = service.get_statistics()
    return api_success(
        data=stats,
        message="Corpus statistics computed successfully",
    )
