"""
Unit and Integration Tests for OpenRouter LLM Integration in Hybrid RAG Pipeline.

Verifies:
1. Strict boundary isolation: LLM receives only user query and canonical retrieved evidence.
2. Structured JSON generation adhering to FinalAnswerSchema.
3. Fallback resilience: deterministic synthesis when API key is missing or invalid.
4. Insufficient evidence handling: returns explicit insufficient_evidence status without hallucination.
5. End-to-end REST API endpoint POST /api/retrieval/answer.
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from config import Config
from llm.openrouter_client import OpenRouterClient
from retrieval.structured_context_builder import (
    StructuredRAGContext,
    GroundedPassageContext,
    GroundedGraphRelationship,
)
from retrieval.hybrid_rag_pipeline import EvidenceItem, hybrid_rag_pipeline


@pytest.fixture(scope="module")
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _create_mock_context(is_sufficient=True):
    passages = []
    if is_sufficient:
        passages.append(
            GroundedPassageContext(
                passage_id="tol-porul-akam-005",
                rank=1,
                relevance_score=0.92,
                text="மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
                source_reference="Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5",
                work="Tolkāppiyam",
                section="Poruḷatikāram",
                chapter="Akattiṇaiyiyal",
                sutra_number=5,
                tinai="Kuṟiñci",
                entities=["சேயோன்", "மாயோன்", "மைவரை"],
                concepts=["முதற்பொருள்", "அகத்திணை"],
                relationships=[GroundedGraphRelationship("ASSOCIATED_WITH", "Kuṟiñci", "Kuṟiñci", "Tiṇai")],
                retrieval_methods=["semantic_vector", "keyword_entity", "graph_traversal"],
            )
        )
    rendered = ""
    if is_sufficient:
        rendered = (
            "=== BEGIN CANONICAL SOURCE EVIDENCE (READ ONLY - DO NOT INVENT) ===\n"
            "[PASSAGE 1] (ID: tol-porul-akam-005 | Relevance: 0.9200)\n"
            "Source: Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 5\n"
            "Text (Tamil): மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...\n"
            "=== END CANONICAL SOURCE EVIDENCE ==="
        )
    else:
        rendered = (
            "=== BEGIN CANONICAL SOURCE EVIDENCE (READ ONLY - DO NOT INVENT) ===\n"
            "[NO RELEVANT CANONICAL EVIDENCE SATISFIES THRESHOLDS]\n"
            "=== END CANONICAL SOURCE EVIDENCE ==="
        )

    return StructuredRAGContext(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        is_sufficient=is_sufficient,
        status="sufficient_evidence" if is_sufficient else "insufficient_evidence",
        evidence_passages=passages,
        passage_count=len(passages),
        total_characters=len(rendered),
        min_relevance_threshold=0.30,
        min_evidence_count=1,
        insufficient_reason=None if is_sufficient else "Retrieved evidence does not satisfy minimum relevance threshold",
        rendered_context=rendered,
    )


def test_openrouter_prompt_construction_and_isolation():
    """Verify that messages sent to OpenRouter LLM contain strict boundary markers and prompt isolation."""
    client_instance = OpenRouterClient(api_key="test-key-mock", model="test-model")
    mock_context = _create_mock_context(is_sufficient=True)

    messages = client_instance._build_prompt_messages(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        structured_context=mock_context,
        tinai="Kuṟiñci",
        evidence_items=[],
    )

    assert len(messages) == 2
    system_msg = messages[0]["content"]
    user_msg = messages[1]["content"]

    # Verify anti-hallucination instructions in system prompt
    assert "DO NOT invent, extrapolate, hypothesize, or assume" in system_msg
    assert "Strictly and solely using the canonical source evidence" in system_msg or "canonical source evidence" in system_msg

    # Verify boundary isolation in user prompt
    assert "=== BEGIN CANONICAL SOURCE EVIDENCE" in user_msg
    assert "=== END CANONICAL SOURCE EVIDENCE ===" in user_msg
    assert "tol-porul-akam-005" in user_msg
    assert "மாயோன் மேய காடுறை உலகமும்" in user_msg


def test_openrouter_mock_successful_json_synthesis():
    """Verify that a valid JSON response from OpenRouter is parsed into FinalAnswerSchema."""
    client_instance = OpenRouterClient(api_key="mock-valid-key", model="google/gemini-2.5-flash")
    mock_context = _create_mock_context(is_sufficient=True)

    mock_response_payload = {
        "choices": [
            {
                "message": {
                    "content": """
                    {
                        "tamilAnswer": "சேயோன் மேய மைவரை உலகம் குறிஞ்சி நிலத்தின் முதற்பொருளாகும்.",
                        "englishAnswer": "The mountainous terrain governed by Ceyon is the primary landscape of Kurinci.",
                        "subtitle": "Tolkappiyam Akattinaiyiyal Sutra 5 canonically establishes the mountain habitat.",
                        "confidenceScore": 0.95,
                        "starsCount": 5.0,
                        "verdictStatus": "Sound Canonical Grounding",
                        "justificationTamil": "தொல்காப்பியம் அகத்திணையியல் 5 ஆம் சூத்திரம் இதனைத் தெளிவுபடுத்துகிறது.",
                        "justificationEnglish": "Tolkappiyam Akattinaiyiyal Sutra 5 explicitly grounds Kurinci in mountain terrain.",
                        "keySources": [
                            {
                                "id": "tol-porul-akam-005",
                                "label": "E1",
                                "sutra": "Sūtra 5",
                                "section": "Akattiṇaiyiyal",
                                "topic": "Kuṟiñci",
                                "score": "0.92"
                            }
                        ]
                    }
                    """
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_payload

    with patch("requests.post", return_value=mock_resp):
        res = client_instance.synthesize_grounded_answer(
            query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
            structured_context=mock_context,
            tinai="Kuṟiñci",
            evidence_records=[],
        )

        assert res.tamilAnswer == "சேயோன் மேய மைவரை உலகம் குறிஞ்சி நிலத்தின் முதற்பொருளாகும்."
        assert res.confidenceScore == 0.95
        assert len(res.keySources) == 1
        assert res.keySources[0].id == "tol-porul-akam-005"


def test_openrouter_offline_deterministic_fallback():
    """Verify fallback to deterministic synthesis when API key is unset or request fails."""
    client_instance = OpenRouterClient(api_key="", model="google/gemini-2.5-flash")
    # Force api_key to empty string in case Config picked up an env var
    client_instance.api_key = ""
    mock_context = _create_mock_context(is_sufficient=True)

    res = client_instance.synthesize_grounded_answer(
        query="குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        structured_context=mock_context,
        tinai="Kuṟiñci",
        evidence_records=[],
    )

    assert "குறிஞ்சி" in res.tamilAnswer or "tol-porul-akam-005" in res.tamilAnswer
    assert res.confidenceScore >= 0.8
    assert len(res.keySources) >= 1
    assert res.keySources[0].id == "tol-porul-akam-005"


def test_openrouter_insufficient_evidence_handling():
    """Verify that insufficient context yields an insufficient evidence answer without hallucination."""
    client_instance = OpenRouterClient(api_key="mock-key", model="google/gemini-2.5-flash")
    mock_context = _create_mock_context(is_sufficient=False)

    res = client_instance.synthesize_grounded_answer(
        query="வெளிநாட்டு விண்வெளி ஆராய்ச்சி பற்றி தொல்காப்பியம் கூறுவது யாது?",
        structured_context=mock_context,
        tinai="General",
        evidence_records=[],
    )

    assert "போதுமான" in res.tamilAnswer or "இல்லை" in res.tamilAnswer
    assert res.confidenceScore == 0.0
    assert "Insufficient" in res.verdictStatus


def test_api_retrieval_answer_endpoint_success(client):
    """Test POST /api/retrieval/answer with a valid classical query."""
    payload = {
        "query": "குறிஞ்சி நிலத்தின் முதற்பொருள் யாது?",
        "top_k": 3,
        "max_graph_depth": 2,
    }
    resp = client.post("/api/retrieval/answer", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    res_data = data["data"]

    assert "final_answer" in res_data
    assert "retrieved_evidence" in res_data
    assert "sources" in res_data
    assert "confidence_info" in res_data
    assert "reasoning_metadata" in res_data
    assert res_data["reasoning_metadata"]["provider"] == "openrouter"

    final_ans = res_data["final_answer"]
    assert "tamilAnswer" in final_ans
    assert "englishAnswer" in final_ans
    assert "keySources" in final_ans


def test_api_retrieval_answer_endpoint_empty_query(client):
    """Test POST /api/retrieval/answer error handling on empty query."""
    resp = client.post("/api/retrieval/answer", json={"query": ""})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_QUERY"
