"""
Tests for Multilingual Grounded Hybrid RAG Pipeline.

Validates that:
1. LLM responds appropriately to Tamil, English, and mixed-language queries.
2. Detected language and original query are passed to the RAG generation layer with validated context.
3. Answer is generated primarily in the user's query language unless user explicitly overrides.
4. Classical Tamil terminology, names, and grammatical concepts are preserved accurately without translation distortion.
5. Evidence passages remain in their original Tamil form without unnecessary translation.
6. When sufficient evidence is unavailable, zero answers or citations are fabricated (returns confidence 0.0, empty keySources).
"""
import pytest
from unittest.mock import patch, MagicMock

from retrieval.language_utils import (
    detect_query_language,
    strip_diacritics,
    format_insufficient_evidence_response,
)
from llm.openrouter_client import OpenRouterClient
from llm.client import LLMClient
from retrieval.hybrid_rag_pipeline import HybridRAGPipeline
from retrieval.structured_context_builder import (
    StructuredRAGContext,
    GroundedPassageContext,
    GroundedGraphRelationship,
)


def _mock_tamil_passage():
    return GroundedPassageContext(
        passage_id="tol-porul-akam-005",
        rank=1,
        relevance_score=0.95,
        text="மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும் வேந்தன் மேய தீம்புனல் உலகமும் வருணன் மேய பெருமணல் உலகமும்",
        source_reference="Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
        work="Tolkāppiyam",
        section="Poruḷatikāram",
        chapter="Akattiṇaiyiyal",
        sutra_number=5,
        tinai="Kuṟiñci",
        entities=["மாயோன்", "சேயோன்", "வேந்தன்", "வருணன்"],
        concepts=["முதற்பொருள்", "அகத்திணை"],
        relationships=[GroundedGraphRelationship("GOVERNS_TERRITORY", "Kuṟiñci", "Cēyōṉ", "Deity")],
        retrieval_methods=["semantic_vector", "keyword_entity", "graph_traversal"],
    )


def test_language_detection_tamil_query():
    query = "குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?"
    lang_info = detect_query_language(query)

    assert lang_info["code"] == "ta"
    assert lang_info["primary_language"] == "tamil"
    assert lang_info["target_response_language"] == "tamil"
    assert lang_info["is_tamil"] is True
    assert "Mutalporuḷ" in lang_info["detected_terms"] or "Kuṟiñci" in lang_info["detected_terms"]


def test_language_detection_english_query():
    query = "How does Mutalporul govern Uripporul in Kurinci?"
    lang_info = detect_query_language(query)

    assert lang_info["code"] == "en"
    assert lang_info["primary_language"] == "english"
    assert lang_info["target_response_language"] == "english"
    assert lang_info["is_english"] is True
    assert "Mutalporuḷ" in lang_info["detected_terms"]
    assert "Uripporuḷ" in lang_info["detected_terms"]
    assert "Kuṟiñci" in lang_info["detected_terms"]


def test_explicit_user_language_override():
    # English query with explicit request for Tamil
    query_req_tamil = "Explain the ecological boundaries of Kurinci. Answer in Tamil please."
    lang_info_tamil = detect_query_language(query_req_tamil)
    assert lang_info_tamil["explicit_override"] == "tamil"
    assert lang_info_tamil["target_response_language"] == "tamil"

    # Tamil query with explicit request for English
    query_req_english = "குறிஞ்சி நிலத்தின் இயல்புகளை ஆங்கிலத்தில் விடையளிக்கவும்."
    lang_info_english = detect_query_language(query_req_english)
    assert lang_info_english["explicit_override"] == "english"
    assert lang_info_english["target_response_language"] == "english"


