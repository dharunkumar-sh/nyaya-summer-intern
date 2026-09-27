"""
Evidence-Ranking Layer for Classical Tamil Literary Knowledge in Hybrid RAG.

Ranks retrieved evidence passages using five deterministic, configurable, and normalized signals:
1. Semantic Relevance (S_sem): Dense vector similarity and query semantic alignment.
2. Graph Relevance (S_graph): Ontological connectivity, seed entity overlap, and graph path depth.
3. Source Reliability (S_source): Canonical authority (Tolkāppiyam hierarchy, Poruḷatikāram axioms, citation completeness).
4. Context Relevance (S_context): Keyword/entity coverage across verse text, transliteration, translation, and tiṇai concordance.
5. Evidence Confidence (S_conf): Multi-channel consensus (number of retrieval channels finding the passage, score distribution, and stability).

Normalizes individual score components to [0.0, 1.0] before weighted combination into a final ranking score.
Provides transparent score components and explanations for frontend display and provenance tracing.
Preserves backward compatibility with legacy EvidenceRanker.format_evidence_records.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
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
            chars.append(c)
        elif not unicodedata.combining(c):
            chars.append(c)
    cleaned = "".join(chars)
    return unicodedata.normalize("NFC", cleaned).lower().strip()


def _tokenize_query(query: str, min_len: int = 2) -> List[str]:
    """Tokenizes query into normalized content terms, removing punctuation and stopwords."""
    norm = _normalize_text(query)
    tokens = re.findall(r"[\w\u0B80-\u0BFF]+", norm)
    stopwords = {
        # English functional words
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
        "of", "from", "is", "are", "was", "were", "what", "which", "who", "whom",
        "how", "where", "when", "why", "that", "this", "these", "those", "into", "about",
        # Tamil functional/grammatical words
        "என", "என்ற", "என்று", "ஆகும்", "ஆகிய", "ஆன", "மற்றும்", "அல்லது", "அதாவது",
        "அது", "இது", "அவை", "இவை", "ஒரு", "பல", "படும்", "முறை",
    }
    return [t for t in tokens if len(t) >= min_len and t not in stopwords]


# ---------------------------------------------------------------------------
# Data Models for Evidence Ranking
# ---------------------------------------------------------------------------

@dataclass
class EvidenceScoreComponents:
    """
    Transparent breakdown of all five normalized evidence ranking components [0.0, 1.0].
    """
    semantic_relevance: float
    graph_relevance: float
    source_reliability: float
    context_relevance: float
    evidence_confidence: float
    raw_components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Returns rounded JSON-serializable dictionary."""
        return {
            "semantic_relevance": round(self.semantic_relevance, 4),
            "graph_relevance": round(self.graph_relevance, 4),
            "source_reliability": round(self.source_reliability, 4),
            "context_relevance": round(self.context_relevance, 4),
            "evidence_confidence": round(self.evidence_confidence, 4),
            "raw_components": {k: round(v, 4) for k, v in self.raw_components.items()},
        }


@dataclass
class EvidenceRankingExplanation:
    """
    Human-readable diagnostics explaining the ranking decision and evidence selection.
    """
    summary: str
    matched_terms: List[str]
    matched_entities: List[str]
    matched_concepts: List[str]
    source_pedigree: str
    channel_consensus: List[str]
    component_contributions: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable explanation."""
        return {
            "summary": self.summary,
            "matched_terms": self.matched_terms,
            "matched_entities": self.matched_entities,
            "matched_concepts": self.matched_concepts,
            "source_pedigree": self.source_pedigree,
            "channel_consensus": self.channel_consensus,
            "component_contributions": {k: round(v, 4) for k, v in self.component_contributions.items()},
        }


@dataclass
class RankedEvidenceItem:
    """
    Final ranked evidence item preserving exact source references,
    transparent score components, and explanations.
    """
    passage_id: str
    text: str
    source: Dict[str, Any]
    final_score: float
    score_components: EvidenceScoreComponents
    explanation: EvidenceRankingExplanation
    rank: int = 1
    score: float = field(init=False)
    graph_path: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_methods: List[str] = field(default_factory=list)
    graph_context: Optional[Dict[str, Any]] = None
    badge_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.score = self.final_score

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary with transparent score breakdown."""
        return {
            "passage_id": self.passage_id,
            "rank": self.rank,
            "final_score": round(self.final_score, 4),
            "score": round(self.score, 4),
            "text": self.text,
            "source": self.source,
            "graph_path": self.graph_path,
            "retrieval_methods": self.retrieval_methods,
            "score_components": self.score_components.to_dict(),
            "explanation": self.explanation.to_dict(),
            "graph_context": self.graph_context,
            "badge_info": self.badge_info,
        }


