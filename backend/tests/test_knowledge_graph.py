"""
Comprehensive unit and integration tests for Hierarchical Knowledge Graph module.

Tests cover:
- 6-level structural hierarchy (L0 to L5)
- 5 logical epistemic layers (Source, Entity, Concept, Event, Reasoning)
- Node and edge schemas (id, label, type, hierarchy_level, source, confidence, validation_level)
- Duplicate entity merging with Bayesian confidence combination
- Graph queries: get_entity(), get_neighbors(), find_paths(), expand_subgraph(), get_source_evidence()
- Multi-hop traversal and confidence propagation
- Graph validation checks
- REST API endpoints (/statistics, /entity/<id>, /subgraph, /path, /graph, /health)
"""
import pytest
from app import create_app
from knowledge_graph.store import (
    HierarchyLevel,
    LogicalLayer,
    KGNode,
    KGEdge,
    NetworkXGraphStore,
)
from knowledge_graph.graph_builder import KnowledgeGraphBuilder, kg_instance
from knowledge_graph.graph_validator import KnowledgeGraphValidator
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from knowledge_graph.ontology import TolkappiyamOntology


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


@pytest.fixture
def store():
    s = NetworkXGraphStore()
    yield s
    s.clear()


@pytest.fixture
def query_engine():
    return KnowledgeGraphQueryEngine(kg_instance)


# ===========================================================================
# 1. Structural Hierarchy (L0 - L5) & Logical Layers
# ===========================================================================

class TestHierarchyAndLayers:

    def test_hierarchy_level_ranks(self):
        assert HierarchyLevel.rank("L0") == 0
        assert HierarchyLevel.rank("L1") == 1
        assert HierarchyLevel.rank("L2") == 2
        assert HierarchyLevel.rank("L3") == 3
        assert HierarchyLevel.rank("L4") == 4
        assert HierarchyLevel.rank("L5") == 5

    def test_all_hierarchy_levels_present_in_graph(self):
        nodes = kg_instance.store.get_all_nodes()
        levels_present = {n.hierarchy_level for n in nodes}
        for lvl in ("L0", "L1", "L2", "L3", "L4", "L5"):
            assert lvl in levels_present, f"Hierarchy level {lvl} missing from KG"

    def test_all_five_logical_layers_present(self):
        nodes = kg_instance.store.get_all_nodes()
        layers_present = {n.metadata.get("layer") for n in nodes}
        expected_layers = {
            LogicalLayer.SOURCE.value,
            LogicalLayer.ENTITY.value,
            LogicalLayer.CONCEPT.value,
            LogicalLayer.EVENT.value,
            LogicalLayer.REASONING.value,
        }
        assert expected_layers.issubset(layers_present)

    def test_l0_literature_node(self):
        node = kg_instance.store.get_node("lit-sangam")
        assert node is not None
        assert node.hierarchy_level == "L0"
        assert node.type == "Literature"
        assert node.metadata.get("layer") == LogicalLayer.SOURCE.value

    def test_l1_work_node(self):
        node = kg_instance.store.get_node("work-tolkappiyam")
        assert node is not None
        assert node.hierarchy_level == "L1"
        assert node.type == "Work"

    def test_l2_section_nodes(self):
        sec = kg_instance.store.get_node("sec-porul-akam")
        assert sec is not None
        assert sec.hierarchy_level == "L2"
        assert sec.type == "Section"

    def test_l3_verse_nodes(self):
        sutra = kg_instance.store.get_node("tol-porul-akam-005")
        assert sutra is not None
        assert sutra.hierarchy_level == "L3"
        assert sutra.type == "Verse"
        assert "original_text" in sutra.metadata

    def test_l4_concept_nodes(self):
        concept = kg_instance.store.get_node("mutalporul")
        assert concept is not None
        assert concept.hierarchy_level == "L4"
        assert concept.type == "Concept"
        assert concept.metadata.get("layer") == LogicalLayer.CONCEPT.value

    def test_l5_entity_and_event_nodes(self):
        deity = kg_instance.store.get_node("ceyon")
        assert deity is not None
        assert deity.hierarchy_level == "L5"
        assert deity.metadata.get("layer") == LogicalLayer.ENTITY.value

        event = kg_instance.store.get_node("punartal")
        assert event is not None
        assert event.hierarchy_level == "L5"
        assert event.metadata.get("layer") == LogicalLayer.EVENT.value


# ===========================================================================
# 2. Node & Edge Schemas
# ===========================================================================

