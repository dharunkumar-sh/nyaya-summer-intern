"""
Second-Stage Re-ranking Layer for Classical Tamil Literature Search.

Re-ranks initial candidate passages retrieved via hybrid search using five deterministic signals:
1. Query-passage semantic similarity (dense embedding alignment)
2. Keyword coverage (token and phrase recall across verse text, translation, transliteration)
3. Entity and concept matching (ontological entities, concepts, tiṇai categories)
4. Source relevance (canonical Tolkāppiyam authority, citation completeness, explicit source queries)
5. Metadata matching (filter satisfaction, tiṇai/chapter/category concordance)

Provides configurable weights, transparent component breakdowns, and human-readable explanations.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.logger import logger


def _normalize_text(text: str) -> str:
    """
    Normalizes Unicode characters, removes Latin diacritics (macrons, accents)
    while strictly preserving Tamil script combining marks (pulli, vowel signs).
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    chars = []
    for c in nfkd:
        if 0x0B80 <= ord(c) <= 0x0BFF:
            # Preserve all Tamil script characters including combining marks
            chars.append(c)
        elif not unicodedata.combining(c):
            chars.append(c)
    cleaned = "".join(chars)
    return unicodedata.normalize("NFC", cleaned).lower().strip()


def _tokenize_query(query: str, min_len: int = 2) -> List[str]:
    """Tokenizes query into normalized content terms, removing punctuation and short stopwords."""
    norm = _normalize_text(query)
    tokens = re.findall(r"[\w\u0B80-\u0BFF]+", norm)
    # Exclude basic grammatical English stopwords
    stopwords = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
        "of", "from", "is", "are", "was", "were", "what", "which", "who", "whom",
        "how", "where", "when", "why", "that", "this", "these", "those", "into", "about",
    }
    return [t for t in tokens if len(t) >= min_len and t not in stopwords]


@dataclass
class RerankScoreComponents:
    """Breakdown of all 5 deterministic relevance score components."""
    semantic_similarity: float
    keyword_coverage: float
    entity_concept_match: float
    source_relevance: float
    metadata_match: float
    initial_combined_score: float = 0.0
    lexical_score: float = 0.0
    semantic_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic_similarity": round(self.semantic_similarity, 4),
            "keyword_coverage": round(self.keyword_coverage, 4),
            "entity_concept_match": round(self.entity_concept_match, 4),
            "source_relevance": round(self.source_relevance, 4),
            "metadata_match": round(self.metadata_match, 4),
            "initial_combined_score": round(self.initial_combined_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "semantic_score": round(self.semantic_score, 4),
        }


@dataclass
class RerankExplanation:
    """Human-readable diagnostics explaining the ranking decision."""
    summary: str
    matched_keywords: List[str]
    matched_entities: List[str]
    matched_concepts: List[str]
    matched_metadata: Dict[str, Any]
    source_authority: str
    component_contributions: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "matched_keywords": self.matched_keywords,
            "matched_entities": self.matched_entities,
            "matched_concepts": self.matched_concepts,
            "matched_metadata": self.matched_metadata,
            "source_authority": self.source_authority,
            "component_contributions": {
                k: round(v, 4) for k, v in self.component_contributions.items()
            },
        }


@dataclass
class RerankedPassage:
    """Final ranked passage result containing score components and ranking explanations."""
    passage_id: str
    text: str
    source_metadata: Dict[str, Any]
    final_score: float
    score_components: RerankScoreComponents
    explanation: RerankExplanation
    rank: int = 1
    score: float = field(init=False)
    retrieval_method: str = "second_stage_rerank"

    def __post_init__(self):
        self.score = self.final_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "rank": self.rank,
            "final_score": round(self.final_score, 4),
            "score": round(self.score, 4),
            "text": self.text,
            "source_metadata": self.source_metadata,
            "score_components": self.score_components.to_dict(),
            "explanation": self.explanation.to_dict(),
            "retrieval_method": self.retrieval_method,
        }


