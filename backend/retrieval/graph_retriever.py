"""
Graph retriever leveraging Knowledge Graph connectivity to retrieve canonical sūtra citations.
"""
from typing import List, Dict, Any, Tuple
from knowledge_graph.graph_builder import kg_instance
from extraction.entity_extractor import EntityExtractor


class GraphRetriever:
    """Uses entity extraction and KG node traversal to retrieve relevant sūtras."""

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Maps query entities to KG nodes and resolves citations back to canonical sūtras."""
        from ingestion.corpus_loader import corpus_loader

        g = kg_instance.graph
        entity_objs = EntityExtractor.extract(query, source_id="query")
        entity_terms = {e.canonical_form for e in entity_objs}

        all_sutras = corpus_loader.get_all_sutras()
        scored_sutras: List[Tuple[Dict[str, Any], float]] = []

        for sutra in all_sutras:
            score = 0.1  # baseline prior
            sutra_entities = set(sutra.get("entities", []))

            # Match overlap
            matched = entity_terms.intersection(sutra_entities)
            if matched:
                score += 0.4 * len(matched)

            # Check if sutra's triples mention any query entity
            for t in sutra.get("triples", []):
                for term in entity_terms:
                    if term in t.get("subject", "") or term in t.get("object", ""):
                        score += 0.25

            # Tiṇai context match
            for e in entity_objs:
                if e.tinai and e.tinai == sutra.get("tinai"):
                    score += 0.2

            score = min(score, 1.0)
            if score > 0.15:
                scored_sutras.append((sutra, score))

        scored_sutras.sort(key=lambda x: x[1], reverse=True)
        return scored_sutras[:top_k]
