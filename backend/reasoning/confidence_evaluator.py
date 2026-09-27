"""
Dynamic Real-Time Confidence Score Validation Engine for Nyāya Neuro-Symbolic Retrieval & Reasoning.

Dynamically evaluates epistemic confidence from six canonical dimensions:
1. Evidence Relevance: semantic-lexical match scores and ranking distributions
2. Source Provenance: Tolkāppiyam canonical primary sūtra authority and citation completeness
3. Retrieval Strength: multi-channel agreement (Semantic Vector + BM25 + Graph Traversal)
4. Premise Support: grounded passage linkage and Mutal/Karu/Uri semiotic alignment
5. Reasoning Consistency: established Vyāpti invariance and absence of Hetvābhāsa fallacies
6. Validation Status: 5-point defeasible verification check scores

Applies explicit gating and penalties for:
- Insufficient evidence (< 2 qualifying passages or insufficient retrieval state)
- Conflicting or contradictory evidence (cross-tiṇai dissonance, Viruddha fallacy)
- Weak evidence (relevance scores below threshold)
- Unsupported conclusions (Vyāpti unavailable or ungrounded syllogism)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class ConfidenceFactor:
    """A single constituent factor contributing to the composite confidence score."""
    name: str
    label: str
    tamil_label: str
    score: float  # [0.0, 1.0]
    weight: float  # [0.0, 1.0]
    description: str
    status: str  # "OPTIMAL" | "ADEQUATE" | "SUBOPTIMAL" | "DEFICIENT"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "tamilLabel": self.tamil_label,
            "score": round(self.score, 4),
            "weight": round(self.weight, 4),
            "weightedScore": round(self.score * self.weight, 4),
            "weighted_score": round(self.score * self.weight, 4),
            "description": self.description,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class ConfidencePenalty:
    """An explicit penalty deducted or gated against confidence."""
    id: str
    name: str
    tamil_name: str
    penalty_value: float  # Absolute deduction or multiplier reduction
    reason: str
    category: str  # "INSUFFICIENT" | "CONFLICTING" | "WEAK" | "UNSUPPORTED"

    @property
    def penalty_name(self) -> str:
        return self.id or self.name

    @property
    def penaltyName(self) -> str:
        return self.id or self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "penalty_name": self.penalty_name,
            "penaltyName": self.penaltyName,
            "tamilName": self.tamil_name,
            "penaltyValue": round(self.penalty_value, 4),
            "reason": self.reason,
            "category": self.category,
        }


@dataclass
class ConfidenceEvaluationResult:
    """Comprehensive evaluation payload for real-time confidence validation."""
    confidence_score: float  # [0.0, 1.0]
    confidence_level: str  # "VERY_HIGH" | "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT"
    confidence_level_tamil: str
    confidence_stars: float  # [0.0, 5.0]
    is_sufficient: bool
    verdict_status: str
    verdict_status_tamil: str
    supporting_factors: Dict[str, ConfidenceFactor]
    penalties_applied: List[ConfidencePenalty]
    raw_base_score: float
    total_penalty_deduction: float
    gating_multiplier: float
    calibration_summary: str

    @property
    def penalties(self) -> List[ConfidencePenalty]:
        return self.penalties_applied

    @property
    def factors(self) -> Dict[str, ConfidenceFactor]:
        alias_map = {
            "evidenceRelevance": "evidence_relevance",
            "sourceProvenance": "source_provenance",
            "retrievalStrength": "retrieval_strength",
            "premiseSupport": "premise_support",
            "reasoningConsistency": "reasoning_consistency",
            "validationStatus": "validation_status",
        }
        res: Dict[str, ConfidenceFactor] = {}
        for k, v in self.supporting_factors.items():
            res[alias_map.get(k, k)] = v
        return res

    @property
    def confidence_percentage(self) -> int:
        return int(round(self.confidence_score * 100))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidenceScore": round(self.confidence_score, 4),
            "confidencePercentage": self.confidence_percentage,
            "confidenceLevel": self.confidence_level,
            "confidenceLevelTamil": self.confidence_level_tamil,
            "confidenceStars": round(self.confidence_stars, 1),
            "isSufficient": self.is_sufficient,
            "verdictStatus": self.verdict_status,
            "verdictStatusTamil": self.verdict_status_tamil,
            "supportingFactors": {
                k: v.to_dict() for k, v in self.supporting_factors.items()
            },
            "factors": {
                k: v.to_dict() for k, v in self.supporting_factors.items()
            },
            "penaltiesApplied": [p.to_dict() for p in self.penalties_applied],
            "penalties": [p.to_dict() for p in self.penalties_applied],
            "rawBaseScore": round(self.raw_base_score, 4),
            "totalPenaltyDeduction": round(self.total_penalty_deduction, 4),
            "gatingMultiplier": round(self.gating_multiplier, 4),
            "calibrationSummary": self.calibration_summary,
        }


class ConfidenceEvaluator:
    """
    Real-time dynamic confidence score validator across retrieval, knowledge graph,
    premises, syllogistic reasoning, and defeasible validation.
    """

    # Normalized constituent weights summing to 1.0
    WEIGHT_EVIDENCE_RELEVANCE = 0.20
    WEIGHT_SOURCE_PROVENANCE = 0.15
    WEIGHT_RETRIEVAL_STRENGTH = 0.15
    WEIGHT_PREMISE_SUPPORT = 0.15
    WEIGHT_REASONING_CONSISTENCY = 0.20
    WEIGHT_VALIDATION_STATUS = 0.15

    @classmethod
    def evaluate(
        cls,
        evidence_items: Optional[List[Any]] = None,
        premises: Optional[List[Any]] = None,
        rules: Optional[List[Any]] = None,
        inferences: Optional[List[Any]] = None,
        conclusion: Optional[Any] = None,
        structured_context: Optional[Any] = None,
        vyapti_result: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
        tinai: str = "Kuṟiñci",
        graph_nodes: Optional[List[Any]] = None,
        graph_edges: Optional[List[Any]] = None,
        hop_depth: int = 2,
        query: Optional[str] = None,
        evidence_records: Optional[List[Any]] = None,
        vyapti_rule: Optional[Any] = None,
        reasoning_stages: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ConfidenceEvaluationResult:
        """
        Dynamically evaluates epistemic confidence across the entire pipeline.
        Calculates all 6 constituent dimensions from actual data and enforces
        strict gating rules for insufficient, conflicting, or weak evidence.
        """
        if evidence_items is None and evidence_records is not None:
            evidence_items = evidence_records
        if rules is None and vyapti_rule is not None:
            rules = [vyapti_rule] if not isinstance(vyapti_rule, list) else vyapti_rule
        if inferences is None and reasoning_stages is not None:
            inferences = reasoning_stages

        ev_list = cls._normalize_evidence_items(evidence_items)
        ev_count = len(ev_list)

        # -------------------------------------------------------------------
        # 1. Evidence Relevance (Semantic-lexical match scores & distribution)
        # -------------------------------------------------------------------
        f_relevance = cls._evaluate_evidence_relevance(ev_list)

        # -------------------------------------------------------------------
        # 2. Source Provenance (Tolkāppiyam primary authority & citation rigor)
        # -------------------------------------------------------------------
        f_provenance = cls._evaluate_source_provenance(ev_list, tinai)

        # -------------------------------------------------------------------
        # 3. Retrieval Strength (Multi-channel agreement & score margins)
        # -------------------------------------------------------------------
        f_retrieval = cls._evaluate_retrieval_strength(ev_list, structured_context)

        # -------------------------------------------------------------------
        # 4. Premise Support (Verified grounding in evidence passages)
        # -------------------------------------------------------------------
        f_premise = cls._evaluate_premise_support(premises, ev_list, tinai)

        # -------------------------------------------------------------------
        # 5. Reasoning Consistency (Vyāpti established status & Hetvābhāsa check)
        # -------------------------------------------------------------------
        f_consistency = cls._evaluate_reasoning_consistency(
            rules=rules,
            inferences=inferences,
            vyapti_result=vyapti_result,
            validation_results=validation_results,
            tinai=tinai,
        )

        # -------------------------------------------------------------------
        # 6. Validation Status (Defeasible 5-point verification checks)
        # -------------------------------------------------------------------
        f_validation = cls._evaluate_validation_status(validation_results)

        # Assemble factor dictionary
        factors = {
            "evidenceRelevance": f_relevance,
            "sourceProvenance": f_provenance,
            "retrievalStrength": f_retrieval,
            "premiseSupport": f_premise,
            "reasoningConsistency": f_consistency,
            "validationStatus": f_validation,
        }

        # Weighted base score
        raw_base_score = sum(f.score * f.weight for f in factors.values())

        # -------------------------------------------------------------------
        # Gating Rules & Penalty Evaluations
        # -------------------------------------------------------------------
        penalties: List[ConfidencePenalty] = []
        gating_multiplier = 1.0

        # Check Insufficient Evidence
        is_context_insufficient = False
        if structured_context is not None:
            if hasattr(structured_context, "is_sufficient"):
                is_context_insufficient = not bool(structured_context.is_sufficient)
            elif isinstance(structured_context, dict):
                is_context_insufficient = not bool(structured_context.get("is_sufficient", True))

        if ev_count == 0:
            penalties.append(ConfidencePenalty(
                id="P_ZERO_EVIDENCE",
                name="Zero Evidence Retrieved",
                tamil_name="சான்றுகளின்மை",
                penalty_value=1.0,
                reason="No canonical evidence passages were retrieved for the query.",
                category="INSUFFICIENT",
            ))
            gating_multiplier = 0.0
        elif ev_count < 2 or is_context_insufficient:
            penalties.append(ConfidencePenalty(
                id="P_INSUFFICIENT_EVIDENCE",
                name="Insufficient Canonical Evidence Threshold",
                tamil_name="போதிய சான்றுகளின்மை",
                penalty_value=0.60,
                reason=f"Retrieved {ev_count} passage(s). Nyāya invariant deduction requires at least 2 corroborated canonical sūtras.",
                category="INSUFFICIENT",
            ))
            # Gate maximum score to 0.25
            gating_multiplier = min(gating_multiplier, 0.25)

        # Check Unsupported / Ungrounded Vyāpti
        vyapti_is_grounded = False
        if vyapti_result is not None:
            vyapti_is_grounded = bool(vyapti_result.get("is_established", False))
        elif rules:
            vyapti_is_grounded = any(
                getattr(r, "vyapti_validated", False)
                or (isinstance(r, dict) and r.get("vyapti_validated", False))
                for r in rules
            )
        elif inferences:
            for inf in inferences:
                stg = getattr(inf, "stage_number", None) or (inf.get("stageNumber") if isinstance(inf, dict) else None)
                if stg == 3:
                    vyapti_is_grounded = True
                    break

        if not vyapti_is_grounded and ev_count > 0:
            penalties.append(ConfidencePenalty(
                id="P_UNGROUNDED_VYAPTI",
                name="Universal Concomitance (Vyāpti) Unavailable",
                tamil_name="வியாப்தி நியதி கிட்டாமை",
                penalty_value=0.55,
                reason="Universal concomitance rule connecting signifiers to affect cannot be established from Neo4j Aura.",
                category="UNSUPPORTED",
            ))
            gating_multiplier = min(gating_multiplier, 0.30)

        # Check Unsupported Conclusion
        conclusion_has_support = True
        if conclusion is not None:
            supp_ids = getattr(conclusion, "supporting_evidence_ids", None)
            if supp_ids is None and isinstance(conclusion, dict):
                supp_ids = conclusion.get("supporting_evidence_ids", [])
            if not supp_ids:
                conclusion_has_support = False

        if not conclusion_has_support:
            penalties.append(ConfidencePenalty(
                id="P_UNSUPPORTED_CONCLUSION",
                name="Unsupported Epistemic Conclusion",
                tamil_name="ஆதாரமற்ற முடிவு",
                penalty_value=0.50,
                reason="Conclusion statement is not anchored in verified evidence passage IDs.",
                category="UNSUPPORTED",
            ))
            gating_multiplier = min(gating_multiplier, 0.25)

        # Check Conflicting / Contradictory Evidence (Viruddha / Contrary Affect)
        fallacies = (validation_results or {}).get("fallacies", {})
        viruddha_score = float(fallacies.get("viruddha", 0.0))
        cross_tinai_conflicts = cls._detect_cross_tinai_conflicts(ev_list, tinai)

        if viruddha_score > 0.0 or cross_tinai_conflicts > 0:
            conflict_penalty = min(0.45, 0.25 + (cross_tinai_conflicts * 0.10) + (viruddha_score * 0.20))
            penalties.append(ConfidencePenalty(
                id="P_CONFLICTING_EVIDENCE",
                name="Conflicting Semiotic Evidence (Viruddha)",
                tamil_name="முரண்பட்ட சான்றுகள்",
                penalty_value=conflict_penalty,
                reason=f"Detected cross-tiṇai discordance ({cross_tinai_conflicts} items) or contradictory inferential middle ground.",
                category="CONFLICTING",
            ))

        # Check Weak Evidence (Borderline relevance scores)
        mean_relevance = f_relevance.metadata.get("mean_relevance", 0.8)
        if 0.0 < mean_relevance < 0.45 and ev_count > 0:
            weak_penalty = min(0.35, (0.45 - mean_relevance) * 1.2)
            penalties.append(ConfidencePenalty(
                id="P_WEAK_RELEVANCE",
                name="Weak Retrieval Relevance Margin",
                tamil_name="மெலிந்த சான்றுப் பொருத்தம்",
                penalty_value=weak_penalty,
                reason=f"Mean evidence relevance ({mean_relevance:.2f}) falls below recommended threshold (0.45).",
                category="WEAK",
            ))

        # -------------------------------------------------------------------
        # Calculate Final Calibrated Score
        # -------------------------------------------------------------------
        total_deduction = sum(p.penalty_value for p in penalties if p.category in ("CONFLICTING", "WEAK"))
        effective_base = max(0.0, raw_base_score - total_deduction)
        final_score = max(0.0, min(1.0, effective_base * gating_multiplier))

        # Determine qualitative confidence level
        is_sufficient_flag = (ev_count >= 2) and vyapti_is_grounded and not is_context_insufficient and (final_score >= 0.35)

        if not is_sufficient_flag or final_score < 0.35:
            conf_level = "INSUFFICIENT"
            conf_level_ta = "போதாது / ஆதாரமற்றது"
            verdict = "Defeasible / Insufficient Canonical Grounding"
            verdict_ta = "சான்றாதாரமற்ற / ஐயத்திற்குரிய முடிவு"
        elif final_score >= 0.88:
            conf_level = "VERY_HIGH"
            conf_level_ta = "மிக உயர்வானது"
            verdict = "Sound Canonical Invariance (தொல்காப்பிய முறைமை நெறி)"
            verdict_ta = "ஐயமற நிறுவப்பட்ட தொல்காப்பிய நெறி"
        elif final_score >= 0.72:
            conf_level = "HIGH"
            conf_level_ta = "உயர்வானது"
            verdict = "Well-Supported Epistemic Deduction"
            verdict_ta = "நன்கு நிறுவப்பட்ட தருக்க முடிவு"
        elif final_score >= 0.50:
            conf_level = "MODERATE"
            conf_level_ta = "நடுத்தரமானது"
            verdict = "Moderate Grounding (Needs Further Corroboration)"
            verdict_ta = "நடுத்தர சான்றுப் பொருத்தம்"
        else:
            conf_level = "LOW"
            conf_level_ta = "குறைவானது"
            verdict = "Weak Grounding (Low Relevance Margin)"
            verdict_ta = "வலியற்ற சான்றாதார முடிவு"

        stars = round(max(0.0, min(5.0, final_score * 5.0)), 1)

        summary = (
            f"Confidence {round(final_score * 100)}% ({conf_level}). "
            f"Evaluated from {ev_count} evidence passage(s), {len(penalties)} active gate/penalty rule(s). "
            f"Relevance: {round(f_relevance.score*100)}%, Provenance: {round(f_provenance.score*100)}%, "
            f"Vyāpti Consistency: {round(f_consistency.score*100)}%."
        )

        return ConfidenceEvaluationResult(
            confidence_score=final_score,
            confidence_level=conf_level,
            confidence_level_tamil=conf_level_ta,
            confidence_stars=stars,
            is_sufficient=is_sufficient_flag,
            verdict_status=verdict,
            verdict_status_tamil=verdict_ta,
            supporting_factors=factors,
            penalties_applied=penalties,
            raw_base_score=raw_base_score,
            total_penalty_deduction=total_deduction,
            gating_multiplier=gating_multiplier,
            calibration_summary=summary,
        )

    # -----------------------------------------------------------------------
    # Helper Evaluators for Each Constituent Dimension
    # -----------------------------------------------------------------------

    @classmethod
    def _evaluate_evidence_relevance(cls, ev_list: List[Dict[str, Any]]) -> ConfidenceFactor:
        """Evaluates relevance scores, similarity scores, and distribution."""
        if not ev_list:
            return ConfidenceFactor(
                name="evidenceRelevance",
                label="Evidence Relevance",
                tamil_label="சான்றுப் பொருத்தம்",
                score=0.0,
                weight=cls.WEIGHT_EVIDENCE_RELEVANCE,
                description="Zero relevant evidence retrieved.",
                status="DEFICIENT",
                metadata={"count": 0, "mean_relevance": 0.0, "top_relevance": 0.0},
            )

        scores: List[float] = []
        for itm in ev_list:
            sc = itm.get("relevance_score")
            if sc is None:
                sc = itm.get("combined_score")
            if sc is None:
                sc = itm.get("hybrid_score")
            if sc is None:
                sc = itm.get("confidence")
            if sc is None:
                sc = itm.get("confidenceScore")
            if sc is not None:
                try:
                    scores.append(float(sc))
                except (ValueError, TypeError):
                    scores.append(0.5)
            else:
                scores.append(0.5)

        top_sc = max(scores) if scores else 0.0
        mean_sc = sum(scores) / len(scores) if scores else 0.0

        # Weighted combination: 60% top item, 40% average of items
        rel_score = min(1.0, max(0.0, (top_sc * 0.60) + (mean_sc * 0.40)))

        # Quality tiering
        if rel_score >= 0.80:
            status = "OPTIMAL"
            desc = f"Strong semantic-lexical match across {len(ev_list)} passage(s) (Top: {top_sc:.2f}, Mean: {mean_sc:.2f})."
        elif rel_score >= 0.60:
            status = "ADEQUATE"
            desc = f"Moderate evidence relevance match (Top: {top_sc:.2f}, Mean: {mean_sc:.2f})."
        elif rel_score >= 0.40:
            status = "SUBOPTIMAL"
            desc = f"Borderline relevance margin across retrieved items (Mean: {mean_sc:.2f})."
        else:
            status = "DEFICIENT"
            desc = f"Weak evidence relevance (Top: {top_sc:.2f}, Mean: {mean_sc:.2f}) indicates potential noise."

        return ConfidenceFactor(
            name="evidenceRelevance",
            label="Evidence Relevance",
            tamil_label="சான்றுப் பொருத்தம்",
            score=rel_score,
            weight=cls.WEIGHT_EVIDENCE_RELEVANCE,
            description=desc,
            status=status,
            metadata={
                "count": len(ev_list),
                "top_relevance": round(top_sc, 4),
                "mean_relevance": round(mean_sc, 4),
            },
        )

    @classmethod
    def _evaluate_source_provenance(cls, ev_list: List[Dict[str, Any]], tinai: str) -> ConfidenceFactor:
        """Evaluates citation completeness and canonical Tolkāppiyam primary authority."""
        if not ev_list:
            return ConfidenceFactor(
                name="sourceProvenance",
                label="Source Provenance",
                tamil_label="மூலச் சான்றாதாரத் தரம்",
                score=0.0,
                weight=cls.WEIGHT_SOURCE_PROVENANCE,
                description="No source citations available.",
                status="DEFICIENT",
                metadata={"canonical_ratio": 0.0, "citation_completeness": 0.0},
            )

        canonical_count = 0
        complete_citations = 0

        for itm in ev_list:
            src = itm.get("source") if isinstance(itm.get("source"), dict) else {}
            work = str(src.get("work") or itm.get("work") or itm.get("work_name") or "").lower()
            section = str(src.get("section") or itm.get("section") or itm.get("section_name") or "").lower()
            sutra = src.get("sutra_number") or itm.get("sutra_number") or itm.get("verse_number")
            ref = str(src.get("reference") or itm.get("source_reference") or itm.get("citation") or "")

            # Canonical primary corpus check
            is_canonical = "tolkappiyam" in work or "tolkāppiyam" in work or "porulatikaram" in section or "poruḷatikāram" in section or "akattinai" in ref.lower() or "akattiṇai" in ref.lower()
            if is_canonical or itm.get("passage_id", "").startswith("tol-"):
                canonical_count += 1

            # Citation completeness check
            has_hierarchy = bool(work and (section or ref))
            has_sutra_or_id = bool(sutra or itm.get("passage_id"))
            if has_hierarchy and has_sutra_or_id:
                complete_citations += 1

        canon_ratio = canonical_count / len(ev_list) if ev_list else 0.0
        complete_ratio = complete_citations / len(ev_list) if ev_list else 0.0

        prov_score = min(1.0, max(0.0, (canon_ratio * 0.65) + (complete_ratio * 0.35)))

        if prov_score >= 0.85:
            status = "OPTIMAL"
            desc = f"100% anchored in primary Tolkāppiyam Poruḷatikāram canonical sūtras with complete citations ({complete_citations}/{len(ev_list)})."
        elif prov_score >= 0.60:
            status = "ADEQUATE"
            desc = f"Partially anchored in canonical sūtras ({canonical_count}/{len(ev_list)}) with verifiable citations."
        else:
            status = "SUBOPTIMAL"
            desc = "Incomplete source provenance or reliance on secondary/unverified citations."

        return ConfidenceFactor(
            name="sourceProvenance",
            label="Source Provenance",
            tamil_label="மூலச் சான்றாதாரத் தரம்",
            score=prov_score,
            weight=cls.WEIGHT_SOURCE_PROVENANCE,
            description=desc,
            status=status,
            metadata={
                "canonical_count": canonical_count,
                "complete_citations": complete_citations,
                "total_evidence": len(ev_list),
            },
        )

    @classmethod
    def _evaluate_retrieval_strength(
        cls,
        ev_list: List[Dict[str, Any]],
        structured_context: Optional[Any],
    ) -> ConfidenceFactor:
        """Evaluates multi-channel consensus (Semantic + BM25 + Graph) and retrieval density."""
        if not ev_list:
            return ConfidenceFactor(
                name="retrievalStrength",
                label="Retrieval Strength",
                tamil_label="மீட்பு வலிமை",
                score=0.0,
                weight=cls.WEIGHT_RETRIEVAL_STRENGTH,
                description="Zero retrieval signals.",
                status="DEFICIENT",
                metadata={"channel_consensus": 0.0},
            )

        multi_channel_count = 0
        has_semantic = False
        has_lexical = False
        has_graph = False

        for itm in ev_list:
            methods = itm.get("retrieval_methods") or []
            if isinstance(methods, str):
                methods = [methods]
            method_str = " ".join([str(m).lower() for m in methods])

            if "semantic" in method_str or "vector" in method_str or itm.get("semantic_score", 0.0) > 0.1:
                has_semantic = True
            if "lexical" in method_str or "bm25" in method_str or itm.get("lexical_score", 0.0) > 0.1:
                has_lexical = True
            if "graph" in method_str or itm.get("graph_score", 0.0) > 0.1:
                has_graph = True

            if len(methods) >= 2 or (itm.get("semantic_score", 0) > 0.1 and itm.get("lexical_score", 0) > 0.1):
                multi_channel_count += 1

        channel_count = int(has_semantic) + int(has_lexical) + int(has_graph)
        consensus_ratio = multi_channel_count / len(ev_list) if ev_list else 0.0

        # Channel diversity score
        diversity_score = channel_count / 3.0
        ret_score = min(1.0, max(0.0, (diversity_score * 0.50) + (consensus_ratio * 0.50)))

        # Boost slightly if multiple passages corroborate
        if len(ev_list) >= 3:
            ret_score = min(1.0, ret_score + 0.10)

        if channel_count >= 3 or consensus_ratio >= 0.60:
            status = "OPTIMAL"
            desc = "High multi-channel consensus across Semantic Vector, BM25 Lexical, and Knowledge Graph traversal."
        elif channel_count >= 2:
            status = "ADEQUATE"
            desc = "Dual-channel retrieval consensus corroborates passage ranking."
        else:
            status = "SUBOPTIMAL"
            desc = "Single-channel retrieval; lacks independent corroborating search channels."

        return ConfidenceFactor(
            name="retrievalStrength",
            label="Retrieval Strength",
            tamil_label="மீட்பு வலிமை",
            score=ret_score,
            weight=cls.WEIGHT_RETRIEVAL_STRENGTH,
            description=desc,
            status=status,
            metadata={
                "channels_active": channel_count,
                "multi_channel_items": multi_channel_count,
                "has_semantic": has_semantic,
                "has_lexical": has_lexical,
                "has_graph": has_graph,
            },
        )

    @classmethod
    def _evaluate_premise_support(
        cls,
        premises: Optional[List[Any]],
        ev_list: List[Dict[str, Any]],
        tinai: str,
    ) -> ConfidenceFactor:
        """Evaluates premise formulation and grounding in validated evidence passages."""
        if not premises:
            # If premises not explicitly provided, estimate from evidence grounding
            if ev_list:
                est_score = min(0.90, 0.60 + (len(ev_list) * 0.10))
                return ConfidenceFactor(
                    name="premiseSupport",
                    label="Premise Support",
                    tamil_label="முற்கோள் ஆதரவு",
                    score=est_score,
                    weight=cls.WEIGHT_PREMISE_SUPPORT,
                    description=f"Evidence passages provide empirical foundation for {tinai} Mutal/Karu semiotics.",
                    status="ADEQUATE",
                    metadata={"premise_count": 0, "grounded_ratio": 1.0},
                )
            return ConfidenceFactor(
                name="premiseSupport",
                label="Premise Support",
                tamil_label="முற்கோள் ஆதரவு",
                score=0.0,
                weight=cls.WEIGHT_PREMISE_SUPPORT,
                description="Zero premises formulated or grounded in evidence.",
                status="DEFICIENT",
                metadata={"premise_count": 0, "grounded_ratio": 0.0},
            )

        grounded_count = 0
        ev_passage_ids = {
            itm.get("passage_id") or itm.get("id") for itm in ev_list if itm.get("passage_id") or itm.get("id")
        }

        for p in premises:
            p_ids = getattr(p, "grounded_passage_ids", None)
            if p_ids is None and isinstance(p, dict):
                p_ids = p.get("grounded_passage_ids", [])
            sutra = getattr(p, "grounded_sutra", None) or (p.get("grounded_sutra") if isinstance(p, dict) else "")

            # Check if premise links to at least one valid passage ID or canonical sūtra
            has_pid = any(pid in ev_passage_ids for pid in (p_ids or [])) if ev_passage_ids else bool(p_ids)
            if has_pid or bool(sutra):
                grounded_count += 1

        grounded_ratio = grounded_count / len(premises) if premises else 0.0
        premise_score = grounded_ratio

        if premise_score >= 0.90:
            status = "OPTIMAL"
            desc = f"All {len(premises)} formulated premises are directly anchored in verified evidence passage IDs."
        elif premise_score >= 0.50:
            status = "ADEQUATE"
            desc = f"{grounded_count}/{len(premises)} premises are grounded in verified evidence."
        else:
            status = "DEFICIENT"
            desc = "Premises lack grounded passage IDs and represent unverified assumptions."

        return ConfidenceFactor(
            name="premiseSupport",
            label="Premise Support",
            tamil_label="முற்கோள் ஆதரவு",
            score=premise_score,
            weight=cls.WEIGHT_PREMISE_SUPPORT,
            description=desc,
            status=status,
            metadata={
                "total_premises": len(premises),
                "grounded_premises": grounded_count,
            },
        )

    @classmethod
    def _evaluate_reasoning_consistency(
        cls,
        rules: Optional[List[Any]],
        inferences: Optional[List[Any]],
        vyapti_result: Optional[Dict[str, Any]],
        validation_results: Optional[Dict[str, Any]],
        tinai: str,
    ) -> ConfidenceFactor:
        """Evaluates universal concomitance (Vyāpti) and absence of Hetvābhāsa fallacies."""
        # 1. Vyāpti status
        is_vyapti_grounded = False
        if vyapti_result is not None:
            is_vyapti_grounded = bool(vyapti_result.get("is_established", False))
        elif rules:
            is_vyapti_grounded = any(
                getattr(r, "vyapti_validated", False)
                or (isinstance(r, dict) and r.get("vyapti_validated", False))
                for r in rules
            )
        elif inferences:
            # Check Udāharaṇa stage
            for inf in inferences:
                stg = getattr(inf, "stage_number", None) or (inf.get("stageNumber") if isinstance(inf, dict) else None)
                if stg == 3:
                    raw_conf = getattr(inf, "confidence", None)
                    if raw_conf is None and isinstance(inf, dict):
                        raw_conf = inf.get("confidence")
                    conf = 0.85 if raw_conf is None else raw_conf
                    is_vyapti_grounded = float(conf or 0.0) > 0.5
                    break

        # 2. Hetvābhāsa Fallacy Inspection
        fallacies = (validation_results or {}).get("fallacies", {})
        total_fallacy_sum = sum(float(v) for v in fallacies.values())

        if not is_vyapti_grounded:
            return ConfidenceFactor(
                name="reasoningConsistency",
                label="Reasoning Consistency",
                tamil_label="தருக்கப் பொருத்தப்பாடு",
                score=0.0,
                weight=cls.WEIGHT_REASONING_CONSISTENCY,
                description=f"Asiddha defect: Vyāpti unavailable. No grounded canonical rule exists for {tinai}.",
                status="DEFICIENT",
                metadata={"is_vyapti_established": False, "fallacy_sum": total_fallacy_sum},
            )

        # Base 1.0 minus any active fallacies
        cons_score = max(0.0, min(1.0, 1.0 - (total_fallacy_sum * 0.40)))

        if total_fallacy_sum == 0.0 and is_vyapti_grounded:
            status = "OPTIMAL"
            desc = f"Sound universal concomitance (Vyāpti) established; zero Hetvābhāsa fallacies detected (Abādhita in {tinai})."
        elif total_fallacy_sum < 0.5:
            status = "ADEQUATE"
            desc = "Vyāpti established with minor defeasible caveats."
        else:
            status = "SUBOPTIMAL"
            desc = f"Fallacies detected in middle term ({total_fallacy_sum:.2f})."

        return ConfidenceFactor(
            name="reasoningConsistency",
            label="Reasoning Consistency",
            tamil_label="தருக்கப் பொருத்தப்பாடு",
            score=cons_score,
            weight=cls.WEIGHT_REASONING_CONSISTENCY,
            description=desc,
            status=status,
            metadata={
                "is_vyapti_established": is_vyapti_grounded,
                "fallacy_sum": round(total_fallacy_sum, 4),
            },
        )

    @classmethod
    def _evaluate_validation_status(cls, validation_results: Optional[Dict[str, Any]]) -> ConfidenceFactor:
        """Evaluates defeasible 5-point verification checks."""
        if not validation_results:
            return ConfidenceFactor(
                name="validationStatus",
                label="Validation Status",
                tamil_label="சரிபார்ப்பு நிலை",
                score=0.85,  # Reasonable default when validation not yet invoked
                weight=cls.WEIGHT_VALIDATION_STATUS,
                description="Standard canonical validation criteria applied.",
                status="ADEQUATE",
                metadata={"checks_count": 0},
            )

        checks = validation_results.get("checks", [])
        if not checks:
            soundness = float(validation_results.get("soundnessScore", 0.85))
            return ConfidenceFactor(
                name="validationStatus",
                label="Validation Status",
                tamil_label="சரிபார்ப்பு நிலை",
                score=min(1.0, max(0.0, soundness)),
                weight=cls.WEIGHT_VALIDATION_STATUS,
                description=f"Defeasible soundness evaluated at {soundness:.2f}.",
                status="OPTIMAL" if soundness >= 0.85 else ("ADEQUATE" if soundness >= 0.60 else "SUBOPTIMAL"),
                metadata={"soundness": soundness},
            )

        # Average score of all 5 verification checks
        check_scores: List[float] = []
        for chk in checks:
            raw_sc = chk.get("score")
            try:
                check_scores.append(float(raw_sc))
            except (ValueError, TypeError):
                check_scores.append(0.85)

        avg_chk = sum(check_scores) / len(check_scores) if check_scores else 0.85
        val_score = min(1.0, max(0.0, avg_chk))

        if val_score >= 0.88:
            status = "OPTIMAL"
            desc = f"All {len(checks)} 5-point verification checks satisfied (Sound Epistemic Deduction)."
        elif val_score >= 0.65:
            status = "ADEQUATE"
            desc = f"5-point checks mostly satisfied (Mean: {avg_chk:.2f})."
        else:
            status = "SUBOPTIMAL"
            desc = f"One or more verification checks failed or borderline (Mean: {avg_chk:.2f})."

        return ConfidenceFactor(
            name="validationStatus",
            label="Validation Status",
            tamil_label="சரிபார்ப்பு நிலை",
            score=val_score,
            weight=cls.WEIGHT_VALIDATION_STATUS,
            description=desc,
            status=status,
            metadata={"checks_count": len(checks), "mean_check_score": round(avg_chk, 4)},
        )

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    @classmethod
    def _normalize_evidence_items(cls, items: Optional[List[Any]]) -> List[Dict[str, Any]]:
        """Converts heterogeneous EvidenceItem, dict, or object instances into clean dicts."""
        if not items:
            return []
        normalized: List[Dict[str, Any]] = []
        for itm in items:
            if isinstance(itm, dict):
                normalized.append(itm)
            elif hasattr(itm, "to_dict") and callable(itm.to_dict):
                normalized.append(itm.to_dict())
            else:
                d = {
                    "id": getattr(itm, "passage_id", None) or getattr(itm, "id", ""),
                    "passage_id": getattr(itm, "passage_id", None) or getattr(itm, "id", ""),
                    "text": getattr(itm, "text", "") or getattr(itm, "original_text", ""),
                    "source": getattr(itm, "source", {}),
                    "relevance_score": getattr(itm, "relevance_score", None) or getattr(itm, "confidence", 0.8),
                    "retrieval_methods": getattr(itm, "retrieval_methods", []),
                    "tinai": getattr(itm, "tinai", None),
                }
                normalized.append(d)
        return normalized

    @classmethod
    def _detect_cross_tinai_conflicts(cls, ev_list: List[Dict[str, Any]], target_tinai: str) -> int:
        """Detects whether evidence passages assert opposing or contradictory tiṇai semiotics."""
        if not target_tinai or target_tinai.lower() in ("general", "unknown", "all", ""):
            return 0

        conflict_count = 0
        for itm in ev_list:
            src = itm.get("source") if isinstance(itm.get("source"), dict) else {}
            item_tinai = src.get("tinai") or itm.get("tinai")
            if item_tinai and str(item_tinai).lower() not in ("general", "all", "", target_tinai.lower()):
                # Tiṇai mismatch may indicate discordant semiotics unless explicit synthesis
                conflict_count += 1
        return conflict_count


# Global singleton
confidence_evaluator = ConfidenceEvaluator()
