"""
Integration tests validating bilingual (English and Tamil) query processing,
entity extraction, lexical/BM25 retrieval, and grounded Knowledge Graph retrieval.
"""
import pytest
from query.language_detector import LanguageDetector
from query.intent_classifier import IntentClassifier
from query.query_decomposer import QueryDecomposer
from extraction.entity_extractor import EntityExtractor
from retrieval.lexical_search import lexical_search_engine
from services.query_service import query_service
from services.graph_retrieval_service import graph_retrieval_service
from app import create_app


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


class TestBilingualQueryProcessing:
    """Validates seamless handling of English and Classical Tamil queries."""

    def test_language_detection_bilingual(self):
        ta_res = LanguageDetector.detect_language("குறிஞ்சி நிலத்தின் புணர்தல் ஒழுக்கம்")
        assert ta_res["is_tamil"] is True
        assert ta_res["primary_language"] == "ta"

        en_res = LanguageDetector.detect_language("How does the primary ground govern emotional union?")
        assert en_res["is_english"] is True
        assert en_res["primary_language"] == "en"

        mixed_res = LanguageDetector.detect_language("In kurinci tinai புணர்தல் what is ceyon?")
        assert mixed_res["is_mixed"] is True
        assert mixed_res["is_tamil"] is True
        assert mixed_res["is_english"] is True

    def test_bilingual_entity_extraction(self):
        # English query with transliterated / English deity and landscape
        en_query = "What is the role of Varunan in coastal seashore Neytal poetics?"
        entities = EntityExtractor.extract(en_query, source_id="test_en")
        terms = [e.canonical_form for e in entities]
        assert "வருணன்" in terms or "Varuṉaṉ" in [e.transliteration for e in entities] or any("varunan" in e.canonical_form.lower() for e in entities)
        assert any(e.tinai == "Neytal" for e in entities)

        # Tamil query
        ta_query = "முல்லை நிலத்தின் தெய்வம் மாயோன் மற்றும் அதன் உரிப்பொருள் யாது?"
        entities_ta = EntityExtractor.extract(ta_query, source_id="test_ta")
        assert any(e.tinai == "Mullai" for e in entities_ta)

    def test_bilingual_intent_classification(self):
        why_en = IntentClassifier.classify_intent("Why is Kurinji associated with union?")
        assert why_en["intent"] == "Why / Justification"

        how_en = IntentClassifier.classify_intent("How does space-time interact with biota?")
        assert how_en["intent"] == "How / Process"

        who_en = IntentClassifier.classify_intent("Which deity presides over the montane landscape?")
        assert who_en["intent"] == "Who / Entity"

        how_ta = IntentClassifier.classify_intent("குறிஞ்சி நில ஒழுக்கம் எவ்வாறு அமைகிறது?")
        assert how_ta["intent"] == "How / Process"

    def test_bilingual_query_decomposition(self):
        decomp = QueryDecomposer.decompose("How does the primary ground in Kuṟiñci govern emotional union?")
        assert decomp["detected_tinai"] == "Kuṟiñci"
        assert "Kuṟiñci" in decomp["thesis"]
        assert decomp["language"]["is_english"] is True

        decomp_neytal = QueryDecomposer.decompose("What is the role of coastal seascape in Neytal?")
        assert decomp_neytal["detected_tinai"] == "Neytal"

    def test_english_query_bm25_lexical_recall(self):
        # Lexical search engine should match English keywords from translation/metadata
        results = lexical_search_engine.search("Varunan seashore coastal", top_k=3)
        assert len(results) > 0
        top = results[0]
        assert top.score > 0.0
        # The result must correspond to Neytal or Sūtra 5
        assert top.source_metadata.get("tinai") == "Neytal" or "varuna" in str(top.source_metadata).lower()

    def test_grounded_graph_retrieval_english(self):
        res = graph_retrieval_service.retrieve_grounded_graph(
            query_input={"query": "What is the role of Varunan in coastal seashore?"},
            hop_depth=2,
        )
        data = res.to_dict()
        assert len(data["nodes"]) > 0
        assert len(data["relationships"]) > 0
        # Should detect Neytal / Varunan
        node_ids = [n["id"] for n in data["nodes"]]
        assert any("varunan" in nid or "neytal" in nid for nid in node_ids)

    def test_full_query_service_bilingual(self):
        res = query_service.process_query(
            "How does the primary ground (Mutalporuḷ) in Kuṟiñci govern emotional union?",
            depth=2,
            focus="Relationship"
        )
        assert res["detected_tinai"] == "Kuṟiñci"
        assert len(res["evidence_records"]) > 0
        assert len(res["grounded_graph"]["nodes"]) > 0
