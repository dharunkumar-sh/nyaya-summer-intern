"""
Graph store abstraction layer for Hierarchical Knowledge Graph.

Defines the core node/edge schemas, structural hierarchy (L0-L5),
five logical epistemic layers, and an abstract GraphStore interface.
Provides NetworkXGraphStore as the in-memory engine, designed so the
system can cleanly migrate to Neo4j without rewriting application logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from core.logger import logger


# ---------------------------------------------------------------------------
# Hierarchy & Layer Enums
# ---------------------------------------------------------------------------

class HierarchyLevel(str, Enum):
    """6-level structural hierarchy for classical Tamil literary knowledge."""
    L0 = "L0"  # Literature (e.g. Classical Tamil Literature)
    L1 = "L1"  # Work (e.g. Tolkāppiyam)
    L2 = "L2"  # Section (e.g. Poruḷatikāram, Akattiṇaiyiyal)
    L3 = "L3"  # Verse / Passage (e.g. Sūtra)
    L4 = "L4"  # Concept (e.g. Mutalporuḷ, Karupporuḷ, Uripporuḷ)
    L5 = "L5"  # Entity / Event (e.g. Cēyōṉ, Kuṟiñci, Puṇartal)

    @classmethod
    def rank(cls, level: str) -> int:
        """Returns numeric rank 0-5 for hierarchy level comparison."""
        mapping = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
        return mapping.get(level.upper(), 5)


class LogicalLayer(str, Enum):
    """5 logical epistemic layers."""
    SOURCE    = "Source Layer"     # Literature, Work, Section, Verse provenance
    ENTITY    = "Entity Layer"     # Deities, landscapes, flora, fauna, instruments
    CONCEPT   = "Concept Layer"    # Epistemic categories, Tiṇai poetics, aesthetics
    EVENT     = "Event Layer"      # Poetic motifs, emotional dynamics, situations
    REASONING = "Reasoning Layer"  # Nyāya syllogistic members, Hetvābhāsa constraints


# ---------------------------------------------------------------------------
# Core Node & Edge Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class KGNode:
    """
    Knowledge Graph Node Schema.
    Must contain: id, label, type, hierarchy_level, source, confidence, metadata.
    """
    id: str
    label: str
    type: str                                    # e.g., "Literature", "Work", "Section", "Verse", "Concept", "Entity", "Event"
    hierarchy_level: str                         # "L0", "L1", "L2", "L3", "L4", "L5"
    source: str                                  # Primary citation, sūtra ID, or treatise
    confidence: float = 1.0                      # Calibrated trust score (0.0 - 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable node dict."""
        data = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "hierarchy_level": self.hierarchy_level,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }
        # Flatten common metadata for easy visualization access
        if "layer" in self.metadata:
            data["layer"] = self.metadata["layer"]
        if "transliteration" in self.metadata:
            data["transliteration"] = self.metadata["transliteration"]
        if "category" in self.metadata:
            data["category"] = self.metadata["category"]
        if "x" in self.metadata and "y" in self.metadata:
            data["x"] = self.metadata["x"]
            data["y"] = self.metadata["y"]
            data["radius"] = self.metadata.get("radius", 30)
        return data


