"""
Integration tests for Swagger UI and OpenAPI 3.0 documentation endpoints (/docs).
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_docs_swagger_ui_html(client):
    """Tests GET /docs returns interactive Swagger UI HTML page."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    html_content = response.get_data(as_text=True)

    assert "swagger-ui" in html_content
    assert "SwaggerUIBundle" in html_content
    assert "/docs/openapi.json" in html_content
    assert "Nyāya Epistemic Reasoner API" in html_content


def test_docs_trailing_slash(client):
    """Tests GET /docs/ returns interactive Swagger UI."""
    response = client.get("/docs/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    html_content = response.get_data(as_text=True)
    assert "swagger-ui" in html_content


def test_docs_openapi_spec_json(client):
    """Tests GET /docs/openapi.json returns valid OpenAPI 3.0 specification."""
    response = client.get("/docs/openapi.json")
    assert response.status_code == 200
    assert response.is_json

    spec = response.get_json()
    assert spec["openapi"].startswith("3.0")
    assert "info" in spec
    assert spec["info"]["title"] == "Nyāya-Inspired Neuro-Symbolic Reasoner for Classical Tamil Literary Knowledge"
    assert "paths" in spec
    assert len(spec["paths"]) >= 14

    # Check key endpoints documented
    expected_paths = [
        "/api/health",
        "/api/query/analyze",
        "/api/query/examples",
        "/api/corpus/info",
        "/api/corpus/statistics",
        "/api/corpus/validate",
        "/api/corpus/sutras",
        "/api/corpus/sutras/{sutra_id}",
        "/api/kg/graph",
        "/api/kg/subgraph",
        "/api/kg/health",
        "/api/reasoning/deduce",
        "/api/reasoning/validate-fallacies",
        "/api/analytics/benchmark",
        "/api/analytics/metrics",
    ]
    for path in expected_paths:
        assert path in spec["paths"], f"Expected path {path} not found in OpenAPI spec"


def test_docs_swagger_alias_json(client):
    """Tests GET /docs/swagger.json returns identical specification."""
    response = client.get("/docs/swagger.json")
    assert response.status_code == 200
    assert response.is_json
    spec = response.get_json()
    assert spec["openapi"].startswith("3.0")
