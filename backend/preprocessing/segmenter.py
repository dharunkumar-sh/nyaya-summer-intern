"""
Segmentation module for Classical Tamil literary texts.

Provides deterministic segmentation at three granularities:
  - Sentence level  (clause / sub-sentence boundaries)
  - Verse level     (Aṭi / sūtra lines on newline breaks)
  - Passage level   (groups of sūtras sharing the same iyal / chapter)

All segmenters are pure functions — same input → same output.
"""
import re
from typing import List, Dict, Any, Optional
from .tamil_normalizer import TamilNormalizer


# ---------------------------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------------------------

class TamilSentenceSegmenter:
    """Segments a Tamil text into sentence-level clauses."""

    # Sentence terminators: period, danda, double-danda, pipe
    TERMINATORS = re.compile(r"[.।॥|]+")

    # Comma-like pauses that can delimit clauses (not full breaks)
    CLAUSE_BREAK = re.compile(r"[,;]+")

    @classmethod
    def segment(cls, text: str) -> List[str]:
        """
        Splits a normalized text into sentences on `.`, `।`, `॥`.
        Empty fragments are discarded.
        """
        normalized = TamilNormalizer.normalize(text)
        # Split on terminators while keeping sentence content
        parts = cls.TERMINATORS.split(normalized)
        sentences = []
        for part in parts:
            part = re.sub(r"[ \t]+", " ", part).strip()
            if part:
                sentences.append(part)
        return sentences

    @classmethod
    def segment_with_metadata(cls, text: str) -> List[Dict[str, Any]]:
        """Returns sentence dicts with index and character offsets."""
        sentences = cls.segment(text)
        return [
            {"index": i, "text": s, "char_count": len(s)}
            for i, s in enumerate(sentences)
        ]


# ---------------------------------------------------------------------------
# Verse / sūtra segmentation  (Aṭi lines)
# ---------------------------------------------------------------------------

class TamilVerseSegmenter:
    """Segments classical sūtras into Aṭi lines and Cīr metrical feet."""

    @classmethod
    def segment_lines(cls, verse_text: str) -> List[str]:
        """Splits verse into individual Aṭi (line) units on newline boundaries."""
        normalized = TamilNormalizer.normalize(verse_text)
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        return lines

    @classmethod
    def analyze_structure(cls, verse_text: str) -> Dict[str, Any]:
        """
        Analyzes verse structure:
          - total_lines  : number of Aṭi
          - total_cir    : total Cīr (metrical feet / words) across all lines
          - lines        : list of per-Aṭi dicts with cīr tokens
        """
        lines = cls.segment_lines(verse_text)
        line_analysis: List[Dict[str, Any]] = []
        total_feet = 0

        for idx, line in enumerate(lines):
            # Cīr = space-separated units after stripping punctuation
            feet = [
                c.strip()
                for c in re.sub(r"[.।॥|,;]+", " ", line).split()
                if c.strip()
            ]
            total_feet += len(feet)
            line_analysis.append({
                "line_number": idx + 1,
                "text":        line,
                "cir_count":   len(feet),
                "cir_tokens":  feet,
            })

        return {
            "total_lines": len(lines),
            "total_cir":   total_feet,
            "lines":       line_analysis,
        }


# ---------------------------------------------------------------------------
# Passage segmentation  (groups of sūtras by chapter / iyal)
# ---------------------------------------------------------------------------

class TamilPassageSegmenter:
    """
    Groups corpus sūtras into passage units based on shared chapter (iyal).
    A passage = all sūtras within one iyal of one atikaram.
    """

    @classmethod
    def segment_passages(cls, sutras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups sūtras by (atikaram, iyal) key.
        Returns a list of passage dicts, each containing:
          - passage_id:  "<atikaram>/<iyal>"
          - work:        corpus name
          - section:     atikaram
          - chapter:     iyal
          - sutra_ids:   list of constituent sūtra IDs
          - combined_text: concatenated Tamil texts (with newline separator)
          - sutra_count: number of constituent sūtras
        """
        groups: Dict[str, Dict[str, Any]] = {}

        for sutra in sutras:
            atikaram = sutra.get("atikaram", "Unknown")
            iyal     = sutra.get("iyal",     "Unknown")
            key      = f"{atikaram}/{iyal}"

            if key not in groups:
                groups[key] = {
                    "passage_id":    key,
                    "work":          "Tolkāppiyam",
                    "section":       atikaram,
                    "chapter":       iyal,
                    "sutra_ids":     [],
                    "combined_text": [],
                    "sutra_count":   0,
                }

            entry = groups[key]
            entry["sutra_ids"].append(sutra.get("id", ""))
            tamil = sutra.get("tamil_text", "")
            if tamil:
                entry["combined_text"].append(tamil)
            entry["sutra_count"] += 1

        # Join combined texts
        passages = []
        for group in groups.values():
            group["combined_text"] = "\n\n".join(group["combined_text"])
            passages.append(group)

        return passages
