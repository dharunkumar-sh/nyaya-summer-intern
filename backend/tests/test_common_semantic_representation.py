"""
Unit and integration tests for the Multilingual Common Semantic Representation
in the Query Center backend for Classical Tamil Literature (Tolkāppiyam).

Tests verify:
1. Multilingual Query Normalization and Language Detection (Tamil, English, Mixed)
2. Preserving authentic Tamil terminology (native Tamil Unicode script + canonical forms)
   without forcing Tamil into English-only keywords
3. Shared Semantic Space & Multilingual Embedding Generation
4. Cross-lingual Semantic Equivalence (English query vs Tamil query high cosine similarity)
5. Unified Retrieval Representation schema:
   - original_query
   - detected_language
   - normalized_query
   - identified_entities / identified_concepts
   - retrieval_representation
6. Query Center API Endpoints:
   - POST /api/query/preprocess
   - POST /api/query/representation
   - POST /api/query/semantic-representation
"""
import math
import pytest
from app import create_app
from query.query_preprocessor import QueryPreprocessingService, query_preprocessor, ProcessedQuery
from retrieval.embeddings import get_embedding_generator


@pytest.fixture
def client():
    """Create a Flask test client."""
    app = create_app("testing")
    with app.test_client() as c:
        yield c


def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two 1D float vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class TestMultilingualNormalizationAndLanguageDetection:
    """Verify normalization and language detection across Tamil, English, and Mixed inputs."""

    def test_pure_tamil_normalization(self):
        query = "  குறிஞ்சி நிலத்தின்   உரிப்பொருள் யாது?  "
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.original_query == query
        assert processed.normalized_query == "குறிஞ்சி நிலத்தின் உரிப்பொருள் யாது"
        assert processed.detected_language == "tamil"
        assert processed.is_tamil is True
        assert processed.is_english is False
        assert processed.is_mixed is False

    def test_pure_english_normalization(self):
        query = "What is the affective mood of the Kurinji landscape?"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.original_query == query
        assert processed.normalized_query == "What is the affective mood of the Kurinji landscape"
        assert processed.detected_language == "english"
        assert processed.is_english is True
        assert processed.is_tamil is False
        assert processed.is_mixed is False

    def test_mixed_language_normalization(self):
        query = "Explain வழுவமைதி (vaḻuvamaiti) grammatical exceptions in Tolkāppiyam"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.original_query == query
        assert "வழுவமைதி" in processed.normalized_query
        assert processed.detected_language == "mixed"
        assert processed.is_mixed is True


class TestTamilTerminologyPreservation:
    """Verify that Tamil terminology is preserved in native Tamil script without being forced into English-only keywords."""

    def test_native_tamil_script_preserved_for_grammatical_concept(self):
        query = "Tolkappiyam rules on vazhuvamaiti"
        processed = QueryPreprocessingService.preprocess(query)

        concepts = processed.identified_concepts
        assert len(concepts) > 0

        # Must have preserved Tamil term in native script
        vazhuvamaiti = next((c for c in concepts if c.get("canonical") in ("Vaḻuvamaiti", "vazhuvamaiti") or c.get("kg_id") == "valuvamaiti"), None)
        assert vazhuvamaiti is not None, "vazhuvamaiti concept should be extracted"
        assert vazhuvamaiti.get("tamil_term") == "வழுவமைதி", "Must preserve native Tamil script"
        assert "வழுவமைதி" in processed.preserved_tamil_terms

    def test_native_tamil_script_preserved_for_poetics_landscape(self):
        tamil_query = "முல்லை நிலத்தின் தெய்வம் மாயோன்"
        processed = QueryPreprocessingService.preprocess(tamil_query)

        # Both Mullai and Mayon should retain native Tamil script
        entities = processed.identified_entities
        concepts = processed.identified_concepts
        all_items = entities + concepts

        tamil_scripts = [item.get("tamil_term") for item in all_items if item.get("tamil_term")]
        assert "முல்லை" in tamil_scripts or "முல்லை" in processed.preserved_tamil_terms
        assert "மாயோன்" in tamil_scripts or "மாயோன்" in processed.preserved_tamil_terms

    def test_not_forced_into_english_only_keywords(self):
        query = "Explain உரிப்பொருள் in அகத்திணை"
        processed = QueryPreprocessingService.preprocess(query)

        # Keywords / bm25 tokens should include Tamil tokens, not just English translations
        assert any("உரிப்பொருள்" in tok or "அகத்திணை" in tok for tok in processed.bm25_tokens)
        # Preserved Tamil terms list must be populated
        assert len(processed.preserved_tamil_terms) >= 1
        assert "உரிப்பொருள்" in processed.preserved_tamil_terms or "அகத்திணை" in processed.preserved_tamil_terms


