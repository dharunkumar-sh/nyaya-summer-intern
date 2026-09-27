"""
Integration tests for Neo4j Node Selection and Dynamic Connected Subgraph Expansion.
Validates:
1. Retrieval of selected node and its first-degree connected nodes from Neo4j Aura.
2. Verification of relationship types, direction ('outgoing' / 'incoming'), confidence, and metadata.
3. Verification that non-existent node returns 404 error.
4. Verification of endpoints: GET /api/kg/node/<id>/connected and POST /api/kg/node/connected.
"""
import pytest
from app import create_app
from services.neo4j_service import neo4j_service
from knowledge_graph.neo4j_repository import neo4j_repository


@pytest.fixture(scope="module")
def test_client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


class TestNeo4jNodeSelectionExpansion:
    """Test suite for node selection and dynamic first-degree expansion."""

    def test_repository_get_node_connected_elements(self):
        """Verify Neo4jRepository.get_node_connected_elements returns valid connected subgraph."""
        if not (neo4j_repository.is_available() and neo4j_service.is_connected()):
            pytest.skip("Neo4j Aura database not connected")

        # Query a known canonical node, e.g. a tinai or concept or passage
        data = neo4j_repository.get_node_connected_elements("tol-porul-akam-005")
        if not data:
            # Try by mutalporul or another concept
            data = neo4j_repository.get_node_connected_elements("mutalporul")

        assert data is not None, "Expected connected elements for canonical node"
        assert "selected_node" in data
        assert "connected_nodes" in data
        assert "relationships" in data
        assert "metadata" in data

        selected = data["selected_node"]
        assert selected["id"] is not None
        assert "labels" in selected

        rels = data["relationships"]
        for r in rels:
            assert "source" in r
            assert "target" in r
            assert "type" in r
            assert "direction" in r
            assert r["direction"] in ("outgoing", "incoming")
            assert "confidence" in r
            assert float(r["confidence"]) >= 0.0

    def test_get_node_connected_api_endpoint(self, test_client):
        """Verify GET /api/kg/node/<id>/connected returns 200 with structured data."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database not connected")

        # Test with known node
        res = test_client.get("/api/kg/node/tol-porul-akam-005/connected")
        if res.status_code == 404:
            res = test_client.get("/api/kg/node/mutalporul/connected")

        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        data = payload["data"]

        assert "selected_node" in data
        assert "connected_nodes" in data
        assert "relationships" in data
        assert "metadata" in data
        assert data["metadata"]["source"] == "neo4j_aura"
        assert data["metadata"]["connected_count"] == len(data["connected_nodes"])
        assert data["metadata"]["relationship_count"] == len(data["relationships"])

        for rel in data["relationships"]:
            assert rel["direction"] in ("outgoing", "incoming")
            assert rel["type"] is not None

    def test_post_node_connected_api_endpoint(self, test_client):
        """Verify POST /api/kg/node/connected returns 200 with structured data."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database not connected")

        res = test_client.post(
            "/api/kg/node/connected",
            json={"node_id": "tol-porul-akam-005", "limit": 50},
        )
        if res.status_code == 404:
            res = test_client.post(
                "/api/kg/node/connected",
                json={"node_id": "mutalporul", "limit": 50},
            )

        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        assert "selected_node" in payload["data"]
        assert "connected_nodes" in payload["data"]
        assert "relationships" in payload["data"]

    def test_node_not_found_returns_404(self, test_client):
        """Verify requesting a non-existent node returns 404."""
        res = test_client.get("/api/kg/node/non_existent_node_xyz_9999/connected")
        assert res.status_code == 404
        payload = res.get_json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "NODE_NOT_FOUND"

    def test_missing_node_id_returns_400(self, test_client):
        """Verify POST with empty body returns 400."""
        res = test_client.post("/api/kg/node/connected", json={})
        assert res.status_code == 400
        payload = res.get_json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "MISSING_NODE_ID"

    def test_multi_hop_traversal_with_depth_and_lineage(self, test_client):
        """Verify multi-hop exploration returns parent-child lineage and path data."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database not connected")

        res = test_client.post(
            "/api/kg/node/traverse",
            json={"node_id": "tol-porul-akam-005", "hops": 2, "limit": 100},
        )
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["success"] is True
        data = payload["data"]

        assert "selected_node" in data
        assert "connected_nodes" in data
        assert "relationships" in data
        assert "paths" in data

        selected = data["selected_node"]
        assert selected["hop_distance"] == 0
        assert selected["parent_id"] is None

        # Check connected nodes have valid parent-child lineage
        connected = data["connected_nodes"]
        assert len(connected) > 0

        hop_distances = set()
        for node in connected:
            assert "hop_distance" in node
            assert node["hop_distance"] >= 1
            assert "parent_id" in node
            assert node["parent_id"] is not None
            assert "path_from_root" in node
            assert len(node["path_from_root"]) == node["hop_distance"] + 1
            assert node["path_from_root"][0] == selected["id"]
            assert node["path_from_root"][-1] == node["id"]
            hop_distances.add(node["hop_distance"])

        # Check paths structure
        paths = data["paths"]
        assert len(paths) > 0
        for p in paths:
            assert "target_id" in p
            assert "hops" in p
            assert p["hops"] in (1, 2)
            assert "path_node_ids" in p
            assert p["path_node_ids"][0] == selected["id"]
            assert "edges" in p

    def test_multi_hop_node_type_filtering(self, test_client):
        """Verify multi-hop exploration respects allowed_types and excluded_types."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database not connected")

        # Traversal with allowed_types whitelist
        res = test_client.get(
            "/api/kg/node/tol-porul-akam-005/connected?depth=2&allowed_types=Concept,Section,Work"
        )
        assert res.status_code == 200
        payload = res.get_json()
        data = payload["data"]

        for n in data["connected_nodes"]:
            labels_set = set(n.get("labels") or [])
            node_type = n.get("type", "")
            matches = any(lbl in ("Concept", "Section", "Work") for lbl in labels_set) or (node_type in ("Concept", "Section", "Work"))
            assert matches, f"Node {n['id']} type {node_type} did not match allowed filter"

        # Traversal with excluded_types blacklist
        res_ex = test_client.post(
            "/api/kg/node/traverse",
            json={"node_id": "tol-porul-akam-005", "hops": 2, "excluded_types": ["Literature"]},
        )
        assert res_ex.status_code == 200
        data_ex = res_ex.get_json()["data"]
        for n in data_ex["connected_nodes"]:
            assert "Literature" not in (n.get("labels") or [])
            assert n.get("type") != "Literature"

    def test_multi_hop_relationship_type_filtering(self, test_client):
        """Verify multi-hop exploration filters by canonical relationship types."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database not connected")

        res = test_client.get(
            "/api/kg/node/tol-porul-akam-005/connected?depth=2&rel_types=ATTESTS_CONCEPT,CONTAINS_PASSAGE"
        )
        assert res.status_code == 200
        data = res.get_json()["data"]

        for rel in data["relationships"]:
            assert rel["type"] in ("ATTESTS_CONCEPT", "CONTAINS_PASSAGE", "HAS_PASSAGE")

