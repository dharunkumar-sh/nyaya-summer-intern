"""
Comprehensive unit tests for Classical Tamil text preprocessing pipeline.

Tests are deterministic: same input always produces same output.
Covers normalization, segmentation, tokenization, lemmatization,
ProcessedPassage schema, and the POST /api/corpus/preprocess API endpoint.
"""
import pytest
from app import create_app

from preprocessing.tamil_normalizer import TamilNormalizer
from preprocessing.tokenizer import TamilTokenizer
from preprocessing.segmenter import (
    TamilSentenceSegmenter,
    TamilVerseSegmenter,
    TamilPassageSegmenter,
)
from preprocessing.processor import TamilTextProcessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SUTRA_TEXT = (
    "முதல்கரு உரிப்பொருள் என்ற மூன்றே\n"
    "நுவலும் காலை முறைசிறந் தனவே\n"
    "பாடலுட் பயின்றவை நாடும் காலை."
)

SAMPLE_SUTRA_DICT = {
    "id":                  "tol-porul-akam-003",
    "sutra_number":        3,
    "atikaram":            "Poruḷatikāram",
    "iyal":                "Akattiṇaiyiyal",
    "tamil_text":          SAMPLE_SUTRA_TEXT,
    "transliteration":     "mutalkaru uripporuḷ eṉṟa mūṉṟē ...",
    "english_translation": "Mutalporuḷ, Karupporuḷ, and Uripporuḷ—three of superior order.",
    "category":            "Epistemic Tripartite Semiotic",
    "tinai":               "General",
    "entities":            ["Mutalporuḷ", "Karupporuḷ", "Uripporuḷ"],
    "triples":             [{"subject": "Akattiṇai", "predicate": "hasConstituent", "object": "Mutalporuḷ"}],
    "nyaya_mapping":       {"member": "Hetu", "pramana": "Śabda Pramāṇa", "axiom": "..."},
}

@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


# ===========================================================================
# 1. Unicode & whitespace normalization
# ===========================================================================

class TestTamilNormalizer:

    def test_nfc_normalization(self):
        """Tabs, multiple spaces, and CRLF are collapsed."""
        raw = "முதல்கரு   உரிப்பொருள்\tஎன்ற   மூன்றே\r\n"
        out = TamilNormalizer.normalize(raw)
        assert "  " not in out
        assert "\t" not in out
        assert "\r" not in out
        assert out.startswith("முதல்கரு உரிப்பொருள்")

    def test_zwnj_removal(self):
        """Zero-width non-joiners are stripped."""
        text = "தமிழ்\u200cமொழி"
        out  = TamilNormalizer.normalize(text)
        assert "\u200c" not in out

    def test_decorative_quotes_removed(self):
        """Smart quotes and em-dashes are replaced."""
        text = "\u201cதமிழ்\u201d"
        out  = TamilNormalizer.normalize(text)
        assert "\u201c" not in out
        assert "\u201d" not in out

    def test_verse_newlines_preserved(self):
        """Newlines separating verse lines are preserved."""
        text = "முதல்கரு\nநுவலும் காலை"
        out  = TamilNormalizer.normalize(text)
        assert "\n" in out

    def test_is_tamil_true(self):
        assert TamilNormalizer.is_tamil(SAMPLE_SUTRA_TEXT) is True

    def test_is_tamil_false(self):
        assert TamilNormalizer.is_tamil("Hello world") is False

    def test_detect_script_tamil(self):
        assert TamilNormalizer.detect_script(SAMPLE_SUTRA_TEXT) == "tamil"

    def test_detect_script_english(self):
        assert TamilNormalizer.detect_script("The mountain habitat grounds love") == "english"

    def test_strip_punctuation_removes_ascii(self):
        text = "முதல்கரு! உரிப்பொருள்."
        out  = TamilNormalizer.strip_punctuation(text)
        assert "!" not in out

    def test_normalize_virama_no_space(self):
        """Virama should directly follow its consonant."""
        text = "தமிழ் \u0BCDமொழி"
        out  = TamilNormalizer.normalize_virama(text)
        # Space before virama removed
        assert " \u0BCD" not in out

    def test_full_pipeline_deterministic(self):
        """Same input always produces same output."""
        a = TamilNormalizer.full_pipeline(SAMPLE_SUTRA_TEXT)
        b = TamilNormalizer.full_pipeline(SAMPLE_SUTRA_TEXT)
        assert a == b