class TestNodeAndEdgeSchemas:

    def test_kg_node_schema(self):
        node = KGNode(
            id="test-node-1",
            label="Test Node",
            type="Concept",
            hierarchy_level="L4",
            source="Test Source",
            confidence=0.95,
            metadata={"layer": "Concept Layer", "attribute": "val"},
        )
        d = node.to_dict()
        required_keys = {"id", "label", "type", "hierarchy_level", "source", "confidence", "metadata"}
        assert required_keys.issubset(d.keys())
        assert d["confidence"] == 0.95

    def test_kg_edge_schema(self):
        edge = KGEdge(
            source="source-node",
            relation="groundsIn",
            target="target-node",
            source_id="citation-001",
            confidence=0.92,
            validation_level="corpus_validated",
        )
        d = edge.to_dict()
        required_keys = {"id", "source", "relation", "target", "source_id", "confidence", "validation_level"}
        assert required_keys.issubset(d.keys())
        assert d["relation"] == "groundsIn"

    def test_graph_nodes_have_all_schema_fields(self):
        for node in kg_instance.store.get_all_nodes():
            assert node.id != ""
            assert node.label != ""
            assert node.type != ""
            assert node.hierarchy_level in ("L0", "L1", "L2", "L3", "L4", "L5")
            assert node.source != ""
            assert 0.0 <= node.confidence <= 1.0

    def test_graph_edges_have_all_schema_fields(self):
        for edge in kg_instance.store.get_all_edges():
            assert edge.source != ""
            assert edge.relation != ""
            assert edge.target != ""
            assert edge.source_id != ""
            assert 0.0 <= edge.confidence <= 1.0
            assert edge.validation_level in ("corpus_validated", "unverified", "manually_verified")


# ===========================================================================
# 3. Duplicate Entity Merging
# ===========================================================================

class TestDuplicateEntityMerging:

    def test_entity_merging_combines_confidence(self, store):
        n1 = KGNode(id="murukan", label="முருகன்", type="Entity", hierarchy_level="L5", source="source1", confidence=0.8)
        n2 = KGNode(id="ceyon_alias", label="சேயோன் (மாற்றுப்பெயர்)", type="Entity", hierarchy_level="L5", source="source2", confidence=0.7)
        target = KGNode(id="mountain", label="வரை", type="Entity", hierarchy_level="L5", source="source3", confidence=1.0)

        store.add_node(n1)
        store.add_node(n2)
        store.add_node(target)

        store.add_edge(KGEdge(source="ceyon_alias", relation="presidesOver", target="mountain", source_id="s1", confidence=0.8))

        # Merge ceyon_alias into murukan
        merged = store.merge_nodes("murukan", ["ceyon_alias"])

        # Confidence: 1 - (1 - 0.8)*(1 - 0.7) = 1 - 0.06 = 0.94
        assert pytest.approx(merged.confidence, 0.01) == 0.94
        assert not store.has_node("ceyon_alias")
        assert "ceyon_alias" in merged.metadata.get("aliases", [])

        # Re-wired edge should now originate from murukan
        neighbors = store.get_neighbors("murukan", direction="out")
        neighbor_ids = [n["neighbor_id"] for n in neighbors]
        assert "mountain" in neighbor_ids


# ===========================================================================
# 4. Graph Query Engine (get_entity, get_neighbors, find_paths, expand_subgraph, get_source_evidence)
# ===========================================================================

class TestGraphQueryEngine:

    def test_get_entity_found(self, query_engine):
        entity = query_engine.get_entity("ceyon")
        assert entity is not None
        assert entity["id"] == "ceyon"
        assert entity["hierarchy_level"] == "L5"
        assert "neighbors" in entity
        assert "evidence" in entity

    def test_get_entity_not_found(self, query_engine):
        assert query_engine.get_entity("non-existent-entity") is None

    def test_get_neighbors(self, query_engine):
        neighbors = query_engine.get_neighbors("kurinci", direction="both")
        assert len(neighbors) > 0
        neighbor_ids = {n["neighbor_id"] for n in neighbors}
        assert "ceyon" in neighbor_ids or "punartal" in neighbor_ids

    def test_get_neighbors_filtered_by_relation(self, query_engine):
        neighbors = query_engine.get_neighbors("kurinci", direction="out", relation="hasUripporuḷ")
        for n in neighbors:
            assert n["relation"] == "hasUripporuḷ"

    def test_find_paths_direct_and_multihop(self, query_engine):
        paths = query_engine.find_paths("ceyon", "uriporul", max_depth=4)
        assert len(paths) > 0
        best_path = paths[0]
        assert best_path["source"] == "ceyon"
        assert best_path["target"] == "uriporul"
        assert best_path["length"] >= 1
        assert 0.0 < best_path["propagated_confidence"] <= 1.0

    def test_expand_subgraph(self, query_engine):
        subgraph = query_engine.expand_subgraph(node_ids=["kurinci"], hops=2)
        assert subgraph["total_nodes"] > 1
        assert subgraph["total_edges"] > 0
        node_ids = {n["id"] for n in subgraph["nodes"]}
        assert "kurinci" in node_ids

    def test_get_source_evidence(self, query_engine):
        evidence = query_engine.get_source_evidence("punartal")
        assert len(evidence) > 0
        levels = {e["hierarchy_level"] for e in evidence}
        # Evidence should trace back to Verse (L3) or Section (L2) or Work (L1)
        assert "L3" in levels or "L2" in levels or "L1" in levels


