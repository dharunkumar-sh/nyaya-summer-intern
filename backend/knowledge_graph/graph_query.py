"""
Knowledge Graph query engine supporting hierarchical traversal, k-hop subgraph extraction,
path search with confidence propagation, and evidence tracing backed authoritatively by Neo4j Aura.
"""
from typing import Dict, Any, List, Optional
from .neo4j_repository import neo4j_repository, Neo4jRepository
from .ontology import TolkappiyamOntology


class KnowledgeGraphQueryEngine:
    """Provides targeted traversal, relationship querying, and subgraph extraction for research queries."""

    def __init__(self, builder=None, repository: Optional[Neo4jRepository] = None):
        if isinstance(builder, Neo4jRepository) or (builder is not None and hasattr(builder, "is_available")):
            self.repo = builder
            self.builder = None
        else:
            self.builder = builder
            self.repo = repository or neo4j_repository

        if self.builder is None:
            try:
                from .graph_builder import kg_instance
                self.builder = kg_instance
            except Exception:
                self.builder = None

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single entity with its hierarchy level, logical layer,
        attributes, and direct neighbors directly from Neo4j Aura.
        """
        if self.repo and self.repo.is_available():
            return self.repo.get_entity_detail(entity_id)
        if self.builder and hasattr(self.builder, "store"):
            node = self.builder.store.get_node(entity_id)
            if not node:
                return None
            node_dict = node.to_dict()
            node_dict["neighbors"] = self.builder.store.get_neighbors(entity_id, direction="both")
            node_dict["evidence"] = self.builder.store.get_source_evidence(entity_id)
            return node_dict
        return None

    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Finds immediate incoming, outgoing, or bidirectional neighbors of an entity."""
        detail = self.get_entity(entity_id)
        if not detail:
            return []
        neighbors = detail.get("neighbors", [])
        if direction != "both":
            neighbors = [n for n in neighbors if n.get("direction") == direction]
        if relation:
            neighbors = [n for n in neighbors if n.get("relation") == relation]
        return neighbors

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Finds all paths between two entities with propagated path confidence via Neo4j Aura.
        """
        if self.repo and self.repo.is_available():
            return self.repo.find_paths(source_id=source_id, target_id=target_id, max_depth=max_depth)
        if self.builder and hasattr(self.builder, "store"):
            return self.builder.store.find_paths(source_id, target_id, max_depth=max_depth)
        return []

    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
        rel_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts a focused multi-hop subgraph around seed node(s) with layer and hierarchy filtering from Neo4j Aura.
        """
        if self.repo and self.repo.is_available():
            return self.repo.expand_subgraph(
                node_ids=node_ids,
                hops=hops,
                layer_filter=layer_filter,
                hierarchy_filter=hierarchy_filter,
                rel_types=rel_types,
            )
        if self.builder and hasattr(self.builder, "store"):
            subgraph = self.builder.store.expand_subgraph(
                node_ids=node_ids,
                hops=hops,
                layer_filter=layer_filter,
                hierarchy_filter=hierarchy_filter,
            )
            subgraph["categories"] = TolkappiyamOntology.get_category_config()
            subgraph["hierarchy_levels"] = TolkappiyamOntology.get_hierarchy_config()
            subgraph["logical_layers"] = TolkappiyamOntology.get_layer_config()
            return subgraph
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    def get_source_evidence(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Traces hierarchy ancestors up to Verse (L3), Section (L2), Work (L1), Literature (L0).
        Returns list of source evidence cards with citation and text.
        """
        detail = self.get_entity(node_id)
        if detail:
            return detail.get("evidence", [])
        return []

    # -----------------------------------------------------------------------
    # Backward Compatibility Methods
    # -----------------------------------------------------------------------

    def query_subgraph(
        self,
        focus_entity_id: Optional[str] = None,
        max_hops: int = 3,
        category_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible query_subgraph method."""
        center = focus_entity_id or "mutalporul"
        subgraph = self.expand_subgraph(
            node_ids=[center],
            hops=max_hops,
        )
        subgraph["center_node"] = center
        subgraph["max_hops"] = max_hops

        if category_filter and category_filter != "All":
            subgraph["nodes"] = [
                n for n in subgraph.get("nodes", [])
                if n.get("category") == category_filter or n.get("id") == center
            ]
            valid_ids = {n["id"] for n in subgraph["nodes"]}
            subgraph["edges"] = [
                e for e in subgraph.get("edges", [])
                if e.get("source") in valid_ids and e.get("target") in valid_ids
            ]
            subgraph["total_nodes"] = len(subgraph["nodes"])
            subgraph["total_edges"] = len(subgraph["edges"])

        return subgraph

    def get_entity_neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        """Backward-compatible get_entity_neighbors method."""
        return self.get_neighbors(entity_id, direction="both")