# ===========================================================================
# 2. Tokenization
# ===========================================================================

class TestTamilTokenizer:

    def test_basic_word_tokens(self):
        text   = "முதல்கரு உரிப்பொருள் என்ற மூன்றே"
        tokens = TamilTokenizer.tokenize_words(text, remove_stopwords=False)
        assert len(tokens) == 4
        assert tokens[0] == "முதல்கரு"
        assert tokens[1] == "உரிப்பொருள்"

    def test_stopword_exclusion(self):
        """'என்ற' is a stopword; not in content_tokens."""
        text    = "முதல்கரு உரிப்பொருள் என்ற மூன்றே"
        content = TamilTokenizer.tokenize_words(text, remove_stopwords=True)
        assert "என்ற" not in content

    def test_stopword_retained_in_full_tokens(self):
        """Stopwords stay in the full token list."""
        text   = "முதல்கரு உரிப்பொருள் என்ற மூன்றே"
        tokens = TamilTokenizer.tokenize_words(text, remove_stopwords=False)
        assert "என்ற" in tokens

    def test_clitic_splitter_e_suffix(self):
        """ஏ clitic particle is split from stem when word ends with the full letter ஏ."""
        # உம் is a well-tested particle — append it to a 3-char stem
        word  = "நிலஏ"   # stem "நில" + particle "ஏ"
        parts = TamilTokenizer.split_clitics(word)
        # stem has len 2 >= MIN_STEM, so split happens
        assert len(parts) == 2
        assert parts[-1] == "ஏ"

    def test_clitic_splitter_no_split_short(self):
        """Short words are not split."""
        parts = TamilTokenizer.split_clitics("ஏ")
        assert parts == ["ஏ"]

    def test_lemmatizer_plural_strip(self):
        """கள் suffix is stripped."""
        assert TamilTokenizer.lemmatize("நிலங்கள்") == "நிலங்"

    def test_lemmatizer_identity_short(self):
        """Words shorter than MIN_STEM are returned unchanged."""
        word = "ஏ"
        assert TamilTokenizer.lemmatize(word) == word

    def test_lemmatizer_deterministic(self):
        word = "உரிப்பொருள்கள்"
        assert TamilTokenizer.lemmatize(word) == TamilTokenizer.lemmatize(word)

    def test_tokenize_with_metadata_schema(self):
        """Each token dict has required fields."""
        text  = "முதல்கரு உரிப்பொருள் என்ற"
        metas = TamilTokenizer.tokenize_with_metadata(text)
        assert len(metas) == 3
        required_keys = {"token", "lemma", "is_stopword", "is_particle", "position"}
        for m in metas:
            assert required_keys.issubset(m.keys())

    def test_stopword_flag_in_metadata(self):
        """Stopword tokens are flagged but NOT removed."""
        text  = "முதல்கரு என்ற உரிப்பொருள்"
        metas = TamilTokenizer.tokenize_with_metadata(text)
        tokens = [m["token"] for m in metas]
        assert "என்ற" in tokens
        stopword_flags = {m["token"]: m["is_stopword"] for m in metas}
        assert stopword_flags["என்ற"] is True
        assert stopword_flags["முதல்கரு"] is False


# ===========================================================================
# 3. Segmentation
# ===========================================================================