@dataclass
class RerankerConfig:
    """Configuration weights and parameters for second-stage re-ranking."""
    semantic_similarity_weight: float = 0.35
    keyword_coverage_weight: float = 0.20
    entity_concept_weight: float = 0.20
    source_relevance_weight: float = 0.15
    metadata_match_weight: float = 0.10
    canonical_base_score: float = 0.80
    min_keyword_length: int = 2


class PassageReranker:
    """
    Deterministic Second-Stage Re-ranking Layer.
    Evaluates candidate passages across semantic, lexical, ontological, provenance, and metadata dimensions.
    """

    def __init__(self, config: Optional[RerankerConfig] = None):
        self.config = config or RerankerConfig()

    def compute_semantic_similarity(
        self,
        query: str,
        candidate_item: Any,
    ) -> float:
        """
        Extracts or computes dense semantic similarity score in [0.0, 1.0].
        Favors existing dense vector similarity if present on candidate.
        """
        # If candidate already has semantic_score from dense retrieval
        if hasattr(candidate_item, "semantic_score") and candidate_item.semantic_score > 0.0:
            return float(candidate_item.semantic_score)

        if isinstance(candidate_item, dict):
            if "semantic_score" in candidate_item and candidate_item["semantic_score"] > 0.0:
                return float(candidate_item["semantic_score"])
            if "cosine_similarity" in candidate_item:
                cos = float(candidate_item["cosine_similarity"])
                return max(0.0, min(1.0, (1.0 + cos) / 2.0))

        # Fallback to semantic engine encoding if query and passage text are available
        try:
            from .semantic_search import semantic_search_engine
            passage_text = getattr(candidate_item, "text", "") or (
                candidate_item.get("text", "") if isinstance(candidate_item, dict) else ""
            )
            if query and passage_text and hasattr(semantic_search_engine, "encoder"):
                q_vec = semantic_search_engine.encoder.encode([query], normalize=True)
                d_vec = semantic_search_engine.encoder.encode([passage_text], normalize=True)
                import numpy as np
                cos = float(np.dot(q_vec[0], d_vec[0]))
                return max(0.0, min(1.0, (1.0 + cos) / 2.0))
        except Exception as e:
            logger.debug(f"Semantic similarity fallback evaluation error: {e}")

        return 0.0

    def compute_keyword_coverage(
        self,
        query: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """
        Calculates exact and tokenized keyword recall across verse text, translation, and transliteration.
        Returns: (normalized_coverage [0.0, 1.0], list_of_matched_terms)
        """
        query_tokens = _tokenize_query(query, min_len=self.config.min_keyword_length)
        if not query_tokens:
            return (0.0, [])

        # Build searchable target corpus from text, translation, transliteration, category
        parts = [text]
        for key in ("translation", "transliteration", "category", "source_reference"):
            val = metadata.get(key)
            if isinstance(val, str) and val:
                parts.append(val)

        composite_target = " ".join(parts)
        norm_target = _normalize_text(composite_target)

        matched_terms: List[str] = []
        for token in query_tokens:
            if token in norm_target:
                matched_terms.append(token)

        coverage = len(matched_terms) / len(query_tokens)

        # Bonus for exact full phrase match
        clean_query = _normalize_text(query)
        if len(query_tokens) > 1 and clean_query in norm_target:
            coverage = min(1.0, coverage + 0.10)

        return (min(1.0, max(0.0, coverage)), matched_terms)

    def compute_entity_concept_match(
        self,
        query: str,
        metadata: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Matches query terms against annotated entities, concepts, and tiṇai categories.
        Returns: (normalized_match_score [0.0, 1.0], matched_entities, matched_concepts)
        """
        query_norm = _normalize_text(query)
        query_tokens = set(_tokenize_query(query, min_len=self.config.min_keyword_length))

        # Gather annotated entities
        entities: List[str] = []
        for key in ("entity", "entities"):
            vals = metadata.get(key)
            if isinstance(vals, list):
                entities.extend([str(v) for v in vals if v])
            elif isinstance(vals, str) and vals:
                entities.append(vals)

        # Gather annotated concepts & tiṇai
        concepts: List[str] = []
        for key in ("concept", "concepts"):
            vals = metadata.get(key)
            if isinstance(vals, list):
                concepts.extend([str(v) for v in vals if v])
            elif isinstance(vals, str) and vals:
                concepts.append(vals)

        tinai_val = metadata.get("tinai")
        if tinai_val and str(tinai_val) != "General":
            concepts.append(str(tinai_val))

        matched_entities: List[str] = []
        for ent in entities:
            ent_norm = _normalize_text(ent)
            if ent_norm and (ent_norm in query_norm or any(t in ent_norm for t in query_tokens if len(t) >= 3)):
                if ent not in matched_entities:
                    matched_entities.append(ent)

        matched_concepts: List[str] = []
        for con in concepts:
            con_norm = _normalize_text(con)
            if con_norm and (con_norm in query_norm or any(t in con_norm for t in query_tokens if len(t) >= 3)):
                if con not in matched_concepts:
                    matched_concepts.append(con)

        total_matched = len(matched_entities) + len(matched_concepts)
        if total_matched == 0:
            match_score = 0.0
        elif total_matched == 1:
            match_score = 0.60
        elif total_matched == 2:
            match_score = 0.85
        else:
            match_score = 1.0

        return (match_score, matched_entities, matched_concepts)

    def compute_source_relevance(
        self,
        query: str,
        passage_id: str,
        metadata: Dict[str, Any],
    ) -> Tuple[float, str]:
        """
        Evaluates source authority and citation completeness.
        Awards bonuses if the query explicitly mentions source citations (e.g. 'sūtra 5', 'tolkāppiyam', 'akattiṇaiyiyal').
        Returns: (normalized_relevance [0.0, 1.0], source_authority_description)
        """
        source_id = str(metadata.get("source_identifier") or passage_id or "")
        ref = str(metadata.get("source_reference") or metadata.get("source") or "")
        verse = metadata.get("verse") or metadata.get("sutra_number")
        work = str(metadata.get("work", ""))
        chapter = str(metadata.get("chapter", ""))

        score = self.config.canonical_base_score  # Base score 0.80 for canonical dataset

        # Check canonical identifier
        if source_id.startswith("tol-"):
            score = max(score, 0.85)

        # Verified reference and verse completeness
        if ref:
            score += 0.05
        if verse is not None:
            score += 0.05

        # Query explicit source mention check
        query_norm = _normalize_text(query)
        if work and _normalize_text(work) in query_norm:
            score += 0.05
        if chapter and _normalize_text(chapter) in query_norm:
            score += 0.05
        if verse is not None and str(verse) in query_norm:
            score += 0.05

        final_score = min(1.0, max(0.0, score))
        desc = ref if ref else f"{work} {chapter} (Sūtra {verse})".strip()
        return (final_score, desc or "Canonical Tolkāppiyam Source")

    def compute_metadata_match(
        self,
        metadata: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        query: str = "",
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Scores concordance with user-specified filters and query-inferred metadata attributes.
        Returns: (normalized_score [0.0, 1.0], matched_metadata_dict)
        """
        matched_metadata: Dict[str, Any] = {}
        total_criteria = 0
        satisfied_criteria = 0

        # 1. Explicit user filters
        if filters:
            for k, expected_v in filters.items():
                total_criteria += 1
                actual_v = metadata.get(k)
                if actual_v is None:
                    continue

                if isinstance(expected_v, (list, set, tuple)):
                    if isinstance(actual_v, (list, set, tuple)):
                        if set(expected_v).intersection(set(actual_v)):
                            satisfied_criteria += 1
                            matched_metadata[k] = actual_v
                    elif actual_v in expected_v:
                        satisfied_criteria += 1
                        matched_metadata[k] = actual_v
                elif isinstance(actual_v, (list, set, tuple)):
                    if expected_v in actual_v or str(expected_v).lower() in [str(x).lower() for x in actual_v]:
                        satisfied_criteria += 1
                        matched_metadata[k] = actual_v
                else:
                    if str(expected_v).lower() == str(actual_v).lower():
                        satisfied_criteria += 1
                        matched_metadata[k] = actual_v

        # 2. Implicit query contextual metadata concordance (e.g. tiṇai or chapter keywords)
        query_norm = _normalize_text(query)
        for field_name in ("tinai", "chapter", "category"):
            val = metadata.get(field_name)
            if val and str(val) != "General":
                val_norm = _normalize_text(str(val))
                if val_norm and val_norm in query_norm:
                    total_criteria += 1
                    satisfied_criteria += 1
                    matched_metadata[f"inferred_{field_name}"] = val

        if total_criteria == 0:
            # Baseline concordance when no filters or inferred attributes are active
            return (1.0, {"status": "all_metadata_concordant"})

        score = satisfied_criteria / total_criteria
        return (min(1.0, max(0.0, score)), matched_metadata)

    def _resolve_weights(
        self,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Resolves and normalizes component weights so they sum to 1.0."""
        weights = {
            "semantic_similarity": self.config.semantic_similarity_weight,
            "keyword_coverage": self.config.keyword_coverage_weight,
            "entity_concept": self.config.entity_concept_weight,
            "source_relevance": self.config.source_relevance_weight,
            "metadata_match": self.config.metadata_match_weight,
        }

        if custom_weights:
            for k, v in custom_weights.items():
                if k in weights and v is not None:
                    weights[k] = max(0.0, float(v))

        total = sum(weights.values())
        if total <= 0.0:
            return {k: 0.20 for k in weights}
        return {k: v / total for k, v in weights.items()}

    def _build_summary_explanation(
        self,
        rank: int,
        final_score: float,
        components: RerankScoreComponents,
        matched_keywords: List[str],
        matched_entities: List[str],
        matched_concepts: List[str],
        source_authority: str,
    ) -> str:
        """Synthesizes human-readable natural language explanation for why this passage achieved this rank."""
        points: List[str] = [f"Rank {rank} (score: {final_score:.4f})"]

        # Semantic
        points.append(f"Semantic similarity {components.semantic_similarity:.2f}")

        # Keywords
        if matched_keywords:
            points.append(f"Matched {len(matched_keywords)} query term(s) ({', '.join(matched_keywords[:4])})")
        else:
            points.append("No exact keyword matches")

        # Entities & concepts
        matches = matched_entities + matched_concepts
        if matches:
            points.append(f"Correlated ontology: {', '.join(matches[:3])}")

        # Provenance
        if source_authority:
            points.append(f"Authority: {source_authority}")

        return "; ".join(points) + "."

    def rerank(
        self,
        candidates: List[Any],
        query: str,
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RerankedPassage]:
        """
        Executes deterministic second-stage re-ranking over candidate passages.

        Args:
            candidates: Initial candidates (list of HybridSearchResult or dicts).
            query: Search query text.
            top_k: Number of re-ranked passages to return.
            weights: Optional custom dictionary of weights for the 5 components.
            filters: Optional metadata filtering criteria.

        Returns:
            List of RerankedPassage instances sorted descending by final_score.
        """
        if not candidates:
            return []

        norm_weights = self._resolve_weights(weights)
        reranked_items: List[RerankedPassage] = []

        for candidate in candidates:
            # Extract common candidate fields
            if isinstance(candidate, dict):
                passage_id = str(candidate.get("passage_id", ""))
                text = str(candidate.get("text", ""))
                metadata = candidate.get("source_metadata", {}) or {}
                init_combined = float(candidate.get("combined_score", candidate.get("score", 0.0)))
                init_lex = float(candidate.get("lexical_score", 0.0))
                init_sem = float(candidate.get("semantic_score", 0.0))
            else:
                passage_id = getattr(candidate, "passage_id", "")
                text = getattr(candidate, "text", "")
                metadata = getattr(candidate, "source_metadata", {}) or {}
                init_combined = float(getattr(candidate, "combined_score", getattr(candidate, "score", 0.0)))
                init_lex = float(getattr(candidate, "lexical_score", 0.0))
                init_sem = float(getattr(candidate, "semantic_score", 0.0))

            # 1. Semantic similarity
            s_sem = self.compute_semantic_similarity(query, candidate)

            # 2. Keyword coverage
            s_kw, matched_keywords = self.compute_keyword_coverage(query, text, metadata)

            # 3. Entity & concept match
            s_ent, matched_entities, matched_concepts = self.compute_entity_concept_match(query, metadata)

            # 4. Source relevance
            s_src, source_authority = self.compute_source_relevance(query, passage_id, metadata)

            # 5. Metadata match
            s_meta, matched_metadata = self.compute_metadata_match(metadata, filters=filters, query=query)

            # Calculate weighted final score
            w_sem = norm_weights["semantic_similarity"]
            w_kw = norm_weights["keyword_coverage"]
            w_ent = norm_weights["entity_concept"]
            w_src = norm_weights["source_relevance"]
            w_meta = norm_weights["metadata_match"]

            final_score = (
                (w_sem * s_sem)
                + (w_kw * s_kw)
                + (w_ent * s_ent)
                + (w_src * s_src)
                + (w_meta * s_meta)
            )
            final_score = min(1.0, max(0.0, final_score))

            components = RerankScoreComponents(
                semantic_similarity=s_sem,
                keyword_coverage=s_kw,
                entity_concept_match=s_ent,
                source_relevance=s_src,
                metadata_match=s_meta,
                initial_combined_score=init_combined,
                lexical_score=init_lex,
                semantic_score=init_sem,
            )

            contributions = {
                "semantic_similarity": w_sem * s_sem,
                "keyword_coverage": w_kw * s_kw,
                "entity_concept": w_ent * s_ent,
                "source_relevance": w_src * s_src,
                "metadata_match": w_meta * s_meta,
            }

            explanation = RerankExplanation(
                summary="",  # filled after sort rank assignment
                matched_keywords=matched_keywords,
                matched_entities=matched_entities,
                matched_concepts=matched_concepts,
                matched_metadata=matched_metadata,
                source_authority=source_authority,
                component_contributions=contributions,
            )

            reranked_items.append(
                RerankedPassage(
                    passage_id=passage_id,
                    text=text,
                    source_metadata=metadata,
                    final_score=final_score,
                    score_components=components,
                    explanation=explanation,
                )
            )

        # Sort deterministically: descending final_score, descending semantic, descending keyword, passage_id tie-breaker
        reranked_items.sort(
            key=lambda r: (
                -round(r.final_score, 6),
                -round(r.score_components.semantic_similarity, 6),
                -round(r.score_components.keyword_coverage, 6),
                r.passage_id,
            )
        )

        # Assign ranks and natural language summaries
        final_top = reranked_items[:top_k]
        for idx, item in enumerate(final_top):
            item.rank = idx + 1
            item.explanation.summary = self._build_summary_explanation(
                rank=item.rank,
                final_score=item.final_score,
                components=item.score_components,
                matched_keywords=item.explanation.matched_keywords,
                matched_entities=item.explanation.matched_entities,
                matched_concepts=item.explanation.matched_concepts,
                source_authority=item.explanation.source_authority,
            )

        return final_top


# Global singleton instance
passage_reranker = PassageReranker()
