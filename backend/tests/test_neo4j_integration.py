"""
Unit and integration tests for Neo4j Aura Service, Neo4jGraphStore repository,
and Graph RAG integration service.
"""
import pytest
from unittest.mock import MagicMock, patch
from app import create_app
from config import Neo4jConfig
from core.config import neo4j_settings, Neo4jSettings
from core.exceptions import (
    KnowledgeGraphError,
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    CypherQueryError,
    DatabaseTransactionError,
)
from services.neo4j_service import Neo4jService
from knowledge_graph.store import (
    KGNode,
    KGEdge,
    get_graph_store,
    NetworkXGraphStore,
)
from knowledge_graph.neo4j_store import Neo4jGraphStore
from services.graph_rag_service import GraphRAGService, graph_rag_service


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


# ===========================================================================
# 1. Configuration Validation
# ===========================================================================

class TestNeo4jConfiguration:

    def test_neo4j_config_class_attributes(self):
        assert hasattr(Neo4jConfig, "URI")
        assert hasattr(Neo4jConfig, "USERNAME")
        assert hasattr(Neo4jConfig, "PASSWORD")
        assert hasattr(Neo4jConfig, "DATABASE")
        assert hasattr(Neo4jConfig, "MAX_CONNECTION_POOL_SIZE")
        assert hasattr(Neo4jConfig, "CONNECTION_TIMEOUT")

    def test_neo4j_settings_pydantic_model(self):
        settings = Neo4jSettings(
            uri="neo4j+s://test.databases.neo4j.io",
            username="test_user",
            password="test_password",
            database="neo4j",
        )
        assert settings.uri == "neo4j+s://test.databases.neo4j.io"
        assert settings.max_connection_pool_size == 50
        assert settings.connection_timeout == 10.0
        assert settings.is_configured() is True
        masked = settings.masked_dict()
        assert "password" not in masked
        assert masked["password_configured"] is True

    def test_neo4j_config_validation_and_masking(self):
        validation = Neo4jConfig.validate()
        assert "valid" in validation
        assert "errors" in validation
        assert "password" not in validation
        assert "password_set" in validation
        masked = Neo4jConfig.get_masked_config()
        assert "password" not in masked

    def test_uri_and_secret_sanitization(self):
        from config import sanitize_uri
        from services.neo4j_service import sanitize_text

        raw_uri = "neo4j+s://admin:SuperSecretPassword123@cf40d45c.databases.neo4j.io"
        clean_uri = sanitize_uri(raw_uri)
        assert "SuperSecretPassword123" not in clean_uri
        assert clean_uri == "neo4j+s://***@cf40d45c.databases.neo4j.io"

        error_msg = "Error connecting with secret_token_xyz to cluster"
        cleaned_err = sanitize_text(error_msg, secret="secret_token_xyz")
        assert "secret_token_xyz" not in cleaned_err
        assert "[REDACTED]" in cleaned_err


# ===========================================================================
# 2. Neo4j Database Service
# ===========================================================================

