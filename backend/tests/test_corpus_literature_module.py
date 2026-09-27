"""
Unit and Integration Tests for Classical Tamil Corpus and Literature Foundation.
Verifies modular architecture, database connectivity abstraction, models, schemas,
services, utilities, and API v1 endpoints.
"""
import pytest
from app import create_app
from database.connection import Neo4jConnectionManager, get_db_manager
from database.session import managed_session
from models.corpus import Sutra, Atikaram, CorpusMetadata
from models.enums import AtikaramType, TinaiType
from services.corpus_service import CorpusService, get_corpus_service
from utilities.tamil_text import normalize_tamil_text, is_tamil_text, tokenize_tamil_words
from utilities.pagination import paginate_items


@pytest.fixture
def client():
    """Flask test client fixture."""
    app = create_app("testing")
    with app.test_client() as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Utilities & Models Tests
# ---------------------------------------------------------------------------

def test_tamil_text_utilities():
    """Verifies Unicode NFC normalization, script detection, and tokenization."""
    raw_tamil = "முதல்கரு  உரிப்பொருள்  என்ற   மூன்றே"
    normalized = normalize_tamil_text(raw_tamil)
    assert "  " not in normalized
    assert is_tamil_text(raw_tamil) is True
    assert is_tamil_text("Hello World English Only") is False

    tokens = tokenize_tamil_words(raw_tamil)
    assert len(tokens) == 4
    assert tokens[0] == "முதல்கரு"


def test_pagination_utility():
    """Verifies in-memory sequence pagination and metadata computation."""
    items = list(range(55))
    sliced, meta = paginate_items(items, page=2, page_size=20)
    assert len(sliced) == 20
    assert sliced[0] == 20
    assert meta.page == 2
    assert meta.total_items == 55
    assert meta.total_pages == 3
    assert meta.has_next is True
    assert meta.has_prev is True


def test_database_connection_manager_diagnostics():
    """Verifies Neo4j manager handles connectivity check safely without crashing."""
    manager = get_db_manager()
    health = manager.verify_connectivity()
    assert "connected" in health
    assert "status" in health
    assert "database" in health
    # Ensure URI does not leak passwords
    if health.get("uri"):
        assert "password" not in health["uri"].lower()


# ---------------------------------------------------------------------------
# Services Tests
# ---------------------------------------------------------------------------

def test_corpus_service_loads_canonical_metadata():
    """Verifies CorpusService loads Tolkāppiyam metadata, atikarams, and sūtras."""
    service = get_corpus_service()
    meta = service.get_metadata()
    assert "Tolkāppiyam" in meta.name
    assert meta.books_count == 3
    assert meta.total_sutras == 1610

    atikarams = service.get_atikarams()
    assert len(atikarams) == 3
    book_ids = [b.id for b in atikarams]
    assert "eluttu" in book_ids
    assert "col" in book_ids
    assert "porul" in book_ids


def test_corpus_service_sutras_filtering_and_retrieval():
    """Verifies sūtra retrieval with filtering and ID lookup."""
    service = get_corpus_service()
    # Fetch paginated sūtras
    sutras, page_meta = service.get_sutras(page=1, page_size=10)
    assert len(sutras) > 0
    assert page_meta.total_items > 0

    first_sutra = sutras[0]
    fetched_by_id = service.get_sutra_by_id(first_sutra.id)
    assert fetched_by_id.id == first_sutra.id
    assert fetched_by_id.tamil_text == first_sutra.tamil_text


def test_corpus_service_tinai_and_statistics():
    """Verifies Tiṇai landscapes and corpus statistics."""
    service = get_corpus_service()
    landscapes = service.get_tinai_landscapes()
    assert len(landscapes) == 5
    tinai_names = [l.tinai for l in landscapes]
    assert "Kuriñci" in tinai_names
    assert "Mullai" in tinai_names

    stats = service.get_statistics()
    assert stats.total_sutras == 1610
    assert stats.books_count == 3
    assert len(stats.atikaram_breakdown) > 0


# ---------------------------------------------------------------------------
# API v1 REST Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_v1_corpus_info(client):
    """GET /api/v1/corpus/info returns standardized response with corpus metadata."""
    resp = client.get("/api/v1/corpus/info")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "Tolkāppiyam" in data["data"]["name"]
    assert data["data"]["total_sutras"] == 1610


def test_api_v1_corpus_atikarams(client):
    """GET /api/v1/corpus/atikarams and /api/v1/corpus/atikarams/<id>."""
    resp = client.get("/api/v1/corpus/atikarams")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["data"]) == 3

    detail_resp = client.get("/api/v1/corpus/atikarams/porul")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.get_json()
    assert detail_data["success"] is True
    assert detail_data["data"]["id"] == "porul"
    assert "Poruḷatikāram" in detail_data["data"]["name"]


def test_api_v1_corpus_sutras_and_error_handling(client):
    """GET /api/v1/corpus/sutras and individual sūtra lookup with 404 test."""
    resp = client.get("/api/v1/corpus/sutras?page=1&page_size=5")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["success"] is True
    assert "items" in json_data["data"]
    assert "pagination" in json_data["data"]
    assert len(json_data["data"]["items"]) <= 5

    first_sutra = json_data["data"]["items"][0]
    sutra_id = first_sutra["id"]

    # Valid ID lookup
    detail_resp = client.get(f"/api/v1/corpus/sutras/{sutra_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.get_json()
    assert detail_data["success"] is True
    assert detail_data["data"]["id"] == sutra_id

    # Invalid ID lookup returns 404 with standardized error envelope
    not_found_resp = client.get("/api/v1/corpus/sutras/non-existent-sutra-xyz")
    assert not_found_resp.status_code == 404
    not_found_data = not_found_resp.get_json()
    assert not_found_data["success"] is False
    assert not_found_data["error"]["code"] == "SUTRA_NOT_FOUND"


def test_api_v1_corpus_tinai_and_statistics(client):
    """GET /api/v1/corpus/tinai and /api/v1/corpus/statistics."""
    tinai_resp = client.get("/api/v1/corpus/tinai")
    assert tinai_resp.status_code == 200
    tinai_data = tinai_resp.get_json()
    assert tinai_data["success"] is True
    assert len(tinai_data["data"]) == 5

    stats_resp = client.get("/api/v1/corpus/statistics")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json()
    assert stats_data["success"] is True
    assert stats_data["data"]["total_sutras"] == 1610


def test_api_v1_health(client):
    """GET /api/v1/health returns system readiness status."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["api_version"] == "v1"
    assert "Tolkāppiyam" in data["data"]["corpus"]