class TestSharedSemanticSpaceAndEmbedding:
    """Verify the shared multilingual semantic space and cross-lingual equivalence."""

    def test_retrieval_representation_metadata(self):
        query = "What is the affective mood of the Kurinji landscape?"
        processed = QueryPreprocessingService.preprocess(query)

        repr_payload = processed.retrieval_representation
        assert repr_payload is not None
        assert "embedding" in repr_payload
        assert isinstance(repr_payload["embedding"], list)
        assert len(repr_payload["embedding"]) > 0
        assert repr_payload["vector_dimension"] == len(repr_payload["embedding"])
        assert repr_payload["shared_space"] is True
        assert "common_semantic_query" in repr_payload
        assert len(repr_payload["common_semantic_query"]) > 0

    def test_cross_lingual_semantic_similarity(self):
        """
        Verify that equivalent queries in English and Tamil:
        - English: 'What is the affective mood of the Kurinji landscape?'
        - Tamil: 'குறிஞ்சி நிலத்தின் உரிப்பொருள் யாது?'
        yield high cosine similarity (> 0.70) in the shared semantic space.
        """
        en_query = "What is the affective mood of the Kurinji landscape?"
        ta_query = "குறிஞ்சி நிலத்தின் உரிப்பொருள் யாது?"

        en_processed = QueryPreprocessingService.preprocess(en_query)
        ta_processed = QueryPreprocessingService.preprocess(ta_query)

        en_vec = en_processed.retrieval_representation["embedding"]
        ta_vec = ta_processed.retrieval_representation["embedding"]

        similarity = cosine_similarity(en_vec, ta_vec)
        assert similarity >= 0.70, (
            f"Cross-lingual cosine similarity {similarity:.4f} between English and Tamil equivalent "
            f"queries should be >= 0.70 in the shared semantic space"
        )

    def test_grammatical_cross_lingual_equivalence(self):
        """
        Verify cross-lingual alignment for Tolkappiyam grammatical exceptions (வழுவமைதி / vazhuvamaiti).
        """
        en_query = "Tolkappiyam grammatical exceptions and error tolerance"
        ta_query = "தொல்காப்பியத்தில் வழுவமைதி விதிகள்"

        en_processed = QueryPreprocessingService.preprocess(en_query)
        ta_processed = QueryPreprocessingService.preprocess(ta_query)

        en_vec = en_processed.retrieval_representation["embedding"]
        ta_vec = ta_processed.retrieval_representation["embedding"]

        similarity = cosine_similarity(en_vec, ta_vec)
        assert similarity >= 0.60, (
            f"Cross-lingual grammatical cosine similarity {similarity:.4f} should be >= 0.60"
        )


class TestUnifiedResponseContract:
    """Verify dictionary outputs strictly follow the required fields."""

    def test_to_dict_includes_all_required_fields(self):
        query = "Explain Varuṉaṉ deity of Neytal landscape in Tolkāppiyam"
        processed = QueryPreprocessingService.preprocess(query)
        data = processed.to_dict()

        # Core required top-level fields
        assert "original_query" in data
        assert data["original_query"] == query
        assert "detected_language" in data
        assert data["detected_language"] in ("tamil", "english", "mixed")
        assert "normalized_query" in data
        assert "identified_entities" in data
        assert "identified_concepts" in data
        assert "identified_entities_concepts" in data
        assert "retrieval_representation" in data

        # Retrieval representation inner fields
        repr_data = data["retrieval_representation"]
        assert "embedding" in repr_data
        assert "vector_dimension" in repr_data
        assert "model_name" in repr_data
        assert "shared_space" in repr_data
        assert repr_data["shared_space"] is True
        assert "common_semantic_query" in repr_data
        assert "preserved_tamil_terms" in repr_data


class TestQueryCenterAPIEndpoints:
    """Verify Flask API endpoints handle multilingual queries and return common semantic representations."""

    def test_api_preprocess_endpoint(self, client):
        res = client.post("/api/query/preprocess", json={"query": "குறிஞ்சி நிலத்தின் உரிப்பொருள்"})
        assert res.status_code == 200
        data = res.get_json()

        assert data.get("success") is True
        payload = data["data"]
        assert payload["original_query"] == "குறிஞ்சி நிலத்தின் உரிப்பொருள்"
        assert payload["detected_language"] == "tamil"
        assert "retrieval_representation" in payload
        assert payload["retrieval_representation"]["shared_space"] is True

    def test_api_representation_endpoint(self, client):
        res = client.post(
            "/api/query/representation",
            json={"query": "What are the கருப்பொருள் elements of Neytal terrain?"}
        )
        assert res.status_code == 200
        data = res.get_json()

        assert data.get("success") is True
        payload = data["data"]
        assert payload["original_query"] == "What are the கருப்பொருள் elements of Neytal terrain?"
        assert payload["detected_language"] == "mixed"
        assert "retrieval_representation" in payload
        assert "embedding" in payload["retrieval_representation"]
        assert len(payload["retrieval_representation"]["embedding"]) > 0

    def test_api_semantic_representation_alias(self, client):
        res = client.post(
            "/api/query/semantic-representation",
            json={"query": "தொல்காப்பிய எழுத்ததிகாரம்"}
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True
        assert data["data"]["detected_language"] == "tamil"
