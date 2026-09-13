"""
Unit tests for Flask app health check and basic error routing.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_health_check_endpoint(client):
    """Verifies that /api/health returns 200 OK, valid status payload, and integrated Neo4j status."""
    response = client.get("/api/health")
    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "HEALTHY"
    assert "Tolkāppiyam" in json_data["data"]["corpus"]

    # Verify Neo4j health is integrated without credential leakage
    assert "neo4j" in json_data["data"]
    neo4j_data = json_data["data"]["neo4j"]
    assert "connection_status" in neo4j_data
    assert "database_status" in neo4j_data
    assert "message" in neo4j_data
    assert "uri" not in neo4j_data
    assert "password" not in str(json_data).lower()
    assert "username" not in neo4j_data


def test_neo4j_health_endpoint_basic(client):
    """Verifies that /api/health/neo4j returns structured response and never exposes credentials."""
    response = client.get("/api/health/neo4j")
    assert response.status_code in (200, 503)

    json_data = response.get_json()
    assert "connection_status" in json_data
    assert "database_status" in json_data
    assert "message" in json_data
    assert "success" in json_data

    # Security assertion: strictly no credential exposure
    assert "uri" not in json_data
    assert "username" not in json_data
    assert "password" not in json_data
    assert "neo4j+s://" not in str(json_data)
    assert "traceback" not in str(json_data).lower()


def test_neo4j_health_endpoint_mocked_states(client, monkeypatch):
    """Verifies that /api/health/neo4j handles success, timeout, auth failure, and offline gracefully."""
    from services.neo4j_service import neo4j_service

    # 1. Success state
    monkeypatch.setattr(
        neo4j_service,
        "get_safe_connection_health",
        lambda database=None: {
            "connected": True,
            "connection_status": "connected",
            "database_status": "online",
            "database": "neo4j",
            "message": "Neo4j Aura database is healthy, reachable, and operational.",
            "latency_ms": 15.2,
            "server_agent": "Neo4j/5.27-aura",
            "protocol_version": "6.1",
        }
    )
    res_ok = client.get("/api/health/neo4j")
    assert res_ok.status_code == 200
    data_ok = res_ok.get_json()
    assert data_ok["success"] is True
    assert data_ok["connection_status"] == "connected"
    assert data_ok["database_status"] == "online"
    assert "operational" in data_ok["message"]

    # 2. Timeout state
    monkeypatch.setattr(
        neo4j_service,
        "get_safe_connection_health",
        lambda database=None: {
            "connected": False,
            "connection_status": "disconnected",
            "database_status": "timeout",
            "database": "neo4j",
            "message": "Connection timed out: Neo4j database did not respond within the allocated timeout period.",
            "latency_ms": None,
            "server_agent": None,
            "protocol_version": None,
        }
    )
    res_timeout = client.get("/api/health/neo4j")
    assert res_timeout.status_code == 503
    data_timeout = res_timeout.get_json()
    assert data_timeout["success"] is False
    assert data_timeout["database_status"] == "timeout"
    assert "timed out" in data_timeout["message"].lower()

    # 3. Authentication failure state
    monkeypatch.setattr(
        neo4j_service,
        "get_safe_connection_health",
        lambda database=None: {
            "connected": False,
            "connection_status": "disconnected",
            "database_status": "authentication_failed",
            "database": "neo4j",
            "message": "Authentication failed: invalid Neo4j database username or password.",
            "latency_ms": None,
            "server_agent": None,
            "protocol_version": None,
        }
    )
    res_auth = client.get("/api/health/neo4j")
    assert res_auth.status_code == 503
    data_auth = res_auth.get_json()
    assert data_auth["success"] is False
    assert data_auth["database_status"] == "authentication_failed"
    assert "Authentication failed" in data_auth["message"]

    # 4. Database unavailable / offline
    monkeypatch.setattr(
        neo4j_service,
        "get_safe_connection_health",
        lambda database=None: {
            "connected": False,
            "connection_status": "disconnected",
            "database_status": "database_unavailable",
            "database": "neo4j",
            "message": "The requested Neo4j database 'neo4j' is unavailable or does not exist.",
            "latency_ms": None,
            "server_agent": None,
            "protocol_version": None,
        }
    )
    res_unavail = client.get("/api/health/neo4j")
    assert res_unavail.status_code == 503
    data_unavail = res_unavail.get_json()
    assert data_unavail["success"] is False
    assert data_unavail["database_status"] == "database_unavailable"


def test_not_found_endpoint(client):
    """Verifies that non-existent routes return structured 404 response."""
    response = client.get("/api/non-existent-endpoint")
    assert response.status_code == 404

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "NOT_FOUND"

