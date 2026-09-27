"""
Structured Logical Reasoning Models for Nyāya Neuro-Symbolic Inference.

Defines typed dataclasses for the five-stage Pañcāvayava deduction:
- PremiseNode: Grounded factual premise derived from validated evidence
- RuleNode: First-order logic Vyāpti rule connecting signifiers with affect
- InferenceNode: Intermediate or stage-specific inference step
- ConclusionNode: Verified Nigamana verdict with provenance
- ReasoningTrace: Complete structured deduction DAG with Neo4j persistence readiness
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PremiseNode:
    """
    Epistemic premise directly derived from retrieved and validated evidence.
    Mapped to Neo4j (:Premise:KGNode) nodes.
    """
    id: str
    label: str
    statement: str
    formal_logic: str
    pramana_mode: str
    grounded_passage_ids: List[str]
    grounded_sutra: str
    tinai: str
    type: str = "Premise"
    tamil_statement: str = ""
    concept_category: str = "General"  # Mutalporuḷ, Karupporuḷ, Uripporuḷ
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "statement": self.statement,
            "tamil_statement": self.tamil_statement,
            "formal_logic": self.formal_logic,
            "pramana_mode": self.pramana_mode,
            "grounded_passage_ids": self.grounded_passage_ids,
            "grounded_sutra": self.grounded_sutra,
            "tinai": self.tinai,
            "concept_category": self.concept_category,
            "confidence": round(self.confidence, 4),
        }

    def to_neo4j_params(self) -> Dict[str, Any]:
        """Formats properties for Cypher MERGE (p:Premise:KGNode {id: $id})."""
        return {
            "id": self.id,
            "label": self.label,
            "type": "Premise",
            "hierarchy_level": "L4",
            "statement": self.statement,
            "tamil_statement": self.tamil_statement,
            "formal_logic": self.formal_logic,
            "pramana_mode": self.pramana_mode,
            "grounded_sutra": self.grounded_sutra,
            "tinai": self.tinai,
            "concept_category": self.concept_category,
            "confidence": float(self.confidence),
            "source": self.grounded_sutra,
            "metadata_json": json.dumps({
                "grounded_passage_ids": self.grounded_passage_ids,
            }, ensure_ascii=False),
        }


@dataclass
class CandidateVyapti:
    """
    Candidate Vyāpti representation maintained during the Vyāpti identification stage:
    {
      "rule": "...",
      "source": "...",
      "evidence": "...",
      "confidence": 0.0,
      "status": "grounded"
    }
    """
    rule: str
    source: str
    evidence: str
    confidence: float = 0.0
    status: str = "grounded"  # "grounded" | "ungrounded" | "candidate" | "Vyāpti unavailable"
    passage_id: Optional[str] = None
    tinai: Optional[str] = None
    antecedents: List[str] = field(default_factory=list)
    consequent: Optional[str] = None
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Returns the canonical 5-field dictionary as specified."""
        return {
            "rule": self.rule,
            "source": self.source,
            "evidence": self.evidence,
            "confidence": round(float(self.confidence), 4),
            "status": self.status,
        }

    def to_extended_dict(self) -> Dict[str, Any]:
        """Extended dictionary with passage_id, tinai, antecedents, consequent, and validation details."""
        base = self.to_dict()
        base.update({
            "passage_id": self.passage_id,
            "tinai": self.tinai,
            "antecedents": self.antecedents,
            "consequent": self.consequent,
            "validation_details": self.validation_details,
        })
        return base


