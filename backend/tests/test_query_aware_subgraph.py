"""
Automated Test Suite for Query-Aware Knowledge Graph Retrieval.

Verifies:
1. Multi-hop traversal with configurable maximum depth (1, 2, 3 hops).
2. Controlled relationship filtering based on Tolkāppiyam Knowledge Graph schema.
3. Preservation of isolated directly relevant seed nodes.
4. Strict endpoint validation (every edge has valid source and target in the node set; zero dangling edges).
5. Epistemic relevance and literary provenance metadata attached to nodes and relationships.
6. Dynamic retrieval without any hardcoded nodes or relationships.
7. Flask REST API endpoints POST /api/kg/query-subgraph and POST /api/kg/subgraph.
"""
import pytest
from flask import Flask

from app import create_app
from knowledge_graph.graph_builder import kg_instance
from knowledge_graph.neo4j_repository import neo4j_repository
from services.graph_retrieval_service import graph_retrieval_service
from knowledge_graph.schema import RelTypes


@pytest.fixture(scope="module")
def test_app():
    """Create Flask test application."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def client(test_app):
    """Create Flask test client."""
    return test_app.test_client()


# =============================================================================
# 1. In-Memory Store & GraphRetrievalService Multi-Hop Traversal Tests
# =============================================================================

class TestQueryAwareSubgraphRetrieval:

    def test_query_subgraph_from_hybrid_seeds(self):
        """Verify dynamic subgraph retrieval seeded by hybrid retrieval identifiers."""
        hybrid_seeds = ["kurinci", "ceyon", "tol-porul-akam-003"]
        result = graph_retrieval_service.retrieve_query_subgraph(
            query_input={"seed_ids": hybrid_seeds},
            max_hops=2,
            limit=50,
        )

        assert "nodes" in result
        assert "relationships" in result
        assert result["total_nodes"] > 0
        assert len(result["nodes"]) == result["total_nodes"]

        node_ids = {n["id"] for n in result["nodes"]}
        # Verify at least one seed is matched and in returned nodes
        assert any(s in node_ids for s in hybrid_seeds)

        # Verify no dangling edges
        for edge in result["relationships"]:
            assert edge["source"] in node_ids, f"Dangling edge source: {edge['source']}"
            assert edge["target"] in node_ids, f"Dangling edge target: {edge['target']}"

    def test_isolated_seed_preservation(self):
        """Verify directly relevant seed nodes without edges in the hop horizon are preserved."""
        # Provide a known seed node plus an isolated node ID that has no connections
        isolated_seed = "isolated_concept_test_node"
        
        # Add a temporary isolated node to the store to simulate a directly matched seed with 0 edges
        from knowledge_graph.store import KGNode
        kg_instance.store.add_node(
            KGNode(
                id=isolated_seed,
                label="Isolated Concept",
                type="Concept",
                hierarchy_level="L4",
                source="test",
                metadata={"description": "Directly matched seed with no neighbors"},
            )
        )

        try:
            result = graph_retrieval_service.retrieve_query_subgraph(
                query_input={"seed_ids": [isolated_seed, "kurinci"]},
                max_hops=1,
                include_isolated=True,
            )

            node_ids = {n["id"] for n in result["nodes"]}
            assert isolated_seed in node_ids, "Isolated relevant seed node was erroneously dropped!"

            # Find the isolated node object
            isolated_node = next(n for n in result["nodes"] if n["id"] == isolated_seed)
            assert isolated_node.get("is_isolated") is True
            assert isolated_node.get("degree") == 0
            assert isolated_node.get("is_seed") is True
            assert isolated_node.get("relevance_score") == 1.0
        finally:
            # Clean up
            if kg_instance.store.has_node(isolated_seed):
                kg_instance.store.graph.remove_node(isolated_seed)

    def test_controlled_multi_hop_depth(self):
        """Verify multi-hop expansion expands monotonically with depth."""
        seed = "mutalporul"

        res_hop1 = graph_retrieval_service.retrieve_query_subgraph(
            query_input={"seed_ids": [seed]},
            max_hops=1,
        )
        res_hop2 = graph_retrieval_service.retrieve_query_subgraph(
            query_input={"seed_ids": [seed]},
            max_hops=2,
        )

        assert res_hop1["depth"] == 1
        assert res_hop2["depth"] == 2
        # Depth 2 should find at least as many nodes as depth 1
        assert res_hop2["total_nodes"] >= res_hop1["total_nodes"]

        # Ensure all node hop_distance values are <= max_hops
        for node in res_hop1["nodes"]:
            assert node.get("hop_distance", 0) <= 1

        for node in res_hop2["nodes"]:
            assert node.get("hop_distance", 0) <= 2

    def test_controlled_relationship_types(self):
        """Verify filtering by schema-controlled relationship types."""
        rel_filter = ["PRESIDES_OVER", "HAS_URIPPORUL", "GROUNDS_IN"]

        result = graph_retrieval_service.retrieve_query_subgraph(
            query_input={"seed_ids": ["kurinci", "ceyon", "mutalporul"]},
            max_hops=2,
            rel_types=rel_filter,
        )

        rel_filter_upper = {r.upper() for r in rel_filter}
        for rel in result["relationships"]:
            rel_type = (rel.get("type") or rel.get("relation", "")).upper()
            assert rel_type in rel_filter_upper, f"Unexpected relationship type: {rel_type}"

    def test_strict_relationship_endpoints_validity(self):
        """Ensure every returned relationship has valid source and target nodes."""
        result = graph_retrieval_service.retrieve_query_subgraph(
            query_input={
                "query": "What is the landscape and deity of Kurinji?",
                "entities": ["ceyon"],
                "concepts": ["kurinci", "mutalporul"],
                "passages": ["tol-porul-akam-005"],
            },
            max_hops=2,
            limit=40,
        )

        node_ids = {n["id"] for n in result["nodes"]}
        for edge in result["relationships"]:
            assert edge["source"] in node_ids, f"Edge source '{edge['source']}' not in nodes"
            assert edge["target"] in node_ids, f"Edge target '{edge['target']}' not in nodes"

    def test_provenance_and_relevance_metadata(self):
        """Verify provenance and relevance metadata are properly attached."""
        result = graph_retrieval_service.retrieve_query_subgraph(
            query_input={"seed_ids": ["ceyon", "kurinci"]},
            max_hops=2,
        )

        for node in result["nodes"]:
            assert "id" in node
            assert "is_seed" in node
            assert "is_isolated" in node
            assert "relevance_score" in node
            assert "relevance_reason" in node
            assert "hierarchy_level" in node or "level" in node

        for edge in result["relationships"]:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge
            assert "confidence" in edge


# =============================================================================
# 2. REST API Route Tests (/api/kg/query-subgraph & /api/kg/subgraph)
# =============================================================================

class TestQueryAwareSubgraphAPI:

    def test_post_query_subgraph_endpoint(self, client):
        """Test POST /api/kg/query-subgraph with query and seed identifiers."""
        payload = {
            "query": "மாயோன் மேய காடுறை உலகம்",
            "seed_ids": ["mullai", "mayon"],
            "passages": ["tol-porul-akam-005"],
            "hops": 2,
            "limit": 50,
        }

        response = client.post("/api/kg/query-subgraph", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "nodes" in data
        assert "relationships" in data
        assert data["total_nodes"] > 0

        node_ids = {n["id"] for n in data["nodes"]}
        for rel in data["relationships"]:
            assert rel["source"] in node_ids
            assert rel["target"] in node_ids

    def test_post_subgraph_delegation_with_query_context(self, client):
        """Test POST /api/kg/subgraph delegates to query-aware retrieval when query is provided."""
        payload = {
            "query": "Kurinji mountainous landscape",
            "entities": ["ceyon"],
            "concepts": ["kurinci"],
            "hops": 2,
        }

        response = client.post("/api/kg/subgraph", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "nodes" in data
        assert len(data["nodes"]) > 0

    def test_post_query_subgraph_isolated_node_preservation(self, client):
        """Test API preservation of isolated relevant seed node."""
        isolated_seed = "api_isolated_seed_node"
        from knowledge_graph.store import KGNode
        kg_instance.store.add_node(
            KGNode(
                id=isolated_seed,
                label="API Isolated Node",
                type="Concept",
                hierarchy_level="L4",
                source="test",
            )
        )

        try:
            payload = {
                "seed_ids": [isolated_seed],
                "hops": 1,
                "include_isolated": True,
            }
            response = client.post("/api/kg/query-subgraph", json=payload)
            assert response.status_code == 200
            data = response.get_json()["data"]

            node_ids = {n["id"] for n in data["nodes"]}
            assert isolated_seed in node_ids
            isolated_node = next(n for n in data["nodes"] if n["id"] == isolated_seed)
            assert isolated_node.get("is_isolated") is True
        finally:
            if kg_instance.store.has_node(isolated_seed):
                kg_instance.store.graph.remove_node(isolated_seed)
