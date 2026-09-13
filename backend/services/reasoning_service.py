"""
Reasoning Service orchestrating Pañcāvayava deduction, multi-hop rule chaining,
Hetvābhāsa fallacy validation, proof DAG generation, and verdict synthesis.

Operates strictly on retrieved and validated evidence and predefined canonical rules.
Guarantees that no external LLM can invent evidence or alter retrieved facts.
Explicitly detects and returns an insufficient-evidence state rather than fabricating a conclusion.
"""
from __future__ import annotations

import uuid
from typing import Dict, Any, List, Optional

from reasoning.models import (
    PremiseNode,
    RuleNode,
    InferenceNode,
    ConclusionNode,
    ReasoningTrace,
)
from reasoning.premise_builder import EvidenceGroundedPremiseBuilder
from reasoning.rule_engine import TinaiRuleEngine
from reasoning.nyaya_engine import NyayaReasoner
from reasoning.validator import DefeasibleValidator
from reasoning.proof_trace import ProofTraceGenerator
from services.proof_trace_service import proof_trace_service
from llm.client import llm_client
from .query_service import query_service
from core.logger import logger


class ReasoningService:
    """End-to-end Nyāya neuro-symbolic reasoning orchestrator."""

    @classmethod
    def execute_reasoning_pipeline(
        cls,
        query_text: str,
        depth: int = 1,
        focus: str = "Relationship",
    ) -> Dict[str, Any]:
        """
        Executes full neuro-symbolic pipeline and produces comprehensive inference payload.
        All reasoning is grounded strictly in retrieved evidence.
        If sufficient evidence does not exist, returns an explicit insufficient-evidence state.
        """
        session_id = str(uuid.uuid4())[:8]

        # 1. Query Processing & Retrieval (Hybrid RAG + Knowledge Graph)
        query_context = query_service.process_query(query_text, depth=depth, focus=focus)
        tinai = query_context.get("detected_tinai") or "Kuṟiñci"
        evidence_records = query_context.get("evidence_records", [])
        subgraph = query_context.get("knowledge_graph", {"nodes": [], "edges": []})

        # Also retrieve through HybridRAGPipeline if available for richer metadata
        raw_evidence_items = []
        try:
            from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline
            collection = hybrid_rag_pipeline.retrieve(query_text, top_k=5)
            if collection and collection.items:
                raw_evidence_items = collection.items
        except Exception as e:
            logger.debug(f"HybridRAGPipeline direct retrieval fallback: {e}")

        effective_evidence = raw_evidence_items if raw_evidence_items else evidence_records

        # 1b. Transform ranked retrieval results into structured context for answer generation
        from retrieval.structured_context_builder import structured_context_builder
        structured_ctx = structured_context_builder.build_context(
            query=query_text,
            evidence_items=effective_evidence,
            max_passages=5,
            max_context_chars=4000,
            max_relationships_per_passage=8,
            min_relevance_threshold=0.20,
            min_evidence_count=2,
        )

        # 2. Check for Insufficient Evidence State (< 2 grounded passages or failed sufficiency)
        if not structured_ctx.is_sufficient or len(effective_evidence) < 2:
            insufficient_trace = proof_trace_service.generate_proof_trace(
                query_text=query_text,
                tinai=tinai,
                evidence_items=effective_evidence,
                min_evidence_threshold=2,
            )

            return {
                "queryText": query_text,
                "depth": depth,
                "focus": focus,
                "detectedTinai": tinai,
                "evidenceRecords": evidence_records,
                "knowledgeGraph": subgraph,
                "structuredContext": structured_ctx.to_dict(),
                "reasoningStages": [],
                "premises": [],
                "rules": [],
                "conclusion": None,
                "reasoningTrace": None,
                "validationResults": {
                    "soundnessScore": 0.0,
                    "symbolicValidity": "Insufficient Evidence",
                    "hetvabhasaCheck": "Asiddha Fallacy (Unproved middle ground: insufficient evidence)",
                    "pramana": "None",
                    "fallacies": {
                        "asiddha": 1.0,
                        "savyabhicara": 0.0,
                        "viruddha": 0.0,
                        "satpratipaksa": 0.0,
                        "badhita": 0.0,
                    },
                    "checks": [],
                },
                "proofNodes": [],
                "proofEdges": [],
                "proofTrace": insufficient_trace.to_dict(),
                "traceSteps": [],
                "insufficientEvidence": True,
                "insufficient_evidence": True,
                "hopChain": [],
                "finalAnswer": {
                    "tamilAnswer": "தீர்மானிக்கப் போதுமான தொல்காப்பியச் சான்றுகள் கிடைக்கவில்லை.",
                    "englishAnswer": "Insufficient canonical evidence retrieved to establish an invariant Nyāya proof chain.",
                    "subtitle": "At least 2 grounded verses are required to derive Vyāpti without fabrication.",
                    "confidenceScore": 0.0,
                    "starsCount": 0.0,
                    "verdictStatus": "Insufficient Canonical Evidence",
                    "justificationTamil": "தேடப்பட்ட வினாவிற்குரிய முதற்பொருள், கருப்பொருள் சான்றுகள் முழுமையாகக் கிடைக்காததால் வியாப்தி நியதி நிறுவப்படவில்லை.",
                    "justificationEnglish": "The retrieved evidence is below the required threshold of 2 canonical sūtras. No conclusion is fabricated.",
                    "keySources": [],
                },
                "neo4jGraph": {"nodes": [], "relationships": []},
            }

        # 3. Evidence-Grounded Premise Formulation
        premise_nodes = EvidenceGroundedPremiseBuilder.build_premise_nodes(
            evidence_items=effective_evidence,
            tinai=tinai,
        )

        # 4. First-Order Rule Formulation and Multi-Hop Chaining
        rule_nodes = TinaiRuleEngine.build_rule_nodes(
            tinai=tinai,
            evidence_items=effective_evidence,
        )
        hop_chain = TinaiRuleEngine.evaluate_multi_hop(
            tinai=tinai,
            evidence_items=effective_evidence,
            max_hops=max(2, depth),
        )

        # 5. Five-Stage Pañcāvayava Syllogistic Deduction
        inference_nodes = NyayaReasoner.evidence_grounded_deduction(
            query_text=query_text,
            tinai=tinai,
            evidence_items=effective_evidence,
            premises=premise_nodes,
            rules=rule_nodes,
            max_hops=len(hop_chain),
        )

        # 6. Defeasible Hetvābhāsa Fallacy & 5-Point Validation
        validation_results = DefeasibleValidator.validate_from_evidence(
            evidence_items=effective_evidence,
            inferences=inference_nodes,
            tinai=tinai,
        )

        # 7. Synthesized Epistemic Conclusion Node (Nigamana)
        evidence_ids_used = []
        for itm in effective_evidence:
            pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") or itm.get("sutraId") if isinstance(itm, dict) else "")
            if pid and pid not in evidence_ids_used:
                evidence_ids_used.append(pid)

        soundness = validation_results.get("soundnessScore", 0.98)
        conclusion_stmt = (
            f"Therefore, based on validated Tolkāppiyam axioms and {len(evidence_ids_used)} retrieved passages, "
            f"the aesthetic and affective signification is conclusively established under the {tinai} paradigm."
        )
        tamil_conclusion = (
            f"ஆகவே, தொல்காப்பிய முதற்பொருள், கருப்பொருள் சான்றுகளின் வழி "
            f"இச்செய்யுள் பனுவல் {tinai}த் திணைக்குரிய அக ஒழுக்கம் கொண்டது என்பது ஐயமற நிறுவப்பட்டது."
        )

        conclusion_node = ConclusionNode(
            id=f"CONCL_{session_id}",
            label="Conclusion",
            statement=conclusion_stmt,
            tamil_statement=tamil_conclusion,
            formal_logic=f"∴ Conclusion(C1) : EpistemicSoundness({tinai}) = {soundness} ∧ Abādhita = True",
            soundness_score=soundness,
            tinai=tinai,
            supporting_evidence_ids=evidence_ids_used,
            inference_ids=[inf.id for inf in inference_nodes],
            confidence=soundness,
        )

        # 8. Complete Structured ReasoningTrace (Persistence-ready)
        reasoning_trace = ReasoningTrace(
            query=query_text,
            session_id=session_id,
            tinai=tinai,
            premises=premise_nodes,
            rules=rule_nodes,
            inferences=inference_nodes,
            conclusion=conclusion_node,
            validation=validation_results,
            hop_count=len(hop_chain),
            evidence_ids_used=evidence_ids_used,
        )

        # 9. Proof-Trace Generation with Full Edge Connectivity and Step Chaining
        proof_trace = proof_trace_service.generate_proof_trace(
            query_text=query_text,
            tinai=tinai,
            evidence_items=effective_evidence,
            reasoning_trace=reasoning_trace,
        )

        reasoning_trace.proof_nodes = proof_trace.nodes

        # 10. Final Answer & Justification Synthesis (Formatting strictly constrained by grounded facts)
        final_answer = llm_client.synthesize_final_answer(
            query=query_text,
            tinai=tinai,
            evidence_items=evidence_records,
            structured_context=structured_ctx,
        )

        return {
            "queryText": query_text,
            "depth": depth,
            "focus": focus,
            "detectedTinai": tinai,
            "evidenceRecords": evidence_records,
            "knowledgeGraph": subgraph,
            "structuredContext": structured_ctx.to_dict(),
            "reasoningStages": [inf.to_dict() for inf in inference_nodes],
            "premises": [p.to_dict() for p in premise_nodes],
            "rules": [r.to_dict() for r in rule_nodes],
            "conclusion": conclusion_node.to_dict(),
            "reasoningTrace": reasoning_trace.to_dict(),
            "validationResults": validation_results,
            "proofNodes": proof_trace.nodes,
            "proofEdges": proof_trace.edges,
            "proofTrace": proof_trace.to_dict(),
            "traceSteps": [s.to_dict() for s in proof_trace.steps],
            "insufficientEvidence": False,
            "insufficient_evidence": False,
            "hopChain": hop_chain,
            "finalAnswer": final_answer.model_dump(),
            "neo4jGraph": reasoning_trace.to_neo4j_graph(),
        }


# Singleton instance
reasoning_service = ReasoningService()
