"""
Knowledge Graph query engine supporting hierarchical traversal, k-hop subgraph extraction,
path search with confidence propagation, and evidence tracing.
"""
from typing import Dict, Any, List, Optional
from .graph_builder import kg_instance
from .ontology import TolkappiyamOntology


class KnowledgeGraphQueryEngine:
    """Provides targeted traversal, relationship querying, and subgraph extraction for research queries."""

    def __init__(self, graph_builder=None):
        self.builder = graph_builder or kg_instance

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single entity with its hierarchy level, logical layer,
        attributes, and direct neighbors.
        """
        node = self.builder.store.get_node(entity_id)
        if not node:
            return None

        node_dict = node.to_dict()
        neighbors = self.builder.store.get_neighbors(entity_id, direction="both")
        evidence = self.builder.store.get_source_evidence(entity_id)

        node_dict["neighbors"] = neighbors
        node_dict["evidence"] = evidence
        return node_dict

    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Finds immediate incoming, outgoing, or bidirectional neighbors of an entity."""
        return self.builder.store.get_neighbors(entity_id, direction=direction, relation=relation)

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Finds all paths between two entities with propagated path confidence.
        Confidence propagation: product of edge confidences along the path.
        """
        return self.builder.store.find_paths(source_id, target_id, max_depth=max_depth)

    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts a focused multi-hop subgraph around seed node(s) with layer and hierarchy filtering.
        """
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

    def get_source_evidence(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Traces hierarchy ancestors up to Verse (L3), Section (L2), Work (L1), Literature (L0).
        Returns list of source evidence cards with citation and text.
        """
        return self.builder.store.get_source_evidence(node_id)

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
        if not self.builder.store.has_node(center):
            center = "mutalporul"

        subgraph = self.expand_subgraph(
            node_ids=[center],
            hops=max_hops,
        )
        subgraph["center_node"] = center
        subgraph["max_hops"] = max_hops

        if category_filter and category_filter != "All":
            subgraph["nodes"] = [
                n for n in subgraph["nodes"]
                if n.get("category") == category_filter or n.get("id") == center
            ]
            valid_ids = {n["id"] for n in subgraph["nodes"]}
            subgraph["edges"] = [
                e for e in subgraph["edges"]
                if e["source"] in valid_ids and e["target"] in valid_ids
            ]
            subgraph["total_nodes"] = len(subgraph["nodes"])
            subgraph["total_edges"] = len(subgraph["edges"])

        return subgraph

    def get_entity_neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        """Backward-compatible get_entity_neighbors method."""
        return self.get_neighbors(entity_id, direction="both")
