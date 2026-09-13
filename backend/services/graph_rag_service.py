"""
Graph RAG Service uniting Neo4j Knowledge Graph Traversal with FAISS and BM25 RAG.

Extracts dense semantic and lexical evidence chunks, maps them to topological
Knowledge Graph nodes, and enriches evidence with multi-hop ontological context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from core.logger import logger
from retrieval.rag_service import rag_engine, RAGRetrievalEngine
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from knowledge_graph.graph_builder import kg_instance
from query.query_decomposer import QueryDecomposer


class GraphRAGService:
    """
    High-level Graph-Augmented Retrieval Service.
    Enriches RAG retrieved chunks with Neo4j / Knowledge Graph ontological hierarchy.
    """

    def __init__(
        self,
        retrieval_engine: Optional[RAGRetrievalEngine] = None,
        kg_query_engine: Optional[KnowledgeGraphQueryEngine] = None,
    ):
        self.retrieval = retrieval_engine or rag_engine
        self.kg_query = kg_query_engine or KnowledgeGraphQueryEngine(kg_instance)

    def retrieve_graph_augmented_context(
        self,
        query: str,
        top_k: int = 5,
        hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval (FAISS + BM25) and enriches results with
        multi-hop Knowledge Graph topological context.
        """
        # 1. Hybrid Retrieval (FAISS Dense Vector + BM25 Lexical)
        evidence_chunks = self.retrieval.hybrid_search(query, top_k=top_k)

        # 2. Query Decomposition & Entity Detection
        decomposed = QueryDecomposer.decompose(query)
        detected_tinai = decomposed.get("detected_tinai", "General")
        detected_entities = decomposed.get("entities", [])

        # 3. Collect seed entity IDs from query and retrieved chunks
        seed_nodes: List[str] = []

        # From query entities
        for ent in detected_entities:
            term = ent.get("term", "").lower()
            if self.kg_query.builder.store.has_node(term):
                seed_nodes.append(term)

        # From retrieved chunks
        for chunk in evidence_chunks:
            doc_id = chunk.get("document_id")
            if doc_id and self.kg_query.builder.store.has_node(doc_id):
                seed_nodes.append(doc_id)

            for ent in chunk.get("metadata", {}).get("entities", []):
                ent_lower = str(ent).lower()
                if self.kg_query.builder.store.has_node(ent_lower):
                    seed_nodes.append(ent_lower)

        # Fallback to tiṇai or central concept if no seeds found
        if not seed_nodes:
            if detected_tinai == "Kuṟiñci":
                seed_nodes = ["kurinci", "ceyon"]
            elif detected_tinai == "Mullai":
                seed_nodes = ["mullai", "mayon"]
            else:
                seed_nodes = ["mutalporul", "uriporul"]

        # Deduplicate seeds
        seed_nodes = list(dict.fromkeys(seed_nodes))

        # 4. Expand Multi-hop Subgraph from Neo4j / KG
        subgraph = self.kg_query.expand_subgraph(node_ids=seed_nodes, hops=hops)

        # 5. Extract structural source evidence and axioms
        axioms = []
        for seed in seed_nodes[:3]:
            ev_list = self.kg_query.get_source_evidence(seed)
            if ev_list:
                axioms.extend(ev_list[:2])

        return {
            "query": query,
            "detected_tinai": detected_tinai,
            "seed_entities": seed_nodes,
            "retrieved_evidence": evidence_chunks,
            "total_evidence_chunks": len(evidence_chunks),
            "graph_subgraph": subgraph,
            "graph_axioms": axioms,
        }


# Singleton service instance
graph_rag_service = GraphRAGService()
