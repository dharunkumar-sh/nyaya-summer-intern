"""
Dedicated Graph Retrieval Service on Neo4j Aura for the Classical Tamil Query Pipeline.

Retrieves grounded knowledge from Neo4j Aura (nodes, relationships, passages,
evidence paths, and provenance hierarchy) given structured or unstructured user queries.
Supports configurable traversal depth (defaulting safely to 2-3 hops) and gracefully
falls back to the in-memory Hierarchical Knowledge Graph when Neo4j is offline.

Strictly non-generative: Grounded retrieval and context preparation only.
No synthetic answers are generated at this layer.
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.logger import logger
from core.exceptions import KnowledgeGraphError
from query.query_preprocessor import (
    ProcessedQuery,
    query_preprocessor,
    LITERARY_TERMINOLOGY,
)
from ingestion.corpus_loader import corpus_loader
from knowledge_graph.graph_builder import kg_instance
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from knowledge_graph.neo4j_repository import neo4j_repository, Neo4jRepository
from knowledge_graph.ontology import TolkappiyamOntology


# =============================================================================
# Structured Retrieval Models
# =============================================================================

@dataclass
class EvidencePath:
    """Represents a grounded evidence/proof trace path in the Knowledge Graph."""
    start_id: str
    target_id: str
    length: int
    cumulative_confidence: float
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    target_type: Optional[str] = None
    ground_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphRetrievalResult:
    """
    Structured retrieval result containing grounded knowledge from the Knowledge Graph.
    Prepared strictly for downstream RAG and Nyāya reasoning layers without answer generation.
    """
    query_summary: Dict[str, Any]
    passage_ids: List[str]
    passages: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    evidence_paths: List[Dict[str, Any]]
    provenance: Dict[str, Dict[str, Any]]
    subgraph: Dict[str, Any]
    epistemic_context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Canonical Sūtra Citation & Alias Mappings
# =============================================================================

SUTRA_CITATION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Tolkappiyam Porulatikaram Akattinaiyiyal
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:3\b|003\b)", re.IGNORECASE), "tol-porul-akam-003"),
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:4\b|004\b)", re.IGNORECASE), "tol-porul-akam-004"),
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:5\b|005\b)", re.IGNORECASE), "tol-porul-akam-005"),
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:14\b|014\b)", re.IGNORECASE), "tol-porul-akam-014"),
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:18\b|018\b)", re.IGNORECASE), "tol-porul-akam-018"),
    # Meyppattiyal
    (re.compile(r"(?:s[uū]tra|சூத்திரம்)\s*(?:1\b|001\b).*(?:mey|மெய்|rasa)", re.IGNORECASE), "tol-porul-mey-001"),
    (re.compile(r"(?:mey|மெய்ப்பாட்டியல்).*(?:s[uū]tra|சூத்திரம்)\s*(?:1\b|001\b)", re.IGNORECASE), "tol-porul-mey-001"),
]

# Canonical fallback alias map
SYNONYM_KG_MAP: Dict[str, str] = {
    "ceyon": "ceyon",
    "cēyōṉ": "ceyon",
    "murugan": "ceyon",
    "murukan": "ceyon",
    "சேயோன்": "ceyon",
    "முருகன்": "ceyon",
    "mayon": "mayon",
    "māyōṉ": "mayon",
    "thirumal": "mayon",
    "tirumal": "mayon",
    "vishnu": "mayon",
    "மாயோன்": "mayon",
    "திருமால்": "mayon",
    "ventan": "ventan",
    "vēntaṉ": "ventan",
    "indran": "ventan",
    "வேந்தன்": "ventan",
    "இந்திரன்": "ventan",
    "varunan": "varunan",
    "varuṇaṉ": "varunan",
    "வருணன்": "varunan",
    "kotravai": "kotravai",
    "koṟṟavai": "kotravai",
    "கொற்றவை": "kotravai",
    "mutalporul": "mutalporul",
    "mutalporuḷ": "mutalporul",
    "முதற்பொருள்": "mutalporul",
    "mutal": "mutalporul",
    "karupporul": "karupporul",
    "karupporuḷ": "karupporul",
    "கருப்பொருள்": "karupporul",
    "karu": "karupporul",
    "uriporul": "uripporul",
    "uripporul": "uripporul",
    "uripporuḷ": "uripporul",
    "உரிப்பொருள்": "uripporul",
    "uri": "uripporul",
    "kurinci": "kurinci",
    "kuṟiñci": "kurinci",
    "kurinji": "kurinci",
    "குறிஞ்சி": "kurinci",
    "mullai": "mullai",
    "முல்லை": "mullai",
    "marutam": "marutam",
    "மருதம்": "marutam",
    "neytal": "neytal",
    "நெய்தல்": "neytal",
    "palai": "palai",
    "pālai": "palai",
    "பாலை": "palai",
    "punartal": "punartal",
    "puṇartal": "punartal",
    "புணர்தல்": "punartal",
    "pirital": "pirital",
    "பிரிதல்": "pirital",
    "iruttal": "iruttal",
    "இருத்தல்": "iruttal",
    "irankal": "irankal",
    "iraṅkal": "irankal",
    "irangal": "irankal",
    "இரங்கல்": "irankal",
    "udal": "utal",
    "utal": "utal",
    "ūṭal": "utal",
    "oodal": "utal",
    "ஊடல்": "utal",
    "venkai": "venkai",
    "vēṅkai": "venkai",
    "வேங்கை": "venkai",
}


# =============================================================================
# Graph Retrieval Service Implementation
# =============================================================================

class GraphRetrievalService:
    """
    Dedicated Graph Retrieval Service querying Neo4j Aura with safe in-memory fallback.
    Resolves structured query entities, concepts, and source references to canonical KG nodes,
    executes bounded multi-hop traversals, and extracts proof traces and provenance.
    """

    def __init__(
        self,
        neo4j_repo: Optional[Neo4jRepository] = None,
        kg_query_engine: Optional[KnowledgeGraphQueryEngine] = None,
    ):
        self._neo4j_repo = neo4j_repo
        self._kg_query = kg_query_engine

    @property
    def repo(self) -> Neo4jRepository:
        if self._neo4j_repo is None:
            self._neo4j_repo = neo4j_repository
        return self._neo4j_repo

    @property
    def kg_query(self) -> KnowledgeGraphQueryEngine:
        if self._kg_query is None:
            self._kg_query = KnowledgeGraphQueryEngine(kg_instance)
        return self._kg_query

    # -------------------------------------------------------------------------
    # 1. Seed Resolution & Query Normalization
    # -------------------------------------------------------------------------

    def resolve_seed_nodes(
        self,
        query_input: Union[ProcessedQuery, Dict[str, Any], str],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Parses structured or unstructured query input to extract:
        - metadata dict (original_query, normalized_query, detected_tinai, etc.)
        - resolved canonical KG seed node IDs (concepts, entities)
        - resolved passage IDs (sūtra citations)
        """
        raw_text = ""
        normalized_text = ""
        detected_tinai = "General"
        entities_input: List[Any] = []
        concepts_input: List[Any] = []
        source_refs_input: List[Any] = []
        pre_resolved_seeds: List[str] = []

        if isinstance(query_input, ProcessedQuery):
            raw_text = query_input.original_query
            normalized_text = query_input.normalized_query
            detected_tinai = query_input.detected_tinai or "General"
            entities_input = [e.get("term") if isinstance(e, dict) else e for e in query_input.entities]
            concepts_input = [c.get("term") if isinstance(c, dict) else c for c in query_input.concepts]
            source_refs_input = [s.get("citation") if isinstance(s, dict) else s for s in query_input.source_references]
            pre_resolved_seeds = list(query_input.kg_seed_node_ids or [])

        elif isinstance(query_input, dict):
            raw_text = query_input.get("queryText") or query_input.get("query", "")
            entities_input = query_input.get("entities", [])
            concepts_input = query_input.get("concepts", [])
            source_refs_input = query_input.get("source_references", []) or query_input.get("sources", [])
            detected_tinai = query_input.get("tinai") or query_input.get("detected_tinai", "General")
            pre_resolved_seeds = list(query_input.get("seed_node_ids", []))
            normalized_text = query_input.get("normalized_query", raw_text)

        elif isinstance(query_input, str):
            raw_text = query_input
            processed = query_preprocessor.preprocess(query_input)
            normalized_text = processed.normalized_query
            detected_tinai = processed.detected_tinai or "General"
            entities_input = [e.get("term") for e in processed.entities]
            concepts_input = [c.get("term") for c in processed.concepts]
            source_refs_input = [s.get("citation") for s in processed.source_references]
            pre_resolved_seeds = list(processed.kg_seed_node_ids or [])

        seed_node_ids: Set[str] = set(pre_resolved_seeds)
        passage_ids: Set[str] = set()

        # Check explicit source references
        full_query_context = f"{raw_text} {normalized_text} {' '.join(str(s) for s in source_refs_input)}"
        for pattern, pid in SUTRA_CITATION_PATTERNS:
            if pattern.search(full_query_context):
                passage_ids.add(pid)
                seed_node_ids.add(pid)

        for ref in source_refs_input:
            ref_str = str(ref).strip().lower()
            if ref_str.startswith("tol-porul-"):
                passage_ids.add(ref_str)
                seed_node_ids.add(ref_str)
            for pattern, pid in SUTRA_CITATION_PATTERNS:
                if pattern.search(ref_str):
                    passage_ids.add(pid)
                    seed_node_ids.add(pid)

        # Resolve entity and concept terms
        combined_terms = list(entities_input) + list(concepts_input)
        for term_item in combined_terms:
            if not term_item:
                continue
            term_str = str(term_item).strip().lower()

            # Check direct synonym dictionary
            if term_str in SYNONYM_KG_MAP:
                seed_node_ids.add(SYNONYM_KG_MAP[term_str])
                continue

            # Check LITERARY_TERMINOLOGY
            if term_str in LITERARY_TERMINOLOGY:
                kg_id = LITERARY_TERMINOLOGY[term_str].get("kg_id")
                if kg_id:
                    seed_node_ids.add(kg_id)
                continue

            # Check for direct ID match in synonym keys
            for k, v in SYNONYM_KG_MAP.items():
                if k in term_str or term_str in k:
                    seed_node_ids.add(v)
                    break

        # Fallback to tiṇai seeds if no seeds were detected
        if not seed_node_ids:
            tinai_lower = detected_tinai.lower()
            if "kurin" in tinai_lower:
                seed_node_ids.update(["kurinci", "ceyon"])
            elif "mullai" in tinai_lower:
                seed_node_ids.update(["mullai", "mayon"])
            elif "marut" in tinai_lower:
                seed_node_ids.update(["marutam", "ventan"])
            elif "neytal" in tinai_lower:
                seed_node_ids.update(["neytal", "varunan"])
            elif "palai" in tinai_lower:
                seed_node_ids.update(["palai", "kotravai"])
            else:
                seed_node_ids.update(["mutalporul", "uriporul"])

        query_meta = {
            "original_query": raw_text,
            "normalized_query": normalized_text,
            "detected_tinai": detected_tinai,
            "extracted_entities": [str(e) for e in entities_input if e],
            "extracted_concepts": [str(c) for c in concepts_input if c],
            "extracted_source_references": [str(s) for s in source_refs_input if s],
        }

        return query_meta, sorted(list(seed_node_ids)), sorted(list(passage_ids))

    # -------------------------------------------------------------------------
    # 2. Main Retrieval Entry Point
    # -------------------------------------------------------------------------

    def retrieve_grounded_graph(
        self,
        query_input: Union[ProcessedQuery, Dict[str, Any], str],
        hop_depth: int = 2,
        max_nodes: int = 50,
        max_paths: int = 20,
    ) -> GraphRetrievalResult:
        """
        Executes grounded knowledge graph retrieval across Neo4j Aura or in-memory fallback.
        Returns strictly grounded structured knowledge without answer generation.
        """
        # Clamp hop depth safely to [1, 4]
        safe_hops = min(max(int(hop_depth), 1), 4)

        query_meta, seed_node_ids, seed_passage_ids = self.resolve_seed_nodes(query_input)
        logger.info(
            f"GraphRetrievalService: Retrieving grounded graph for seeds {seed_node_ids}, "
            f"passages {seed_passage_ids}, hops={safe_hops}"
        )

        use_neo4j = self.repo.is_available()
        retrieval_source = "neo4j_aura" if use_neo4j else "in_memory_fallback"

        result: Optional[GraphRetrievalResult] = None

        if use_neo4j:
            try:
                result = self._retrieve_from_neo4j(
                    query_meta=query_meta,
                    seed_node_ids=seed_node_ids,
                    seed_passage_ids=seed_passage_ids,
                    hop_depth=safe_hops,
                    max_nodes=max_nodes,
                    max_paths=max_paths,
                )
            except Exception as e:
                logger.warning(
                    f"Neo4j Aura retrieval encountered error: {e}. Falling back to in-memory graph store.",
                    exc_info=True,
                )
                retrieval_source = "in_memory_fallback (recovery)"
                result = None

        if result is None:
            result = self._retrieve_from_memory(
                query_meta=query_meta,
                seed_node_ids=seed_node_ids,
                seed_passage_ids=seed_passage_ids,
                hop_depth=safe_hops,
                max_nodes=max_nodes,
                max_paths=max_paths,
                retrieval_source=retrieval_source,
            )

        return result

    # -------------------------------------------------------------------------
    # 3. Neo4j Aura Execution Engine
    # -------------------------------------------------------------------------

    def _retrieve_from_neo4j(
        self,
        query_meta: Dict[str, Any],
        seed_node_ids: List[str],
        seed_passage_ids: List[str],
        hop_depth: int,
        max_nodes: int,
        max_paths: int,
    ) -> GraphRetrievalResult:
        """Retrieves grounded nodes, paths, passages, and provenance from Neo4j Aura."""
        all_nodes_dict: Dict[str, Dict[str, Any]] = {}
        all_edges_dict: Dict[str, Dict[str, Any]] = {}
        evidence_paths: List[Dict[str, Any]] = []
        provenance_map: Dict[str, Dict[str, Any]] = {}
        discovered_passage_ids: Set[str] = set(seed_passage_ids)

        # 1. Multi-hop traversal for each seed node
        for seed_id in seed_node_ids:
            traversal_paths = self.repo.traverse_multi_hop(
                start_id=seed_id,
                max_hops=hop_depth,
            )
            for path in traversal_paths:
                p_nodes = path.get("nodes", [])
                p_rels = path.get("relationships", [])
                for node in p_nodes:
                    nid = node.get("id")
                    if nid:
                        all_nodes_dict[nid] = node
                        if node.get("type") in ("Passage", "Verse") or str(nid).startswith("tol-porul-"):
                            discovered_passage_ids.add(nid)

                for i in range(len(p_nodes) - 1):
                    u_id = p_nodes[i].get("id")
                    v_id = p_nodes[i + 1].get("id")
                    rel_info = p_rels[i] if i < len(p_rels) else {}
                    rel_type = rel_info.get("type", "RELATED_TO")
                    edge_id = f"e_{u_id}_{rel_type}_{v_id}"
                    all_edges_dict[edge_id] = {
                        "id": edge_id,
                        "source": u_id,
                        "target": v_id,
                        "type": rel_type,
                        "relation": rel_type,
                        "confidence": float(rel_info.get("confidence", 1.0)),
                    }

        # 2. Evidence proof traces for seeds
        for seed_id in seed_node_ids:
            paths = self.repo.get_evidence_paths(concept_or_entity_id=seed_id, max_depth=hop_depth + 1)
            for ep in paths:
                conf = float(ep.get("confidence", 1.0))
                norm_ep = {
                    "start_id": ep.get("target_id") or seed_id,
                    "target_id": ep.get("ground_id"),
                    "ground_id": ep.get("ground_id"),
                    "ground_type": ep.get("ground_type", "Passage"),
                    "length": ep.get("length", 1),
                    "confidence": conf,
                    "cumulative_confidence": conf,
                    "nodes": ep.get("nodes", []),
                    "edges": ep.get("edges", []),
                }
                evidence_paths.append(norm_ep)
                for node in ep.get("nodes", []):
                    nid = node.get("id")
                    if nid:
                        all_nodes_dict[nid] = node
                        if node.get("type") in ("Passage", "Verse") or str(nid).startswith("tol-porul-"):
                            discovered_passage_ids.add(nid)
                if ep.get("ground_id") and str(ep.get("ground_id")).startswith("tol-porul-"):
                    discovered_passage_ids.add(ep["ground_id"])

        # 3. Retrieve detailed literary context and provenance for all discovered passages
        passages_list: List[Dict[str, Any]] = []
        for pid in sorted(list(discovered_passage_ids)):
            passage_ctx = self.repo.get_literary_context_for_passage(pid)
            if passage_ctx and passage_ctx.get("passage"):
                pass_data = passage_ctx["passage"]
                prov_path = passage_ctx.get("provenance_path", [])
                passages_list.append({
                    "id": pid,
                    "sutra_number": pass_data.get("sutra_number"),
                    "chapter_name": pass_data.get("chapter_name") or pass_data.get("section_name"),
                    "work_name": pass_data.get("work_name", "Tolkāppiyam"),
                    "source_reference": pass_data.get("source_reference") or f"Sūtra {pass_data.get('sutra_number')}",
                    "text": pass_data.get("original_text") or pass_data.get("text", ""),
                    "translation": pass_data.get("translation", ""),
                    "tinai": pass_data.get("tinai"),
                    "connected_concepts": [c.get("id") for c in passage_ctx.get("concepts", [])],
                    "connected_entities": [e.get("id") for e in passage_ctx.get("entities", [])],
                })
                provenance_map[pid] = self._build_provenance_record(pid, prov_path)
            else:
                # Fallback to local corpus metadata
                local_sutra = self._get_corpus_sutra(pid)
                if local_sutra:
                    passages_list.append(local_sutra)
                    provenance_map[pid] = self._build_default_provenance(pid)

        # Build Epistemic Context
        epistemic_context = self._compile_epistemic_context(
            query_meta=query_meta,
            nodes=list(all_nodes_dict.values()),
            edges=list(all_edges_dict.values()),
            passages=passages_list,
            evidence_paths=evidence_paths,
            source="neo4j_aura",
        )

        nodes_out = list(all_nodes_dict.values())[:max_nodes]
        edges_out = list(all_edges_dict.values())
        # Filter edges so endpoints exist in nodes_out
        node_id_set = {n["id"] for n in nodes_out}
        valid_edges = [e for e in edges_out if e["source"] in node_id_set and e["target"] in node_id_set]

        summary = {
            **query_meta,
            "seed_node_ids": seed_node_ids,
            "hop_depth": hop_depth,
            "retrieval_source": "neo4j_aura",
            "total_nodes": len(nodes_out),
            "total_relationships": len(valid_edges),
            "total_passages": len(passages_list),
            "total_evidence_paths": len(evidence_paths),
        }

        return GraphRetrievalResult(
            query_summary=summary,
            passage_ids=[p["id"] for p in passages_list],
            passages=passages_list,
            nodes=nodes_out,
            relationships=valid_edges,
            evidence_paths=evidence_paths[:max_paths],
            provenance=provenance_map,
            subgraph={
                "nodes": nodes_out,
                "edges": valid_edges,
                "total_nodes": len(nodes_out),
                "total_edges": len(valid_edges),
            },
            epistemic_context=epistemic_context,
        )

    # -------------------------------------------------------------------------
    # 4. In-Memory Graph Fallback Engine
    # -------------------------------------------------------------------------

    def _retrieve_from_memory(
        self,
        query_meta: Dict[str, Any],
        seed_node_ids: List[str],
        seed_passage_ids: List[str],
        hop_depth: int,
        max_nodes: int,
        max_paths: int,
        retrieval_source: str = "in_memory_fallback",
    ) -> GraphRetrievalResult:
        """Retrieves grounded nodes, paths, passages, and provenance from in-memory NetworkX store."""
        store = kg_instance.store
        all_nodes_dict: Dict[str, Dict[str, Any]] = {}
        all_edges_dict: Dict[str, Dict[str, Any]] = {}
        evidence_paths: List[Dict[str, Any]] = []
        provenance_map: Dict[str, Dict[str, Any]] = {}
        discovered_passage_ids: Set[str] = set(seed_passage_ids)

        # 1. Expand subgraph around seeds
        expanded = store.expand_subgraph(node_ids=seed_node_ids, hops=hop_depth)
        for n in expanded.get("nodes", []):
            nid = n.get("id")
            if nid:
                all_nodes_dict[nid] = n
                if n.get("hierarchy_level") == "L3" or str(nid).startswith("tol-porul-"):
                    discovered_passage_ids.add(nid)

        for e in expanded.get("edges", []):
            eid = e.get("id") or f"e_{e.get('source')}_{e.get('relation')}_{e.get('target')}"
            all_edges_dict[eid] = {
                "id": eid,
                "source": e.get("source"),
                "target": e.get("target"),
                "type": e.get("relation", "RELATED_TO"),
                "relation": e.get("relation", "RELATED_TO"),
                "confidence": float(e.get("confidence", 1.0)),
                "validation_level": e.get("validation_level", "corpus_validated"),
            }

        # 2. Add seed passages and their hierarchical ancestors if not already in store
        for pid in seed_passage_ids:
            if store.has_node(pid):
                pnode = store.get_node(pid)
                if pnode:
                    all_nodes_dict[pid] = pnode.to_dict()
                    discovered_passage_ids.add(pid)

        # 3. Find proof paths connecting seeds to known passages or among seeds
        for seed_id in seed_node_ids:
            if not store.has_node(seed_id):
                continue
            for target_id in list(discovered_passage_ids) + [s for s in seed_node_ids if s != seed_id]:
                if not store.has_node(target_id) or seed_id == target_id:
                    continue
                paths = store.find_paths(source_id=seed_id, target_id=target_id, max_depth=hop_depth)
                for p in paths:
                    conf = float(p.get("propagated_confidence", 1.0))
                    evidence_paths.append({
                        "start_id": seed_id,
                        "target_id": target_id,
                        "ground_id": target_id,
                        "ground_type": "Passage" if str(target_id).startswith("tol-porul-") else "Concept",
                        "length": p.get("length", len(p.get("edges", []))),
                        "confidence": conf,
                        "cumulative_confidence": conf,
                        "nodes": p.get("nodes", []),
                        "edges": p.get("edges", []),
                    })

        # 4. Compile passage records & provenance hierarchy
        passages_list: List[Dict[str, Any]] = []
        for pid in sorted(list(discovered_passage_ids)):
            sutra_info = self._get_corpus_sutra(pid)
            if sutra_info:
                passages_list.append(sutra_info)
                provenance_map[pid] = self._build_default_provenance(pid)

        # If no passages were discovered directly, passages_list remains empty (zero fake/mock fallback injection)

        # Build Epistemic Context
        epistemic_context = self._compile_epistemic_context(
            query_meta=query_meta,
            nodes=list(all_nodes_dict.values()),
            edges=list(all_edges_dict.values()),
            passages=passages_list,
            evidence_paths=evidence_paths,
            source="in_memory_fallback",
        )

        nodes_out = list(all_nodes_dict.values())[:max_nodes]
        node_id_set = {n["id"] for n in nodes_out}
        valid_edges = [
            e for e in all_edges_dict.values()
            if e["source"] in node_id_set and e["target"] in node_id_set
        ]

        summary = {
            **query_meta,
            "seed_node_ids": seed_node_ids,
            "hop_depth": hop_depth,
            "retrieval_source": retrieval_source,
            "total_nodes": len(nodes_out),
            "total_relationships": len(valid_edges),
            "total_passages": len(passages_list),
            "total_evidence_paths": len(evidence_paths),
        }

        return GraphRetrievalResult(
            query_summary=summary,
            passage_ids=[p["id"] for p in passages_list],
            passages=passages_list,
            nodes=nodes_out,
            relationships=valid_edges,
            evidence_paths=evidence_paths[:max_paths],
            provenance=provenance_map,
            subgraph={
                "nodes": nodes_out,
                "edges": valid_edges,
                "total_nodes": len(nodes_out),
                "total_edges": len(valid_edges),
            },
            epistemic_context=epistemic_context,
        )

    # -------------------------------------------------------------------------
    # 5. Provenance & Epistemic Context Helpers
    # -------------------------------------------------------------------------

    def _build_provenance_record(self, passage_id: str, prov_path: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Constructs 4-tier provenance breadcrumbs from Cypher path."""
        lit = {"id": "lit-sangam", "label": "Classical Tamil Sangam Literature", "level": "L0"}
        work = {"id": "work-tolkappiyam", "label": "Tolkāppiyam (தொல்காப்பியம்)", "level": "L1"}
        sec = {"id": "sec-porul-akam", "label": "Akattiṇaiyiyal (அகத்திணையியல்)", "level": "L2"}
        passage = {"id": passage_id, "label": f"Sūtra {passage_id.split('-')[-1]}", "level": "L3"}

        for n in prov_path:
            lvl = n.get("hierarchy_level") or n.get("type")
            if lvl in ("L0", "Literature"):
                lit = {"id": n.get("id", lit["id"]), "label": n.get("label", lit["label"]), "level": "L0"}
            elif lvl in ("L1", "Work"):
                work = {"id": n.get("id", work["id"]), "label": n.get("label", work["label"]), "level": "L1"}
            elif lvl in ("L2", "Section"):
                sec = {"id": n.get("id", sec["id"]), "label": n.get("label", sec["label"]), "level": "L2"}
            elif lvl in ("L3", "Passage", "Verse"):
                passage = {"id": n.get("id", passage["id"]), "label": n.get("label", passage["label"]), "level": "L3"}

        return {
            "passage_id": passage_id,
            "literature": lit,
            "work": work,
            "section": sec,
            "passage": passage,
            "chain": [lit["label"], work["label"], sec["label"], passage["label"]],
        }

    def _build_default_provenance(self, passage_id: str) -> Dict[str, Any]:
        """Generates canonical 4-tier provenance hierarchy for a Tolkappiyam passage."""
        iyal = "Akattiṇaiyiyal (அகத்திணையியல்)" if "akam" in passage_id else "Meyppāṭṭiyal (மெய்ப்பாட்டியல்)"
        sec_id = "sec-porul-akam" if "akam" in passage_id else "sec-porul-mey"
        sutra_num = passage_id.split("-")[-1]

        lit = {"id": "lit-sangam", "label": "Classical Tamil Sangam Literature (சங்க இலக்கியம்)", "level": "L0"}
        work = {"id": "work-tolkappiyam", "label": "Tolkāppiyam (தொல்காப்பியம்)", "level": "L1"}
        sec = {"id": sec_id, "label": iyal, "level": "L2"}
        passage = {"id": passage_id, "label": f"Sūtra {sutra_num} (நூற்பா {int(sutra_num) if sutra_num.isdigit() else sutra_num})", "level": "L3"}

        return {
            "passage_id": passage_id,
            "literature": lit,
            "work": work,
            "section": sec,
            "passage": passage,
            "chain": [lit["label"], work["label"], sec["label"], passage["label"]],
        }

    def _get_corpus_sutra(self, passage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves sūtra content and metadata from CorpusLoader."""
        for s in corpus_loader.get_all_sutras():
            if s.get("id") == passage_id:
                return {
                    "id": s["id"],
                    "sutra_number": s.get("sutra_number"),
                    "chapter_name": s.get("iyal"),
                    "work_name": "Tolkāppiyam",
                    "source_reference": f"Tolkāppiyam, Poruḷatikāram, {s.get('iyal')}, Sūtra {s.get('sutra_number')}",
                    "text": s.get("tamil_text", ""),
                    "translation": s.get("english_translation", ""),
                    "tinai": s.get("tinai"),
                    "entities": [e.get("name") if isinstance(e, dict) else e for e in s.get("entities", [])],
                    "triples": s.get("triples", []),
                }
        return None

    def _compile_epistemic_context(
        self,
        query_meta: Dict[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        passages: List[Dict[str, Any]],
        evidence_paths: List[Dict[str, Any]],
        source: str,
    ) -> Dict[str, Any]:
        """
        Compiles strictly grounded epistemic structures (premises, candidate hetu,
        vyāpti relations) for downstream Pañcāvayava and Hetvābhāsa reasoning.
        Strictly non-generative: no natural language answer is synthesized.
        """
        premises: List[Dict[str, Any]] = []
        middle_terms: Set[str] = set()
        invariant_relations: List[Dict[str, Any]] = []
        grounded_axioms: List[Dict[str, Any]] = []

        # Extract premises from edges
        for e in edges[:15]:
            premises.append({
                "subject": e.get("source"),
                "predicate": e.get("type") or e.get("relation"),
                "object": e.get("target"),
                "confidence": e.get("confidence", 1.0),
                "grounded": True,
            })
            # Middle terms / signifiers
            if e.get("relation") in ("associated_with", "manifests", "grounds_landscape", "has_karupporul"):
                middle_terms.add(e.get("target"))

        # Extract invariable rules from passages
        for p in passages:
            grounded_axioms.append({
                "passage_id": p.get("id"),
                "source": p.get("source_reference"),
                "sutra_number": p.get("sutra_number"),
                "canonical_statement": p.get("translation") or p.get("text", "")[:100],
            })

            # Check tripartite semiotics
            if p.get("tinai") and p.get("tinai") != "General":
                invariant_relations.append({
                    "antecedent": p.get("tinai"),
                    "consequent": p.get("id"),
                    "rule_type": "TripartiteSemiotics",
                    "confidence": 1.0,
                })

        return {
            "strictly_grounded": True,
            "answer_generated": False,
            "retrieval_source": source,
            "detected_tinai": query_meta.get("detected_tinai", "General"),
            "premises": premises,
            "candidate_middle_terms": sorted(list(middle_terms)),
            "invariant_relations": invariant_relations,
            "grounded_axioms": grounded_axioms,
        }


# Singleton service instance
graph_retrieval_service = GraphRetrievalService()
