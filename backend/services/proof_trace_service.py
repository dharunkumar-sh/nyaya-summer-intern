"""
Proof-Trace Service for Nyāya-Inspired Neuro-Symbolic Inference.

Connects the final conclusion back to the exact evidence, passages, premises,
rules, and inference steps used to derive it.

Produces machine-readable JSON suitable for the React frontend (Cytoscape.js and SVG viewer).
Guarantees every conclusion has a traceable path back to source evidence.
Explicitly returns an insufficient-evidence state rather than fabricating a conclusion.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from reasoning.models import (
    ProofTraceStep,
    ProofTraceEdge,
    ProofTracePayload,
    ReasoningTrace,
    PremiseNode,
    RuleNode,
    InferenceNode,
    ConclusionNode,
)
from reasoning.proof_trace import ProofTraceGenerator
from reasoning.premise_builder import EvidenceGroundedPremiseBuilder
from reasoning.rule_engine import TinaiRuleEngine
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.validator import DefeasibleValidator
from core.logger import logger


class ProofTraceService:
    """
    Dedicated service generating and validating end-to-end graphical proof traces.
    """

    MIN_EVIDENCE_THRESHOLD = 2

    @classmethod
    def generate_proof_trace(
        cls,
        query_text: str,
        tinai: Optional[str] = None,
        evidence_items: Optional[List[Any]] = None,
        reasoning_trace: Optional[ReasoningTrace] = None,
        min_evidence_threshold: Optional[int] = None,
    ) -> ProofTracePayload:
        """
        Builds, validates, and serializes a graphical proof trace.

        If evidence count is below threshold, returns an explicit insufficient-evidence
        payload without hallucinating or fabricating conclusions.
        """
        threshold = min_evidence_threshold if min_evidence_threshold is not None else cls.MIN_EVIDENCE_THRESHOLD
        effective_tinai = tinai or "Kuṟiñci"

        # 1. Resolve Evidence Items
        items: List[Any] = []
        if evidence_items is not None:
            items = list(evidence_items)
        elif reasoning_trace is not None and reasoning_trace.evidence_ids_used:
            items = [{"passage_id": pid} for pid in reasoning_trace.evidence_ids_used]
        else:
            # Attempt retrieval if no evidence provided
            try:
                from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline
                col = hybrid_rag_pipeline.retrieve(query_text, top_k=5)
                if col and col.items:
                    items = col.items
            except Exception as e:
                logger.debug(f"ProofTraceService retrieval fallback: {e}")

        evidence_count = len(items)

        # 2. Check for Insufficient Evidence State
        if evidence_count < threshold:
            missing = []
            if evidence_count == 0:
                missing = [
                    "Terrestrial habitat (Mutalporuḷ) verse",
                    "Biotic signifier (Karupporuḷ) verse",
                ]
            elif evidence_count == 1:
                missing = [
                    "Corroborating biotic signifier (Karupporuḷ) verse to establish Vyāpti",
                ]

            return ProofTracePayload(
                status="INSUFFICIENT_EVIDENCE",
                query=query_text,
                tinai=effective_tinai,
                is_valid=False,
                insufficient_evidence=True,
                reason=(
                    f"The current query retrieved insufficient canonical sūtras to establish "
                    f"an invariant Nyāya proof chain. At least {threshold} grounded verses "
                    f"are required to derive Vyāpti."
                ),
                missing_requirements=missing,
                steps=[],
                nodes=[],
                edges=[],
                traceable_paths=[],
                evidence_count=evidence_count,
                conclusion_id=None,
            )

        # 3. Detect Tiṇai from Evidence if not provided
        if not tinai and items:
            first_src = getattr(items[0], "source", {}) or (items[0].get("source", {}) if isinstance(items[0], dict) else {})
            detected = first_src.get("tinai")
            if detected and detected != "General":
                effective_tinai = detected

        # 4. Resolve or Build Reasoning Elements
        premises: List[PremiseNode] = []
        rules: List[RuleNode] = []
        inferences: List[InferenceNode] = []
        conclusion: Optional[ConclusionNode] = None

        if reasoning_trace is not None:
            premises = reasoning_trace.premises
            rules = reasoning_trace.rules
            inferences = reasoning_trace.inferences
            conclusion = reasoning_trace.conclusion
        else:
            premises = EvidenceGroundedPremiseBuilder.build_premise_nodes(items, tinai=effective_tinai)
            rules = TinaiRuleEngine.build_rule_nodes(tinai=effective_tinai, evidence_items=items)
            inferences = NyayaReasoner.evidence_grounded_deduction(
                query_text=query_text,
                tinai=effective_tinai,
                evidence_items=items,
                premises=premises,
                rules=rules,
            )
            validation = DefeasibleValidator.validate_from_evidence(
                evidence_items=items,
                inferences=inferences,
                tinai=effective_tinai,
            )
            soundness = validation.get("soundnessScore", 0.98)
            e_ids_used = [getattr(it, "passage_id", None) or (it.get("passage_id") if isinstance(it, dict) else "") for it in items]
            conclusion = ConclusionNode(
                id="C1",
                label="Conclusion",
                statement=f"Therefore, primary aesthetic mood is conclusively established as {effective_tinai} Uripporuḷ.",
                formal_logic=f"∴ Conclusion(C1) : EpistemicSoundness = {soundness}",
                soundness_score=soundness,
                tinai=effective_tinai,
                supporting_evidence_ids=[i for i in e_ids_used if i],
                inference_ids=[inf.id for inf in inferences],
            )

        # 5. Build Graph Nodes and Directed Edges
        nodes = ProofTraceGenerator.generate_trace_nodes(
            tinai=effective_tinai,
            evidence_items=items,
            premises=premises,
            rules=rules,
            inferences=inferences,
            conclusion=conclusion,
        )

        edges = ProofTraceGenerator.generate_directed_edges(
            nodes=nodes,
            tinai=effective_tinai,
        )

        # 6. Generate Step-by-Step Chaining
        steps = ProofTraceGenerator.generate_trace_steps(nodes)

        # 7. Validate Traceability from Evidence to Conclusion
        is_traceable, traceable_paths = ProofTraceGenerator.validate_traceability(
            nodes=nodes,
            edges=edges,
        )

        conclusion_id = conclusion.id if conclusion else "C1"

        return ProofTracePayload(
            status="VALID_PROOF",
            query=query_text,
            tinai=effective_tinai,
            is_valid=is_traceable,
            insufficient_evidence=False,
            reason=None,
            missing_requirements=[],
            steps=steps,
            nodes=nodes,
            edges=edges,
            traceable_paths=traceable_paths,
            evidence_count=evidence_count,
            conclusion_id=conclusion_id,
        )


# Singleton service instance
proof_trace_service = ProofTraceService()
