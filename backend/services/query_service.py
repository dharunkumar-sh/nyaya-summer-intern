"""
Query Service orchestrating query decomposition, hybrid retrieval, and KG grounding.
"""
from typing import Dict, Any
from query.query_decomposer import QueryDecomposer
from query.query_preprocessor import query_preprocessor
from retrieval.ranker import EvidenceRanker
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from services.graph_retrieval_service import graph_retrieval_service


class QueryService:
    """Orchestrates query parsing, multi-channel retrieval, and ontological context gathering."""

    def __init__(self):
        self._retriever = None
        self._kg_query = None

    @property
    def retriever(self):
        if self._retriever is None:
            from retrieval.hybrid_retriever import HybridRetriever
            self._retriever = HybridRetriever()
        return self._retriever

    @property
    def kg_query(self):
        if self._kg_query is None:
            from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
            self._kg_query = KnowledgeGraphQueryEngine()
        return self._kg_query

    def process_query(self, query_text: str, depth: int = 1, focus: str = "Relationship") -> Dict[str, Any]:
        """Executes query decomposition and hybrid evidence retrieval."""
        # 0. Dedicated Query Preprocessing Pipeline
        processed_query = query_preprocessor.preprocess(query_text, focus=focus)

        # 1. Parse and decompose inquiry
        decomposed = QueryDecomposer.decompose(processed_query.normalized_query or query_text, focus=focus)
        tinai = processed_query.detected_tinai or decomposed["detected_tinai"]

        # 2. Hybrid Retrieval (BM25 + Vector + KG) using preprocessed query
        search_str = processed_query.bm25_query if processed_query.bm25_query else query_text
        ranked_sutras = self.retriever.search(search_str, top_k=5)
        evidence_records = EvidenceRanker.format_evidence_records(ranked_sutras)

        # 3. Knowledge Graph Subgraph Extraction
        center_node = processed_query.kg_seed_node_ids[0] if processed_query.kg_seed_node_ids else ("kurinci" if tinai == "Kuṟiñci" else "mutalporul")
        if decomposed["entities"]:
            first_term = decomposed["entities"][0]["term"]
            term_to_id = {
                "சேயோன்": "ceyon",
                "குறிஞ்சி": "kurinci",
                "முதற்பொருள்": "mutalporul",
                "வேங்கை": "venkai",
                "புணர்தல்": "punartal",
            }
            center_node = term_to_id.get(first_term, center_node)

        subgraph = self.kg_query.query_subgraph(
            focus_entity_id=center_node,
            max_hops=depth,
        )

        # 4. Dedicated Grounded Graph Retrieval (Neo4j Aura with safe in-memory fallback)
        grounded_graph = graph_retrieval_service.retrieve_grounded_graph(
            query_input=processed_query,
            hop_depth=depth,
        )

        return {
            "processed_query": processed_query.to_dict(),
            "query_decomposition": decomposed,
            "detected_tinai": tinai,
            "evidence_records": evidence_records,
            "knowledge_graph": subgraph,
            "grounded_graph": grounded_graph.to_dict(),
        }


# Singleton service instance
query_service = QueryService()
