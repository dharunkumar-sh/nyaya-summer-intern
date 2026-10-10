"""
Query routes: POST /api/query/analyze and GET /api/query/examples.
"""
from flask import Blueprint, request
from api.responses import success_response, error_response
from services.reasoning_service import reasoning_service
from services.graph_retrieval_service import graph_retrieval_service
from query.query_preprocessor import query_preprocessor
from core.exceptions import InvalidQueryError
from core.logger import logger

query_bp = Blueprint("query", __name__, url_prefix="/api/query")


@query_bp.route("/preprocess", methods=["POST"])
def preprocess_query():
    """
    Dedicated endpoint preprocessing a Classical Tamil or multilingual search query.
    Returns normalized text, detected language/script, preserved literary terms,
    entities, concepts, source references, and channel payloads (BM25, Vector, KG).
    Preserves original query unchanged.
    """
    try:
        data = request.get_json(silent=True) or {}
        query_text = data.get("queryText") or data.get("query")
        focus = data.get("focus", "Relationship")

        if query_text is None:
            query_text = ""

        processed = query_preprocessor.preprocess(query_text, focus=focus)
        return success_response(
            data=processed.to_dict(),
            message="Query preprocessed successfully",
        )
    except Exception as e:
        logger.error(f"Error in /api/query/preprocess: {e}", exc_info=True)
        return error_response(str(e), error_code="PREPROCESS_FAILED", status_code=500)


@query_bp.route("/representation", methods=["POST"])
@query_bp.route("/semantic-representation", methods=["POST"])
def get_semantic_representation():
    """
    Dedicated endpoint returning the common semantic representation for Tamil,
    English, and mixed-language queries over Classical Tamil literature.
    Returns original_query, detected_language, normalized_query,
    identified_entities, identified_concepts, and retrieval_representation.
    """
    try:
        data = request.get_json(silent=True) or {}
        query_text = data.get("queryText") or data.get("query")
        focus = data.get("focus", "Relationship")

        if query_text is None:
            query_text = ""

        processed = query_preprocessor.preprocess(query_text, focus=focus)
        payload = {
            "original_query": processed.original_query,
            "detected_language": processed.detected_language,
            "normalized_query": processed.normalized_query,
            "identified_entities": processed.identified_entities,
            "identified_concepts": processed.identified_concepts,
            "retrieval_representation": processed.retrieval_representation,
        }
        return success_response(
            data=payload,
            message="Common semantic retrieval representation generated successfully",
        )
    except Exception as e:
        logger.error(f"Error in /api/query/representation: {e}", exc_info=True)
        return error_response(str(e), error_code="REPRESENTATION_FAILED", status_code=500)


@query_bp.route("/analyze", methods=["POST"])
def analyze_query():
    """Executes end-to-end neuro-symbolic analysis for an input question."""
    try:
        data = request.get_json(silent=True) or {}
        query_text = data.get("queryText") or data.get("query")

        if not query_text or not query_text.strip():
            raise InvalidQueryError("Inquiry text (queryText) cannot be empty")

        depth = int(data.get("depth", 1))
        focus = data.get("focus", "Relationship")

        result = reasoning_service.execute_reasoning_pipeline(
            query_text=query_text.strip(),
            depth=depth,
            focus=focus,
        )

        return success_response(
            data=result,
            message="Epistemic analysis completed successfully",
        )
    except InvalidQueryError as e:
        return error_response(e.message, error_code="INVALID_QUERY", status_code=422)
    except Exception as e:
        logger.error(f"Error in /api/query/analyze: {e}", exc_info=True)
        return error_response(str(e), error_code="ANALYSIS_FAILED", status_code=500)


@query_bp.route("/examples", methods=["GET"])
def get_canonical_examples():
    """Returns canonical Classical Tamil research inquiries."""
    examples = [
        {
            "id": "ex-1",
            "query": "குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?",
            "translation": "How do primary elements, environmental signifiers, and psychological mood in Kuṟiñci poetics manifest interiority?",
            "queryType": "How / Process",
            "focus": "Relationship",
            "depth": 3,
            "tinai": "Kuṟiñci",
        },
        {
            "id": "ex-2",
            "query": "முல்லை நிலத்தில் கார்காலமும் மாலையும் காதலியின் ஆற்றுதல் ஒழுக்கத்திற்கு ஏதுவாவது ஏன்?",
            "translation": "Why do the monsoon season and evening twilight serve as the inferential ground for patient endurance in Mullai?",
            "queryType": "Why / Justification",
            "focus": "Judgment / Justice",
            "depth": 3,
            "tinai": "Mullai",
        },
        {
            "id": "ex-3",
            "query": "நெய்தல் நிலத்து இரங்கல் உரிப்பொருளுக்குப் பெருமணல் உலகமும் எற்பாடும் எவ்வாறு ஏதுவாகின்றன?",
            "translation": "How do littoral sandy shores and twilight sunset ground melancholic pining in Neytal poetics?",
            "queryType": "How / Process",
            "focus": "Relationship",
            "depth": 4,
            "tinai": "Neytal",
        },
        {
            "id": "ex-4",
            "query": "தொல்காப்பிய அகத்திணை முறைமையில் நிலமும் பொழுதும் இன்றி மனித உள்ளுணர்வு இயங்க முடியுமா?",
            "translation": "In Tolkāppiyam poetics, can human interior emotional states manifest independently of spatio-temporal ground?",
            "queryType": "What / Fact",
            "focus": "General",
            "depth": 2,
            "tinai": "General",
        },
    ]

    return success_response(
        data=examples,
        message="Retrieved canonical research inquiries",
    )


