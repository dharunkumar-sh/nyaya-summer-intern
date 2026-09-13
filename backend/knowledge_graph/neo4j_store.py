"""
Neo4j Graph Store repository implementing the GraphStore interface.

Translates node/edge operations, multi-hop path search, k-hop subgraph expansion,
and provenance evidence tracing into Cypher queries executed on Neo4j Aura.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from services.neo4j_service import neo4j_service, Neo4jService
from core.logger import logger
from .store import (
    GraphStore,
    KGNode,
    KGEdge,
    HierarchyLevel,
    LogicalLayer,
)
from .schema import NodeLabels, RelTypes
from .neo4j_repository import Neo4jRepository, neo4j_repository


class Neo4jGraphStore(GraphStore):
    """
    Neo4j Aura implementation of the GraphStore abstract interface.
    """

    def __init__(
        self,
        service: Optional[Neo4jService] = None,
        repository: Optional[Neo4jRepository] = None,
    ):
        self.service = service or neo4j_service
        self.repo = repository or Neo4jRepository(service=self.service)

    def is_available(self) -> bool:
        """Checks whether the Neo4j Aura driver is initialized and connected."""
        driver = self.service.get_driver()
        return driver is not None

    def add_node(self, node: KGNode) -> None:
        """Upserts a node into Neo4j with primary and category labels."""
        if not self.is_available():
            logger.warning(f"Neo4j unavailable. Skipped node add '{node.id}'")
            return

        # Canonical domain label with sanitized fallback
        type_label = (
            NodeLabels.from_string(node.type)
            or "".join(c for c in node.type if c.isalnum())
            or "Entity"
        )
        hier_label = node.hierarchy_level

        query = f"""
        MERGE (n:KGNode {{id: $id}})
        SET n:{type_label},
            n:{hier_label},
            n.label = $label,
            n.type = $type,
            n.hierarchy_level = $hierarchy_level,
            n.source = $source,
            n.confidence = $confidence,
            n.metadata_json = $metadata_json
        """
        params = {
            "id": node.id,
            "label": node.label,
            "type": node.type,
            "hierarchy_level": node.hierarchy_level,
            "source": node.source,
            "confidence": float(node.confidence),
            "metadata_json": json.dumps(node.metadata, ensure_ascii=False),
        }
        self.service.execute_write(query, params)

    def add_edge(self, edge: KGEdge) -> None:
        """Creates a relationship between two nodes in Neo4j."""
        if not self.is_available():
            logger.warning(f"Neo4j unavailable. Skipped edge add '{edge.id}'")
            return

        # Ensure relationship type is a canonical Cypher identifier
        rel_type = RelTypes.canonicalize(edge.relation)

        query = f"""
        MERGE (s:KGNode {{id: $source}})
        MERGE (t:KGNode {{id: $target}})
        MERGE (s)-[r:{rel_type} {{id: $edge_id}}]->(t)
        SET r.relation = $relation,
            r.source_id = $source_id,
            r.confidence = $confidence,
            r.validation_level = $validation_level,
            r.metadata_json = $metadata_json
        """
        params = {
            "source": edge.source,
            "target": edge.target,
            "edge_id": edge.id,
            "relation": edge.relation,
            "source_id": edge.source_id,
            "confidence": float(edge.confidence),
            "validation_level": edge.validation_level,
            "metadata_json": json.dumps(edge.metadata, ensure_ascii=False),
        }
        self.service.execute_write(query, params)

    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Retrieves a single node by identifier from Neo4j."""
        if not self.is_available():
            return None

        query = "MATCH (n:KGNode {id: $id}) RETURN n"
        records = self.service.execute_read(query, {"id": node_id})
        if not records:
            return None

        data = records[0]["n"]
        metadata = {}
        if "metadata_json" in data and data["metadata_json"]:
            try:
                metadata = json.loads(data["metadata_json"])
            except Exception:
                metadata = {}

        return KGNode(
            id=data.get("id", node_id),
            label=data.get("label", node_id),
            type=data.get("type", "Entity"),
            hierarchy_level=data.get("hierarchy_level", "L5"),
            source=data.get("source", ""),
            confidence=float(data.get("confidence", 1.0)),
            metadata=metadata,
        )

    def has_node(self, node_id: str) -> bool:
        """Checks if a node exists in Neo4j."""
        if not self.is_available():
            return False

        query = "MATCH (n:KGNode {id: $id}) RETURN count(n) AS cnt"
        records = self.service.execute_read(query, {"id": node_id})
        return bool(records and records[0].get("cnt", 0) > 0)

    def get_all_nodes(self) -> List[KGNode]:
        """Returns all KGNode records in Neo4j."""
        if not self.is_available():
            return []

        query = "MATCH (n:KGNode) RETURN n LIMIT 1000"
        records = self.service.execute_read(query)
        nodes: List[KGNode] = []

        for rec in records:
            data = rec["n"]
            metadata = {}
            if "metadata_json" in data and data["metadata_json"]:
                try:
                    metadata = json.loads(data["metadata_json"])
                except Exception:
                    pass
            nodes.append(
                KGNode(
                    id=data.get("id", ""),
                    label=data.get("label", ""),
                    type=data.get("type", "Entity"),
                    hierarchy_level=data.get("hierarchy_level", "L5"),
                    source=data.get("source", ""),
                    confidence=float(data.get("confidence", 1.0)),
                    metadata=metadata,
                )
            )
        return nodes

    def get_all_edges(self) -> List[KGEdge]:
        """Returns all relationships in Neo4j."""
        if not self.is_available():
            return []

        query = "MATCH (s:KGNode)-[r]->(t:KGNode) RETURN s.id AS source, t.id AS target, r LIMIT 2000"
        records = self.service.execute_read(query)
        edges: List[KGEdge] = []

        for rec in records:
            source = rec["source"]
            target = rec["target"]
            rel_data = rec["r"]
            metadata = {}
            if "metadata_json" in rel_data and rel_data["metadata_json"]:
                try:
                    metadata = json.loads(rel_data["metadata_json"])
                except Exception:
                    pass

            edges.append(
                KGEdge(
                    id=rel_data.get("id"),
                    source=source,
                    relation=rel_data.get("relation", "RELATED_TO"),
                    target=target,
                    source_id=rel_data.get("source_id", "neo4j"),
                    confidence=float(rel_data.get("confidence", 1.0)),
                    validation_level=rel_data.get("validation_level", "corpus_validated"),
                    metadata=metadata,
                )
            )
        return edges

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves direct neighbors with relationship details via Cypher."""
        if not self.is_available():
            return []

        if direction == "out":
            pattern = "(n:KGNode {id: $id})-[r]->(m:KGNode)"
            dir_label = "outgoing"
        elif direction == "in":
            pattern = "(n:KGNode {id: $id})<-[r]-(m:KGNode)"
            dir_label = "incoming"
        else:
            pattern = "(n:KGNode {id: $id})-[r]-(m:KGNode)"
            dir_label = "bidirectional"

        query = f"""
        MATCH {pattern}
        RETURN m.id AS neighbor_id,
               m.label AS neighbor_label,
               m.type AS neighbor_type,
               m.hierarchy_level AS neighbor_hierarchy,
               r.relation AS relation,
               r.id AS edge_id,
               r.confidence AS confidence,
               r.validation_level AS validation_level
        LIMIT 100
        """
        records = self.service.execute_read(query, {"id": node_id})
        neighbors: List[Dict[str, Any]] = []

        for r in records:
            if relation and r.get("relation") != relation:
                continue
            neighbors.append({
                "direction": dir_label,
                "edge_id": r.get("edge_id"),
                "relation": r.get("relation", "RELATED_TO"),
                "neighbor_id": r.get("neighbor_id"),
                "neighbor_label": r.get("neighbor_label"),
                "neighbor_type": r.get("neighbor_type"),
                "neighbor_hierarchy": r.get("neighbor_hierarchy"),
                "confidence": float(r.get("confidence", 1.0)),
                "validation_level": r.get("validation_level", "unverified"),
            })

        return neighbors

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """Executes variable-length path query up to max_depth in Neo4j."""
        if not self.is_available():
            return []

        depth = min(max(max_depth, 1), 5)
        query = f"""
        MATCH p = (s:KGNode {{id: $source}})-[*1..{depth}]-(t:KGNode {{id: $target}})
        RETURN [n in nodes(p) | {{id: n.id, label: n.label, type: n.type, hierarchy_level: n.hierarchy_level}}] AS nodes,
               [r in relationships(p) | {{relation: r.relation, confidence: r.confidence}}] AS edges,
               length(p) AS length
        LIMIT 25
        """
        records = self.service.execute_read(query, {"source": source_id, "target": target_id})
        paths: List[Dict[str, Any]] = []

        for rec in records:
            edges = rec.get("edges", [])
            path_conf = 1.0
            for e in edges:
                path_conf *= float(e.get("confidence", 1.0))

            paths.append({
                "source": source_id,
                "target": target_id,
                "length": rec.get("length", len(edges)),
                "propagated_confidence": round(path_conf, 4),
                "nodes": rec.get("nodes", []),
                "edges": edges,
            })

        paths.sort(key=lambda p: (-p["propagated_confidence"], p["length"]))
        return paths

    def expand_subgraph(
        self,
        node_ids: List[str],
        hops: int = 1,
        layer_filter: Optional[str] = None,
        hierarchy_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extracts k-hop neighborhood around seed nodes using Cypher pattern matching."""
        if not self.is_available() or not node_ids:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        h = min(max(hops, 1), 4)
        query = f"""
        MATCH (s:KGNode) WHERE s.id IN $seeds
        CALL apoc.path.subgraphAll(s, {{maxLevel: {h}}})
        YIELD nodes, relationships
        RETURN [n in nodes | n {{.*}}] AS nodes,
               [r in relationships | r {{.*, source: startNode(r).id, target: endNode(r).id}}] AS edges
        """
        # Fallback query if APOC is not enabled in Aura
        simple_query = f"""
        MATCH p = (s:KGNode)-[*0..{h}]-(m:KGNode)
        WHERE s.id IN $seeds
        WITH collect(distinct m) AS all_nodes
        UNWIND all_nodes AS n
        OPTIONAL MATCH (n)-[r]->(t) WHERE t IN all_nodes
        RETURN collect(distinct n {{.*}}) AS nodes,
               collect(distinct r {{.*, source: n.id, target: t.id}}) AS edges
        """
        try:
            records = self.service.execute_read(simple_query, {"seeds": node_ids})
        except Exception as e:
            logger.warning(f"Neo4j subgraph expansion query failed: {e}")
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        if not records:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        raw_nodes = records[0].get("nodes", [])
        raw_edges = [e for e in records[0].get("edges", []) if e is not None and "source" in e]

        # Deserialization of metadata_json
        cleaned_nodes = []
        for n in raw_nodes:
            if "metadata_json" in n and n["metadata_json"]:
                try:
                    n["metadata"] = json.loads(n["metadata_json"])
                except Exception:
                    n["metadata"] = {}
            cleaned_nodes.append(n)

        return {
            "center_nodes": node_ids,
            "hops": hops,
            "nodes": cleaned_nodes,
            "edges": raw_edges,
            "total_nodes": len(cleaned_nodes),
            "total_edges": len(raw_edges),
        }

    def merge_nodes(self, canonical_id: str, alias_ids: List[str]) -> KGNode:
        """Merges duplicate entities into canonical node via Cypher."""
        if not self.is_available():
            raise RuntimeError("Neo4j unavailable for entity merging")

        canonical = self.get_node(canonical_id)
        if not canonical:
            raise ValueError(f"Canonical node '{canonical_id}' not found in Neo4j")

        for alias_id in alias_ids:
            if alias_id == canonical_id:
                continue
            query = """
            MATCH (a:KGNode {id: $alias_id})
            MATCH (c:KGNode {id: $canonical_id})
            OPTIONAL MATCH (a)-[out_r]->(target)
            WHERE target <> c
            MERGE (c)-[new_out:RELATED_TO]->(target)
            SET new_out += properties(out_r)
            WITH a, c
            OPTIONAL MATCH (source)-[in_r]->(a)
            WHERE source <> c
            MERGE (source)-[new_in:RELATED_TO]->(c)
            SET new_in += properties(in_r)
            DETACH DELETE a
            """
            self.service.execute_write(query, {"alias_id": alias_id, "canonical_id": canonical_id})

        return canonical

    def get_source_evidence(self, node_id: str) -> List[Dict[str, Any]]:
        """Traces hierarchy ancestors up to Verse (L3), Section (L2), Work (L1) via Cypher."""
        if not self.is_available():
            return []

        query = """
        MATCH p = (ancestor:KGNode)-[*1..4]->(n:KGNode {id: $id})
        WHERE ancestor.hierarchy_level IN ['L3', 'L2', 'L1', 'L0']
        RETURN distinct ancestor.id AS evidence_node_id,
                        ancestor.hierarchy_level AS hierarchy_level,
                        ancestor.label AS label,
                        ancestor.type AS type,
                        ancestor.source AS source,
                        ancestor.metadata_json AS metadata_json
        """
        records = self.service.execute_read(query, {"id": node_id})
        evidence_list = []

        for rec in records:
            metadata = {}
            if "metadata_json" in rec and rec["metadata_json"]:
                try:
                    metadata = json.loads(rec["metadata_json"])
                except Exception:
                    pass
            evidence_list.append({
                "evidence_node_id": rec.get("evidence_node_id"),
                "hierarchy_level": rec.get("hierarchy_level"),
                "label": rec.get("label"),
                "type": rec.get("type"),
                "source": rec.get("source"),
                "citation": metadata.get("citation", rec.get("source")),
                "original_text": metadata.get("original_text", ""),
                "translation": metadata.get("translation", ""),
            })

        return evidence_list

    def node_count(self) -> int:
        if not self.is_available():
            return 0
        records = self.service.execute_read("MATCH (n:KGNode) RETURN count(n) AS cnt")
        return records[0].get("cnt", 0) if records else 0

    def edge_count(self) -> int:
        if not self.is_available():
            return 0
        records = self.service.execute_read("MATCH ()-[r]->() RETURN count(r) AS cnt")
        return records[0].get("cnt", 0) if records else 0

    def clear(self) -> None:
        """Deletes all nodes and relationships in the Neo4j database."""
        if not self.is_available():
            return
        self.service.execute_write("MATCH (n) DETACH DELETE n")
        logger.info("Cleared Neo4j graph database.")

    def sync_from_store(self, source_store: GraphStore) -> Dict[str, int]:
        """
        Synchronizes all nodes and edges from an in-memory GraphStore into Neo4j Aura.
        """
        nodes = source_store.get_all_nodes()
        edges = source_store.get_all_edges()

        synced_nodes = 0
        for node in nodes:
            self.add_node(node)
            synced_nodes += 1

        synced_edges = 0
        for edge in edges:
            self.add_edge(edge)
            synced_edges += 1

        logger.info(f"Synchronized {synced_nodes} nodes and {synced_edges} edges into Neo4j Aura.")
        return {"synced_nodes": synced_nodes, "synced_edges": synced_edges}