@dataclass
class KGEdge:
    """
    Knowledge Graph Edge Schema.
    Must contain: source, relation, target, source_id, confidence, validation_level.
    """
    source: str
    relation: str
    target: str
    source_id: str                               # Provenance reference
    confidence: float = 1.0                      # Calibrated trust score (0.0 - 1.0)
    validation_level: str = "corpus_validated"   # "corpus_validated", "unverified", "manually_verified"
    id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"e_{self.source}_{self.relation}_{self.target}"

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable edge dict."""
        data = {
            "id": self.id,
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "source_id": self.source_id,
            "confidence": round(self.confidence, 4),
            "validation_level": self.validation_level,
            "metadata": self.metadata,
        }
        # Include readable label and cytoscape compatibility type
        data["type"] = self.relation
        if "label" in self.metadata:
            data["label"] = self.metadata["label"]
        else:
            data["label"] = self.relation
        if "predicate" in self.metadata:
            data["predicate"] = self.metadata["predicate"]
        return data


# ---------------------------------------------------------------------------
# Abstract Graph Store Interface (Neo4j Ready)
# ---------------------------------------------------------------------------

class GraphStore(ABC):
    """
    Abstract Graph Storage Interface.
    Enables plug-and-play backend swapping between NetworkX and Neo4j.
    """

    @abstractmethod
    def add_node(self, node: KGNode) -> None:
        """Adds or updates a node in the graph."""
        pass

    @abstractmethod
    def add_edge(self, edge: KGEdge) -> None:
        """Adds a directed edge between existing nodes."""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Retrieves a single node by identifier."""
        pass

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """Checks if a node exists."""
        pass

    @abstractmethod
    def get_all_nodes(self) -> List[KGNode]:
        """Returns all nodes in the store."""
        pass

    @abstractmethod
    def get_all_edges(self) -> List[KGEdge]:
        """Returns all edges in the store."""
        pass

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves direct neighbors with edge details."""
        pass

    @abstractmethod
    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """Finds multi-hop paths with propagated confidence."""
        pass

    @abstractmethod
    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extracts k-hop neighborhood around node(s) with filtering."""
        pass

    @abstractmethod
    def merge_nodes(self, canonical_id: str, alias_ids: List[str]) -> KGNode:
        """Merges duplicate entities into canonical entity and re-wires edges."""
        pass

    @abstractmethod
    def get_source_evidence(self, node_id: str) -> List[Dict[str, Any]]:
        """Traces hierarchy ancestors up to Verse/Section/Work evidence."""
        pass

    @abstractmethod
    def node_count(self) -> int:
        """Returns total node count."""
        pass

    @abstractmethod
    def edge_count(self) -> int:
        """Returns total edge count."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears all nodes and edges."""
        pass


# ---------------------------------------------------------------------------
# Concrete NetworkX Implementation
# ---------------------------------------------------------------------------

