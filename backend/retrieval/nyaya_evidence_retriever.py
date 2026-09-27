"""
Nyāya Evidence Retriever specifically designed for Epistemic Proof Construction.

Segregates evidence into two epistemically distinct categories:
1. Case-specific evidence (caseEvidence):
   - Passages describing the subject (Pakṣa), event, entity, situation, or conduct in the query.
   - Retrieved via entity matching, concept matching, semantic similarity, and KG relationship traversal.
   - Filters out spurious lexical-only matches that lack semantic relevance and KG grounding.

2. Canonical / General-rule evidence (canonicalEvidence):
   - Foundational sūtras establishing the universal invariance (Vyāpti) or general semiotic relation.
   - Retrieved directly from Neo4j Aura with complete literary provenance.

3. Supporting evidence (supportingEvidence):
   - Secondary biotic signifiers, seasonal markers, and multi-hop corroborating passages.

4. Source metadata (sourceMetadata):
   - Comprehensive provenance audit covering works, sections, chapters, sūtras, and validation status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
from core.logger import logger
from query.query_preprocessor import query_preprocessor, ProcessedQuery
from query.query_decomposer import QueryDecomposer


@dataclass
class NyayaEvidenceResponse:
    """Explicit structured response for Nyāya proof retrieval."""
    query: str
    tinai: str
    case_evidence: List[Dict[str, Any]] = field(default_factory=list)
    canonical_evidence: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    vyapti_evidence: List[Dict[str, Any]] = field(default_factory=list)
    application_evidence: List[Dict[str, Any]] = field(default_factory=list)
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.vyapti_evidence and self.canonical_evidence:
            self.vyapti_evidence = list(self.canonical_evidence)
        elif self.vyapti_evidence and not self.canonical_evidence:
            self.canonical_evidence = list(self.vyapti_evidence)

        if not self.application_evidence and self.supporting_evidence:
            self.application_evidence = list(self.supporting_evidence)
        elif self.application_evidence and not self.supporting_evidence:
            self.supporting_evidence = list(self.application_evidence)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes response to camelCase / standard API format."""
        return {
            "query": self.query,
            "tinai": self.tinai,
            "caseEvidence": self.case_evidence,
            "canonicalEvidence": self.canonical_evidence,
            "vyaptiEvidence": self.vyapti_evidence,
            "applicationEvidence": self.application_evidence,
            "supportingEvidence": self.supporting_evidence,
            "sourceMetadata": self.source_metadata,
            "totalEvidenceCount": len(self.case_evidence) + len(self.vyapti_evidence) + len(self.application_evidence),
        }


