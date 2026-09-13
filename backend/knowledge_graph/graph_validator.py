"""
Graph validator checking connectivity, structural hierarchy (L0-L5),
logical layers, orphaned nodes, and ontological validity.
"""
from typing import Dict, Any, List
import networkx as nx
from .graph_builder import kg_instance
from .store import HierarchyLevel, LogicalLayer


class KnowledgeGraphValidator:
    """Checks sanity, structural hierarchy, and integrity of the Knowledge Graph."""

    @classmethod
    def validate(cls, builder=None) -> Dict[str, Any]:
        """Runs comprehensive validation checks on the knowledge graph."""
        b = builder or kg_instance
        g = b.graph
        store = b.store

        node_count = store.node_count()
        edge_count = store.edge_count()

        # Check for isolated (orphaned) nodes
        isolated_nodes = list(nx.isolates(g.to_undirected())) if node_count > 0 else []

        # Check density and connectivity
        undirected_g = g.to_undirected()
        density = nx.density(undirected_g) if node_count > 1 else 0.0
        is_connected = nx.is_connected(undirected_g) if node_count > 0 else False

        # Validate hierarchy levels (L0-L5)
        hierarchy_distribution: Dict[str, int] = {}
        invalid_hierarchy_nodes: List[str] = []
        valid_levels = {lvl.value for lvl in HierarchyLevel}

        # Validate logical layers
        layer_distribution: Dict[str, int] = {}
        invalid_layer_nodes: List[str] = []
        valid_layers = {layer.value for layer in LogicalLayer}

        for node in store.get_all_nodes():
            # Hierarchy check
            lvl = node.hierarchy_level
            if lvl in valid_levels:
                hierarchy_distribution[lvl] = hierarchy_distribution.get(lvl, 0) + 1
            else:
                invalid_hierarchy_nodes.append(node.id)

            # Layer check
            layer = node.metadata.get("layer")
            if layer in valid_layers:
                layer_distribution[layer] = layer_distribution.get(layer, 0) + 1
            else:
                invalid_layer_nodes.append(node.id)

        # Edge validity checks
        invalid_edges = []
        for edge in store.get_all_edges():
            if not store.has_node(edge.source) or not store.has_node(edge.target):
                invalid_edges.append(edge.to_dict())

        valid = (
            len(isolated_nodes) == 0
            and node_count > 0
            and len(invalid_hierarchy_nodes) == 0
            and len(invalid_edges) == 0
        )

        return {
            "valid": valid,
            "node_count": node_count,
            "edge_count": edge_count,
            "is_connected": is_connected,
            "density": round(density, 4),
            "isolated_nodes": isolated_nodes,
            "hierarchy_distribution": hierarchy_distribution,
            "layer_distribution": layer_distribution,
            "invalid_hierarchy_nodes": invalid_hierarchy_nodes,
            "invalid_layer_nodes": invalid_layer_nodes,
            "invalid_edges_count": len(invalid_edges),
        }