class NetworkXGraphStore(GraphStore):
    """
    In-memory GraphStore implementation using NetworkX MultiDiGraph.
    Provides fast graph traversal and NetworkX algorithmic compatibility.
    """

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self._nodes_dict: Dict[str, KGNode] = {}
        self._edges_list: List[KGEdge] = []

    def add_node(self, node: KGNode) -> None:
        self._nodes_dict[node.id] = node
        self.graph.add_node(
            node.id,
            label=node.label,
            type=node.type,
            hierarchy_level=node.hierarchy_level,
            source=node.source,
            confidence=node.confidence,
            metadata=node.metadata,
            **node.metadata,
        )

    def add_edge(self, edge: KGEdge) -> None:
        # Canonicalize aliases
        if edge.source == "uripporul" and "uriporul" in self._nodes_dict:
            edge.source = "uriporul"
        elif edge.source == "uriporul" and "uripporul" in self._nodes_dict:
            edge.source = "uripporul"

        if edge.target == "uripporul" and "uriporul" in self._nodes_dict:
            edge.target = "uriporul"
        elif edge.target == "uriporul" and "uripporul" in self._nodes_dict:
            edge.target = "uripporul"

        # Ensure endpoints exist
        if not self.has_node(edge.source):
            logger.warning(f"Creating missing placeholder source node '{edge.source}'")
            self.add_node(
                KGNode(
                    id=edge.source,
                    label=edge.source,
                    type="Entity",
                    hierarchy_level="L5",
                    source=edge.source_id,
                )
            )
        if not self.has_node(edge.target):
            logger.warning(f"Creating missing placeholder target node '{edge.target}'")
            self.add_node(
                KGNode(
                    id=edge.target,
                    label=edge.target,
                    type="Entity",
                    hierarchy_level="L5",
                    source=edge.source_id,
                )
            )

        self._edges_list.append(edge)
        self.graph.add_edge(
            edge.source,
            edge.target,
            key=edge.id,
            id=edge.id,
            relation=edge.relation,
            source_id=edge.source_id,
            confidence=edge.confidence,
            validation_level=edge.validation_level,
            metadata=edge.metadata,
            label=edge.metadata.get("label", edge.relation),
            predicate=edge.metadata.get("predicate", edge.relation),
        )

    def get_node(self, node_id: str) -> Optional[KGNode]:
        node = self._nodes_dict.get(node_id)
        if node is None:
            if node_id == "uripporul":
                return self._nodes_dict.get("uriporul")
            elif node_id == "uriporul":
                return self._nodes_dict.get("uripporul")
        return node

    def has_node(self, node_id: str) -> bool:
        if node_id in self._nodes_dict:
            return True
        if node_id == "uripporul" and "uriporul" in self._nodes_dict:
            return True
        if node_id == "uriporul" and "uripporul" in self._nodes_dict:
            return True
        return False

    def get_all_nodes(self) -> List[KGNode]:
        return list(self._nodes_dict.values())

    def get_all_edges(self) -> List[KGEdge]:
        return list(self._edges_list)

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.has_node(node_id):
            return []

        neighbors: List[Dict[str, Any]] = []

        # Outgoing edges
        if direction in ("out", "both"):
            for u, v, k, data in self.graph.out_edges(node_id, keys=True, data=True):
                if relation and data.get("relation") != relation:
                    continue
                target_node = self.get_node(v)
                neighbors.append({
                    "direction": "outgoing",
                    "edge_id": data.get("id", str(k)),
                    "relation": data.get("relation", "relatedTo"),
                    "neighbor_id": v,
                    "neighbor_label": target_node.label if target_node else v,
                    "neighbor_type": target_node.type if target_node else "Unknown",
                    "neighbor_hierarchy": target_node.hierarchy_level if target_node else "L5",
                    "confidence": data.get("confidence", 1.0),
                    "validation_level": data.get("validation_level", "unverified"),
                })

        # Incoming edges
        if direction in ("in", "both"):
            for u, v, k, data in self.graph.in_edges(node_id, keys=True, data=True):
                if relation and data.get("relation") != relation:
                    continue
                source_node = self.get_node(u)
                neighbors.append({
                    "direction": "incoming",
                    "edge_id": data.get("id", str(k)),
                    "relation": data.get("relation", "relatedTo"),
                    "neighbor_id": u,
                    "neighbor_label": source_node.label if source_node else u,
                    "neighbor_type": source_node.type if source_node else "Unknown",
                    "neighbor_hierarchy": source_node.hierarchy_level if source_node else "L5",
                    "confidence": data.get("confidence", 1.0),
                    "validation_level": data.get("validation_level", "unverified"),
                })

        return neighbors

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Finds all simple directed and undirected paths up to max_depth.
        Calculates propagated path confidence as the product of edge confidences.
        """
        if not self.has_node(source_id) or not self.has_node(target_id):
            return []

        # Convert to simple DiGraph to find simple paths
        simple_digraph = nx.DiGraph(self.graph)
        paths_found = []

        try:
            directed_paths = list(
                nx.all_simple_paths(simple_digraph, source=source_id, target=target_id, cutoff=max_depth)
            )
        except Exception:
            directed_paths = []

        # If directed yields nothing, explore undirected pathways
        if not directed_paths:
            simple_undirected = self.graph.to_undirected()
            try:
                undirected_paths = list(
                    nx.all_simple_paths(simple_undirected, source=source_id, target=target_id, cutoff=max_depth)
                )
            except Exception:
                undirected_paths = []
            candidate_node_paths = undirected_paths
        else:
            candidate_node_paths = directed_paths

        for node_path in candidate_node_paths:
            edge_details = []
            path_conf = 1.0

            for i in range(len(node_path) - 1):
                u = node_path[i]
                v = node_path[i + 1]

                # Fetch edge data (check u->v, then v->u)
                if self.graph.has_edge(u, v):
                    edge_dict = next(iter(self.graph.get_edge_data(u, v).values()))
                    direction = "forward"
                elif self.graph.has_edge(v, u):
                    edge_dict = next(iter(self.graph.get_edge_data(v, u).values()))
                    direction = "reverse"
                else:
                    edge_dict = {"relation": "associated_with", "confidence": 0.5}
                    direction = "undirected"

                conf = float(edge_dict.get("confidence", 1.0))
                path_conf *= conf

                edge_details.append({
                    "source": u,
                    "target": v,
                    "relation": edge_dict.get("relation", "relatedTo"),
                    "direction": direction,
                    "confidence": conf,
                })

            nodes_in_path = [
                self.get_node(nid).to_dict() if self.get_node(nid) else {"id": nid, "label": nid}
                for nid in node_path
            ]

            paths_found.append({
                "source": source_id,
                "target": target_id,
                "length": len(node_path) - 1,
                "propagated_confidence": round(path_conf, 4),
                "nodes": nodes_in_path,
                "edges": edge_details,
            })

        # Sort paths by propagated confidence (highest first), then shortest length
        paths_found.sort(key=lambda p: (-p["propagated_confidence"], p["length"]))
        return paths_found

    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
        rel_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extracts k-hop neighborhood around node(s) with layer, hierarchy, and relationship filtering."""
        valid_seeds = [nid for nid in node_ids if self.has_node(nid)]
        if not valid_seeds:
            return {
                "center_nodes": [],
                "hops": hops,
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
            }

        rel_types_set = {r.upper() for r in rel_types} if rel_types else None

        undirected_g = self.graph.to_undirected()
        subgraph_nodes: Set[str] = set(valid_seeds)
        hop_distance: Dict[str, int] = {s: 0 for s in valid_seeds}

        current_frontier = set(valid_seeds)
        for h in range(1, min(hops, 5) + 1):
            next_frontier = set()
            for n in current_frontier:
                if n in self.graph:
                    # Check both outgoing and incoming neighbors in the directed graph
                    for neighbor in set(self.graph.successors(n)).union(set(self.graph.predecessors(n))):
                        # If rel_types filter is given, verify at least one edge matches
                        if rel_types_set:
                            has_matching_edge = False
                            if self.graph.has_edge(n, neighbor):
                                for ed in self.graph.get_edge_data(n, neighbor).values():
                                    if (ed.get("relation") or ed.get("type", "")).upper() in rel_types_set:
                                        has_matching_edge = True
                                        break
                            if not has_matching_edge and self.graph.has_edge(neighbor, n):
                                for ed in self.graph.get_edge_data(neighbor, n).values():
                                    if (ed.get("relation") or ed.get("type", "")).upper() in rel_types_set:
                                        has_matching_edge = True
                                        break
                            if not has_matching_edge:
                                continue

                        if neighbor not in hop_distance:
                            hop_distance[neighbor] = h
                            next_frontier.add(neighbor)
            subgraph_nodes.update(next_frontier)
            current_frontier = next_frontier

        # Apply filters
        filtered_node_ids: Set[str] = set()
        for nid in subgraph_nodes:
            node = self.get_node(nid)
            if not node:
                continue

            # Check layer filter
            if layer_filter and layer_filter != "All":
                node_layer = node.metadata.get("layer")
                if node_layer != layer_filter:
                    if nid not in valid_seeds:
                        continue

            # Check hierarchy filter
            if hierarchy_filter and hierarchy_filter != "All":
                if node.hierarchy_level != hierarchy_filter:
                    if nid not in valid_seeds:
                        continue

            filtered_node_ids.add(nid)

        # Ensure seed nodes remain in subgraph even if isolated
        filtered_node_ids.update(valid_seeds)

        # Build edge output, ensuring endpoints exist in filtered_node_ids
        edges_out = []
        node_degrees: Dict[str, int] = {nid: 0 for nid in filtered_node_ids}
        for u, v, k, data in self.graph.edges(keys=True, data=True):
            if u in filtered_node_ids and v in filtered_node_ids:
                edge_dict = dict(data)
                rel_val = (edge_dict.get("relation") or edge_dict.get("type", "RELATED_TO")).upper()
                if rel_types_set and rel_val not in rel_types_set:
                    continue
                edge_dict["source"] = u
                edge_dict["target"] = v
                edge_dict["type"] = edge_dict.get("relation", "RELATED_TO")
                edge_dict["relation"] = edge_dict.get("relation", "RELATED_TO")
                edge_dict["id"] = edge_dict.get("id", f"e_{u}_{v}_{k}")
                edges_out.append(edge_dict)
                node_degrees[u] = node_degrees.get(u, 0) + 1
                node_degrees[v] = node_degrees.get(v, 0) + 1

        # Build node output with provenance & relevance metadata
        nodes_out = []
        for nid in filtered_node_ids:
            node_obj = self.get_node(nid)
            if not node_obj:
                continue
            nd = node_obj.to_dict()
            is_seed = nid in valid_seeds
            dist = hop_distance.get(nid, 0 if is_seed else 1)
            deg = node_degrees.get(nid, 0)
            nd["is_seed"] = is_seed
            nd["hop_distance"] = dist
            nd["degree"] = deg
            nd["is_isolated"] = deg == 0
            nd["relevance_reason"] = (
                "Direct Seed Node from Query / Hybrid Retrieval"
                if is_seed
                else f"Multi-hop Graph Context (Hop Distance: {dist})"
            )
            nd["relevance_score"] = round(1.0 / (1.0 + dist), 4)
            nodes_out.append(nd)

        return {
            "center_nodes": valid_seeds,
            "hops": hops,
            "nodes": nodes_out,
            "edges": edges_out,
            "relationships": edges_out,
            "total_nodes": len(nodes_out),
            "total_edges": len(edges_out),
            "isolated_nodes_count": len([n for n in nodes_out if n.get("is_isolated")]),
        }

    def merge_nodes(self, canonical_id: str, alias_ids: List[str]) -> KGNode:
        """
        Merges duplicate entities into canonical entity and re-wires edges.
        Combines confidence: c_merged = 1 - (1 - c1)(1 - c2).
        """
        canonical = self.get_node(canonical_id)
        if not canonical:
            raise ValueError(f"Canonical node '{canonical_id}' does not exist")

        for alias_id in alias_ids:
            if alias_id == canonical_id or not self.has_node(alias_id):
                continue
            alias = self.get_node(alias_id)
            if not alias:
                continue

            # Bayesian confidence combination
            combined_conf = 1.0 - (1.0 - canonical.confidence) * (1.0 - alias.confidence)
            canonical.confidence = min(1.0, combined_conf)

            # Merge metadata
            aliases = canonical.metadata.setdefault("aliases", [])
            if alias.label not in aliases:
                aliases.append(alias.label)
            if alias_id not in aliases:
                aliases.append(alias_id)

            # Re-wire outgoing edges
            for u, v, k, data in list(self.graph.out_edges(alias_id, keys=True, data=True)):
                if v != canonical_id:
                    self.add_edge(
                        KGEdge(
                            source=canonical_id,
                            relation=data.get("relation", "relatedTo"),
                            target=v,
                            source_id=data.get("source_id", "merge"),
                            confidence=data.get("confidence", 1.0),
                            validation_level=data.get("validation_level", "unverified"),
                            metadata=dict(data.get("metadata", {})),
                        )
                    )

            # Re-wire incoming edges
            for u, v, k, data in list(self.graph.in_edges(alias_id, keys=True, data=True)):
                if u != canonical_id:
                    self.add_edge(
                        KGEdge(
                            source=u,
                            relation=data.get("relation", "relatedTo"),
                            target=canonical_id,
                            source_id=data.get("source_id", "merge"),
                            confidence=data.get("confidence", 1.0),
                            validation_level=data.get("validation_level", "unverified"),
                            metadata=dict(data.get("metadata", {})),
                        )
                    )

            # Remove alias node from store & graph
            self.graph.remove_node(alias_id)
            self._nodes_dict.pop(alias_id, None)

        return canonical

    def get_source_evidence(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Traces hierarchy ancestors up to Verse (L3), Section (L2), Work (L1), Literature (L0).
        Returns list of source evidence cards with citation and text.
        """
        if not self.has_node(node_id):
            return []

        evidence_list: List[Dict[str, Any]] = []
        visited: Set[str] = set()

        # Perform BFS traversal along incoming hierarchy edges ("contains", "grounds", etc.)
        queue = [node_id]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            curr_node = self.get_node(curr)
            if not curr_node:
                continue

            # If node is L3 (Verse), L2 (Section), or L1 (Work), capture evidence
            if curr_node.hierarchy_level in ("L3", "L2", "L1", "L0"):
                evidence_list.append({
                    "evidence_node_id": curr_node.id,
                    "hierarchy_level": curr_node.hierarchy_level,
                    "label": curr_node.label,
                    "type": curr_node.type,
                    "source": curr_node.source,
                    "citation": curr_node.metadata.get("citation", curr_node.source),
                    "original_text": curr_node.metadata.get("original_text", ""),
                    "translation": curr_node.metadata.get("translation", ""),
                })

            # Follow incoming structural or grounds edges
            for u, v, data in self.graph.in_edges(curr, data=True):
                if u not in visited:
                    queue.append(u)

        return evidence_list

    def node_count(self) -> int:
        return len(self._nodes_dict)

    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def clear(self) -> None:
        self.graph.clear()
        self._nodes_dict.clear()
        self._edges_list.clear()


def get_graph_store(backend: Optional[str] = None) -> GraphStore:
    """
    Factory function instantiating either NetworkXGraphStore or Neo4jGraphStore
    based on configuration or explicit parameter.
    """
    import os
    selected_backend = (backend or os.getenv("GRAPH_STORE_BACKEND", "networkx")).lower()

    if selected_backend == "neo4j":
        try:
            from .neo4j_store import Neo4jGraphStore
            return Neo4jGraphStore()
        except Exception as e:
            logger.warning(f"Failed to load Neo4jGraphStore: {e}. Falling back to NetworkXGraphStore.")
            return NetworkXGraphStore()

    return NetworkXGraphStore()