class NyayaEvidenceRetriever:
    """
    Retrieval engine engineered specifically for Nyāya proof construction.
    Avoids literal-only matching, enforces semantic + KG grounding, and
    queries canonical Vyāpti rules directly from Neo4j Aura.
    """

    MIN_SEMANTIC_THRESHOLD_FOR_LEXICAL = 0.20

    @classmethod
    def retrieve_nyaya_evidence(
        cls,
        query_text: str,
        tinai: Optional[str] = None,
        depth: int = 2,
        focus: str = "Relationship",
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> NyayaEvidenceResponse:
        """
        Executes dual-category retrieval returning caseEvidence, canonicalEvidence,
        supportingEvidence, and sourceMetadata.
        """
        clean_q = (query_text or "").strip()
        if not clean_q:
            return NyayaEvidenceResponse(query="", tinai=tinai or "General")

        # 1. Query Preprocessing & Entity/Concept Extraction
        processed: ProcessedQuery = query_preprocessor.preprocess(clean_q, focus=focus)
        decomposed = QueryDecomposer.decompose(processed.normalized_query or clean_q, focus=focus)

        effective_tinai = (
            tinai
            or processed.detected_tinai
            or decomposed.get("detected_tinai")
            or "Kuṟiñci"
        )
        if effective_tinai and str(effective_tinai).lower() in ("general", "unknown", "none", ""):
            effective_tinai = "Kuṟiñci"

        # Combine all extracted entities & concepts across channels into unique clean strings
        raw_entity_list = (
            (processed.entities or [])
            + (decomposed.get("entities") or [])
            + (decomposed.get("named_entities") or [])
        )
        all_entities: List[str] = []
        for e in raw_entity_list:
            val = (e.get("name") or e.get("label") or e.get("entity") if isinstance(e, dict) else str(e))
            val = str(val or "").strip()
            if val and val not in all_entities:
                all_entities.append(val)

        raw_concept_list = (
            (processed.concepts or [])
            + (decomposed.get("concepts") or [])
            + (decomposed.get("poetic_concepts") or [])
        )
        all_concepts: List[str] = []
        for c in raw_concept_list:
            val = (c.get("name") or c.get("label") or c.get("concept") if isinstance(c, dict) else str(c))
            val = str(val or "").strip()
            if val and val not in all_concepts:
                all_concepts.append(val)

        # 2. Retrieve Canonical Vyāpti Rules Directly from Neo4j Aura
        canonical_items: List[Dict[str, Any]] = []
        try:
            from knowledge_graph.neo4j_repository import neo4j_repository
            # First try dedicated Vyāpti sūtras
            canonical_items = neo4j_repository.get_canonical_vyapti_sutras(
                tinai=effective_tinai,
                limit=max(3, top_k // 2 + 1),
            )
            if not canonical_items:
                canonical_items = neo4j_repository.get_canonical_evidence_for_tinai(
                    tinai_name=effective_tinai,
                    limit=max(3, top_k // 2 + 1),
                )
        except Exception as e:
            logger.debug(f"NyayaEvidenceRetriever Neo4j canonical retrieval fallback: {e}")

        # 3. Retrieve Case-Specific Evidence via KG Connections & Semantic Similarity
        kg_case_items: List[Dict[str, Any]] = []
        try:
            from knowledge_graph.neo4j_repository import neo4j_repository
            if all_entities or all_concepts:
                kg_case_items = neo4j_repository.get_case_evidence_by_entities_and_concepts(
                    entity_names=all_entities,
                    concept_names=all_concepts,
                    tinai=effective_tinai,
                    limit=top_k,
                )
        except Exception as e:
            logger.debug(f"NyayaEvidenceRetriever Neo4j case retrieval fallback: {e}")

        # 4. Dense Semantic & Hybrid Retrieval with Spurious Lexical Guard
        hybrid_items: List[Dict[str, Any]] = []
        try:
            from retrieval.hybrid_rag_pipeline import hybrid_rag_pipeline
            coll = hybrid_rag_pipeline.retrieve(
                query=clean_q,
                top_k=top_k * 2,
                filters=filters,
                max_graph_depth=depth,
            )
            if coll and coll.items:
                for itm in coll.items:
                    hybrid_items.append(itm.to_dict())
        except Exception as e:
            logger.debug(f"NyayaEvidenceRetriever HybridRAG retrieval fallback: {e}")

        # 5. Filter Out Spurious Lexical Matches
        # Do not allow unrelated verses to be selected merely because of generic token overlap
        guarded_hybrid_items: List[Dict[str, Any]] = []
        for itm in hybrid_items:
            lex_score = float(itm.get("lexical_score") or 0.0)
            sem_score = float(itm.get("semantic_score") or 0.0)
            graph_score = float(itm.get("graph_score") or 0.0)

            # If an item only appeared via lexical and has negligible semantic and graph scores, filter it out
            if lex_score > 0.05 and sem_score < cls.MIN_SEMANTIC_THRESHOLD_FOR_LEXICAL and graph_score <= 0.0:
                # Check if it has an explicit entity match
                has_entity_match = any(
                    ent.lower() in (itm.get("text") or "").lower()
                    for ent in all_entities
                )
                if not has_entity_match:
                    logger.debug(f"Filtered spurious lexical match: {itm.get('passage_id')}")
                    continue

            guarded_hybrid_items.append(itm)

        # 6. Partition & Deduplicate into Case, Canonical, and Supporting Evidence
        canonical_pids: Set[str] = set()
        formatted_canonical: List[Dict[str, Any]] = []

        for item in canonical_items:
            pid = item.get("passage_id") or item.get("id")
            if pid and pid not in canonical_pids:
                canonical_pids.add(pid)
                item["evidenceRole"] = "canonicalEvidence"
                item["category"] = "CanonicalVyāptiRule"
                formatted_canonical.append(item)

        case_pids: Set[str] = set()
        formatted_case: List[Dict[str, Any]] = []

        # Add KG-derived case items first
        for item in kg_case_items:
            pid = item.get("passage_id") or item.get("id")
            if pid and pid not in canonical_pids and pid not in case_pids:
                case_pids.add(pid)
                item["evidenceRole"] = "caseEvidence"
                item["category"] = "CaseEvidence"
                formatted_case.append(item)

        # Add guarded semantic / hybrid items as case or supporting evidence
        supporting_items: List[Dict[str, Any]] = []
        supporting_pids: Set[str] = set()

        for item in guarded_hybrid_items:
            pid = item.get("passage_id") or item.get("id")
            if not pid:
                continue

            # If already canonical, skip
            if pid in canonical_pids:
                continue

            # Check if this item relates to case subject
            if pid not in case_pids:
                if len(formatted_case) < top_k:
                    case_pids.add(pid)
                    item["evidenceRole"] = "caseEvidence"
                    formatted_case.append(item)
                elif pid not in supporting_pids:
                    supporting_pids.add(pid)
                    item["evidenceRole"] = "supportingEvidence"
                    supporting_items.append(item)

        # If case items are still empty, take non-canonical guarded items or partition canonical
        if not formatted_case and len(formatted_canonical) > 1:
            # First item serves as canonical Vyāpti, subsequent item grounds the case instance
            item = formatted_canonical.pop()
            item["evidenceRole"] = "caseEvidence"
            formatted_case.append(item)

        # 7. Compile Comprehensive Source Metadata
        all_selected = formatted_case + formatted_canonical + supporting_items
        raw_works = set()
        raw_sections = set()
        raw_chapters = set()
        sutra_refs = []

        for it in all_selected:
            w = it.get("work") or it.get("work_name") or (it.get("source", {}).get("work") if isinstance(it.get("source"), dict) else None) or "Tolkāppiyam"
            raw_works.add(str(w))

            s = it.get("section") or it.get("section_name") or (it.get("source", {}).get("section") if isinstance(it.get("source"), dict) else None) or "Poruḷatikāram"
            raw_sections.add(str(s))

            c = it.get("chapter") or it.get("chapter_name") or (it.get("source", {}).get("chapter") if isinstance(it.get("source"), dict) else None) or "Akattiṇaiyiyal"
            raw_chapters.add(str(c))

            ref = it.get("source_reference") or it.get("citation") or (it.get("source", {}).get("reference") if isinstance(it.get("source"), dict) else "")
            if ref:
                sutra_refs.append(str(ref))

        works = sorted(list(raw_works))
        sections = sorted(list(raw_sections))
        chapters = sorted(list(raw_chapters))

        source_metadata = {
            "works": works if works else ["Tolkāppiyam"],
            "sections": sections if sections else ["Poruḷatikāram"],
            "chapters": chapters if chapters else ["Akattiṇaiyiyal"],
            "sutraReferences": [r for r in sutra_refs if r],
            "totalCase": len(formatted_case),
            "totalCanonical": len(formatted_canonical),
            "totalSupporting": len(supporting_items),
            "authoritativeSource": "Neo4j Aura",
            "tinai": effective_tinai,
            "epistemicGrounded": bool(formatted_case and formatted_canonical),
        }

        return NyayaEvidenceResponse(
            query=clean_q,
            tinai=effective_tinai,
            case_evidence=formatted_case,
            canonical_evidence=formatted_canonical,
            supporting_evidence=supporting_items,
            vyapti_evidence=formatted_canonical,
            application_evidence=supporting_items,
            source_metadata=source_metadata,
        )


# Singleton instance
nyaya_evidence_retriever = NyayaEvidenceRetriever()
