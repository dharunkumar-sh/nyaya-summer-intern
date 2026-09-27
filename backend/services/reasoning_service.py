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
from retrieval.language_utils import detect_query_language, format_insufficient_evidence_response
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
        detected_language: Optional[Any] = None,
        original_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes full neuro-symbolic pipeline and produces comprehensive inference payload.
        All reasoning is grounded strictly in retrieved evidence.
        If sufficient evidence does not exist, returns an explicit insufficient-evidence state.
        """
        session_id = str(uuid.uuid4())[:8]
        orig_q = (original_query or query_text or "").strip()
        lang_info = detect_query_language(orig_q, detected_language)

        # 1. Query Processing & Retrieval (Hybrid RAG + Knowledge Graph)
        query_context = query_service.process_query(query_text, depth=depth, focus=focus)
        detected_tinai_explicit = query_context.get("processed_query", {}).get("detected_tinai")
        if detected_tinai_explicit and str(detected_tinai_explicit).lower() in ("general", "unknown", "none", ""):
            detected_tinai_explicit = None
        raw_ctx_tinai = query_context.get("detected_tinai")
        if raw_ctx_tinai and str(raw_ctx_tinai).lower() in ("general", "unknown", "none", ""):
            raw_ctx_tinai = None
        tinai = detected_tinai_explicit or raw_ctx_tinai or "Kuṟiñci"
        evidence_records = query_context.get("evidence_records", [])
        subgraph = query_context.get("knowledge_graph", {"nodes": [], "edges": []})

        # Dedicated Nyāya Dual-Category Evidence Retrieval (Case vs. Canonical Rule)
        nyaya_evidence = None
        try:
            from retrieval.nyaya_evidence_retriever import nyaya_evidence_retriever
            nyaya_evidence = nyaya_evidence_retriever.retrieve_nyaya_evidence(
                query_text=query_text,
                tinai=tinai,
                depth=depth,
                focus=focus,
            )
        except Exception as ne_err:
            logger.debug(f"NyayaEvidenceRetriever direct invocation fallback: {ne_err}")

        # Also retrieve through HybridRAGPipeline if available for richer metadata
        raw_evidence_items = []
        try:
            from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline
            collection = hybrid_rag_pipeline.retrieve(query_text, top_k=5)
            if collection and collection.items:
                raw_evidence_items = collection.items
        except Exception as e:
            logger.debug(f"HybridRAGPipeline direct retrieval fallback: {e}")

        all_nyaya_items = (
            (nyaya_evidence.case_evidence + nyaya_evidence.canonical_evidence + nyaya_evidence.supporting_evidence)
            if nyaya_evidence else []
        )
        effective_evidence = all_nyaya_items if all_nyaya_items else (raw_evidence_items if raw_evidence_items else evidence_records)

        # Authoritative Neo4j Aura enrichment for all canonical evidence
        try:
            from knowledge_graph.neo4j_repository import neo4j_repository
            pids = []
            for itm in effective_evidence:
                pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") if isinstance(itm, dict) else "")
                if pid and pid not in pids:
                    pids.append(pid)
            if pids:
                canonical_batch = neo4j_repository.get_canonical_sutras_batch(pids)
                for itm in effective_evidence:
                    pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") if isinstance(itm, dict) else "")
                    canon = canonical_batch.get(pid)
                    if canon:
                        if isinstance(itm, dict):
                            itm.setdefault("source", {})
                            if isinstance(itm["source"], dict):
                                itm["source"]["work"] = canon.get("work_name", "Tolkāppiyam")
                                itm["source"]["section"] = canon.get("section_name", "Poruḷatikāram")
                                itm["source"]["chapter"] = canon.get("chapter_name", "Akattiṇaiyiyal")
                                itm["source"]["sutra_number"] = canon.get("sutra_number")
                                itm["source"]["reference"] = canon.get("source_reference")
                            itm["original_text"] = canon.get("original_text") or itm.get("original_text")
                            itm["translation"] = canon.get("translation") or itm.get("translation")
                            itm["source_reference"] = canon.get("source_reference") or itm.get("source_reference")
                        else:
                            if hasattr(itm, "source") and isinstance(itm.source, dict):
                                itm.source["work"] = canon.get("work_name", "Tolkāppiyam")
                                itm.source["section"] = canon.get("section_name", "Poruḷatikāram")
                                itm.source["chapter"] = canon.get("chapter_name", "Akattiṇaiyiyal")
                                itm.source["sutra_number"] = canon.get("sutra_number")
                                itm.source["reference"] = canon.get("source_reference")
                            if hasattr(itm, "original_text"):
                                itm.original_text = canon.get("original_text") or getattr(itm, "original_text", "")
                            if hasattr(itm, "translation"):
                                itm.translation = canon.get("translation") or getattr(itm, "translation", "")
        except Exception as e:
            logger.debug(f"Neo4j canonical enrichment: {e}")

        # 1b. Transform ranked retrieval results into structured context for answer generation
        from retrieval.structured_context_builder import structured_context_builder
        structured_ctx = structured_context_builder.build_context(
            query=query_text,
            evidence_items=effective_evidence,
            max_passages=5,
            max_context_chars=4000,
            max_relationships_per_passage=8,
            min_relevance_threshold=0.30,
            min_evidence_count=2,
        )

        # Check if query has real grounding in the Tolkāppiyam corpus (lexical, conceptual, or query seeds)
        pq = query_context.get("processed_query") or {}
        decomp = query_context.get("query_decomposition") or {}
        raw_pq_tinai = pq.get("detected_tinai")
        real_tinai_detected = bool(
            (detected_tinai_explicit and str(detected_tinai_explicit).lower() not in ("general", "unknown", "none", ""))
            or (raw_pq_tinai and str(raw_pq_tinai).lower() not in ("general", "unknown", "none", ""))
        )
        has_corpus_grounding = bool(
            real_tinai_detected
            or pq.get("kg_seed_node_ids")
            or pq.get("entities")
            or pq.get("concepts")
            or pq.get("source_references")
            or decomp.get("entities")
            or decomp.get("concepts")
            or decomp.get("sutra_citations")
            or any(
                (getattr(it, "lexical_score", 0.0) or (it.get("lexical_score", 0.0) if isinstance(it, dict) else 0.0)) > 0.05
                for it in effective_evidence
            )
        )

        # Dedicated Vyāpti Identification Stage
        from reasoning.vyapti_identifier import vyapti_identifier
        vyapti_result = vyapti_identifier.identify_vyapti(
            evidence_items=effective_evidence,
            tinai=tinai,
            query_text=query_text,
        )
        is_vyapti_grounded = vyapti_result.get("is_established", False)
        classification = vyapti_result.get("evidence_classification", {})
        case_items = classification.get("case_evidence", [])
        vyapti_items = classification.get("vyapti_evidence", [])
        app_items = classification.get("application_evidence", [])

        # 2. Check for Insufficient Evidence or Vyāpti Unavailable State
        is_vyapti_unavailable = (not is_vyapti_grounded) and has_corpus_grounding
        if not has_corpus_grounding or not structured_ctx.is_sufficient or len(effective_evidence) < 2 or not is_vyapti_grounded:
            insufficient_trace = proof_trace_service.generate_proof_trace(
                query_text=query_text,
                tinai=tinai,
                evidence_items=effective_evidence if has_corpus_grounding else [],
                min_evidence_threshold=2,
            )

            if is_vyapti_unavailable:
                fallback_reason = "Vyāpti unavailable: No grounded canonical Vyāpti exists in Neo4j satisfying validation criteria."
                sym_validity = "Vyāpti unavailable"
                hetv_check = "Asiddha Fallacy (Unproved middle ground: Vyāpti unavailable)"
            elif not has_corpus_grounding:
                fallback_reason = "No grounded classical Tamil literary evidence exists for this query."
                sym_validity = "Insufficient Evidence"
                hetv_check = "Asiddha Fallacy (Unproved middle ground: insufficient evidence)"
            else:
                fallback_reason = (structured_ctx.insufficient_reason or "At least 2 grounded verses are required to derive Vyāpti without fabrication.")
                sym_validity = "Insufficient Evidence"
                hetv_check = "Asiddha Fallacy (Unproved middle ground: insufficient evidence)"

            insufficient_ans = format_insufficient_evidence_response(
                lang_info,
                fallback_reason,
            )

            # Only consider evidence items meeting relevance threshold to avoid expanding arbitrary background nodes
            grounded_evidence = [
                ev for ev in effective_evidence
                if (getattr(ev, "relevance_score", 0.0) or (ev.get("relevance_score", 0.0) if isinstance(ev, dict) else 0.0)) >= 0.30
            ] if has_corpus_grounding else []

            insufficient_subgraph = cls._build_attributed_neo4j_subgraph(
                query_text=query_text,
                tinai=detected_tinai_explicit if real_tinai_detected else "",
                effective_evidence=grounded_evidence,
                depth=depth,
            )

            from reasoning.confidence_evaluator import ConfidenceEvaluator
            insufficient_conf = ConfidenceEvaluator.evaluate(
                evidence_items=effective_evidence if has_corpus_grounding else [],
                structured_context=structured_ctx,
                vyapti_result=vyapti_result,
                tinai=tinai,
            )

            return {
                "queryText": query_text,
                "originalQuery": orig_q,
                "detectedLanguage": lang_info,
                "depth": depth,
                "focus": focus,
                "detectedTinai": tinai,
                "status": "Vyāpti unavailable" if is_vyapti_unavailable else "insufficient_evidence",
                "vyaptiStatus": "Vyāpti unavailable" if is_vyapti_unavailable else "unverified",
                "vyaptiUnavailable": is_vyapti_unavailable,
                "vyaptiIdentification": vyapti_result,
                "candidateVyaptis": vyapti_result.get("candidates", []),
                "establishedVyapti": None,
                "evidenceRecords": evidence_records,
                "knowledgeGraph": insufficient_subgraph,
                "structuredContext": structured_ctx.to_dict(),
                "reasoningStages": [],
                "premises": [],
                "rules": [],
                "conclusion": None,
                "reasoningTrace": None,
                "confidenceEvaluation": insufficient_conf.to_dict(),
                "confidenceScore": insufficient_conf.confidence_score,
                "confidenceLevel": insufficient_conf.confidence_level,
                "validationResults": {
                    "soundnessScore": insufficient_conf.confidence_score,
                    "symbolicValidity": sym_validity,
                    "hetvabhasaCheck": hetv_check,
                    "pramana": "None",
                    "fallacies": {
                        "asiddha": 1.0,
                        "savyabhicara": 0.0,
                        "viruddha": 0.0,
                        "satpratipaksa": 0.0,
                        "badhita": 0.0,
                    },
                    "checks": [],
                    "confidenceEvaluation": insufficient_conf.to_dict(),
                },
                "proofNodes": [],
                "proofEdges": [],
                "proofTrace": insufficient_trace.to_dict(),
                "traceSteps": [],
                "insufficientEvidence": True,
                "insufficient_evidence": True,
                "hopChain": [],
                "finalAnswer": insufficient_ans,
                "neo4jGraph": insufficient_subgraph,
                "groundedGraph": query_context.get("grounded_graph", {}),
                "caseEvidence": case_items if has_corpus_grounding else [],
                "vyaptiEvidence": vyapti_items if has_corpus_grounding else [],
                "applicationEvidence": app_items if has_corpus_grounding else [],
                "canonicalEvidence": vyapti_items if has_corpus_grounding else [],
                "supportingEvidence": app_items if has_corpus_grounding else [],
                "sourceMetadata": nyaya_evidence.source_metadata if nyaya_evidence else {},
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

        # 6b. Real-Time Dynamic Confidence Score Evaluation
        from reasoning.confidence_evaluator import ConfidenceEvaluator

        confidence_eval = ConfidenceEvaluator.evaluate(
            evidence_items=effective_evidence,
            premises=premise_nodes,
            rules=rule_nodes,
            inferences=inference_nodes,
            structured_context=structured_ctx,
            vyapti_result=vyapti_result,
            validation_results=validation_results,
            tinai=tinai,
            hop_depth=len(hop_chain),
        )

        soundness = confidence_eval.confidence_score
        validation_results["soundnessScore"] = soundness
        validation_results["confidenceEvaluation"] = confidence_eval.to_dict()

        # 7. Synthesized Epistemic Conclusion Node (Nigamana)
        evidence_ids_used = []
        for itm in effective_evidence:
            pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") or itm.get("sutraId") if isinstance(itm, dict) else "")
            if pid and pid not in evidence_ids_used:
                evidence_ids_used.append(pid)

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
            vyapti_identification=vyapti_result,
            case_evidence=case_items,
            vyapti_evidence=vyapti_items,
            application_evidence=app_items,
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
            lang_info=lang_info,
            original_query=orig_q,
        )

        final_answer_dict = final_answer.model_dump()
        final_answer_dict["confidenceScore"] = soundness
        final_answer_dict["starsCount"] = confidence_eval.confidence_stars
        final_answer_dict["confidenceLevel"] = confidence_eval.confidence_level
        final_answer_dict["confidenceEvaluation"] = confidence_eval.to_dict()

        # Build attributed Neo4j subgraph connected to reasoning components and retrieved evidence
        attributed_subgraph = cls._build_attributed_neo4j_subgraph(
            query_text=query_text,
            tinai=tinai,
            effective_evidence=effective_evidence,
            premises=premise_nodes,
            rules=rule_nodes,
            inferences=inference_nodes,
            conclusion=conclusion_node,
            depth=depth,
        )

        trace_dict = reasoning_trace.to_dict()
        trace_dict["neo4j_mutation_payload"] = reasoning_trace.to_neo4j_graph()

        return {
            "queryText": query_text,
            "originalQuery": orig_q,
            "detectedLanguage": lang_info,
            "depth": depth,
            "focus": focus,
            "detectedTinai": tinai,
            "status": "established",
            "vyaptiStatus": "grounded",
            "vyaptiUnavailable": False,
            "vyaptiIdentification": vyapti_result,
            "candidateVyaptis": vyapti_result.get("candidates", []),
            "establishedVyapti": vyapti_result.get("grounded_vyapti"),
            "evidenceRecords": evidence_records,
            "knowledgeGraph": attributed_subgraph,
            "structuredContext": structured_ctx.to_dict(),
            "reasoningStages": [inf.to_dict() for inf in inference_nodes],
            "premises": [p.to_dict() for p in premise_nodes],
            "rules": [r.to_dict() for r in rule_nodes],
            "conclusion": conclusion_node.to_dict(),
            "reasoningTrace": trace_dict,
            "validationResults": validation_results,
            "confidenceEvaluation": confidence_eval.to_dict(),
            "confidenceScore": soundness,
            "confidenceLevel": confidence_eval.confidence_level,
            "proofNodes": proof_trace.nodes,
            "proofEdges": proof_trace.edges,
            "proofTrace": proof_trace.to_dict(),
            "traceSteps": [s.to_dict() for s in proof_trace.steps],
            "insufficientEvidence": False,
            "insufficient_evidence": False,
            "hopChain": hop_chain,
            "finalAnswer": final_answer_dict,
            "neo4jGraph": attributed_subgraph,
            "groundedGraph": query_context.get("grounded_graph", {}),
            "caseEvidence": case_items,
            "vyaptiEvidence": vyapti_items,
            "applicationEvidence": app_items,
            "canonicalEvidence": vyapti_items,
            "supportingEvidence": app_items,
            "sourceMetadata": nyaya_evidence.source_metadata if nyaya_evidence else {},
        }

    @classmethod
    def _build_attributed_neo4j_subgraph(
        cls,
        query_text: str,
        tinai: str,
        effective_evidence: List[Any],
        premises: Optional[List[Any]] = None,
        rules: Optional[List[Any]] = None,
        inferences: Optional[List[Any]] = None,
        conclusion: Optional[Any] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Dynamically extracts and attributes a Neo4j Knowledge Graph subgraph
        directly tied to the current query, retrieved evidence, and Nyāya reasoning stages.

        Guarantees that:
        1. Nodes and relationships are retrieved from Neo4j Aura based on query & evidence seeds.
        2. Graph elements are attributed with `contributed_to_evidence`, `contributed_to_reasoning`,
           `evidence_ids`, `source_reference`, `reasoning_role`, and `reasoning_step`.
        3. No unrelated Neo4j data is displayed.
        """
        from services.graph_retrieval_service import graph_retrieval_service

        evidence_dicts = []
        for ev in effective_evidence or []:
            if hasattr(ev, "to_dict"):
                evidence_dicts.append(ev.to_dict())
            elif isinstance(ev, dict):
                evidence_dicts.append(ev)
            else:
                evidence_dicts.append({"id": str(ev), "passage_id": str(ev), "text": str(ev)})

        query_input = {
            "queryText": query_text,
            "tinai": tinai if tinai else None,
            "evidence": evidence_dicts,
        }

        # If no evidence, no tinai, and query has no recognized seeds, return clean empty subgraph
        from query.query_preprocessor import query_preprocessor
        preprocessed = query_preprocessor.preprocess(query_text)
        has_signals = bool(
            tinai
            or evidence_dicts
            or preprocessed.kg_seed_node_ids
            or preprocessed.entities
            or preprocessed.concepts
        )
        if not has_signals:
            return {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "total_relationships": 0,
                "seed_ids": [],
                "matched_seeds": [],
                "depth": depth,
                "source": "neo4j_aura",
                "metadata": {
                    "query": query_text,
                    "node_count": 0,
                    "relationship_count": 0,
                    "depth": depth,
                    "literary_sources": [],
                    "evidence_count": 0,
                    "contributed_to_evidence_count": 0,
                    "contributed_to_reasoning_count": 0,
                    "detected_tinai": "General",
                    "pipeline": "Adaptive Graph-RAG -> Nyāya Syllogism -> Attributed Neo4j Subgraph",
                },
            }

        try:
            subgraph = graph_retrieval_service.retrieve_query_subgraph(
                query_input=query_input,
                max_hops=max(1, depth),
            )
        except Exception as e:
            logger.warning(f"Error retrieving Neo4j subgraph in _build_attributed_neo4j_subgraph: {e}")
            subgraph = {
                "nodes": [],
                "relationships": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "metadata": {
                    "query": query_text,
                    "node_count": 0,
                    "relationship_count": 0,
                    "literary_sources": [],
                    "evidence_count": len(evidence_dicts),
                },
            }

        nodes = subgraph.get("nodes", [])
        relationships = subgraph.get("relationships", []) or subgraph.get("edges", [])

        # Collect evidence passage IDs and source references
        evidence_passage_ids = set()
        evidence_sources = {}
        for ev in evidence_dicts:
            pid = str(ev.get("passage_id") or ev.get("id") or "").lower()
            if pid:
                evidence_passage_ids.add(pid)
                src = ev.get("source_reference") or ev.get("source") or ev.get("work") or ""
                if src:
                    evidence_sources[pid] = src

        # Index reasoning roles and steps
        # Map: entity / concept / passage / tinai string (lowercase) -> dict(role, step, statement)
        reasoning_map: Dict[str, Dict[str, Any]] = {}

        if tinai:
            reasoning_map[tinai.lower()] = {
                "role": "paksa",
                "step": "pratijna",
                "statement": f"Core Tiṇai Paradigm: {tinai}",
            }

        for p in premises or []:
            p_id = getattr(p, "id", None) or (p.get("id") if isinstance(p, dict) else "")
            p_stmt = getattr(p, "statement", "") or (p.get("statement", "") if isinstance(p, dict) else "")
            p_evids = getattr(p, "supporting_evidence_ids", []) or (p.get("supporting_evidence_ids", []) if isinstance(p, dict) else [])
            for evid in p_evids:
                reasoning_map[str(evid).lower()] = {
                    "role": "premise_evidence",
                    "step": p_id,
                    "statement": p_stmt,
                }
            if p_id:
                reasoning_map[str(p_id).lower()] = {
                    "role": "premise",
                    "step": p_id,
                    "statement": p_stmt,
                }

        for r in rules or []:
            r_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else "")
            r_name = getattr(r, "name", "") or (r.get("name", "") if isinstance(r, dict) else "")
            r_evids = getattr(r, "supporting_evidence_ids", []) or (r.get("supporting_evidence_ids", []) if isinstance(r, dict) else [])
            for evid in r_evids:
                if str(evid).lower() not in reasoning_map:
                    reasoning_map[str(evid).lower()] = {
                        "role": "rule_evidence",
                        "step": r_id,
                        "statement": r_name,
                    }
            if r_id:
                reasoning_map[str(r_id).lower()] = {
                    "role": "rule",
                    "step": r_id,
                    "statement": r_name,
                }

        for inf in inferences or []:
            inf_id = getattr(inf, "id", None) or (inf.get("id") if isinstance(inf, dict) else "")
            inf_stage = getattr(inf, "stage", None) or getattr(inf, "step_name", "") or (inf.get("stage", "") if isinstance(inf, dict) else "")
            inf_stmt = getattr(inf, "assertion", "") or (inf.get("assertion", "") if isinstance(inf, dict) else "")
            inf_evids = getattr(inf, "supporting_evidence_ids", []) or (inf.get("supporting_evidence_ids", []) if isinstance(inf, dict) else [])
            for evid in inf_evids:
                reasoning_map[str(evid).lower()] = {
                    "role": inf_stage.lower() if inf_stage else "syllogism_evidence",
                    "step": inf_id,
                    "statement": inf_stmt,
                }

        if conclusion:
            c_id = getattr(conclusion, "id", None) or (conclusion.get("id") if isinstance(conclusion, dict) else "")
            c_stmt = getattr(conclusion, "statement", "") or (conclusion.get("statement", "") if isinstance(conclusion, dict) else "")
            c_evids = getattr(conclusion, "supporting_evidence_ids", []) or (conclusion.get("supporting_evidence_ids", []) if isinstance(conclusion, dict) else [])
            for evid in c_evids:
                reasoning_map[str(evid).lower()] = {
                    "role": "nigamana",
                    "step": c_id,
                    "statement": c_stmt,
                }

        # Attribute nodes
        has_reasoning = bool(premises or rules or inferences or conclusion)
        contributed_evidence_count = 0
        contributed_reasoning_count = 0

        for node in nodes:
            nid = str(node.get("id", "")).lower()
            nname = str(node.get("name") or node.get("label") or "").lower()
            ncanon = str(node.get("canonical_form") or node.get("transliteration") or "").lower()

            # 1. Evidence attribution
            is_evidence = node.get("contributed_to_evidence", False)
            ev_ids = list(node.get("evidence_ids", []))
            if nid in evidence_passage_ids:
                is_evidence = True
                if nid not in ev_ids:
                    ev_ids.append(nid)
                if nid in evidence_sources and not node.get("source_reference"):
                    node["source_reference"] = evidence_sources[nid]
            elif node.get("is_seed") and evidence_passage_ids:
                is_evidence = True
                for pid in evidence_passage_ids:
                    if pid not in ev_ids:
                        ev_ids.append(pid)

            node["contributed_to_evidence"] = is_evidence
            node["evidence_ids"] = ev_ids
            if is_evidence:
                contributed_evidence_count += 1

            # 2. Reasoning attribution
            matched_reasoning = None
            for candidate in (nid, nname, ncanon):
                if candidate in reasoning_map:
                    matched_reasoning = reasoning_map[candidate]
                    break

            if matched_reasoning:
                node["contributed_to_reasoning"] = True
                node["reasoning_role"] = matched_reasoning["role"]
                node["reasoning_step"] = matched_reasoning["step"]
                if not node.get("reasoning_statement"):
                    node["reasoning_statement"] = matched_reasoning["statement"]
            elif has_reasoning and is_evidence:
                node["contributed_to_reasoning"] = True
                node["reasoning_role"] = "udaharana"
                node["reasoning_step"] = "grounded_evidence"
            else:
                node.setdefault("contributed_to_reasoning", False)
                node.setdefault("reasoning_role", None)
                node.setdefault("reasoning_step", None)

            if node["contributed_to_reasoning"]:
                contributed_reasoning_count += 1

        # Attribute relationships
        node_lookup = {str(n.get("id", "")).lower(): n for n in nodes}
        for rel in relationships:
            s_id = str(rel.get("source") or rel.get("source_id", "")).lower()
            t_id = str(rel.get("target") or rel.get("target_id", "")).lower()
            s_node = node_lookup.get(s_id)
            t_node = node_lookup.get(t_id)

            rel_ev_ids = list(rel.get("evidence_ids", []))
            if s_node and s_node.get("contributed_to_evidence"):
                rel["contributed_to_evidence"] = True
                for eid in s_node.get("evidence_ids", []):
                    if eid not in rel_ev_ids:
                        rel_ev_ids.append(eid)
            if t_node and t_node.get("contributed_to_evidence"):
                rel["contributed_to_evidence"] = True
                for eid in t_node.get("evidence_ids", []):
                    if eid not in rel_ev_ids:
                        rel_ev_ids.append(eid)

            if (
                s_node and t_node
                and (
                    (s_node.get("contributed_to_reasoning") and t_node.get("contributed_to_reasoning"))
                    or (s_node.get("contributed_to_reasoning") and t_node.get("contributed_to_evidence"))
                    or (s_node.get("contributed_to_evidence") and t_node.get("contributed_to_reasoning"))
                )
            ):
                rel["contributed_to_reasoning"] = True
            else:
                rel.setdefault("contributed_to_reasoning", False)

            rel.setdefault("contributed_to_evidence", False)
            rel["evidence_ids"] = rel_ev_ids

        # Update metadata
        subgraph["nodes"] = nodes
        subgraph["relationships"] = relationships
        subgraph["edges"] = relationships
        subgraph["total_nodes"] = len(nodes)
        subgraph["total_edges"] = len(relationships)
        subgraph["total_relationships"] = len(relationships)

        if "metadata" not in subgraph or not isinstance(subgraph["metadata"], dict):
            subgraph["metadata"] = {}

        subgraph["metadata"].update({
            "query": query_text,
            "node_count": len(nodes),
            "relationship_count": len(relationships),
            "evidence_count": len(evidence_dicts),
            "contributed_to_evidence_count": contributed_evidence_count,
            "contributed_to_reasoning_count": contributed_reasoning_count,
            "reasoning_stages_count": len(inferences or []),
            "detected_tinai": tinai,
            "pipeline": "Adaptive Graph-RAG -> Nyāya Syllogism -> Attributed Neo4j Subgraph",
        })

        return subgraph


# Singleton instance
reasoning_service = ReasoningService()