@dataclass
class RuleNode:
    """
    Universal invariant concomitance rule (Vyāpti Horn-clause).
    Mapped to Neo4j (:Rule:KGNode) nodes.
    """
    id: str
    label: str
    rule_id: str
    rule_name: str
    antecedents: List[str]
    consequent: str
    formal_logic: str
    exemplar_sutra: str
    tinai: str
    type: str = "Rule"
    vyapti_validated: bool = True
    vyapti_status: str = "grounded"  # "grounded" | "Vyāpti unavailable" | "ungrounded"
    candidate_vyapti: Optional[Dict[str, Any]] = None
    matched_antecedents: List[str] = field(default_factory=list)
    missing_antecedents: List[str] = field(default_factory=list)
    evidence_support_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "antecedents": self.antecedents,
            "consequent": self.consequent,
            "formal_logic": self.formal_logic,
            "exemplar_sutra": self.exemplar_sutra,
            "tinai": self.tinai,
            "vyapti_validated": self.vyapti_validated,
            "vyapti_status": self.vyapti_status,
            "candidate_vyapti": self.candidate_vyapti,
            "matched_antecedents": self.matched_antecedents,
            "missing_antecedents": self.missing_antecedents,
            "evidence_support_ids": self.evidence_support_ids,
            "confidence": round(self.confidence, 4),
        }

    def to_neo4j_params(self) -> Dict[str, Any]:
        """Formats properties for Cypher MERGE (r:Rule:KGNode {id: $id})."""
        return {
            "id": self.id,
            "label": self.label,
            "type": "Rule",
            "hierarchy_level": "L4",
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "formal_logic": self.formal_logic,
            "consequent": self.consequent,
            "exemplar_sutra": self.exemplar_sutra,
            "tinai": self.tinai,
            "confidence": float(self.confidence),
            "source": self.exemplar_sutra,
            "metadata_json": json.dumps({
                "antecedents": self.antecedents,
                "matched_antecedents": self.matched_antecedents,
                "missing_antecedents": self.missing_antecedents,
                "vyapti_validated": self.vyapti_validated,
                "evidence_support_ids": self.evidence_support_ids,
            }, ensure_ascii=False),
        }


@dataclass
class InferenceNode:
    """
    One of the five classical Pañcāvayava syllogism members:
    1. Pratijñā (Proposition)
    2. Hetu (Reason)
    3. Udāharaṇa (Universal Rule / Exemplar)
    4. Upanaya (Application / Subsumption)
    5. Nigamana (Conclusion)
    Mapped to Neo4j (:Inference:KGNode) nodes.
    """
    id: str
    label: str
    stage_number: int
    sanskrit_name: str
    tamil_name: str
    english_role: str
    full_title: str
    tamil_reasoning_text: str
    english_interpretation: str
    formal_logic: str
    epistemic_grounding: str
    pramana_mode: str
    fallacy_check: str
    linked_evidence_ids: List[str]
    type: str = "Inference"
    in_depth_explanation: str = ""
    premise_ids: List[str] = field(default_factory=list)
    rule_ids: List[str] = field(default_factory=list)
    hop_depth: int = 0
    confidence: float = 0.98

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "stageNumber": self.stage_number,
            "sanskritName": self.sanskrit_name,
            "tamilName": self.tamil_name,
            "englishRole": self.english_role,
            "fullTitle": self.full_title,
            "tamilReasoningText": self.tamil_reasoning_text,
            "englishInterpretation": self.english_interpretation,
            "formalLogic": self.formal_logic,
            "epistemicGrounding": self.epistemic_grounding,
            "pramanaMode": self.pramana_mode,
            "fallacyCheck": self.fallacy_check,
            "linkedEvidenceId": self.linked_evidence_ids[0] if self.linked_evidence_ids else "",
            "linkedEvidenceIds": self.linked_evidence_ids,
            "inDepthExplanation": self.in_depth_explanation,
            "premiseIds": self.premise_ids,
            "ruleIds": self.rule_ids,
            "hopDepth": self.hop_depth,
            "confidence": round(self.confidence, 4),
        }

    def to_neo4j_params(self) -> Dict[str, Any]:
        """Formats properties for Cypher MERGE (i:Inference:KGNode {id: $id})."""
        return {
            "id": self.id,
            "label": self.label,
            "type": "Inference",
            "hierarchy_level": "L4",
            "stage_number": int(self.stage_number),
            "sanskrit_name": self.sanskrit_name,
            "tamil_name": self.tamil_name,
            "english_role": self.english_role,
            "formal_logic": self.formal_logic,
            "pramana_mode": self.pramana_mode,
            "fallacy_check": self.fallacy_check,
            "hop_depth": int(self.hop_depth),
            "confidence": float(self.confidence),
            "source": self.epistemic_grounding,
            "metadata_json": json.dumps({
                "tamil_reasoning_text": self.tamil_reasoning_text,
                "english_interpretation": self.english_interpretation,
                "linked_evidence_ids": self.linked_evidence_ids,
                "premise_ids": self.premise_ids,
                "rule_ids": self.rule_ids,
            }, ensure_ascii=False),
        }


