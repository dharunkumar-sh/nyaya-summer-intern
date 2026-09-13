"""
Corpus Preprocessing Pipeline for Classical Tamil Literary Texts.

Batch-processes all sūtras loaded by CorpusLoader into ProcessedPassage records,
persists the output to data/processed/, and returns processing statistics.

Usage
-----
    from preprocessing.pipeline import CorpusPreprocessingPipeline
    pipeline = CorpusPreprocessingPipeline()
    stats = pipeline.run(sutras)

Output files
------------
    data/processed/preprocessed_corpus.json   - all ProcessedPassage records
    data/processed/preprocessing_stats.json   - pipeline statistics
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logger import logger
from .processor import TamilTextProcessor
from .segmenter import TamilPassageSegmenter


class CorpusPreprocessingPipeline:
    """
    Batch pipeline that turns raw corpus sūtras into ProcessedPassage records.
    All output is deterministic: same corpus → same processed records.
    """

    OUTPUT_FILE  = "preprocessed_corpus.json"
    STATS_FILE   = "preprocessing_stats.json"

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
        self.base_dir    = Path(base_dir)
        self.processed_dir = self.base_dir / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def run(self, sutras: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes all provided sūtras and persists results.

        Returns statistics dict matching:
        {
          "total_sutras":           int,
          "processed_count":        int,
          "failed_count":           int,
          "total_tokens":           int,
          "avg_tokens_per_passage": float,
          "tamil_passage_count":    int,
          "verse_line_count":       int,
          "unique_tokens":          int,
          "processing_time_ms":     int,
          "output_file":            str,
          "passages_by_chapter":    dict,
          "pipeline_version":       str,
          "processed_at":           str,
        }
        """
        start_ms = time.monotonic()

        passages: List[Dict[str, Any]] = []
        failed:   List[Dict[str, Any]] = []
        all_tokens: List[str]          = []
        verse_line_count               = 0

        for sutra in sutras:
            sutra_id = sutra.get("id", "<unknown>")
            try:
                passage = TamilTextProcessor.process_corpus_sutra(sutra)
                passages.append(passage)
                all_tokens.extend(passage["tokens"])
                verse_line_count += len(passage["verse_lines"])
            except Exception as exc:
                logger.warning(
                    f"Failed to preprocess sūtra '{sutra_id}': {exc}"
                )
                failed.append({"sutra_id": sutra_id, "error": str(exc)})

        # Aggregate passage-level segmentation
        passage_groups = TamilPassageSegmenter.segment_passages(sutras)
        by_chapter: Dict[str, int] = {
            pg["passage_id"]: pg["sutra_count"] for pg in passage_groups
        }

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)

        total   = len(sutras)
        ok      = len(passages)
        tamil_c = sum(1 for p in passages if p["metadata"].get("is_tamil"))
        unique  = len(set(all_tokens))
        avg_tok = round(len(all_tokens) / ok, 2) if ok else 0.0

        stats: Dict[str, Any] = {
            "total_sutras":           total,
            "processed_count":        ok,
            "failed_count":           len(failed),
            "total_tokens":           len(all_tokens),
            "avg_tokens_per_passage": avg_tok,
            "tamil_passage_count":    tamil_c,
            "verse_line_count":       verse_line_count,
            "unique_tokens":          unique,
            "processing_time_ms":     elapsed_ms,
            "output_file":            str(self.processed_dir / self.OUTPUT_FILE),
            "passages_by_chapter":    by_chapter,
            "pipeline_version":       "1.0.0",
            "processed_at":           datetime.now(timezone.utc).isoformat(),
            "failures":               failed,
        }

        self._persist(passages, stats)
        logger.info(
            f"Preprocessing pipeline complete: {ok}/{total} passages "
            f"in {elapsed_ms} ms"
        )
        return stats

    def run_single(self, sutra: Dict[str, Any]) -> Dict[str, Any]:
        """Processes and returns a single sūtra's ProcessedPassage."""
        return TamilTextProcessor.process_corpus_sutra(sutra)

    def load_preprocessed(self) -> Optional[List[Dict[str, Any]]]:
        """
        Loads previously persisted preprocessed corpus from disk.
        Returns None if no output file exists.
        """
        output_path = self.processed_dir / self.OUTPUT_FILE
        if not output_path.exists():
            return None
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_stats(self) -> Optional[Dict[str, Any]]:
        """Loads previously persisted pipeline statistics from disk."""
        stats_path = self.processed_dir / self.STATS_FILE
        if not stats_path.exists():
            return None
        with open(stats_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist(
        self,
        passages: List[Dict[str, Any]],
        stats:    Dict[str, Any],
    ) -> None:
        output_path = self.processed_dir / self.OUTPUT_FILE
        stats_path  = self.processed_dir / self.STATS_FILE

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(passages, f, ensure_ascii=False, indent=2)

        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Persisted {len(passages)} passages → {output_path}"
        )


# Singleton pipeline instance
preprocessing_pipeline = CorpusPreprocessingPipeline()