# ===========================================================================
# 5. Graph Validation Checks
# ===========================================================================

class TestGraphValidator:

    def test_validation_health(self):
        report = KnowledgeGraphValidator.validate(kg_instance)
        assert report["valid"] is True
        assert report["node_count"] >= 20
        assert report["edge_count"] >= 20
        assert report["is_connected"] is True
        assert len(report["isolated_nodes"]) == 0
        assert report["invalid_edges_count"] == 0
        assert len(report["invalid_hierarchy_nodes"]) == 0

    def test_hierarchy_distribution_complete(self):
        report = KnowledgeGraphValidator.validate(kg_instance)
        dist = report["hierarchy_distribution"]
        for lvl in ("L0", "L1", "L2", "L3", "L4", "L5"):
            assert lvl in dist
            assert dist[lvl] > 0


# ===========================================================================
# 6. REST API Endpoints
# ===========================================================================

class TestKnowledgeGraphApiEndpoints:

    def test_get_kg_statistics(self, client):
        resp = client.get("/api/kg/statistics")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        required_keys = {
            "total_nodes", "total_edges", "density", "is_connected",
            "hierarchy_distribution", "layer_distribution", "relation_distribution",
            "categories", "hierarchy_levels", "logical_layers",
        }
        assert required_keys.issubset(data.keys())
        assert data["total_nodes"] >= 20
        assert data["total_edges"] >= 20
        assert "L0" in data["hierarchy_distribution"]
        assert "Source Layer" in data["layer_distribution"]

    def test_get_entity_endpoint_valid(self, client):
        resp = client.get("/api/kg/entity/ceyon")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        data = json_data["data"]
        assert data["id"] == "ceyon"
        assert data["hierarchy_level"] == "L5"
        assert isinstance(data["neighbors"], list)
        assert isinstance(data["evidence"], list)

    def test_get_entity_endpoint_not_found(self, client):
        resp = client.get("/api/kg/entity/does_not_exist_123")
        assert resp.status_code == 404
        json_data = resp.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "ENTITY_NOT_FOUND"

    def test_post_subgraph_endpoint(self, client):
        resp = client.post(
            "/api/kg/subgraph",
            json={"node_ids": ["kurinci"], "hops": 2},
        )
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        data = json_data["data"]
        assert "nodes" in data
        assert "edges" in data
        assert data["total_nodes"] > 1

    def test_get_subgraph_backward_compatible(self, client):
        resp = client.get("/api/kg/subgraph?centerId=mutalporul&depth=2")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        data = json_data["data"]
        assert "nodes" in data
        assert "edges" in data

    def test_get_path_endpoint_valid(self, client):
        resp = client.get("/api/kg/path?source=ceyon&target=uriporul&depth=4")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        data = json_data["data"]
        assert data["source"] == "ceyon"
        assert data["target"] == "uriporul"
        assert data["total_paths"] > 0
        assert data["highest_confidence"] > 0.0

    def test_get_path_endpoint_missing_parameters(self, client):
        resp = client.get("/api/kg/path?source=ceyon")
        assert resp.status_code == 400
        json_data = resp.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "MISSING_PARAMETERS"

    def test_get_path_endpoint_node_not_found(self, client):
        resp = client.get("/api/kg/path?source=ceyon&target=unknown_target_xyz")
        assert resp.status_code == 404
        json_data = resp.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "NODE_NOT_FOUND"

    def test_get_full_graph(self, client):
        resp = client.get("/api/kg/graph")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["total_nodes"] >= 20

    def test_get_kg_health(self, client):
        resp = client.get("/api/kg/health")
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["valid"] is True
