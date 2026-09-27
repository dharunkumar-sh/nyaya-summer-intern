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

        from reasoning.vyapti_identifier import vyapti_identifier
        vyapti_result = vyapti_identifier.identify_vyapti(
            evidence_items=evidence_items,
            tinai=tinai,
            query_text=query_text,
        )
        classification = vyapti_result.get("evidence_classification", {})

        return success_response(
            data={
                "tinai": tinai,
                "status": "established" if vyapti_result.get("is_established") else "Vyāpti unavailable",
                "vyaptiStatus": "grounded" if vyapti_result.get("is_established") else "Vyāpti unavailable",
                "vyaptiIdentification": vyapti_result,
                "candidateVyaptis": vyapti_result.get("candidates", []),
                "establishedVyapti": vyapti_result.get("grounded_vyapti"),
                "caseEvidence": classification.get("case_evidence", []),
                "vyaptiEvidence": classification.get("vyapti_evidence", []),
                "applicationEvidence": classification.get("application_evidence", []),
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


@reasoning_bp.route("/identify-vyapti", methods=["POST"])
def identify_vyapti_endpoint():
    """
    Dedicated endpoint for the Vyāpti identification stage in the Nyāya reasoning pipeline.
    Distinguishes Case Evidence, Vyāpti Evidence, and Application Evidence.
    Enforces that candidate Vyāptis are verified against canonical Neo4j evidence.
    Returns established Vyāpti or explicit 'Vyāpti unavailable' state.
    """
    try:
        from reasoning.vyapti_identifier import vyapti_identifier, VyaptiValidationCriteria

        data = request.get_json(silent=True) or {}
        query_text = (data.get("queryText") or data.get("query") or "").strip()
        tinai = data.get("tinai") or "Kuṟiñci"
        evidence_items = data.get("evidenceItems") or data.get("evidence") or data.get("evidence_items") or []

        criteria_data = data.get("criteria") or {}
        criteria = None
        if criteria_data:
            criteria = VyaptiValidationCriteria(
                min_confidence=float(criteria_data.get("min_confidence", criteria_data.get("minConfidence", 0.85))),
                require_canonical_neo4j=bool(criteria_data.get("require_canonical_neo4j", criteria_data.get("requireCanonicalNeo4j", True))),
                require_concomitance_rule=bool(criteria_data.get("require_concomitance_rule", criteria_data.get("requireConcomitanceRule", True))),
                require_source_provenance=bool(criteria_data.get("require_source_provenance", criteria_data.get("requireSourceProvenance", True))),
                require_evidence_text=bool(criteria_data.get("require_evidence_text", criteria_data.get("requireEvidenceText", True))),
                min_evidence_length=int(criteria_data.get("min_evidence_length", criteria_data.get("minEvidenceLength", 15))),
                require_tinai_congruence=bool(criteria_data.get("require_tinai_congruence", criteria_data.get("requireTinaiCongruence", True))),
            )

        result = vyapti_identifier.identify_vyapti(
            evidence_items=evidence_items,
            tinai=tinai,
            query_text=query_text,
            criteria=criteria,
        )

        msg = "Vyāpti established successfully" if result.get("is_established") else "Vyāpti unavailable"
        return success_response(data=result, message=msg)
    except Exception as e:
        logger.error(f"Error in /api/reasoning/identify-vyapti: {e}", exc_info=True)
        return error_response(str(e), error_code="VYAPTI_IDENTIFICATION_FAILED", status_code=500)


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


@reasoning_bp.route("/confidence/validate", methods=["POST"])
@reasoning_bp.route("/validate-confidence", methods=["POST"])
def validate_confidence_endpoint():
    """
    Real-time dynamic confidence score validation endpoint.
    Recalculates confidence score and supporting factor breakdown whenever
    evidence, graph traversal, premises, or reasoning results change.
    """
    try:
        from reasoning.confidence_evaluator import ConfidenceEvaluator

        data = request.get_json(silent=True) or {}
        evidence_items = data.get("evidenceItems") or data.get("evidence") or data.get("evidence_items") or []
        premises = data.get("premises") or []
        rules = data.get("rules") or []
        inferences = data.get("reasoningStages") or data.get("inferences") or []
        conclusion = data.get("conclusion")
        structured_context = data.get("structuredContext") or data.get("structured_context")
        vyapti_result = data.get("vyaptiIdentification") or data.get("vyaptiResult") or data.get("vyapti_result")
        validation_results = data.get("validationResults") or data.get("validation_results")
        tinai = data.get("tinai") or data.get("detectedTinai") or "Kuṟiñci"
        graph_nodes = data.get("graphNodes") or data.get("nodes")
        graph_edges = data.get("graphEdges") or data.get("edges")
        hop_depth = int(data.get("hopDepth") or data.get("depth") or 2)

        evaluation = ConfidenceEvaluator.evaluate(
            evidence_items=evidence_items,
            premises=premises,
            rules=rules,
            inferences=inferences,
            conclusion=conclusion,
            structured_context=structured_context,
            vyapti_result=vyapti_result,
            validation_results=validation_results,
            tinai=tinai,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            hop_depth=hop_depth,
        )

        return success_response(
            data=evaluation.to_dict(),
            message=f"Confidence evaluated: {evaluation.confidence_level} ({round(evaluation.confidence_score * 100)}%)",
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/confidence/validate: {e}", exc_info=True)
        return error_response(str(e), error_code="CONFIDENCE_VALIDATION_FAILED", status_code=500)


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


@reasoning_bp.route("/retrieve", methods=["POST"])
def retrieve_nyaya_evidence():
    """
    Dedicated endpoint retrieving dual-category Nyāya evidence:
    - caseEvidence (describing subject/event/scenario via entities, concepts, semantics, graph traversal)
    - canonicalEvidence (authoritative Vyāpti sūtras directly from Neo4j)
    - supportingEvidence (corroborating biotic/seasonal signifiers)
    - sourceMetadata (provenance audit)
    """
    try:
        from retrieval.nyaya_evidence_retriever import nyaya_evidence_retriever

        data = request.get_json(silent=True) or {}
        query_text = (data.get("queryText") or data.get("query") or "").strip()
        if not query_text:
            return error_response("Parameter 'queryText' cannot be empty", error_code="INVALID_QUERY", status_code=400)

        tinai = data.get("tinai")
        depth = int(data.get("depth", 2))
        focus = data.get("focus", "Relationship")
        top_k = int(data.get("top_k", data.get("topK", 5)))

        result = nyaya_evidence_retriever.retrieve_nyaya_evidence(
            query_text=query_text,
            tinai=tinai,
            depth=depth,
            focus=focus,
            top_k=top_k,
        )

        return success_response(
            data=result.to_dict(),
            message="Dual-category Nyāya evidence retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/retrieve: {e}", exc_info=True)
        return error_response(str(e), error_code="RETRIEVAL_FAILED", status_code=500)


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
    detected_language = data.get("detected_language") or data.get("detectedLanguage") or data.get("language")
    original_query = data.get("original_query") or data.get("originalQuery") or query_text

    try:
        result = reasoning_service.execute_reasoning_pipeline(
            query_text=query_text,
            depth=depth,
            focus=focus,
            detected_language=detected_language,
            original_query=original_query,
        )

        return success_response(
            data=result,
            message="Evidence-grounded epistemic answer synthesized successfully",
            meta={
                "query": query_text,
                "original_query": original_query,
                "detected_language": result.get("detectedLanguage"),
                "depth": depth,
                "detectedTinai": result.get("detectedTinai"),
                "insufficientEvidence": result.get("insufficientEvidence", False),
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/reasoning/answer: {e}", exc_info=True)
        return error_response(str(e), error_code="ANSWER_SYNTHESIS_FAILED", status_code=500)
    finally:
        try:
            from retrieval.rag_service import rag_engine
            rag_engine.clear_runtime_cache()
        except Exception:
            pass
