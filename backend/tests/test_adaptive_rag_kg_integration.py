"""
Integration Test Suite: Adaptive Graph-RAG Pipeline Integrated with Knowledge Graph Visualization.

Validates the full pipeline:
User Query
-> Query Understanding
-> Lexical Retrieval
-> Semantic Retrieval
-> Graph Retrieval from Neo4j
-> Evidence Aggregation
-> Relevant Neo4j Subgraph
-> Evidence-to-Premise Transformation
-> Nyaya-Inspired Reasoning
-> Conclusion
-> Graph Visualization

Ensures:
1. The final graph displayed after a query is based on the exact same retrieval results used for reasoning.
2. The graph does not display unrelated Neo4j data.
3. Graph elements are properly attributed with contributed_to_evidence, contributed_to_reasoning,
   evidence_ids, source_reference, reasoning_role, and reasoning_step.
4. D3-consumable structure is delivered without client-side inference dependencies.
"""
import pytest
from app import create_app
from services.reasoning_service import reasoning_service
from services.graph_retrieval_service import graph_retrieval_service


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_reasoning_service_attributed_subgraph_pipeline():
    """
    Test that execute_reasoning_pipeline generates a coherent Neo4j subgraph
    attributed with evidence IDs and reasoning roles based on the same retrieved evidence.
    """
    query = "Explain how mountain landscape (Kurinji) and night season evoke Punartal union."
    res = reasoning_service.execute_reasoning_pipeline(
        query_text=query,
        depth=2,
        focus="Relationship",
    )

    assert isinstance(res, dict)
    assert "knowledgeGraph" in res
    assert "neo4jGraph" in res
    assert "evidenceRecords" in res
    assert "premises" in res
    assert "rules" in res
    assert "conclusion" in res

    kg = res["knowledgeGraph"]
    assert isinstance(kg, dict)
    assert "nodes" in kg
    assert "relationships" in kg
    assert "metadata" in kg

    # Identical authoritative graph returned in both fields
    assert kg["nodes"] == res["neo4jGraph"]["nodes"]
    assert kg["relationships"] == res["neo4jGraph"]["relationships"]

    # Verify query and pipeline metadata
    meta = kg["metadata"]
    assert meta["query"] == query
    assert meta["node_count"] == len(kg["nodes"])
    assert meta["relationship_count"] == len(kg["relationships"])
    assert "contributed_to_evidence_count" in meta
    assert "contributed_to_reasoning_count" in meta

    # Check node attribution fields
    if kg["nodes"]:
        for node in kg["nodes"]:
            assert "contributed_to_evidence" in node
            assert "contributed_to_reasoning" in node
            assert "evidence_ids" in node
            assert isinstance(node["evidence_ids"], list)
            assert "source_reference" in node

        # Check that at least some nodes contributed to evidence and reasoning
        evidence_contributors = [n for n in kg["nodes"] if n["contributed_to_evidence"]]
        reasoning_contributors = [n for n in kg["nodes"] if n["contributed_to_reasoning"]]
        assert len(evidence_contributors) > 0
        assert len(reasoning_contributors) > 0

        # Verify reasoning roles are assigned (e.g. paksa, udaharana, premise, hetu)
        roles = [n.get("reasoning_role") for n in reasoning_contributors if n.get("reasoning_role")]
        assert len(roles) > 0

    # Check relationship attribution fields
    for rel in kg["relationships"]:
        assert "contributed_to_evidence" in rel
        assert "contributed_to_reasoning" in rel
        assert "evidence_ids" in rel
        assert isinstance(rel["evidence_ids"], list)


def test_subgraph_isolation_no_unrelated_nodes():
    """
    Ensure that arbitrary queries with no matching concepts return an empty subgraph
    with 0 nodes, 0 relationships, and zero mock fallbacks.
    """
    unrelated_query = "quantum mechanics particle entanglement theory 987654"
    res = reasoning_service.execute_reasoning_pipeline(
        query_text=unrelated_query,
        depth=2,
    )

    kg = res["knowledgeGraph"]
    assert kg["nodes"] == []
    assert kg["relationships"] == []
    assert kg["metadata"]["node_count"] == 0
    assert kg["metadata"]["relationship_count"] == 0
    assert res.get("insufficientEvidence") is True


def test_api_reasoning_answer_endpoint(client):
    """
    Verify POST /api/reasoning/answer returns the attributed Neo4j subgraph
    integrated with full Pañcāvayava deduction and Hetvābhāsa validation.
    """
    payload = {
        "queryText": "முல்லை நிலத்தில் மாயோன் வழிபாடும் முல்லை ஒழுக்கமும்",
        "depth": 2,
        "focus": "Relationship",
    }
    response = client.post("/api/reasoning/answer", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    res_data = data["data"]

    assert "knowledgeGraph" in res_data
    assert "neo4jGraph" in res_data
    kg = res_data["knowledgeGraph"]
    assert isinstance(kg["nodes"], list)
    assert isinstance(kg["relationships"], list)
    assert len(kg["nodes"]) > 0

    # Verify that Mullai or Mayon seeds contributed to evidence/reasoning
    matched_nodes = [
        n for n in kg["nodes"]
        if "mullai" in str(n.get("id", "")).lower() or "mayon" in str(n.get("id", "")).lower()
    ]
    assert len(matched_nodes) > 0
    assert any(n.get("contributed_to_reasoning") or n.get("contributed_to_evidence") for n in matched_nodes)


def test_retrieval_answer_endpoint_graph_integration(client):
    """
    Verify POST /api/retrieval/answer includes the synchronized Knowledge Graph
    reflecting the retrieved evidence for that query.
    """
    payload = {
        "query": "What is the relationship between Kurinji landscape and Murugan?",
        "top_k": 5,
        "max_graph_depth": 2,
    }
    response = client.post("/api/retrieval/answer", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    res_data = data["data"]

    assert "knowledge_graph" in res_data
    kg = res_data["knowledge_graph"]
    assert isinstance(kg["nodes"], list)
    assert isinstance(kg["relationships"], list)
    assert kg["metadata"]["node_count"] == len(kg["nodes"])
    assert kg["metadata"]["evidence_count"] >= 1


def test_graph_retrieval_service_attribution_direct():
    """
    Direct unit test on graph_retrieval_service.retrieve_query_subgraph
    verifying evidence attribution for provided passages and entities.
    """
    sample_evidence = [
        {
            "passage_id": "tol-porul-akam-004",
            "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 4",
            "entities": ["ceyon", "kurinci"],
            "concepts": ["punartal"],
        }
    ]
    res = graph_retrieval_service.retrieve_query_subgraph(
        query_input={
            "queryText": "ceyon kurinci punartal",
            "evidence": sample_evidence,
        },
        max_hops=1,
    )

    assert "nodes" in res
    assert len(res["nodes"]) > 0
    # Check that passage / entity nodes have contributed_to_evidence=True
    ev_nodes = [n for n in res["nodes"] if n.get("contributed_to_evidence")]
    assert len(ev_nodes) > 0
    # Check that connected evidence IDs are populated
    has_ev_ids = any("tol-porul-akam-004" in n.get("evidence_ids", []) for n in ev_nodes)
    assert has_ev_ids
