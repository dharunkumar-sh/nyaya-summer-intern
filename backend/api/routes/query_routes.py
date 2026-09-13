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