@dataclass
class ConclusionNode:
    """
    Synthesized final epistemic verdict (Nigamana).
    Mapped to Neo4j (:Conclusion:KGNode) nodes.
    """
    id: str
    label: str
    statement: str
    formal_logic: str
    soundness_score: float
    tinai: str
    supporting_evidence_ids: List[str]
    inference_ids: List[str]
    type: str = "Conclusion"
    tamil_statement: str = ""
    epistemic_verdict: str = "Sound Canonical Invariance (தொல்காப்பிய முறைமை நெறி)"
    confidence: float = 0.98

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "statement": self.statement,
            "tamil_statement": self.tamil_statement,
            "formal_logic": self.formal_logic,
            "soundness_score": round(self.soundness_score, 4),
            "tinai": self.tinai,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "inference_ids": self.inference_ids,
            "epistemic_verdict": self.epistemic_verdict,
            "confidence": round(self.confidence, 4),
        }

    def to_neo4j_params(self) -> Dict[str, Any]:
        """Formats properties for Cypher MERGE (c:Conclusion:KGNode {id: $id})."""
        return {
            "id": self.id,
            "label": self.label,
            "type": "Conclusion",
            "hierarchy_level": "L4",
            "statement": self.statement,
            "tamil_statement": self.tamil_statement,
            "formal_logic": self.formal_logic,
            "soundness_score": float(self.soundness_score),
            "tinai": self.tinai,
            "confidence": float(self.confidence),
            "epistemic_verdict": self.epistemic_verdict,
            "metadata_json": json.dumps({
                "supporting_evidence_ids": self.supporting_evidence_ids,
                "inference_ids": self.inference_ids,
            }, ensure_ascii=False),
        }


@dataclass
class ReasoningTrace:
    """
    Complete structured reasoning DAG containing all derived nodes,
    validation checks, proof nodes, and multi-hop paths.
    """
    query: str
    session_id: str
    tinai: str
    premises: List[PremiseNode] = field(default_factory=list)
    rules: List[RuleNode] = field(default_factory=list)
    inferences: List[InferenceNode] = field(default_factory=list)
    conclusion: Optional[ConclusionNode] = None
    proof_nodes: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    hop_count: int = 0
    evidence_ids_used: List[str] = field(default_factory=list)
    vyapti_identification: Optional[Dict[str, Any]] = None
    case_evidence: List[Dict[str, Any]] = field(default_factory=list)
    vyapti_evidence: List[Dict[str, Any]] = field(default_factory=list)
    application_evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sessionId": self.session_id,
            "detectedTinai": self.tinai,
            "premises": [p.to_dict() for p in self.premises],
            "rules": [r.to_dict() for r in self.rules],
            "reasoningStages": [i.to_dict() for i in self.inferences],
            "conclusion": self.conclusion.to_dict() if self.conclusion else None,
            "proofNodes": self.proof_nodes,
            "validationResults": self.validation,
            "hopCount": self.hop_count,
            "evidenceIdsUsed": self.evidence_ids_used,
            "vyaptiIdentification": self.vyapti_identification,
            "caseEvidence": self.case_evidence,
            "vyaptiEvidence": self.vyapti_evidence,
            "applicationEvidence": self.application_evidence,
        }

    def to_neo4j_graph(self) -> Dict[str, Any]:
        """
        Builds batch nodes and relationship edges for Neo4j persistence.
        Nodes: :Premise, :Rule, :Inference, :Conclusion
        Relationships:
        - (:Premise)-[:SUPPORTED_BY]->(:Passage)
        - (:Rule)-[:SUPPORTED_BY]->(:Passage)
        - (:Inference)-[:DERIVED_FROM]->(:Premise)
        - (:Inference)-[:SUB_SUMES]->(:Rule)
        - (:Conclusion)-[:DERIVED_FROM]->(:Inference)
        """
        nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        for p in self.premises:
            nodes.append({"label": "Premise", "params": p.to_neo4j_params()})
            for pid in p.grounded_passage_ids:
                relationships.append({
                    "source_id": p.id,
                    "target_id": pid,
                    "rel_type": "SUPPORTED_BY",
                    "properties": {"confidence": p.confidence},
                })

        for r in self.rules:
            nodes.append({"label": "Rule", "params": r.to_neo4j_params()})
            for pid in r.evidence_support_ids:
                relationships.append({
                    "source_id": r.id,
                    "target_id": pid,
                    "rel_type": "SUPPORTED_BY",
                    "properties": {"confidence": r.confidence},
                })

        for inf in self.inferences:
            nodes.append({"label": "Inference", "params": inf.to_neo4j_params()})
            for prem_id in inf.premise_ids:
                relationships.append({
                    "source_id": inf.id,
                    "target_id": prem_id,
                    "rel_type": "DERIVED_FROM",
                    "properties": {"confidence": inf.confidence},
                })
            for rule_id in inf.rule_ids:
                relationships.append({
                    "source_id": inf.id,
                    "target_id": rule_id,
                    "rel_type": "SUB_SUMES",
                    "properties": {"confidence": inf.confidence},
                })
            for evid in inf.linked_evidence_ids:
                relationships.append({
                    "source_id": inf.id,
                    "target_id": evid,
                    "rel_type": "SUPPORTED_BY",
                    "properties": {"confidence": inf.confidence},
                })

        if self.conclusion:
            nodes.append({"label": "Conclusion", "params": self.conclusion.to_neo4j_params()})
            for inf_id in self.conclusion.inference_ids:
                relationships.append({
                    "source_id": self.conclusion.id,
                    "target_id": inf_id,
                    "rel_type": "DERIVED_FROM",
                    "properties": {"confidence": self.conclusion.confidence},
                })

        return {
            "nodes": nodes,
            "relationships": relationships,
        }