class TestNeo4jService:

    def test_neo4j_service_init_with_params(self):
        service = Neo4jService(
            uri="neo4j+s://demo.databases.neo4j.io",
            username="demo_user",
            password="demo_password",
            database="demo_db",
        )
        assert service.uri == "neo4j+s://demo.databases.neo4j.io"
        assert service.username == "demo_user"
        assert service.database == "demo_db"

    def test_neo4j_service_uninitialized_health_check(self):
        service = Neo4jService(uri="", username="", password="")
        health = service.verify_connectivity()
        assert health["connected"] is False
        assert health["status"] == "DISCONNECTED"
        assert "Driver not initialized" in health["error"]

    def test_neo4j_service_mocked_connectivity(self):
        mock_driver = MagicMock()
        mock_server_info = MagicMock()
        mock_server_info.agent = "Neo4j/5.15.0"
        mock_server_info.protocol_version = "5.0"
        mock_driver.get_server_info.return_value = mock_server_info

        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password")
        service._driver = mock_driver

        health = service.verify_connectivity()
        assert health["connected"] is True
        assert health["status"] == "CONNECTED"
        assert health["server_agent"] == "Neo4j/5.15.0"

    def test_neo4j_service_close(self):
        mock_driver = MagicMock()
        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password")
        service._driver = mock_driver
        service.close()
        mock_driver.close.assert_called_once()
        assert service._driver is None

    def test_neo4j_reusable_driver_caching(self):
        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password")
        mock_driver = MagicMock()
        with patch("neo4j.GraphDatabase.driver", return_value=mock_driver) as mock_builder:
            d1 = service.get_driver()
            d2 = service.get_driver()
            assert d1 is d2
            assert d1 is mock_driver
            mock_builder.assert_called_once()

    def test_neo4j_database_selection(self):
        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password", database="initial_db")
        assert service.database == "initial_db"
        assert service.get_default_database() == "initial_db"
        service.set_default_database("tamil_literary_kg")
        assert service.database == "tamil_literary_kg"
        assert service.get_default_database() == "tamil_literary_kg"
        with pytest.raises(ValueError):
            service.set_default_database("")

    def test_neo4j_startup_check_success(self):
        mock_driver = MagicMock()
        mock_server_info = MagicMock()
        mock_server_info.agent = "Neo4j/5.27-aura"
        mock_server_info.protocol_version = (6, 1)
        mock_driver.get_server_info.return_value = mock_server_info

        service = Neo4jService(uri="neo4j+s://demo.databases.neo4j.io", username="user", password="secret_password")
        service._driver = mock_driver

        res = service.startup_check(raise_on_failure=False)
        assert res["connected"] is True
        assert res["status"] == "CONNECTED"
        assert res["server_agent"] == "Neo4j/5.27-aura"

    def test_neo4j_startup_check_failure(self):
        service = Neo4jService(uri="", username="", password="")
        # Should not raise when raise_on_failure is False
        res = service.startup_check(raise_on_failure=False)
        assert res["connected"] is False
        assert res["status"] == "DISCONNECTED"

        # Should raise DatabaseConnectionError when raise_on_failure is True
        with pytest.raises(DatabaseConnectionError):
            service.startup_check(raise_on_failure=True)

    def test_neo4j_health_check_lightweight(self):
        mock_driver = MagicMock()
        mock_server_info = MagicMock()
        mock_server_info.agent = "Neo4j/5.27-aura"
        mock_server_info.protocol_version = (6, 1)
        mock_driver.get_server_info.return_value = mock_server_info

        service = Neo4jService(uri="neo4j+s://demo.databases.neo4j.io", username="user", password="secret_password")
        service._driver = mock_driver

        health = service.health_check()
        assert health["status"] == "CONNECTED"
        assert health["connected"] is True
        assert "pool_size" in health
        assert "max_connection_lifetime" in health
        assert "latency_ms" in health
        # Must never expose secret_password
        assert "secret_password" not in str(health)

    def test_neo4j_parameterized_execution(self):
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value = mock_session

        # Mock execute_read work callback
        def fake_execute_read(work_fn):
            mock_tx = MagicMock()
            rec1 = MagicMock()
            rec1.data.return_value = {"id": "kurinci", "label": "குறிஞ்சி"}
            mock_tx.run.return_value = [rec1]
            return work_fn(mock_tx)

        def fake_execute_write(work_fn):
            mock_tx = MagicMock()
            rec1 = MagicMock()
            rec1.data.return_value = {"updated": 1}
            mock_tx.run.return_value = [rec1]
            return work_fn(mock_tx)

        mock_session.execute_read.side_effect = fake_execute_read
        mock_session.execute_write.side_effect = fake_execute_write

        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password")
        service._driver = mock_driver

        # Read
        read_res = service.execute_read(
            "MATCH (n:KGNode {id: $id}) RETURN n.id AS id, n.label AS label",
            parameters={"id": "kurinci"}
        )
        assert len(read_res) == 1
        assert read_res[0]["id"] == "kurinci"

        # Write
        write_res = service.execute_write(
            "MERGE (n:KGNode {id: $id}) SET n.label = $label",
            parameters={"id": "kurinci", "label": "குறிஞ்சி"}
        )
        assert len(write_res) == 1
        assert write_res[0]["updated"] == 1

    def test_neo4j_explicit_transaction(self):
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_tx = MagicMock()
        mock_session.begin_transaction.return_value = mock_tx
        mock_driver.session.return_value = mock_session

        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="password")
        service._driver = mock_driver

        # Successful transaction commits
        with service.transaction(mode="write") as tx:
            tx.run("CREATE (n:Test)", {})
        mock_tx.commit.assert_called_once()

    def test_neo4j_exception_handling_without_credentials(self):
        from neo4j.exceptions import ClientError, AuthError, ServiceUnavailable

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value = mock_session

        mock_session.execute_read.side_effect = ClientError("Invalid Cypher syntax near secret_token_xyz")

        service = Neo4jService(uri="bolt://localhost:7687", username="neo4j", password="secret_token_xyz")
        service._driver = mock_driver

        with pytest.raises(CypherQueryError) as excinfo:
            service.execute_read("INVALID CYPHER")
        # Ensure password/secret is redacted
        assert "secret_token_xyz" not in str(excinfo.value)
        assert "[REDACTED]" in str(excinfo.value)


