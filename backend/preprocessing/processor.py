"""
End-to-end Classical Tamil Text Processor.

Unifies normalization, tokenization (with lemmatization), and segmentation
into a single `ProcessedPassage` output that preserves the full source
provenance so every retrieved answer can be traced back to its origin.

ProcessedPassage schema
-----------------------
{
  "document_id":    str,   # unique sūtra / passage identifier
  "work":           str,   # e.g. "Tolkāppiyam"
  "section":        str,   # atikāram (book)
  "chapter":        str,   # iyal (chapter)
  "passage_id":     str,   # same as document_id for sūtra-level records
  "original_text":  str,   # raw text exactly as loaded from corpus
  "normalized_text":str,   # NFC + whitespace normalized
  "tokens":         list,  # all word tokens (stopwords included)
  "lemmas":         list,  # lemmatized form of each token
  "content_tokens": list,  # non-stopword tokens only
  "token_count":    int,
  "sentences":      list,  # sentence-segmented fragments
  "verse_lines":    list,  # Aṭi lines
  "verse_structure":dict,  # full structural analysis
  "metadata": {
    "tinai":                str,
    "sutra_number":         int | None,
    "category":             str,
    "entities":             list,
    "triples":              list,
    "nyaya_mapping":        dict,
    "is_tamil":             bool,
    "has_transliteration":  bool,
    "english_translation":  str,
    "script":               str,
    "processed_at":         str   # ISO 8601 UTC
  }
}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .tamil_normalizer import TamilNormalizer
from .tokenizer import TamilTokenizer
from .segmenter import TamilSentenceSegmenter, TamilVerseSegmenter


class TamilTextProcessor:
    """Unified pipeline for processing Classical Tamil sūtras and passages."""

    WORK_NAME = "Tolkāppiyam"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def process_sutra(cls, raw_text: str) -> Dict[str, Any]:
        """
        Minimal single-text processing used by existing tests.
        Returns a dict compatible with previous `process_sutra` callers.
        """
        normalized = TamilNormalizer.full_pipeline(raw_text)
        tokens = TamilTokenizer.tokenize_words(normalized, remove_stopwords=False)
        content_tokens = TamilTokenizer.tokenize_words(normalized, remove_stopwords=True)
        structure = TamilVerseSegmenter.analyze_structure(normalized)
        sentences = TamilSentenceSegmenter.segment(normalized)

        return {
            "normalized_text": normalized,
            "tokens":          tokens,
            "content_tokens":  content_tokens,
            "token_count":     len(tokens),
            "sentences":       sentences,
            "structure":       structure,
            "is_tamil":        TamilNormalizer.is_tamil(normalized),
        }

    @classmethod
    def process_corpus_sutra(
        cls,
        sutra: Dict[str, Any],
        work: str = WORK_NAME,
    ) -> Dict[str, Any]:
        """
        Produces a full `ProcessedPassage` from a corpus sūtra dict.

        Parameters
        ----------
        sutra : dict
            A sūtra record as loaded by CorpusLoader (from tolkappiyam_canonical.json).
        work : str
            Name of the source work.

        Returns
        -------
        ProcessedPassage dict — retains both original_text and normalized_text
        so downstream retrieval can always trace answers back to the source.
        """
        original_text: str = sutra.get("tamil_text", "")
        document_id:   str = sutra.get("id", "")
        section:       str = sutra.get("atikaram", "")
        chapter:       str = sutra.get("iyal", "")

        # ---- Normalization ----
        normalized_text = TamilNormalizer.full_pipeline(original_text)

        # ---- Tokenization ----
        token_meta = TamilTokenizer.tokenize_with_metadata(
            normalized_text, include_lemmas=True
        )
        tokens        = [t["token"] for t in token_meta]
        lemmas        = [t["lemma"] for t in token_meta]
        content_tokens = [
            t["token"] for t in token_meta if not t["is_stopword"]
        ]

        # ---- Sentence segmentation ----
        sentences = TamilSentenceSegmenter.segment(normalized_text)

        # ---- Verse segmentation ----
        verse_lines     = TamilVerseSegmenter.segment_lines(normalized_text)
        verse_structure = TamilVerseSegmenter.analyze_structure(normalized_text)

        # ---- Metadata preservation ----
        is_tamil           = TamilNormalizer.is_tamil(original_text)
        script             = TamilNormalizer.detect_script(original_text)
        has_transliteration = bool(sutra.get("transliteration"))
        english_translation = sutra.get("english_translation", "")

        return {
            "document_id":     document_id,
            "work":            work,
            "section":         section,
            "chapter":         chapter,
            "passage_id":      document_id,
            "original_text":   original_text,
            "normalized_text": normalized_text,
            "tokens":          tokens,
            "lemmas":          lemmas,
            "content_tokens":  content_tokens,
            "token_count":     len(tokens),
            "sentences":       sentences,
            "verse_lines":     verse_lines,
            "verse_structure": verse_structure,
            "metadata": {
                "tinai":               sutra.get("tinai", "General"),
                "sutra_number":        sutra.get("sutra_number"),
                "category":            sutra.get("category", ""),
                "entities":            sutra.get("entities", []),
                "triples":             sutra.get("triples", []),
                "nyaya_mapping":       sutra.get("nyaya_mapping", {}),
                "is_tamil":            is_tamil,
                "has_transliteration": has_transliteration,
                "english_translation": english_translation,
                "script":              script,
                "processed_at":        datetime.now(timezone.utc).isoformat(),
            },
        }