@dataclass
class EvidenceRankerConfig:
    """
    Configuration weights for the 5 evidence ranking signals.
    Automatically normalizes weights to sum to 1.0.
    """
    semantic_weight: float = 0.30
    graph_weight: float = 0.25
    source_weight: float = 0.15
    context_weight: float = 0.15
    confidence_weight: float = 0.15

    def __post_init__(self):
        self.normalize_weights()

    def normalize_weights(self) -> None:
        """Normalizes all active weights so that their sum equals exactly 1.0."""
        total = (
            self.semantic_weight
            + self.graph_weight
            + self.source_weight
            + self.context_weight
            + self.confidence_weight
        )
        if total <= 0.0:
            self.semantic_weight = 0.30
            self.graph_weight = 0.25
            self.source_weight = 0.15
            self.context_weight = 0.15
            self.confidence_weight = 0.15
            total = 1.0

        self.semantic_weight = self.semantic_weight / total
        self.graph_weight = self.graph_weight / total
        self.source_weight = self.source_weight / total
        self.context_weight = self.context_weight / total
        self.confidence_weight = self.confidence_weight / total

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic_weight": round(self.semantic_weight, 4),
            "graph_weight": round(self.graph_weight, 4),
            "source_weight": round(self.source_weight, 4),
            "context_weight": round(self.context_weight, 4),
            "confidence_weight": round(self.confidence_weight, 4),
        }


# ---------------------------------------------------------------------------
# Evidence Ranking Engine
# ---------------------------------------------------------------------------