# ===========================================================================
# 3. Neo4jGraphStore Repository
# ===========================================================================

class TestNeo4jGraphStore:

    def test_neo4j_store_availability_check(self):
        service = Neo4jService(uri="", username="", password="")
        store = Neo4jGraphStore(service=service)
        assert store.is_available() is False
        assert store.node_count() == 0
        assert store.edge_count() == 0

    def test_neo4j_store_mocked_read_queries(self):
        mock_service = MagicMock()
        mock_service.get_driver.return_value = MagicMock()
        mock_service.execute_read.return_value = [
            {
                "n": {
                    "id": "kurinci",
                    "label": "குறிஞ்சி",
                    "type": "Entity",
                    "hierarchy_level": "L5",
                    "source": "Tolkāppiyam",
                    "confidence": 1.0,
                    "metadata_json": '{"tinai": "Kuṟiñci"}',
                }
            }
        ]

        store = Neo4jGraphStore(service=mock_service)
        node = store.get_node("kurinci")

        assert node is not None
        assert node.id == "kurinci"
        assert node.label == "குறிஞ்சி"
        assert node.metadata.get("tinai") == "Kuṟiñci"

    def test_neo4j_store_mocked_path_query(self):
        mock_service = MagicMock()
        mock_service.get_driver.return_value = MagicMock()
        mock_service.execute_read.return_value = [
            {
                "nodes": [{"id": "ceyon"}, {"id": "kurinci"}, {"id": "uriporul"}],
                "edges": [{"relation": "presidesOver", "confidence": 0.95}, {"relation": "hasUripporuḷ", "confidence": 0.98}],
                "length": 2,
            }
        ]

        store = Neo4jGraphStore(service=mock_service)
        paths = store.find_paths("ceyon", "uriporul", max_depth=3)

        assert len(paths) == 1
        assert paths[0]["length"] == 2
        assert pytest.approx(paths[0]["propagated_confidence"], 0.01) == 0.931

    def test_get_graph_store_factory(self):
        nx_store = get_graph_store("networkx")
        assert isinstance(nx_store, NetworkXGraphStore)

        neo_store = get_graph_store("neo4j")
        assert isinstance(neo_store, Neo4jGraphStore)


# ===========================================================================
# 4. Graph RAG Service Integration
# ===========================================================================

class TestGraphRAGService:

    def test_retrieve_graph_augmented_context(self):
        context = graph_rag_service.retrieve_graph_augmented_context(
            query="குறிஞ்சி நிலத்தின் முதற்பொருள் மற்றும் சேயோன் தொடர்பு",
            top_k=3,
            hops=2,
        )
        assert "query" in context
        assert "detected_tinai" in context
        assert "retrieved_evidence" in context
        assert "graph_subgraph" in context
        assert "graph_axioms" in context
        assert len(context["retrieved_evidence"]) > 0
        assert "nodes" in context["graph_subgraph"]
        assert "edges" in context["graph_subgraph"]


# ===========================================================================
# 5. Neo4j API Endpoints
# ===========================================================================

class TestNeo4jApiEndpoints:

    def test_get_neo4j_health_endpoint(self, client):
        resp = client.get("/api/kg/neo4j/health")
        # May be 200 (if reachable) or 503 (if cloud credentials offline in test env)
        assert resp.status_code in (200, 503)
        json_data = resp.get_json()
        assert "status" in str(json_data).lower()

    def test_get_neo4j_validate_endpoint(self, client):
        resp = client.get("/api/kg/neo4j/validate")
        assert resp.status_code in (200, 400)
        json_data = resp.get_json()
        assert "password" not in str(json_data).lower() or "password_set" in str(json_data)

    def test_post_neo4j_sync_endpoint_when_disconnected(self, client):
        resp = client.post("/api/kg/neo4j/sync")
        # Should gracefully return structured JSON with 503 or 200
        assert resp.status_code in (200, 503)
        json_data = resp.get_json()
        assert "message" in json_data or "error" in json_data