class TestTamilSentenceSegmenter:

    def test_sentence_split_on_period(self):
        text      = "முதல்கரு உரிப்பொருள். நிலம் பொழுது."
        sentences = TamilSentenceSegmenter.segment(text)
        assert len(sentences) >= 2

    def test_sentence_split_on_danda(self):
        text      = "முதல்கரு உரிப்பொருள்। நிலம் பொழுது।"
        sentences = TamilSentenceSegmenter.segment(text)
        assert len(sentences) >= 2

    def test_no_empty_sentences(self):
        sentences = TamilSentenceSegmenter.segment(SAMPLE_SUTRA_TEXT)
        for s in sentences:
            assert s.strip() != ""

    def test_with_metadata_schema(self):
        metas = TamilSentenceSegmenter.segment_with_metadata(SAMPLE_SUTRA_TEXT)
        for m in metas:
            assert "index" in m and "text" in m and "char_count" in m


class TestTamilVerseSegmenter:

    def test_verse_line_count(self):
        """Sample sūtra has 3 Aṭi lines."""
        lines = TamilVerseSegmenter.segment_lines(SAMPLE_SUTRA_TEXT)
        assert len(lines) == 3

    def test_no_empty_lines(self):
        lines = TamilVerseSegmenter.segment_lines(SAMPLE_SUTRA_TEXT)
        for line in lines:
            assert line.strip() != ""

    def test_analyze_structure_schema(self):
        structure = TamilVerseSegmenter.analyze_structure(SAMPLE_SUTRA_TEXT)
        assert "total_lines" in structure
        assert "total_cir"   in structure
        assert "lines"       in structure
        assert structure["total_lines"] == 3
        for line_info in structure["lines"]:
            assert "line_number" in line_info
            assert "text"        in line_info
            assert "cir_count"   in line_info
            assert "cir_tokens"  in line_info

    def test_cir_count_positive(self):
        structure = TamilVerseSegmenter.analyze_structure(SAMPLE_SUTRA_TEXT)
        assert structure["total_cir"] > 0


class TestTamilPassageSegmenter:

    SUTRAS = [
        {"id": "s1", "atikaram": "Poruḷatikāram", "iyal": "Akattiṇaiyiyal", "tamil_text": "text1"},
        {"id": "s2", "atikaram": "Poruḷatikāram", "iyal": "Akattiṇaiyiyal", "tamil_text": "text2"},
        {"id": "s3", "atikaram": "Collatikāram",  "iyal": "Peyariyal",      "tamil_text": "text3"},
    ]

    def test_passage_count(self):
        passages = TamilPassageSegmenter.segment_passages(self.SUTRAS)
        assert len(passages) == 2

    def test_passage_schema(self):
        passages = TamilPassageSegmenter.segment_passages(self.SUTRAS)
        required = {"passage_id", "work", "section", "chapter", "sutra_ids",
                    "combined_text", "sutra_count"}
        for p in passages:
            assert required.issubset(p.keys())

    def test_passage_combined_text(self):
        passages = TamilPassageSegmenter.segment_passages(self.SUTRAS)
        akam = next(p for p in passages if "Akattiṇaiyiyal" in p["chapter"])
        assert "text1" in akam["combined_text"]
        assert "text2" in akam["combined_text"]
        assert akam["sutra_count"] == 2


# ===========================================================================
# 4. ProcessedPassage schema contract
# ===========================================================================

