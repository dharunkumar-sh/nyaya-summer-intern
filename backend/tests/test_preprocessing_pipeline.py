"""
Integration tests for the CorpusPreprocessingPipeline against the real corpus.

Verifies batch processing, file persistence, statistics schema, and
single-passage roundtrip traceability.
"""
import os
import json
import pytest
from pathlib import Path

from preprocessing.pipeline import CorpusPreprocessingPipeline
from ingestion.corpus_loader import corpus_loader


@pytest.fixture
def pipeline(tmp_path):
    """Pipeline instance writing to a temporary directory."""
    return CorpusPreprocessingPipeline(base_dir=tmp_path)


@pytest.fixture
def real_sutras():
    return corpus_loader.get_all_sutras()


# ---------------------------------------------------------------------------
# Statistics schema contract
# ---------------------------------------------------------------------------

REQUIRED_STAT_KEYS = {
    "total_sutras",
    "processed_count",
    "failed_count",
    "total_tokens",
    "avg_tokens_per_passage",
    "tamil_passage_count",
    "verse_line_count",
    "unique_tokens",
    "processing_time_ms",
    "output_file",
    "passages_by_chapter",
    "pipeline_version",
    "processed_at",
    "failures",
}


class TestPipelineStats:

    def test_stats_schema(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert REQUIRED_STAT_KEYS.issubset(stats.keys())

    def test_all_sutras_processed(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["processed_count"] == stats["total_sutras"]
        assert stats["failed_count"] == 0

    def test_token_totals_positive(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["total_tokens"] > 0
        assert stats["unique_tokens"] > 0
        assert stats["unique_tokens"] <= stats["total_tokens"]

    def test_avg_tokens_per_passage(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["avg_tokens_per_passage"] > 0

    def test_verse_line_count_positive(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["verse_line_count"] > 0

    def test_tamil_passage_count(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["tamil_passage_count"] > 0
        assert stats["tamil_passage_count"] <= stats["processed_count"]

    def test_processing_time_non_negative(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert stats["processing_time_ms"] >= 0

    def test_passages_by_chapter_dict(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert isinstance(stats["passages_by_chapter"], dict)
        assert len(stats["passages_by_chapter"]) > 0


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------

class TestPipelinePersistence:

    def test_output_file_created(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        assert os.path.exists(stats["output_file"])

    def test_stats_file_created(self, pipeline, real_sutras):
        pipeline.run(real_sutras)
        stats_path = pipeline.processed_dir / pipeline.STATS_FILE
        assert stats_path.exists()

    def test_output_file_valid_json(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        assert isinstance(passages, list)
        assert len(passages) == stats["processed_count"]

    def test_load_preprocessed_returns_list(self, pipeline, real_sutras):
        pipeline.run(real_sutras)
        loaded = pipeline.load_preprocessed()
        assert isinstance(loaded, list)
        assert len(loaded) > 0

    def test_load_stats_returns_dict(self, pipeline, real_sutras):
        pipeline.run(real_sutras)
        loaded = pipeline.load_stats()
        assert isinstance(loaded, dict)
        assert "processed_count" in loaded

    def test_load_preprocessed_before_run_returns_none(self, pipeline):
        """Before any run, load returns None."""
        assert pipeline.load_preprocessed() is None


# ---------------------------------------------------------------------------
# ProcessedPassage roundtrip traceability
# ---------------------------------------------------------------------------

class TestPassageTraceability:

    REQUIRED_PASSAGE_KEYS = {
        "document_id", "work", "section", "chapter", "passage_id",
        "original_text", "normalized_text", "tokens", "lemmas",
        "content_tokens", "token_count", "sentences",
        "verse_lines", "verse_structure", "metadata",
    }

    def test_passage_schema_in_output(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert self.REQUIRED_PASSAGE_KEYS.issubset(p.keys()), (
                f"Passage {p.get('document_id')} missing keys"
            )

    def test_original_text_preserved(self, pipeline, real_sutras):
        """original_text must never be empty — source provenance intact."""
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert p["original_text"] != "", (
                f"Passage {p['document_id']} has empty original_text"
            )

    def test_document_id_matches_passage_id(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert p["document_id"] == p["passage_id"]

    def test_all_passages_have_tokens(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert len(p["tokens"]) > 0, (
                f"Passage {p['document_id']} has no tokens"
            )

    def test_content_tokens_subset_of_tokens(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            token_set   = set(p["tokens"])
            content_set = set(p["content_tokens"])
            assert content_set.issubset(token_set), (
                f"content_tokens not subset of tokens in {p['document_id']}"
            )

    def test_lemmas_same_length_as_tokens(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert len(p["lemmas"]) == len(p["tokens"]), (
                f"Lemma/token mismatch in {p['document_id']}"
            )

    def test_metadata_entities_preserved(self, pipeline, real_sutras):
        """Entities from original sūtra dict must be in passage metadata."""
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)

        # Build a lookup from the original sutras
        sutra_entities = {s["id"]: s.get("entities", []) for s in real_sutras}
        for p in passages:
            original_entities = sutra_entities.get(p["document_id"], [])
            assert p["metadata"]["entities"] == original_entities, (
                f"Entities not preserved for {p['document_id']}"
            )

    def test_work_name_consistent(self, pipeline, real_sutras):
        stats = pipeline.run(real_sutras)
        with open(stats["output_file"], encoding="utf-8") as f:
            passages = json.load(f)
        for p in passages:
            assert p["work"] == "Tolkāppiyam"


# ---------------------------------------------------------------------------
# Single-passage run_single
# ---------------------------------------------------------------------------

class TestRunSingle:

    def test_run_single_returns_passage(self, pipeline, real_sutras):
        sutra  = real_sutras[0]
        result = pipeline.run_single(sutra)
        assert result["document_id"] == sutra["id"]
        assert result["original_text"] == sutra["tamil_text"]

    def test_run_single_deterministic(self, pipeline, real_sutras):
        sutra = real_sutras[0]
        r1    = pipeline.run_single(sutra)
        r2    = pipeline.run_single(sutra)
        assert r1["tokens"]          == r2["tokens"]
        assert r1["normalized_text"] == r2["normalized_text"]
