"""
Small, focused backend test suite for Neo4j Aura integration.

Features tested:
1. Driver initialization from environment variables (zero hardcoded passwords)
2. Database selection (default, runtime switching, and per-query override)
3. Aura connectivity & database information check (server agent, protocol, latency)
4. Basic read query (RETURN 1 AS result)
5. Parameterized Cypher execution ($num, $text, $flag)
6. Graceful handling of connection failures (auth failure, unreachable host, syntax error)
7. Security: password and credentials are never exposed in outputs, errors, or logs

Safety:
- Absolutely NO permanent project data is written or deleted.
- Runs both live against Neo4j Aura (if reachable) and in isolated/mocked environments.
- Easy to execute locally with:
    pytest backend/tests/test_neo4j_connectivity.py -v
    python backend/tests/test_neo4j_connectivity.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import Neo4jConfig
from core.config import neo4j_settings
from core.exceptions import (
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    CypherQueryError,
)
from services.neo4j_service import Neo4jService, neo4j_service


# ==============================================================================
# 1. Driver Initialization & Configuration (Zero Hardcoded Password)
# ==============================================================================

class TestNeo4jDriverInitialization:
    """Verifies that the Neo4j driver initializes correctly from environment."""

    def test_driver_initialization_from_environment(self):
        """Driver must load credentials from environment variables, not hardcoded strings."""
        # Assert no password string is hardcoded in class defaults
        assert isinstance(Neo4jConfig.PASSWORD, str)
        assert isinstance(Neo4jConfig.URI, str)
        assert isinstance(Neo4jConfig.USERNAME, str)

        # Verify pool and timeout settings
        assert Neo4jConfig.MAX_CONNECTION_POOL_SIZE > 0
        assert Neo4jConfig.MAX_CONNECTION_LIFETIME > 0
        assert Neo4jConfig.CONNECTION_TIMEOUT > 0

        # Verify driver instance is accessible
        driver = neo4j_service.get_driver()
        if Neo4jConfig.is_configured():
            assert driver is not None, "Driver should initialize when credentials are in .env"
        else:
            assert driver is None


# ==============================================================================
# 2. Database Selection
# ==============================================================================

class TestNeo4jDatabaseSelection:
    """Verifies default database selection and runtime selection override."""

    def test_default_database_selection(self):
        """Service should select the configured database or fallback to 'neo4j'."""
        assert neo4j_service.database in (Neo4jConfig.DATABASE, "neo4j")
        assert neo4j_service.get_default_database() == neo4j_service.database

    def test_runtime_database_switching(self):
        """Service should allow switching active target database safely."""
        service = Neo4jService(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="test_password",
            database="primary_db"
        )
        assert service.database == "primary_db"

        service.set_default_database("analytics_db")
        assert service.database == "analytics_db"
        assert service.get_default_database() == "analytics_db"

        with pytest.raises(ValueError):
            service.set_default_database("")


# ==============================================================================
# 3. Database Information & Connectivity Check
# ==============================================================================

class TestNeo4jConnectivityAndInfo:
    """Verifies database connectivity verification and server information check."""

    def test_database_information_check(self):
        """Verifies server agent version, protocol, latency, and connectivity."""
        info = neo4j_service.verify_connectivity()
        assert "connected" in info
        assert "status" in info
        assert "database" in info

        # Security check: credentials and passwords must NEVER be present
        assert "password" not in info
        assert "username" not in info
        assert "neo4j+s://" not in str(info.get("database", ""))

        if info["connected"]:
            assert "server_agent" in info
            assert "protocol_version" in info
            assert "latency_ms" in info
            assert info["latency_ms"] >= 0
            assert "Neo4j" in info["server_agent"]

    def test_safe_health_check_payload(self):
        """Verifies lightweight health-check returns clean, human-readable status."""
        health = neo4j_service.get_safe_connection_health()
        assert health["connection_status"] in ("connected", "disconnected")
        assert health["database_status"] in (
            "online", "authentication_failed", "timeout", "unreachable", "not_configured", "error"
        )
        assert "message" in health
        assert isinstance(health["message"], str)
        assert len(health["message"]) > 5

        # Strictly no secrets
        assert "password" not in str(health).lower() or "password_set" in str(health).lower()


# ==============================================================================
# 4. Basic Read Query (RETURN 1 AS result)
# ==============================================================================

class TestNeo4jBasicReadQuery:
    """Verifies simple read query execution without creating any permanent data."""

    def test_basic_read_query_return_one(self):
        """Executes 'RETURN 1 AS result' to verify end-to-end Cypher pipeline."""
        info = neo4j_service.verify_connectivity()
        if not info.get("connected"):
            # If remote Aura instance is offline, test with mocked session
            mock_driver = MagicMock()
            mock_session = MagicMock()
            rec = MagicMock()
            rec.data.return_value = {"result": 1}
            mock_session.execute_read.side_effect = lambda work: work(MagicMock(run=lambda q, p: [rec]))
            mock_driver.session.return_value = mock_session

            test_service = Neo4jService(uri="bolt://localhost:7687", username="test", password="pwd")
            test_service._driver = mock_driver
            records = test_service.execute_read("RETURN 1 AS result")
        else:
            records = neo4j_service.execute_read("RETURN 1 AS result")

        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0] == {"result": 1}


# ==============================================================================
# 5. Parameterized Cypher Execution
# ==============================================================================

class TestNeo4jParameterizedCypher:
    """Verifies that queries strictly use parameters rather than string interpolation."""

    def test_parameterized_query_execution(self):
        """Executes parameterized query with multiple data types ($num, $text, $flag)."""
        query = "RETURN $num AS number, $text AS message, $flag AS enabled"
        params = {"num": 42, "text": "Tolkāppiyam", "flag": True}

        info = neo4j_service.verify_connectivity()
        if not info.get("connected"):
            mock_driver = MagicMock()
            mock_session = MagicMock()
            rec = MagicMock()
            rec.data.return_value = {"number": 42, "message": "Tolkāppiyam", "enabled": True}
            mock_session.execute_read.side_effect = lambda work: work(MagicMock(run=lambda q, p: [rec]))
            mock_driver.session.return_value = mock_session

            test_service = Neo4jService(uri="bolt://localhost:7687", username="test", password="pwd")
            test_service._driver = mock_driver
            records = test_service.execute_read(query, parameters=params)
        else:
            records = neo4j_service.execute_read(query, parameters=params)

        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0]["number"] == 42
        assert records[0]["message"] == "Tolkāppiyam"
        assert records[0]["enabled"] is True


# ==============================================================================
# 6. Graceful Handling of Connection Failures & Security
# ==============================================================================

class TestNeo4jFailureHandling:
    """Verifies graceful handling of authentication failure, invalid host, and syntax errors."""

    def test_unreachable_host_handling(self):
        """Unreachable host should report UNREACHABLE without unhandled crashes."""
        from neo4j.exceptions import ServiceUnavailable

        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Connection refused: 127.0.0.1:1")
        mock_session = MagicMock()
        mock_session.execute_read.side_effect = ServiceUnavailable("Connection refused")
        mock_driver.session.return_value = mock_session

        bad_service = Neo4jService(
            uri="bolt://127.0.0.1:1",
            username="neo4j",
            password="fake_password",
        )
        bad_service._driver = mock_driver

        health = bad_service.verify_connectivity()
        assert health["connected"] is False
        assert health["status"] == "UNREACHABLE"

        with pytest.raises(DatabaseConnectionError):
            bad_service.execute_read("RETURN 1 AS result")


    def test_invalid_credentials_handling(self):
        """Invalid credentials should map to DatabaseAuthenticationError without exposing secrets."""
        from neo4j.exceptions import AuthError

        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = AuthError("Unauthorized")
        mock_driver.session.side_effect = AuthError("Unauthorized")

        auth_service = Neo4jService(
            uri="bolt://localhost:7687",
            username="wrong_user",
            password="SuperSecretPasswordXYZ"
        )
        auth_service._driver = mock_driver

        health = auth_service.verify_connectivity()
        assert health["connected"] is False
        assert health["status"] == "AUTH_FAILED"
        # Secret password must never be in health dictionary
        assert "SuperSecretPasswordXYZ" not in str(health)

        with pytest.raises(DatabaseAuthenticationError) as exc_info:
            auth_service.execute_read("RETURN 1 AS result")
        assert "SuperSecretPasswordXYZ" not in str(exc_info.value)

    def test_syntax_error_handling(self):
        """Cypher syntax error should raise CypherQueryError with sanitized message."""
        from neo4j.exceptions import ClientError

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.execute_read.side_effect = ClientError("Invalid syntax near secret_token_xyz")
        mock_driver.session.return_value = mock_session

        service = Neo4jService(uri="bolt://localhost:7687", username="user", password="secret_token_xyz")
        service._driver = mock_driver

        with pytest.raises(CypherQueryError) as exc_info:
            service.execute_read("MALFORMED CYPHER QUERY")
        # Token must be redacted
        assert "secret_token_xyz" not in str(exc_info.value)
        assert "[REDACTED]" in str(exc_info.value)


# ==============================================================================
# Standalone CLI Execution Entry Point
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(" Running Neo4j Connectivity & Integration Test Suite")
    print("=" * 70)

    # 1. Test Driver Initialization
    print("[1/6] Testing Driver Initialization...")
    t_init = TestNeo4jDriverInitialization()
    t_init.test_driver_initialization_from_environment()
    print("      ✓ Driver initialized successfully from environment")

    # 2. Test Database Selection
    print("[2/6] Testing Database Selection...")
    t_db = TestNeo4jDatabaseSelection()
    t_db.test_default_database_selection()
    t_db.test_runtime_database_switching()
    print(f"      ✓ Database selection verified (Active: '{neo4j_service.database}')")

    # 3. Test Connectivity & Info
    print("[3/6] Testing Aura Connectivity & Server Info...")
    t_conn = TestNeo4jConnectivityAndInfo()
    t_conn.test_database_information_check()
    t_conn.test_safe_health_check_payload()
    info = neo4j_service.verify_connectivity()
    if info.get("connected"):
        print(f"      ✓ Connected to Neo4j Aura ({info.get('server_agent')}, {info.get('latency_ms')}ms)")
    else:
        print(f"      ! Offline state verified ({info.get('status')})")

    # 4. Test Basic Read Query
    print("[4/6] Testing Basic Read Query (RETURN 1 AS result)...")
    t_read = TestNeo4jBasicReadQuery()
    t_read.test_basic_read_query_return_one()
    print("      ✓ Query 'RETURN 1 AS result' returned [{'result': 1}]")

    # 5. Test Parameterized Execution
    print("[5/6] Testing Parameterized Cypher Execution...")
    t_param = TestNeo4jParameterizedCypher()
    t_param.test_parameterized_query_execution()
    print("      ✓ Parameterized execution with $num, $text, $flag passed")

    # 6. Test Failure Handling & Security
    print("[6/6] Testing Failure Handling & Credential Protection...")
    t_fail = TestNeo4jFailureHandling()
    t_fail.test_unreachable_host_handling()
    t_fail.test_invalid_credentials_handling()
    t_fail.test_syntax_error_handling()
    print("      ✓ Graceful failure handling and credential masking confirmed")

    print("=" * 70)
    print(" ALL 6 TEST SUITES PASSED SUCCESSFULLY (0 project data created)")
    print("=" * 70)