class EvidenceRankingEngine:
    """
    Deterministic evidence-ranking engine for the Hybrid RAG system.
    Evaluates semantic relevance, graph connectivity, source reliability,
    contextual match, and multi-channel evidence confidence.
    """

    REASONING_STEP_MAP = {
        0: "Stage 3: Udāharaṇa (Universal Rule)",
        1: "Stage 1: Pratijñā (Target Proposition)",
        2: "Stage 4: Upanaya (Application)",
        3: "Stage 5: Nigamana (Conclusion)",
        4: "Stage 2: Hetu (Reason)",
    }

    def __init__(self, config: Optional[EvidenceRankerConfig] = None):
        self.config = config or EvidenceRankerConfig()

    # -----------------------------------------------------------------------
    # Signal 1: Semantic Relevance [0.0, 1.0]
    # -----------------------------------------------------------------------
    def compute_semantic_relevance(
        self,
        item: Any,
        query: str,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Extracts and normalizes query-passage semantic alignment.
        """
        sem_score = 0.0
        # Check standard properties
        if hasattr(item, "semantic_score"):
            sem_score = float(item.semantic_score)
        elif isinstance(item, dict):
            sem_score = float(item.get("semantic_score") or item.get("cosine_similarity") or 0.0)

        # Ensure normalized in [0.0, 1.0]
        norm_sem = min(1.0, max(0.0, sem_score))
        return norm_sem, {"raw_semantic": sem_score}

    # -----------------------------------------------------------------------
    # Signal 2: Graph Relevance [0.0, 1.0]
    # -----------------------------------------------------------------------
    def compute_graph_relevance(
        self,
        item: Any,
        query: str,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Evaluates ontological connectivity, seed entity overlap, and graph path depth.
        """
        graph_score = 0.0
        if hasattr(item, "graph_score"):
            graph_score = float(item.graph_score)
        elif isinstance(item, dict):
            graph_score = float(item.get("graph_score") or 0.0)

        # Context details
        ctx = getattr(item, "graph_context", None)
        if ctx is None and isinstance(item, dict):
            ctx = item.get("graph_context")

        matched_entities: List[str] = []
        matched_concepts: List[str] = []

        query_tokens = set(_tokenize_query(query, min_len=2))
        query_norm = _normalize_text(query)

        if isinstance(ctx, dict):
            ents = ctx.get("entities", [])
            for e in ents:
                label = e.get("label") or e.get("name") or ""
                e_norm = _normalize_text(label)
                if e_norm and (e_norm in query_norm or any(t in e_norm for t in query_tokens if len(t) >= 3)):
                    if label not in matched_entities:
                        matched_entities.append(label)

            concs = ctx.get("concepts", [])
            for c in concs:
                label = c.get("label") or c.get("name") or ""
                c_norm = _normalize_text(label)
                if c_norm and (c_norm in query_norm or any(t in c_norm for t in query_tokens if len(t) >= 3)):
                    if label not in matched_concepts:
                        matched_concepts.append(label)

        # Check graph path
        path = getattr(item, "graph_path", None)
        if path is None and isinstance(item, dict):
            path = item.get("graph_path", [])
        path_bonus = min(0.20, len(path) * 0.05) if path else 0.0

        overlap_bonus = min(0.30, len(matched_entities) * 0.10 + len(matched_concepts) * 0.08)

        final_graph = min(1.0, max(0.0, (graph_score * 0.6) + path_bonus + overlap_bonus))
        if final_graph == 0.0 and graph_score > 0.0:
            final_graph = min(1.0, graph_score)

        return round(final_graph, 4), matched_entities, matched_concepts

    # -----------------------------------------------------------------------
    # Signal 3: Source Reliability [0.0, 1.0]
    # -----------------------------------------------------------------------
    def compute_source_reliability(self, item: Any) -> Tuple[float, str]:
        """
        Determines canonical authority, citation completeness, and provenance depth.
        Tolkāppiyam primary sūtras get maximum reliability score.
        """
        source = getattr(item, "source", None)
        if source is None and isinstance(item, dict):
            source = item.get("source") or item.get("source_metadata", {})

        pid = getattr(item, "passage_id", "") or (item.get("passage_id", "") if isinstance(item, dict) else "")
        source_str = str(source).lower() if source else ""
        pid_lower = str(pid).lower()

        base_reliability = 0.50
        pedigree_parts: List[str] = []

        # Check canonical work
        work = ""
        if isinstance(source, dict):
            work = str(source.get("work") or "").strip()
        if not work and "tolkappiyam" in source_str or "tol-" in pid_lower:
            work = "Tolkāppiyam"

        if "tolkappiyam" in work.lower() or "tol-" in pid_lower:
            base_reliability += 0.30
            pedigree_parts.append("Tolkāppiyam Canonical Sūtra")
        else:
            pedigree_parts.append("Classical Literary Source")

        # Check section / chapter completeness
        has_section = False
        has_verse = False
        if isinstance(source, dict):
            if source.get("section") or source.get("chapter") or source.get("iyal") or source.get("atikaram"):
                has_section = True
            if source.get("sutra_number") or source.get("verse") or source.get("verse_number"):
                has_verse = True

        if has_section:
            base_reliability += 0.10
        if has_verse or any(tag in pid_lower for tag in ["-00", "-01", "-02", "-03", "-248"]):
            base_reliability += 0.10

        norm_rel = min(1.0, max(0.0, base_reliability))
        pedigree = " • ".join(pedigree_parts) if pedigree_parts else "Classical Sangam Authority"
        return round(norm_rel, 4), pedigree

    # -----------------------------------------------------------------------
    # Signal 4: Context Relevance [0.0, 1.0]
    # -----------------------------------------------------------------------
    def compute_context_relevance(
        self,
        item: Any,
        query: str,
    ) -> Tuple[float, List[str]]:
        """
        Evaluates lexical/token coverage, translations, and tiṇai concordance against the query.
        """
        text = getattr(item, "text", "") or (item.get("text", "") if isinstance(item, dict) else "")
        source = getattr(item, "source", None) or (item.get("source") or item.get("source_metadata", {}) if isinstance(item, dict) else {})

        translation = ""
        transliteration = ""
        tinai = ""
        entities: List[str] = []
        if isinstance(source, dict):
            translation = str(source.get("translation") or source.get("english_translation") or "")
            transliteration = str(source.get("transliteration") or "")
            tinai = str(source.get("tinai") or "")
            entities = [str(e) for e in source.get("entities", [])]

        combined_text = f"{text} {translation} {transliteration} {tinai} {' '.join(entities)}"
        norm_combined = _normalize_text(combined_text)

        query_tokens = _tokenize_query(query, min_len=2)
        if not query_tokens:
            return 0.50, []

        matched_terms: List[str] = []
        for t in query_tokens:
            if t in norm_combined:
                matched_terms.append(t)

        token_coverage = len(matched_terms) / len(query_tokens)

        # Check exact phrase or tiṇai match
        bonus = 0.0
        query_norm = _normalize_text(query)
        if tinai and tinai.lower() != "general" and _normalize_text(tinai) in query_norm:
            bonus += 0.15

        # Incorporate lexical score from retrieval if available
        lex_score = 0.0
        if hasattr(item, "lexical_score"):
            lex_score = float(item.lexical_score)
        elif isinstance(item, dict):
            lex_score = float(item.get("lexical_score") or item.get("bm25_score") or 0.0)

        context_score = (token_coverage * 0.60) + (lex_score * 0.25) + bonus
        norm_context = min(1.0, max(0.0, context_score))
        return round(norm_context, 4), matched_terms

    # -----------------------------------------------------------------------
    # Signal 5: Evidence Confidence [0.0, 1.0]
    # -----------------------------------------------------------------------
    def compute_evidence_confidence(self, item: Any) -> Tuple[float, List[str]]:
        """
        Determines evidence confidence via multi-channel consensus.
        Items discovered through multiple independent channels receive higher confidence.
        """
        methods: List[str] = []
        if hasattr(item, "retrieval_methods"):
            methods = list(item.retrieval_methods)
        elif isinstance(item, dict):
            methods = list(item.get("retrieval_methods") or [])

        channel_count = len(methods)
        if channel_count >= 3:
            conf = 0.95
        elif channel_count == 2:
            conf = 0.85
        elif channel_count == 1:
            conf = 0.70
        else:
            conf = 0.50

        # High base score validation
        base_score = getattr(item, "relevance_score", 0.0) or (item.get("relevance_score") or item.get("score", 0.0) if isinstance(item, dict) else 0.0)
        if base_score > 0.80:
            conf = min(1.0, conf + 0.05)

        return round(conf, 4), methods

    # -----------------------------------------------------------------------
    # Main Ranking Entry Points
    # -----------------------------------------------------------------------
    def rank_evidence(
        self,
        items: List[Any],
        query: str,
        top_k: Optional[int] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[RankedEvidenceItem]:
        """
        Ranks retrieved evidence items using normalized score components and configurable weights.

        Args:
            items: Candidate EvidenceItem or dict objects.
            query: User query string.
            top_k: Maximum number of ranked results to return.
            weights: Optional per-call weight overrides.

        Returns:
            List of RankedEvidenceItem sorted deterministically descending by final_score.
        """
        if not items:
            return []

        # Resolve weights
        w_cfg = EvidenceRankerConfig(
            semantic_weight=weights.get("semantic_weight", self.config.semantic_weight) if weights else self.config.semantic_weight,
            graph_weight=weights.get("graph_weight", self.config.graph_weight) if weights else self.config.graph_weight,
            source_weight=weights.get("source_weight", self.config.source_weight) if weights else self.config.source_weight,
            context_weight=weights.get("context_weight", self.config.context_weight) if weights else self.config.context_weight,
            confidence_weight=weights.get("confidence_weight", self.config.confidence_weight) if weights else self.config.confidence_weight,
        )

        ranked: List[RankedEvidenceItem] = []

        for idx, itm in enumerate(items):
            pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") or itm.get("id") or f"passage-{idx+1}")
            text = getattr(itm, "text", "") or (itm.get("text", "") if isinstance(itm, dict) else "")
            source = getattr(itm, "source", None) or (itm.get("source") or itm.get("source_metadata", {}) if isinstance(itm, dict) else {})
            graph_path = getattr(itm, "graph_path", None) or (itm.get("graph_path", []) if isinstance(itm, dict) else [])
            graph_context = getattr(itm, "graph_context", None) or (itm.get("graph_context") if isinstance(itm, dict) else None)

            # Compute 5 individual normalized signals [0.0, 1.0]
            s_sem, raw_sem = self.compute_semantic_relevance(itm, query)
            s_graph, matched_ents, matched_concs = self.compute_graph_relevance(itm, query)
            s_source, pedigree = self.compute_source_reliability(itm)
            s_context, matched_terms = self.compute_context_relevance(itm, query)
            s_conf, consensus = self.compute_evidence_confidence(itm)

            # Combine scores
            final_score = (
                w_cfg.semantic_weight * s_sem
                + w_cfg.graph_weight * s_graph
                + w_cfg.source_weight * s_source
                + w_cfg.context_weight * s_context
                + w_cfg.confidence_weight * s_conf
            )
            final_score = round(min(1.0, max(0.0, final_score)), 6)

            score_components = EvidenceScoreComponents(
                semantic_relevance=s_sem,
                graph_relevance=s_graph,
                source_reliability=s_source,
                context_relevance=s_context,
                evidence_confidence=s_conf,
                raw_components={
                    "weighted_semantic": w_cfg.semantic_weight * s_sem,
                    "weighted_graph": w_cfg.graph_weight * s_graph,
                    "weighted_source": w_cfg.source_weight * s_source,
                    "weighted_context": w_cfg.context_weight * s_context,
                    "weighted_confidence": w_cfg.confidence_weight * s_conf,
                    **raw_sem,
                },
            )

            # Diagnostic summary
            summary_parts = []
            if s_sem >= 0.70:
                summary_parts.append("High semantic alignment")
            if matched_ents:
                summary_parts.append(f"Entities: {', '.join(matched_ents[:2])}")
            if matched_concs:
                summary_parts.append(f"Concepts: {', '.join(matched_concs[:2])}")
            if len(consensus) > 1:
                summary_parts.append(f"Multi-channel consensus ({'+'.join(consensus)})")
            summary_str = " • ".join(summary_parts) if summary_parts else "Standard corpus evidence match"

            explanation = EvidenceRankingExplanation(
                summary=summary_str,
                matched_terms=matched_terms,
                matched_entities=matched_ents,
                matched_concepts=matched_concs,
                source_pedigree=pedigree,
                channel_consensus=consensus,
                component_contributions={
                    "semantic": round(w_cfg.semantic_weight * s_sem, 4),
                    "graph": round(w_cfg.graph_weight * s_graph, 4),
                    "source": round(w_cfg.source_weight * s_source, 4),
                    "context": round(w_cfg.context_weight * s_context, 4),
                    "confidence": round(w_cfg.confidence_weight * s_conf, 4),
                },
            )

            ranked.append(
                RankedEvidenceItem(
                    passage_id=pid,
                    text=text,
                    source=source,
                    final_score=final_score,
                    score_components=score_components,
                    explanation=explanation,
                    graph_path=graph_path,
                    retrieval_methods=consensus,
                    graph_context=graph_context,
                )
            )

        # Deterministic sorting: final_score desc, confidence desc, semantic desc, passage_id asc
        ranked.sort(
            key=lambda it: (
                -round(it.final_score, 6),
                -round(it.score_components.evidence_confidence, 4),
                -round(it.score_components.semantic_relevance, 4),
                it.passage_id,
            )
        )

        # Assign final rank positions and UI badge information
        limit = top_k if top_k is not None else len(ranked)
        final_top = ranked[:limit]

        for rank_idx, item in enumerate(final_top):
            item.rank = rank_idx + 1
            code = f"E{rank_idx + 1}"
            step_target = self.REASONING_STEP_MAP.get(rank_idx, "Stage 1: Pratijñā (Proposition)")
            conf_pct = int(item.score_components.evidence_confidence * 100)

            tinai = item.source.get("tinai") if isinstance(item.source, dict) else None
            badges = [{"label": item.source.get("category", "Poruḷatikāram Axiom"), "variant": "purple"}]
            if tinai and tinai != "General":
                badges.append({"label": f"{tinai} Tiṇai", "variant": "blue"})
            else:
                badges.append({"label": "Canonical Poruḷ", "variant": "indigo"})

            item.badge_info = {
                "code": code,
                "confidenceScore": item.score_components.evidence_confidence,
                "confidenceFormatted": f"{conf_pct}%",
                "badges": badges,
                "reasoningStepTarget": step_target,
            }

        return final_top

    def rank_collection(
        self,
        collection: Any,
        query: str,
        top_k: Optional[int] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Any:
        """
        Ranks an EvidenceCollection, updating its items with transparent score components and explanations.
        """
        items = getattr(collection, "items", [])
        ranked_items = self.rank_evidence(items=items, query=query, top_k=top_k, weights=weights)

        # Convert back or update in place
        collection.items = ranked_items
        if hasattr(collection, "retrieval_stats") and isinstance(collection.retrieval_stats, dict):
            collection.retrieval_stats["ranked_by"] = "EvidenceRankingEngine"
            collection.retrieval_stats["ranking_weights"] = self.config.to_dict()
        return collection


# ---------------------------------------------------------------------------
# Global Singleton and Backward-Compatible Interface
# ---------------------------------------------------------------------------

evidence_ranking_engine = EvidenceRankingEngine()


class EvidenceRanker:
    """
    Unified Evidence Ranker:
    - Provides modern rank_evidence() and rank_collection() powered by EvidenceRankingEngine.
    - Preserves format_evidence_records() for complete backward compatibility.
    """

    REASONING_STEP_MAP = EvidenceRankingEngine.REASONING_STEP_MAP

    @classmethod
    def format_evidence_records(
        cls, ranked_results: List[Tuple[Dict[str, Any], float]]
    ) -> List[Dict[str, Any]]:
        """Transforms raw retrieved sūtras into frontend-ready evidence cards."""
        formatted = []

        for idx, (sutra, conf) in enumerate(ranked_results):
            code = f"E{idx + 1}"
            step_target = cls.REASONING_STEP_MAP.get(idx, "Stage 1: Pratijñā (Proposition)")
            conf_pct = int(conf * 100)

            badges = [
                {"label": sutra.get("category", "Classical Epistemology"), "variant": "purple"},
            ]
            if sutra.get("tinai") and sutra["tinai"] != "General":
                badges.append({"label": f"{sutra['tinai']} Tiṇai", "variant": "blue"})
            else:
                badges.append({"label": "Poruḷatikāram Axiom", "variant": "indigo"})

            formatted.append({
                "id": code,
                "code": code,
                "source": f"Tolkāppiyam {sutra.get('atikaram', 'Poruḷ')}",
                "reference": f"{sutra.get('iyal', 'Akattiṇaiyiyal')} • Sūtra {sutra.get('sutra_number', idx + 1)}",
                "tamilText": sutra.get("tamil_text", ""),
                "translation": sutra.get("english_translation", ""),
                "confidenceScore": conf,
                "confidenceFormatted": f"{conf_pct}%",
                "badges": badges,
                "reasoningStepTarget": step_target,
                "sutraId": sutra.get("id"),
            })

        return formatted

    @classmethod
    def rank_evidence(
        cls,
        items: List[Any],
        query: str,
        top_k: Optional[int] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[RankedEvidenceItem]:
        """Convenience method delegating to the EvidenceRankingEngine."""
        return evidence_ranking_engine.rank_evidence(items=items, query=query, top_k=top_k, weights=weights)