def test_openrouter_prompt_preserves_language_and_classical_terms():
    client = OpenRouterClient(api_key="mock-key", model="mock-model")
    passage = _mock_tamil_passage()
    ctx = StructuredRAGContext(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        is_sufficient=True,
        status="sufficient_evidence",
        evidence_passages=[passage],
        passage_count=1,
        total_characters=300,
        rendered_context=(
            "=== BEGIN CANONICAL SOURCE EVIDENCE (READ ONLY - DO NOT INVENT) ===\n"
            f"[PASSAGE 1] ID: {passage.passage_id} | {passage.source_reference}\n"
            f"Tamil Verse: {passage.text}\n"
            "=== END CANONICAL SOURCE EVIDENCE ==="
        ),
    )

    lang_info = detect_query_language("குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?")
    messages = client._build_prompt_messages(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        structured_context=ctx,
        tinai="Kuṟiñci",
        evidence_items=[],
        lang_info=lang_info,
        original_query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
    )

    system_content = messages[0]["content"]
    user_content = messages[1]["content"]

    # Verify target response language in system prompt
    assert "Target Response Language: TAMIL" in system_content
    # Verify terminology preservation directive
    assert "PRESERVE Classical Tamil terminology" in system_content
    assert "DO NOT translate original evidence passages unnecessarily" in system_content
    # Verify evidence passage remains in authentic Tamil in user message
    assert passage.text in user_content
    assert "tol-porul-akam-005" in user_content


def test_insufficient_evidence_blocks_hallucination_and_citations():
    """Verify that when evidence is insufficient, no answers are fabricated and keySources is empty."""
    lang_info_ta = detect_query_language("அறியப்படாத புதிய கருத்து 999")
    ans_ta = format_insufficient_evidence_response(lang_info_ta, "No matching sūtras found")

    assert ans_ta["confidenceScore"] == 0.0
    assert ans_ta["starsCount"] == 0.0
    assert len(ans_ta["keySources"]) == 0
    assert "சான்றுகள் கிடைக்கவில்லை" in ans_ta["tamilAnswer"]
    assert "ஊக விடைகள் தடுத்து நிறுத்தப்பட்டன" in ans_ta["justificationTamil"] or "போதிய" in ans_ta["verdictStatus"]

    lang_info_en = detect_query_language("Unknown entity not in Tolkappiyam")
    ans_en = format_insufficient_evidence_response(lang_info_en, "Below threshold")

    assert ans_en["confidenceScore"] == 0.0
    assert ans_en["starsCount"] == 0.0
    assert len(ans_en["keySources"]) == 0
    assert "Insufficient canonical evidence" in ans_en["englishAnswer"]
    assert "Speculative extrapolation without source evidence is strictly prohibited" in ans_en["justificationEnglish"] or "criteria" in ans_en["justificationEnglish"]


def test_hybrid_rag_pipeline_answer_query_integration():
    """Verify end-to-end integration: detected language, original query, and language-grounded answer."""
    pipeline = HybridRAGPipeline()
    passage = _mock_tamil_passage()

    mock_collection = MagicMock()
    mock_collection.items = [
        MagicMock(
            passage_id="tol-porul-akam-005",
            source_reference="Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
            relevance_score=0.95,
            source={"tinai": "Kuṟiñci", "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5"},
            text=passage.text,
            to_dict=lambda: {
                "passage_id": "tol-porul-akam-005",
                "text": passage.text,
                "relevance_score": 0.95,
            },
        )
    ]
    mock_collection.pipeline_version = "v2.2-multilingual"
    mock_collection.retrieval_stats = {"weights_used": {"semantic": 0.4, "lexical": 0.3, "graph": 0.3}}

    with patch.object(pipeline, "retrieve", return_value=mock_collection):
        result = pipeline.answer_query(
            query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
            original_query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
            detected_language="ta",
            top_k=2,
        )

    assert result["original_query"] == "குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?"
    assert result["detected_language"]["code"] == "ta"
    assert result["final_answer"]["confidenceScore"] > 0.8
    assert len(result["final_answer"]["keySources"]) > 0
    assert result["final_answer"]["keySources"][0]["id"] == "tol-porul-akam-005"
    assert "மாயோன் மேய காடுறை உலகமும்" in result["retrieved_evidence"][0]["text"]
