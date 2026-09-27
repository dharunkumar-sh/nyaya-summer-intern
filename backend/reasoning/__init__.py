"""Nyāya neuro-symbolic reasoning package implementing Pañcāvayava deduction and Hetvābhāsa verification."""
from .models import (
    PremiseNode,
    RuleNode,
    InferenceNode,
    ConclusionNode,
    ReasoningTrace,
    ProofTraceStep,
    ProofTraceEdge,
    ProofTracePayload,
    CandidateVyapti,
)
from .premise_builder import PremiseBuilder, EvidenceGroundedPremiseBuilder
from .rule_engine import TinaiRuleEngine
from .nyaya_engine import NyayaReasoner
from .proof_trace import ProofTraceGenerator
from .validator import DefeasibleValidator
from .vyapti_identifier import (
    VyaptiValidationCriteria,
    VyaptiIdentifier,
    vyapti_identifier,
)

__all__ = [
    "PremiseNode",
    "RuleNode",
    "InferenceNode",
    "ConclusionNode",
    "ReasoningTrace",
    "ProofTraceStep",
    "ProofTraceEdge",
    "ProofTracePayload",
    "CandidateVyapti",
    "PremiseBuilder",
    "EvidenceGroundedPremiseBuilder",
    "TinaiRuleEngine",
    "NyayaReasoner",
    "ProofTraceGenerator",
    "DefeasibleValidator",
    "VyaptiValidationCriteria",
    "VyaptiIdentifier",
    "vyapti_identifier",
]
