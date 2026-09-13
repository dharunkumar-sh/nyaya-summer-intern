"""
Unit tests for the dedicated QueryPreprocessingService in Classical Tamil Literature search.
Tests cover:
- Preserving original query untouched
- Safe Unicode NFC normalization and noise stripping
- Pure Tamil, pure English, and Mixed-Language detection
- Classical Tamil literary terminology preservation
- Source citation and sūtra reference extraction
- Downstream channel payloads (BM25, Vector, Knowledge Graph)
- POST /api/query/preprocess API endpoint
"""
import pytest
from app import create_app
from query.query_preprocessor import QueryPreprocessingService, query_preprocessor, ProcessedQuery


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


class TestQueryPreprocessorNormalization:
    """Tests for safe Unicode normalization and noise removal."""

    def test_preserves_original_query_unaltered(self):
        raw = "  Explain   முதற்பொருள் (Mutalporuḷ)  &   Karupporuḷ!??  #Akam   "
        processed = QueryPreprocessingService.preprocess(raw)

        # Original query must be completely untouched
        assert processed.original_query == raw
        # Normalized query must be clean
        assert "  " not in processed.normalized_query
        assert processed.normalized_query.startswith("Explain")
        assert processed.normalized_query.endswith("#Akam")

    def test_nfc_and_zero_width_character_removal(self):
        # Text with zero-width space (\u200b) and zero-width joiner (\u200d)
        dirty = "குறிஞ்சி\u200b நிலம்\u200d"
        processed = QueryPreprocessingService.preprocess(dirty)

        assert "\u200b" not in processed.normalized_query
        assert "\u200d" not in processed.normalized_query
        assert "குறிஞ்சி நிலம்" in processed.normalized_query

    def test_virama_and_typography_normalization(self):
        # Typographical curly quotes and em-dash
        text = "“Tolkāppiyam”—Akattiṇaiyiyal ‘Sūtra 5’"
        processed = QueryPreprocessingService.preprocess(text)

        assert '"' in processed.normalized_query or "'" in processed.normalized_query
        assert "—" not in processed.normalized_query
        assert "Tolkāppiyam" in processed.normalized_query

    def test_empty_query_handling(self):
        processed = QueryPreprocessingService.preprocess("   ")
        assert processed.original_query == "   "
        assert processed.normalized_query == ""
        assert processed.language == "unknown"
        assert processed.bm25_tokens == []
        assert "mutalporul" in processed.kg_seed_node_ids


class TestLanguageAndScriptDetection:
    """Tests for detecting Tamil, English, or Mixed-Language queries."""

    def test_pure_tamil_detection(self):
        query = "குறிஞ்சி நிலத்தின் முதற்பொருள் கருப்பொருள் உரிப்பொருள் யாவை?"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.language == "tamil"
        assert processed.language_code == "ta"
        assert processed.is_tamil is True
        assert processed.is_english is False
        assert processed.is_mixed is False
        assert processed.tamil_ratio > 0.85

    def test_pure_english_detection(self):
        query = "How do environmental signifiers govern human interiority in Sangam poetics?"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.language == "english"
        assert processed.language_code == "en"
        assert processed.is_english is True
        assert processed.is_tamil is False
        assert processed.is_mixed is False
        assert processed.english_ratio > 0.85

    def test_mixed_language_detection(self):
        query = "Explain முதற்பொருள் and karupporul in Kuṟiñci terrain according to Tolkāppiyam"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.language == "mixed"
        assert processed.language_code == "ta-en"
        assert processed.is_mixed is True
        assert processed.is_tamil is False
        assert processed.is_english is False
        assert processed.tamil_ratio > 0.05
        assert processed.english_ratio > 0.50

    def test_iso15919_transliteration_detection(self):
        query = "Cēyōṉ maivarai ulakam puṇartal"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.language == "english" or processed.language == "mixed"
        assert "ISO 15919" in processed.script or processed.is_english