@query_bp.route("/canonical-1000", methods=["GET"])
def get_canonical_1000_queries():
    """
    Returns the curated 1,000 mixed Tamil and English research queries.
    Supports filtering by search keyword, category, difficulty, queryType,
    and pagination (page, limit).
    """
    import json
    from pathlib import Path

    queries_file = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "canonical_1000_queries.json"
    if not queries_file.exists():
        return error_response("Canonical 1000 queries file not found", error_code="FILE_NOT_FOUND", status_code=404)

    try:
        with open(queries_file, "r", encoding="utf-8") as f:
            all_queries = json.load(f)

        # Filters
        search_term = request.args.get("search", "").strip().lower()
        category = request.args.get("category", "").strip().lower()
        difficulty = request.args.get("difficulty", "").strip().lower()
        query_type = request.args.get("queryType", "").strip().lower()
        theme = request.args.get("theme", "").strip().lower()
        is_all = request.args.get("all", "false").lower() in ("true", "1")

        filtered = all_queries

        if search_term:
            filtered = [
                q for q in filtered
                if search_term in q.get("query", "").lower()
                or search_term in q.get("tamilQuery", "").lower()
                or search_term in q.get("title", "").lower()
                or search_term in q.get("tamilConcept", "").lower()
                or search_term in q.get("englishConcept", "").lower()
                or any(search_term in k.lower() for k in q.get("keywords", []))
            ]

        if category and category != "all":
            filtered = [q for q in filtered if category in q.get("category", "").lower()]

        if theme and theme != "all":
            filtered = [q for q in filtered if theme == q.get("theme", "").lower()]

        if difficulty and difficulty != "all":
            filtered = [q for q in filtered if difficulty == q.get("difficulty", "").lower()]

        if query_type and query_type != "all":
            filtered = [q for q in filtered if query_type in q.get("queryType", "").lower()]

        total_matching = len(filtered)

        if is_all:
            return success_response(
                data={
                    "total": total_matching,
                    "queries": filtered,
                },
                message=f"Retrieved all {total_matching} canonical bilingual queries",
            )

        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(100, int(request.args.get("limit", 24))))
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = filtered[start_idx:end_idx]

        return success_response(
            data={
                "total": total_matching,
                "page": page,
                "limit": limit,
                "totalPages": (total_matching + limit - 1) // limit if total_matching > 0 else 1,
                "queries": paginated,
            },
            message=f"Retrieved {len(paginated)} queries (page {page} of {(total_matching + limit - 1) // limit if total_matching > 0 else 1})",
        )
    except Exception as e:
        logger.error(f"Error reading canonical 1000 queries: {e}", exc_info=True)
        return error_response(str(e), error_code="LOAD_FAILED", status_code=500)


@query_bp.route("/canonical-1000/stats", methods=["GET"])
def get_canonical_1000_stats():
    """Returns statistical distribution of the 1,000 mixed Tamil and English queries."""
    import json
    from pathlib import Path
    from collections import Counter

    queries_file = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "canonical_1000_queries.json"
    if not queries_file.exists():
        return error_response("Canonical 1000 queries file not found", error_code="FILE_NOT_FOUND", status_code=404)

    try:
        with open(queries_file, "r", encoding="utf-8") as f:
            all_queries = json.load(f)

        themes = Counter(q.get("theme") for q in all_queries)
        categories = Counter(q.get("category") for q in all_queries)
        difficulties = Counter(q.get("difficulty") for q in all_queries)
        query_types = Counter(q.get("queryType") for q in all_queries)

        return success_response(
            data={
                "total": len(all_queries),
                "themes": dict(themes),
                "categories": dict(categories),
                "difficulties": dict(difficulties),
                "queryTypes": dict(query_types),
            },
            message="Canonical 1000 query statistics retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error computing canonical 1000 query stats: {e}", exc_info=True)
        return error_response(str(e), error_code="STATS_FAILED", status_code=500)



@query_bp.route("/graph-retrieval", methods=["POST"])
def retrieve_grounded_graph():
    """
    Dedicated endpoint retrieving grounded Knowledge Graph context for a structured query.
    Extracts relevant nodes, relationships, passages, evidence paths, and provenance hierarchy.
    Strictly non-generative: Returns structured grounding data only.
    """
    try:
        data = request.get_json(silent=True) or {}
        hop_depth = int(data.get("hopDepth") or data.get("hop_depth") or data.get("depth") or 2)
        max_nodes = int(data.get("maxNodes") or data.get("max_nodes") or 50)
        max_paths = int(data.get("maxPaths") or data.get("max_paths") or 20)

        result = graph_retrieval_service.retrieve_grounded_graph(
            query_input=data,
            hop_depth=hop_depth,
            max_nodes=max_nodes,
            max_paths=max_paths,
        )

        return success_response(
            data=result.to_dict(),
            message="Grounded graph knowledge retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error in /api/query/graph-retrieval: {e}", exc_info=True)
        return error_response(str(e), error_code="GRAPH_RETRIEVAL_FAILED", status_code=500)

