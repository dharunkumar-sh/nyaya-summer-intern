"""
Pydantic schemas ensuring deterministic JSON outputs matching frontend expectations.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class KeySourceSchema(BaseModel):
    id: str
    label: str
    sutra: str
    section: str
    topic: str
    score: str


class FinalAnswerSchema(BaseModel):
    tamilAnswer: str = Field(description="Direct definitive conclusion in Classical Tamil")
    englishAnswer: str = Field(description="Scholarly English translation of the verdict")
    subtitle: str = Field(description="Concise subtitle summarizing semiotic causality")
    confidenceScore: float = Field(default=0.98, ge=0.0, le=1.0)
    starsCount: float = Field(default=5.0)
    verdictStatus: str = Field(default="Sound Canonical Invariance (தொல்காப்பிய முறைமை நெறி)")
    justificationTamil: str = Field(description="Formal Tamil justification (தமிழ் விளக்கம்)")
    justificationEnglish: str = Field(description="Scholarly English synthesis")
    keySources: List[KeySourceSchema] = Field(default_factory=list)


class ReasoningResponseSchema(BaseModel):
    queryText: str
    detectedTinai: str
    evidenceRecords: List[Dict[str, Any]]
    knowledgeGraph: Dict[str, Any]
    reasoningStages: List[Dict[str, Any]]
    validationResults: Dict[str, Any]
    proofNodes: List[Dict[str, Any]]
    finalAnswer: FinalAnswerSchema