class TestLiteraryTerminologyAndTiṇai:
    """Tests for domain terminology preservation and Tiṇai identification."""

    def test_preserves_classical_terms_in_keywords(self):
        query = "What is the Vyāpti rule between Cēyōṉ and Kuṟiñci in Tolkāppiyam?"
        processed = QueryPreprocessingService.preprocess(query)

        # Canonical terms must be extracted
        term_canonicals = [t["canonical"] for t in processed.literary_terms]
        assert "Vyāpti" in term_canonicals
        assert "Cēyōṉ" in term_canonicals
        assert "Kuṟiñci" in term_canonicals
        assert "Tolkāppiyam" in term_canonicals

        # Literary terms must be in keywords and bm25_tokens
        assert any("vyāpti" in k.lower() or "vyapti" in k.lower() for k in processed.keywords)
        assert any("cēyōṉ" in k.lower() or "ceyon" in k.lower() for k in processed.keywords)

    def test_resolves_primary_tinai_kurinci(self):
        query = "சேயோன் மேய மைவரை உலகம் புணர்தல் நிமித்தம்"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.detected_tinai == "Kuṟiñci"
        assert "kurinci" in processed.kg_seed_node_ids
        assert "ceyon" in processed.kg_seed_node_ids

    def test_resolves_primary_tinai_mullai(self):
        query = "மாயோன் மேய காடுறை உலகம் மற்றும் முல்லை ஒழுக்கம்"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.detected_tinai == "Mullai"
        assert "mullai" in processed.kg_seed_node_ids
        assert "mayon" in processed.kg_seed_node_ids

    def test_resolves_primary_tinai_marutam(self):
        query = "வேந்தன் மேய தீம்புனல் உலகம் மற்றும் ஊடல் நிமித்தம்"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.detected_tinai == "Marutam"
        assert "marutam" in processed.kg_seed_node_ids

    def test_resolves_primary_tinai_neytal(self):
        query = "வருணன் மேய பெருமணல் உலகம் மற்றும் இரங்கல் ஒழுக்கம்"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.detected_tinai == "Neytal"
        assert "neytal" in processed.kg_seed_node_ids


class TestSourceReferenceParsing:
    """Tests for parsing sūtra citations and chapter names."""

    def test_parses_english_sutra_citation(self):
        query = "What is formulated in Tolkāppiyam Akattiṇaiyiyal Sūtra 5?"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.has_source_filter is True
        assert len(processed.source_references) >= 1
        ref = processed.source_references[0]
        assert ref["sutra_number"] == 5
        assert ref["section"] == "Akattiṇaiyiyal"
        assert ref["work"] == "Tolkāppiyam"

    def test_parses_tamil_sutra_citation(self):
        query = "அகத்திணையியல் சூத்திரம் 14 விளக்கும் உரிப்பொருள் யாது?"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.has_source_filter is True
        sutra_nums = [r.get("sutra_number") for r in processed.source_references]
        assert 14 in sutra_nums

    def test_parses_hashtag_and_code_sutra(self):
        query = "Evaluate epistemic validity of tol-porul-akam-003"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.has_source_filter is True
        sutra_nums = [r.get("sutra_number") for r in processed.source_references]
        assert 3 in sutra_nums


class TestDownstreamRetrievalPayloads:
    """Tests verifying channel-specific representations (BM25, Vector, KG)."""

    def test_bm25_payload_generation(self):
        query = "Describe the role of வேங்கை (Vēṅkai) flower in Kuṟiñci puṇartal"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.bm25_query is not None
        assert len(processed.bm25_tokens) > 0
        # Common English stop words like 'the', 'of', 'in' should be filtered from bm25_tokens
        assert "the" not in processed.bm25_tokens
        assert "of" not in processed.bm25_tokens
        # Literary terms should be preserved
        assert any("வேங்கை" in t or "vēṅkai" in t.lower() or "venkai" in t.lower() for t in processed.bm25_tokens)

    def test_vector_payload_generation(self):
        query = "புணர்தல் ஒழுக்கம்"
        processed = QueryPreprocessingService.preprocess(query)

        assert processed.vector_query is not None
        assert "புணர்தல்" in processed.vector_query
        assert "Tiṇai: Kuṟiñci" in processed.vector_query

    def test_kg_cypher_parameters(self):
        query = "How does Cēyōṉ relate to Kuṟiñci in Sūtra 5?"
        processed = QueryPreprocessingService.preprocess(query)

        assert "ceyon" in processed.kg_seed_node_ids
        assert "kurinci" in processed.kg_seed_node_ids
        assert processed.kg_cypher_params["tinai"] == "Kuṟiñci"
        assert processed.kg_cypher_params["sutra_number"] == 5


class TestPreprocessApiEndpoint:
    """Tests for the POST /api/query/preprocess API route."""

    def test_preprocess_api_endpoint_success(self, client):
        payload = {
            "query": "Explain முதற்பொருள் and Karupporuḷ in Kuṟiñci Sūtra 5",
            "focus": "Relationship",
        }
        res = client.post("/api/query/preprocess", json=payload)
        assert res.status_code == 200

        data = res.get_json()
        assert data["success"] is True
        assert "data" in data

        q_data = data["data"]
        assert q_data["original_query"] == payload["query"]
        assert q_data["is_mixed"] is True
        assert q_data["detected_tinai"] == "Kuṟiñci"
        assert len(q_data["source_references"]) >= 1
        assert q_data["source_references"][0]["sutra_number"] == 5
        assert "kurinci" in q_data["kg_seed_node_ids"]
        assert len(q_data["bm25_tokens"]) > 0

    def test_preprocess_api_endpoint_empty_query(self, client):
        res = client.post("/api/query/preprocess", json={"query": ""})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["data"]["language"] == "unknown"