@dataclass
class ProofTraceStep:
    """
    Structured step in the graphical proof trace connecting an evidence item,
    premise, rule, or inference to the downstream conclusion.
    """
    id: str
    type: str  # Evidence | Premise | Rule | Inference | Conclusion
    name: str
    source_reference: str
    passage_id: Optional[str] = None
    relationship_to_next: Optional[str] = None
    relationship_label: Optional[str] = None
    target_step_id: Optional[str] = None
    explanation: str = ""
    formal_logic: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "sourceReference": self.source_reference,
            "source_reference": self.source_reference,
            "passageId": self.passage_id,
            "passage_id": self.passage_id,
            "relationshipToNext": self.relationship_to_next,
            "relationship_to_next": self.relationship_to_next,
            "relationshipLabel": self.relationship_label,
            "relationship_label": self.relationship_label,
            "targetStepId": self.target_step_id,
            "target_step_id": self.target_step_id,
            "explanation": self.explanation,
            "formalLogic": self.formal_logic,
            "formal_logic": self.formal_logic,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class ProofTraceEdge:
    """
    Directed edge in the graphical proof trace DAG.
    Directly compatible with Cytoscape.js and React frontend edge representations.
    """
    id: str
    source: str
    target: str
    label: str
    type: str
    relation: str
    confidence: float = 0.98
    isProofTraceEdge: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "type": self.type,
            "relation": self.relation,
            "confidence": round(self.confidence, 4),
            "isProofTraceEdge": self.isProofTraceEdge,
        }


@dataclass
class ProofTracePayload:
    """
    Complete machine-readable JSON payload representing a graphical proof trace.
    Explicitly returns an insufficient-evidence state if required evidence is missing.
    """
    status: str  # VALID_PROOF | INSUFFICIENT_EVIDENCE
    query: str
    tinai: str
    is_valid: bool
    insufficient_evidence: bool
    reason: Optional[str] = None
    missing_requirements: List[str] = field(default_factory=list)
    steps: List[ProofTraceStep] = field(default_factory=list)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    traceable_paths: List[List[str]] = field(default_factory=list)
    evidence_count: int = 0
    conclusion_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "tinai": self.tinai,
            "isValid": self.is_valid,
            "is_valid": self.is_valid,
            "insufficientEvidence": self.insufficient_evidence,
            "insufficient_evidence": self.insufficient_evidence,
            "reason": self.reason,
            "missingRequirements": self.missing_requirements,
            "missing_requirements": self.missing_requirements,
            "steps": [s.to_dict() for s in self.steps],
            "traceSteps": [s.to_dict() for s in self.steps],
            "proofNodes": self.nodes,
            "nodes": self.nodes,
            "proofEdges": self.edges,
            "edges": self.edges,
            "traceablePaths": self.traceable_paths,
            "traceable_paths": self.traceable_paths,
            "evidenceCount": self.evidence_count,
            "evidence_count": self.evidence_count,
            "conclusionId": self.conclusion_id,
            "conclusion_id": self.conclusion_id,
        }