class TestProcessedPassageSchema:

    REQUIRED_TOP_LEVEL = {
        "document_id", "work", "section", "chapter", "passage_id",
        "original_text", "normalized_text", "tokens", "lemmas",
        "content_tokens", "token_count", "sentences",
        "verse_lines", "verse_structure", "metadata",
    }

    REQUIRED_METADATA = {
        "tinai", "sutra_number", "category", "entities", "triples",
        "nyaya_mapping", "is_tamil", "has_transliteration",
        "english_translation", "script", "processed_at",
    }

    def test_top_level_keys(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert self.REQUIRED_TOP_LEVEL.issubset(result.keys())

    def test_metadata_keys(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert self.REQUIRED_METADATA.issubset(result["metadata"].keys())

    def test_original_text_preserved(self):
        """original_text must be byte-for-byte the raw input."""
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["original_text"] == SAMPLE_SUTRA_TEXT

    def test_normalized_text_differs_only_in_whitespace(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["normalized_text"] is not None
        assert len(result["normalized_text"]) > 0

    def test_tokens_is_list(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert isinstance(result["tokens"], list)
        assert len(result["tokens"]) > 0

    def test_content_tokens_subset_of_tokens(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        token_set   = set(result["tokens"])
        content_set = set(result["content_tokens"])
        assert content_set.issubset(token_set)

    def test_lemmas_same_length_as_tokens(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert len(result["lemmas"]) == len(result["tokens"])

    def test_token_count_matches_tokens_list(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["token_count"] == len(result["tokens"])

    def test_verse_lines_count(self):
        """3-line sūtra should yield 3 verse lines."""
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert len(result["verse_lines"]) == 3

    def test_is_tamil_true(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["metadata"]["is_tamil"] is True

    def test_has_transliteration_true(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["metadata"]["has_transliteration"] is True

    def test_entities_preserved(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["metadata"]["entities"] == SAMPLE_SUTRA_DICT["entities"]

    def test_triples_preserved(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["metadata"]["triples"] == SAMPLE_SUTRA_DICT["triples"]

    def test_document_id_preserved(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["document_id"] == "tol-porul-akam-003"

    def test_work_set(self):
        result = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert result["work"] == "Tolkāppiyam"

    def test_deterministic_output(self):
        """Same sūtra processed twice yields identical records."""
        r1 = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        r2 = TamilTextProcessor.process_corpus_sutra(SAMPLE_SUTRA_DICT)
        assert r1["tokens"]          == r2["tokens"]
        assert r1["normalized_text"] == r2["normalized_text"]
        assert r1["verse_lines"]     == r2["verse_lines"]

    def test_backward_compat_process_sutra(self):
        """process_sutra() still returns expected keys for existing callers."""
        result = TamilTextProcessor.process_sutra(SAMPLE_SUTRA_TEXT)
        assert result["is_tamil"] is True
        assert result["token_count"] >= 3
        assert "normalized_text" in result
        assert "content_tokens"  in result
        assert "sentences"       in result


# ===========================================================================
# 5. API endpoint: POST /api/corpus/preprocess
# ===========================================================================

class TestPreprocessApiEndpoint:

    def test_preprocess_full_corpus(self, client):
        response = client.post("/api/corpus/preprocess", json={})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        required_stat_keys = {
            "total_sutras", "processed_count", "failed_count",
            "total_tokens", "avg_tokens_per_passage",
            "tamil_passage_count", "verse_line_count",
            "unique_tokens", "processing_time_ms",
            "output_file", "passages_by_chapter",
        }
        assert required_stat_keys.issubset(data.keys())
        assert data["processed_count"] == data["total_sutras"]
        assert data["failed_count"] == 0
        assert data["total_tokens"] > 0
        assert data["verse_line_count"] > 0
        assert data["processing_time_ms"] >= 0

    def test_preprocess_single_sutra(self, client):
        response = client.post(
            "/api/corpus/preprocess",
            json={"sutra_id": "tol-porul-akam-003"},
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        assert data["document_id"] == "tol-porul-akam-003"
        assert data["original_text"] != ""
        assert "tokens" in data
        assert "metadata" in data
        assert data["metadata"]["is_tamil"] is True

    def test_preprocess_invalid_sutra_id(self, client):
        response = client.post(
            "/api/corpus/preprocess",
            json={"sutra_id": "does-not-exist"},
        )
        assert response.status_code == 404
        json_data = response.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "SUTRA_NOT_FOUND"

    def test_preprocess_no_body(self, client):
        """No body = full corpus mode."""
        response = client.post("/api/corpus/preprocess")
        assert response.status_code == 200
        assert response.get_json()["success"] is True
