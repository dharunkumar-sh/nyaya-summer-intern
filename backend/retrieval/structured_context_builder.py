"""
Structured Context Builder for Grounded Classical Tamil Literary QA.

Transforms ranked retrieval results from the Hybrid RAG pipeline into a
compact, structured context for answer generation.

Key capabilities:
1. Grounded Provenance: Preserves exact source reference, passage ID, text,
   work, section, chapter, sūtra number, tiṇai, and literary metadata.
2. Neo4j Graph Relationships: Extracts and structures incoming and outgoing
   relationships (associated entities, concepts, events, source hierarchy, evidence).
3. Compact Context Limits: Bounded by configurable max passages, token/character
   budget, and relationship limits to prevent LLM context overflow.
4. Unambiguous Separation: Segregates source evidence with strict boundary fences
   from prompt instructions and generated content.
5. Insufficient Evidence Detection: If retrieved passages do not satisfy minimum
   relevance or minimum count thresholds, yields an explicit 'insufficient_evidence'
   state rather than generating an unsupported or fabricated answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from core.logger import logger


@dataclass
class GroundedGraphRelationship:
    """A structured relationship connected to a passage in the Knowledge Graph."""
    relationship_type: str
    target_id: str
    target_label: str
    target_type: str = "Concept"
    direction: str = "OUTGOING"  # OUTGOING or INCOMING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_type": self.relationship_type,
            "target_id": self.target_id,
            "target_label": self.target_label,
            "target_type": self.target_type,
            "direction": self.direction,
        }

    def to_text(self) -> str:
        arrow = f"-[:{self.relationship_type}]->" if self.direction == "OUTGOING" else f"<-[:{self.relationship_type}]-"
        return f"{arrow} ({self.target_label} [{self.target_type}])"


@dataclass
class GroundedPassageContext:
    """A single grounded passage with full provenance and graph neighborhood."""
    rank: int
    passage_id: str
    source_reference: str
    text: str
    work: str
    section: str
    chapter: str
    sutra_number: Optional[int]
    tinai: str
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    relationships: List[GroundedGraphRelationship] = field(default_factory=list)
    translation: Optional[str] = None
    retrieval_methods: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    graph_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "passage_id": self.passage_id,
            "source_reference": self.source_reference,
            "text": self.text,
            "translation": self.translation,
            "work": self.work,
            "section": self.section,
            "chapter": self.chapter,
            "sutra_number": self.sutra_number,
            "tinai": self.tinai,
            "entities": self.entities,
            "concepts": self.concepts,
            "relationships": [r.to_dict() for r in self.relationships],
            "retrieval_methods": self.retrieval_methods,
            "relevance_score": round(self.relevance_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "graph_score": round(self.graph_score, 4),
            "metadata": self.metadata,
        }


@dataclass
class StructuredRAGContext:
    """
    Unified structured context for grounded answer generation.

    Distinguishes clearly between sufficient evidence and insufficient evidence.
    Includes machine-readable structured passages and prompt-ready boundary-fenced text.
    """
    query: str
    is_sufficient: bool
    status: str  # "sufficient_evidence" or "insufficient_evidence"
    evidence_passages: List[GroundedPassageContext] = field(default_factory=list)
    passage_count: int = 0
    total_characters: int = 0
    min_relevance_threshold: float = 0.30
    min_evidence_count: int = 1
    insufficient_reason: Optional[str] = None
    rendered_context: str = ""
    boundary_marker_start: str = "=== BEGIN CANONICAL SOURCE EVIDENCE (READ ONLY - DO NOT INVENT) ==="
    boundary_marker_end: str = "=== END CANONICAL SOURCE EVIDENCE ==="

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "is_sufficient": self.is_sufficient,
            "status": self.status,
            "passage_count": self.passage_count,
            "total_characters": self.total_characters,
            "min_relevance_threshold": self.min_relevance_threshold,
            "min_evidence_count": self.min_evidence_count,
            "insufficient_reason": self.insufficient_reason,
            "evidence_passages": [p.to_dict() for p in self.evidence_passages],
            "rendered_context": self.rendered_context,
            "boundary_markers": {
                "start": self.boundary_marker_start,
                "end": self.boundary_marker_end,
            },
        }

    def to_prompt_context(self) -> str:
        """Returns prompt-ready delimited text containing only grounded source evidence."""
        return self.rendered_context


class StructuredContextBuilder:
    """
    Transforms ranked evidence from Hybrid RAG into a compact, structured context.
    Enforces configurable limits and strict evidence/generation boundary fences.
    """

    DEFAULT_MAX_PASSAGES = 5
    DEFAULT_MAX_CONTEXT_CHARS = 4000
    DEFAULT_MAX_RELATIONSHIPS_PER_PASSAGE = 8
    DEFAULT_MIN_RELEVANCE_THRESHOLD = 0.30
    DEFAULT_MIN_EVIDENCE_COUNT = 1

    @classmethod
    def extract_graph_relationships(
        cls,
        item_dict: Dict[str, Any],
        max_relationships: int = 8,
    ) -> List[GroundedGraphRelationship]:
        """
        Extracts structured Neo4j graph relationships from passage graph_context.
        Supports subgraph nodes/edges, associated entities, concepts, events, and evidence.
        """
        relationships: List[GroundedGraphRelationship] = []
        seen_keys: Set[str] = set()

        passage_id = str(item_dict.get("passage_id") or "")
        graph_ctx = item_dict.get("graph_context")
        if not isinstance(graph_ctx, dict):
            return relationships

        # 1. Inspect explicit subgraph edges if available
        subgraph = graph_ctx.get("subgraph")
        if isinstance(subgraph, dict):
            nodes_by_id = {n.get("id"): n for n in subgraph.get("nodes", []) if isinstance(n, dict)}
            edges = subgraph.get("edges", [])
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                src = edge.get("source") or edge.get("start")
                tgt = edge.get("target") or edge.get("end")
                rel_type = edge.get("type") or edge.get("relationship", "ASSOCIATED_WITH")

                if src == passage_id and tgt in nodes_by_id:
                    target_node = nodes_by_id[tgt]
                    key = f"OUT:{rel_type}:{tgt}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        relationships.append(
                            GroundedGraphRelationship(
                                relationship_type=rel_type,
                                target_id=tgt,
                                target_label=target_node.get("label") or target_node.get("name") or tgt,
                                target_type=target_node.get("type") or "Node",
                                direction="OUTGOING",
                            )
                        )
                elif tgt == passage_id and src in nodes_by_id:
                    source_node = nodes_by_id[src]
                    key = f"IN:{rel_type}:{src}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        relationships.append(
                            GroundedGraphRelationship(
                                relationship_type=rel_type,
                                target_id=src,
                                target_label=source_node.get("label") or source_node.get("name") or src,
                                target_type=source_node.get("type") or "Node",
                                direction="INCOMING",
                            )
                        )
                if len(relationships) >= max_relationships:
                    return relationships

        # 2. Add associated concepts from graph context
        for c in graph_ctx.get("concepts", []):
            cid = c.get("id") or c.get("label") or ""
            clabel = c.get("label") or c.get("name") or cid
            key = f"OUT:grounds_concept:{cid}"
            if key not in seen_keys and cid:
                seen_keys.add(key)
                relationships.append(
                    GroundedGraphRelationship(
                        relationship_type="grounds_concept",
                        target_id=cid,
                        target_label=clabel,
                        target_type="Concept",
                        direction="OUTGOING",
                    )
                )
            if len(relationships) >= max_relationships:
                return relationships

        # 3. Add associated entities from graph context
        for e in graph_ctx.get("entities", []):
            eid = e.get("id") or e.get("label") or ""
            elabel = e.get("label") or e.get("name") or eid
            key = f"OUT:manifests_entity:{eid}"
            if key not in seen_keys and eid:
                seen_keys.add(key)
                relationships.append(
                    GroundedGraphRelationship(
                        relationship_type="manifests_entity",
                        target_id=eid,
                        target_label=elabel,
                        target_type=e.get("category") or "Entity",
                        direction="OUTGOING",
                    )
                )
            if len(relationships) >= max_relationships:
                return relationships

        # 4. Add source hierarchy steps from graph context
        for h in graph_ctx.get("source_hierarchy", []):
            hid = h.get("id") or ""
            hlabel = h.get("label") or h.get("name") or hid
            htype = h.get("type") or "Hierarchy"
            key = f"IN:part_of:{hid}"
            if key not in seen_keys and hid and hid != passage_id:
                seen_keys.add(key)
                relationships.append(
                    GroundedGraphRelationship(
                        relationship_type="belongs_to_hierarchy",
                        target_id=hid,
                        target_label=hlabel,
                        target_type=htype,
                        direction="INCOMING",
                    )
                )
            if len(relationships) >= max_relationships:
                return relationships

        return relationships

    @classmethod
    def build_context(
        cls,
        query: str,
        evidence_items: Union[List[Any], Any],
        max_passages: int = DEFAULT_MAX_PASSAGES,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
        max_relationships_per_passage: int = DEFAULT_MAX_RELATIONSHIPS_PER_PASSAGE,
        min_relevance_threshold: float = DEFAULT_MIN_RELEVANCE_THRESHOLD,
        min_evidence_count: int = DEFAULT_MIN_EVIDENCE_COUNT,
    ) -> StructuredRAGContext:
        """
        Transforms raw or typed evidence items into a compact StructuredRAGContext.
        """
        # Handle EvidenceCollection object or items list
        raw_items: List[Any] = []
        if hasattr(evidence_items, "items"):
            raw_items = list(evidence_items.items)
        elif isinstance(evidence_items, list):
            raw_items = evidence_items
        elif isinstance(evidence_items, dict) and "items" in evidence_items:
            raw_items = evidence_items["items"]

        # 1. Normalize items into dictionaries and extract scores
        normalized_candidates: List[Dict[str, Any]] = []
        for it in raw_items:
            if hasattr(it, "to_dict"):
                it_dict = it.to_dict()
            elif isinstance(it, dict):
                it_dict = dict(it)
            else:
                continue

            rel_score = float(
                it_dict.get("relevance_score")
                or it_dict.get("final_score")
                or it_dict.get("score")
                or (it_dict.get("relevance_scores", {}).get("relevance_score") if isinstance(it_dict.get("relevance_scores"), dict) else 0.0)
                or 0.0
            )
            it_dict["_resolved_relevance"] = rel_score
            normalized_candidates.append(it_dict)

        # Sort descending by relevance score
        normalized_candidates.sort(key=lambda x: -x["_resolved_relevance"])

        # 2. Filter by minimum relevance threshold
        qualifying_items: List[Dict[str, Any]] = [
            it for it in normalized_candidates if it["_resolved_relevance"] >= min_relevance_threshold
        ]

        # 3. Check for Insufficient Evidence
        if len(qualifying_items) < min_evidence_count:
            reason = (
                f"Insufficient canonical evidence retrieved for query '{query}'. "
                f"Found {len(qualifying_items)} qualifying passage(s) with relevance >= {min_relevance_threshold:.2f} "
                f"(minimum required: {min_evidence_count})."
            )
            logger.info(f"StructuredContext: {reason}")
            return StructuredRAGContext(
                query=query,
                is_sufficient=False,
                status="insufficient_evidence",
                evidence_passages=[],
                passage_count=0,
                total_characters=0,
                min_relevance_threshold=min_relevance_threshold,
                min_evidence_count=min_evidence_count,
                insufficient_reason=reason,
                rendered_context=(
                    f"=== BEGIN CANONICAL SOURCE EVIDENCE ===\n"
                    f"STATUS: INSUFFICIENT EVIDENCE\n"
                    f"REASON: {reason}\n"
                    f"NO CONCLUSION OR ASSERTION MAY BE GENERATED.\n"
                    f"=== END CANONICAL SOURCE EVIDENCE ==="
                ),
            )

        # 4. Process Top Qualifying Passages within Limits
        selected_passages: List[GroundedPassageContext] = []
        current_char_count = 0
        prompt_blocks: List[str] = []

        start_banner = "=== BEGIN CANONICAL SOURCE EVIDENCE (READ ONLY - DO NOT INVENT) ==="
        end_banner = "=== END CANONICAL SOURCE EVIDENCE ==="
        char_budget = max_context_chars - len(start_banner) - len(end_banner) - 200

        for idx, it in enumerate(qualifying_items[:max_passages]):
            pid = str(it.get("passage_id") or it.get("id") or f"P{idx+1}")
            text = str(it.get("text") or it.get("original_text") or it.get("passage_text") or "").strip()
            src = it.get("source") or it.get("source_metadata") or {}
            if not isinstance(src, dict):
                src = {}
            inner_meta = src.get("metadata") if isinstance(src.get("metadata"), dict) else {}

            work = str(it.get("work") or src.get("work") or src.get("work_name") or inner_meta.get("work_name") or "Tolkāppiyam")
            section = str(it.get("section") or src.get("section") or src.get("section_name") or inner_meta.get("atikaram") or "")
            chapter = str(it.get("chapter") or src.get("chapter") or src.get("chapter_name") or inner_meta.get("iyal") or "")
            sutra_num = it.get("sutra_number") or src.get("sutra_number") or inner_meta.get("sutra_number")
            tinai = str(it.get("tinai") or src.get("tinai") or inner_meta.get("tinai") or "General")

            # Formulate exact source reference citation
            ref_parts = [work]
            if section:
                ref_parts.append(section)
            if chapter:
                ref_parts.append(chapter)
            if sutra_num:
                ref_parts.append(f"Sūtra {sutra_num}")
            exact_source_ref = str(src.get("source_reference") or " ".join(ref_parts))

            # Entities and concepts normalized to strings
            raw_entities = it.get("entities") or src.get("entities") or inner_meta.get("entities") or []
            raw_concepts = it.get("concepts") or src.get("concepts") or inner_meta.get("concepts") or []
            
            entities: List[str] = []
            for e in (raw_entities if isinstance(raw_entities, list) else [raw_entities]):
                if isinstance(e, dict):
                    val = e.get("label") or e.get("name") or e.get("id") or str(e)
                    if val:
                        entities.append(str(val))
                elif e:
                    entities.append(str(e))

            concepts: List[str] = []
            for c in (raw_concepts if isinstance(raw_concepts, list) else [raw_concepts]):
                if isinstance(c, dict):
                    val = c.get("label") or c.get("name") or c.get("id") or str(c)
                    if val:
                        concepts.append(str(val))
                elif c:
                    concepts.append(str(c))

            translation = str(it.get("translation") or src.get("translation") or inner_meta.get("translation") or "")

            # Graph relationships
            relationships = cls.extract_graph_relationships(it, max_relationships=max_relationships_per_passage)

            rel_methods = list(it.get("retrieval_methods") or ([it["retrieval_method"]] if it.get("retrieval_method") else ["hybrid_rag"]))
            scores_dict = it.get("relevance_scores") if isinstance(it.get("relevance_scores"), dict) else {}

            sem_score = float(scores_dict.get("semantic_score") or it.get("semantic_score") or 0.0)
            lex_score = float(scores_dict.get("lexical_score") or it.get("lexical_score") or 0.0)
            graph_score = float(scores_dict.get("graph_score") or it.get("graph_score") or 0.0)
            relevance_score = float(it["_resolved_relevance"])

            passage_ctx = GroundedPassageContext(
                rank=idx + 1,
                passage_id=pid,
                source_reference=exact_source_ref,
                text=text,
                translation=translation if translation else None,
                work=work,
                section=section,
                chapter=chapter,
                sutra_number=int(sutra_num) if sutra_num is not None and str(sutra_num).isdigit() else None,
                tinai=tinai,
                entities=entities,
                concepts=concepts,
                relationships=relationships,
                retrieval_methods=rel_methods,
                relevance_score=relevance_score,
                semantic_score=sem_score,
                lexical_score=lex_score,
                graph_score=graph_score,
                metadata={
                    "source_reference": exact_source_ref,
                    "tinai": tinai,
                    "retrieval_channels": rel_methods,
                },
            )

            # Build compact text block for this passage
            block_lines = [
                f"[EVIDENCE {idx+1}] ID: {pid} | {exact_source_ref} | Tiṇai: {tinai} | Relevance: {relevance_score:.3f}",
                f"Tamil Verse: {text}",
            ]
            if translation:
                block_lines.append(f"Translation: {translation}")
            if entities:
                block_lines.append(f"Entities: {', '.join(entities[:6])}")
            if concepts:
                block_lines.append(f"Concepts: {', '.join(concepts[:6])}")
            if relationships:
                rel_strs = [r.to_text() for r in relationships[:max_relationships_per_passage]]
                block_lines.append(f"Graph Relationships:\n  " + "\n  ".join(rel_strs))

            block_text = "\n".join(block_lines)

            # Check character budget limit
            if current_char_count + len(block_text) > char_budget and selected_passages:
                # Truncate to avoid exceeding budget while preserving existing passages
                logger.info(f"StructuredContext reached character budget limit of {max_context_chars}")
                break

            selected_passages.append(passage_ctx)
            prompt_blocks.append(block_text)
            current_char_count += len(block_text) + 2

        # 5. Assemble rendered fenced prompt text
        rendered = (
            f"{start_banner}\n"
            f"QUERY: {query}\n"
            f"TOTAL GROUNDED PASSAGES: {len(selected_passages)}\n\n"
            + "\n\n".join(prompt_blocks) + "\n"
            f"{end_banner}\n"
            f"INSTRUCTION: Answer the query using ONLY the evidence demarcated between the boundary fences above. "
            f"Cite exact passage IDs and sūtra references for every statement. Do not extrapolate or fabricate facts."
        )

        return StructuredRAGContext(
            query=query,
            is_sufficient=True,
            status="sufficient_evidence",
            evidence_passages=selected_passages,
            passage_count=len(selected_passages),
            total_characters=len(rendered),
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
            insufficient_reason=None,
            rendered_context=rendered,
        )


# Singleton builder instance
structured_context_builder = StructuredContextBuilder()
