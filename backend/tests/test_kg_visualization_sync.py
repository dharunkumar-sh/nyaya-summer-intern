"""
Unit and Integration Tests for Knowledge Graph Visualization & Data Synchronization.

Verifies end-to-end data flow from backend knowledge graph stores, Cypher queries,
and Flask API routes to ensure:
1. Stable, globally unique identifiers for all nodes and edges.
2. Complete absence of orphan edges (all edge sources and targets exist in returned nodes).
3. Payload atomicity: nodes, edges, relationships, total_nodes, and total_edges are synchronized.
4. Backward compatibility: edges and relationships arrays match identically.
5. Cytoscape compatibility: edge objects contain both 'type' and 'relation'.
6. Alias resolution between canonical identifiers (e.g. uriporul / uripporul).
"""

import pytest
from unittest.mock import MagicMock, patch
from knowledge_graph.graph_builder import kg_instance, KnowledgeGraphBuilder
from knowledge_graph.store import KGNode, KGEdge
from knowledge_graph.neo4j_repository import Neo4jRepository


class TestKGVisualizationDataSync:
    """Tests for data synchronization, schema invariants, and endpoint integrity."""

    def test_in_memory_full_graph_data_invariants(self):
        """Verify that get_full_graph_data returns synchronized nodes, edges, and relationships."""
        data = kg_instance.get_full_graph_data()

        assert "nodes" in data
        assert "edges" in data
        assert "relationships" in data
        assert "total_nodes" in data
        assert "total_edges" in data

        nodes = data["nodes"]
        edges = data["edges"]
        relationships = data["relationships"]

        # 1. Total counts must strictly match array lengths
        assert data["total_nodes"] == len(nodes)
        assert data["total_edges"] == len(edges)
        assert len(edges) == len(relationships)

        # 2. Node IDs must be unique
        node_ids = [n["id"] for n in nodes]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected in full graph data"

        # 3. Edge IDs must be unique
        edge_ids = [e["id"] for e in edges]
        assert len(edge_ids) == len(set(edge_ids)), "Duplicate edge IDs detected in full graph data"

        # 4. Zero orphan edges: every edge source and target must exist in returned nodes
        node_id_set = set(node_ids)
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            assert src in node_id_set, f"Orphan edge {e['id']} has invalid source '{src}'"
            assert tgt in node_id_set, f"Orphan edge {e['id']} has invalid target '{tgt}'"

        # 5. Cytoscape compatibility: both 'type' and 'relation' must be present
        for e in edges:
            assert "type" in e, f"Edge {e['id']} missing 'type' key required by Cytoscape"
            assert "relation" in e, f"Edge {e['id']} missing 'relation' key"
            assert e["type"] == e["relation"]

    def test_edge_alias_normalization(self):
        """Verify that alias nodes such as uripporul -> uriporul are resolved cleanly."""
        builder = KnowledgeGraphBuilder()
        initial_edges_count = len(builder.store.get_all_edges())

        # Add edge targeting the alias 'uripporul'
        builder.store.add_edge(
            KGEdge(
                source="ceyon",
                relation="AESTHETIC_GROUND",
                target="uripporul",
                source_id="test",
                confidence=0.95,
            )
        )

        data = builder.get_full_graph_data()
        assert len(data["edges"]) == initial_edges_count + 1

        # Locate the newly added edge
        added_edge = [e for e in data["edges"] if e["relation"] == "AESTHETIC_GROUND"][0]
        assert added_edge["source"] == "ceyon"
        assert added_edge["target"] == "uriporul"  # normalized to canonical ID
        assert added_edge["type"] == "AESTHETIC_GROUND"
        assert added_edge["relation"] == "AESTHETIC_GROUND"

    def test_neo4j_repository_get_graph_elements_deduplication(self):
        """Verify that neo4j_repository disambiguates edge IDs and discards orphan edges."""
        mock_service = MagicMock()
        mock_service.is_connected.return_value = True
        mock_service.database = "neo4j"

        # Mock Neo4j execute_read returning duplicate relationship IDs and an orphan edge
        mock_service.execute_read.return_value = [
            {
                "nodes": [
                    {"id": "ceyon", "label": "Cēyōn", "category": "Person"},
                    {"id": "mutalporul", "label": "Mutalporuḷ", "category": "Concept"},
                    {"id": "ceyon", "label": "Cēyōn Duplicate", "category": "Person"},  # duplicate node
                ],
                "relationships": [
                    # Two edges with same ID / same endpoints
                    {"id": "e_dup", "source": "ceyon", "target": "mutalporul", "type": "PRESIDES_OVER"},
                    {"id": "e_dup", "source": "ceyon", "target": "mutalporul", "type": "PRESIDES_OVER"},
                    # Orphan edge targeting non-existent node
                    {"id": "e_orphan", "source": "ceyon", "target": "non_existent_node", "type": "RELATES"},
                ],
            }
        ]

        repo = Neo4jRepository(service=mock_service)
        result = repo.get_graph_elements(limit=100)

        # 1. Duplicate node must be filtered out
        assert result["total_nodes"] == 2
        assert len(result["nodes"]) == 2
        node_ids = [n["id"] for n in result["nodes"]]
        assert node_ids == ["ceyon", "mutalporul"]

        # 2. Orphan edge must be discarded, duplicate edge ID must be disambiguated
        assert result["total_edges"] == 2
        assert len(result["relationships"]) == 2
        assert len(result["edges"]) == 2

        edge_ids = [r["id"] for r in result["relationships"]]
        assert len(edge_ids) == len(set(edge_ids)), f"Edge IDs were not unique: {edge_ids}"
        assert edge_ids[0] == "e_dup"
        assert edge_ids[1] != "e_dup"  # disambiguated

        # 3. Both 'type' and 'relation' keys must be present
        for r in result["relationships"]:
            assert "type" in r
            assert "relation" in r
            assert r["type"] == "PRESIDES_OVER"

    def test_flask_api_kg_graph_endpoint_atomicity(self):
        """Verify that GET /api/kg/graph returns an atomic schema matching frontend expectations."""
        from app import create_app

        app = create_app("testing")
        with app.test_client() as client:
            resp = client.get("/api/kg/graph?source=in_memory")
            assert resp.status_code == 200
            json_data = resp.get_json()

            assert json_data["success"] is True
            data = json_data["data"]

            assert "nodes" in data
            assert "edges" in data
            assert "relationships" in data
            assert "total_nodes" in data
            assert "total_edges" in data

            assert data["total_nodes"] == len(data["nodes"])
            assert data["total_edges"] == len(data["edges"])
            assert len(data["edges"]) == len(data["relationships"])

            # Verify no orphan edges in endpoint response
            node_ids = {n["id"] for n in data["nodes"]}
            for edge in data["edges"]:
                assert edge["source"] in node_ids
                assert edge["target"] in node_ids
