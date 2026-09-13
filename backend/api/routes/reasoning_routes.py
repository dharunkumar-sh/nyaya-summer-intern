"""
Reasoning routes:
- POST /api/reasoning/deduce: Generates 5-stage Pañcāvayava syllogism and connected proof trace DAG.
- POST /api/reasoning/validate-fallacies: Executes 5 Hetvābhāsa fallacy checks and 5-point semantic validation.
- POST /api/reasoning/proof-trace: Generates and validates end-to-end graphical proof trace with traceable paths.
"""
from flask import Blueprint, request
from api.responses import success_response, error_response
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.validator import DefeasibleValidator
from reasoning.proof_trace import ProofTraceGenerator
from services.proof_trace_service import proof_trace_service
from core.exceptions import InvalidQueryError
from core.logger import logger

reasoning_bp = Blueprint("reasoning", __name__, url_prefix="/api/reasoning")


@reasoning_bp.route("/deduce", methods=["POST"])
def deduce_reasoning():
    """Generates 5-stage Pañcāvayava syllogism and connected proof trace for a given query and Tiṇai."""
    try:
        data = request.get_json(silent=True) or {}
        query_text = data.get("queryText") or data.get("query") or ""
        tinai = data.get("tinai") or "Kuṟiñci"
        evidence_items = data.get("evidenceItems") or data.get("evidence") or data.get("evidence_items")

        stages = NyayaReasoner.synthesize_deduction(
            query_text=query_text,
            tinai=tinai,
            evidence_items=evidence_items,
        )

        proof_nodes = ProofTraceGenerator.generate_trace_nodes(
            tinai=tinai,
            evidence_items=evidence_items,
        )
        proof_edges = ProofTraceGenerator.generate_directed_edges(
            nodes=proof_nodes,
            tinai=tinai,
        )
        trace_steps = [s.to_dict() for s in ProofTraceGenerator.generate_trace_steps(proof_nodes)]

        return success_response(
            data={
                "tinai": tinai,
                "reasoningStages": stages,
                "proofNodes": proof_nodes,
                "proofEdges": proof_edges,
                "traceSteps": trace_steps,
            },
            message="Pañcāvayava deduction synthesized successfully",
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/deduce: {e}", exc_info=True)
        return error_response(str(e), error_code="DEDUCTION_FAILED", status_code=500)


@reasoning_bp.route("/validate-fallacies", methods=["GET", "POST"])
def validate_fallacies():
    """Executes the 5 Hetvābhāsa fallacy checks and 5-point semantic validation."""
    try:
        if request.method == "GET":
            tinai = request.args.get("tinai", "Kuṟiñci")
            evidence_count = int(request.args.get("evidenceCount", request.args.get("evidence_count", 5)))
            evidence_items = None
        else:
            data = request.get_json(silent=True) or {}
            tinai = data.get("tinai", "Kuṟiñci")
            evidence_count = int(data.get("evidenceCount", data.get("evidence_count", 5)))
            evidence_items = data.get("evidence_items") or data.get("evidence")

        validation = DefeasibleValidator.validate_deduction(
            tinai=tinai,
            evidence_count=evidence_count,
            evidence_items=evidence_items,
        )

        return success_response(data=validation, message="Hetvābhāsa validation completed")
    except Exception as e:
        logger.error(f"Error in /api/reasoning/validate-fallacies: {e}", exc_info=True)
        return error_response(str(e), error_code="VALIDATION_FAILED", status_code=500)


@reasoning_bp.route("/proof-trace", methods=["POST"])
def get_proof_trace():
    """
    Dedicated endpoint generating machine-readable graphical proof trace.
    Returns traceable paths from evidence to conclusion, or an explicit
    insufficient-evidence state if required verses are missing.
    """
    try:
        data = request.get_json(silent=True) or {}
        query_text = data.get("queryText") or data.get("query") or ""
        tinai = data.get("tinai")
        evidence_items = data.get("evidenceItems") if data.get("evidenceItems") is not None else data.get("evidence_items")
        min_threshold = data.get("minEvidenceThreshold", 2)

        payload = proof_trace_service.generate_proof_trace(
            query_text=query_text,
            tinai=tinai,
            evidence_items=evidence_items,
            min_evidence_threshold=int(min_threshold),
        )

        return success_response(
            data=payload.to_dict(),
            message="Proof trace generated successfully" if payload.is_valid else "Insufficient evidence state detected",
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/proof-trace: {e}", exc_info=True)
        return error_response(str(e), error_code="PROOF_TRACE_FAILED", status_code=500)


@reasoning_bp.route("/answer", methods=["POST"])
def get_grounded_answer():
    """
    Primary endpoint for final evidence-grounded answers.
    Executes the full neuro-symbolic reasoning pipeline:
    hybrid retrieval -> premise extraction -> rule subsumption -> Pañcāvayava deduction ->
    fallacy verification -> epistemic verdict synthesis.
    Strictly non-hallucinatory: outputs grounded verdicts without fabricating facts.
    """
    from services.reasoning_service import reasoning_service

    data = request.get_json(silent=True) or {}
    query_text = (data.get("queryText") or data.get("query") or "").strip()

    if not query_text:
        return error_response(
            "Parameter 'queryText' cannot be empty",
            error_code="INVALID_QUERY",
            status_code=422,
        )
    if len(query_text) > 500:
        return error_response(
            "Query length exceeds maximum limit of 500 characters",
            error_code="QUERY_TOO_LONG",
            status_code=400,
        )

    try:
        depth = int(data.get("depth", 2))
        depth = min(max(depth, 1), 5)  # Enforce 1-5 limit
    except (ValueError, TypeError):
        depth = 2

    focus = data.get("focus", "Relationship")

    try:
        result = reasoning_service.execute_reasoning_pipeline(
            query_text=query_text,
            depth=depth,
            focus=focus,
        )

        return success_response(
            data=result,
            message="Evidence-grounded epistemic answer synthesized successfully",
            meta={
                "query": query_text,
                "depth": depth,
                "detectedTinai": result.get("detectedTinai"),
                "insufficientEvidence": result.get("insufficientEvidence", False),
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/answer: {e}", exc_info=True)
        return error_response(str(e), error_code="ANSWER_SYNTHESIS_FAILED", status_code=500)
