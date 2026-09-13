"""
Unit and integration tests for Dataset Ingestion and Validation module.
Verifies CSV loading, UTF-8 normalization, Tamil Unicode validation,
data profiling, schema validation, and REST API endpoints.
"""
import os
import pytest
from app import create_app
from ingestion.dataset_ingestion_service import DatasetIngestionService, ingestion_service


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


class TestDatasetIngestionService:
    """Direct unit tests for DatasetIngestionService."""

    def test_ontology_profiling(self):
        service = DatasetIngestionService()
        profile = service.load_and_profile_dataset("ontology")
        assert profile["dataset_name"] == "ontology"
        assert profile["rows"] == 1000
        assert profile["columns_count"] == 15
        assert profile["duplicates"] == 0
        assert "tamil_unicode_validation" in profile
        assert profile["tamil_unicode_validation"]["tamil_char_count"] > 0
        assert profile["validation_status"] == "valid"

    def test_query_mapping_profiling(self):
        service = DatasetIngestionService()
        profile = service.load_and_profile_dataset("query_mapping")
        assert profile["dataset_name"] == "query_mapping"
        assert profile["rows"] == 2640
        assert profile["columns_count"] == 10
        assert profile["duplicates"] == 0
        assert profile["validation_status"] == "valid"

    def test_validate_datasets_contract_schema(self):
        """
        Verifies exact contract schema:
        {
          "dataset_name": "...",
          "rows": 0,
          "columns": [],
          "missing_values": {},
          "duplicates": 0,
          "validation_status": "valid"
        }
        """
        service = DatasetIngestionService()
        results = service.validate_datasets("all")
        assert isinstance(results, list)
        assert len(results) == 2

        required_keys = {"dataset_name", "rows", "columns", "missing_values", "duplicates", "validation_status"}
        for item in results:
            assert required_keys.issubset(set(item.keys()))
            assert isinstance(item["dataset_name"], str)
            assert isinstance(item["rows"], int) and item["rows"] > 0
            assert isinstance(item["columns"], list) and len(item["columns"]) > 0
            assert isinstance(item["missing_values"], dict)
            assert isinstance(item["duplicates"], int)
            assert item["validation_status"] == "valid"

    def test_raw_and_processed_files_persisted(self):
        service = DatasetIngestionService()
        # Ingestion run persists raw and processed files
        service.load_and_profile_dataset("ontology")
        service.load_and_profile_dataset("query_mapping")

        assert os.path.exists(service.raw_dir)
        assert os.path.exists(service.processed_dir)
        assert os.path.exists(os.path.join(service.processed_dir, "ontology_processed.csv"))
        assert os.path.exists(os.path.join(service.processed_dir, "query_mapping_processed.csv"))
        assert os.path.exists(os.path.join(service.processed_dir, "dataset_metadata.json"))

    def test_get_statistics(self):
        service = DatasetIngestionService()
        stats = service.get_statistics()
        assert "datasets" in stats
        assert "referential_integrity" in stats
        assert "summary" in stats
        assert stats["datasets"]["ontology"]["total_rows"] == 1000
        assert stats["datasets"]["query_mapping"]["total_rows"] == 2640
        assert stats["referential_integrity"]["valid"] is True


class TestCorpusApiEndpoints:
    """Integration tests for corpus statistics and validation API endpoints."""

    def test_get_corpus_statistics_endpoint(self, client):
        response = client.get("/api/corpus/statistics")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        assert "datasets" in data
        assert "referential_integrity" in data
        assert "summary" in data
        assert data["datasets"]["ontology"]["total_rows"] == 1000
        assert data["datasets"]["query_mapping"]["total_rows"] == 2640
        assert data["referential_integrity"]["valid"] is True

    def test_post_corpus_validate_all(self, client):
        response = client.post("/api/corpus/validate", json={"dataset_name": "all"})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        assert isinstance(data, list)
        assert len(data) == 2

        # Check required contract schema fields
        for item in data:
            assert "dataset_name" in item
            assert "rows" in item
            assert "columns" in item
            assert "missing_values" in item
            assert "duplicates" in item
            assert item["validation_status"] == "valid"

    def test_post_corpus_validate_ontology_only(self, client):
        response = client.post("/api/corpus/validate", json={"dataset_name": "ontology"})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        assert data["dataset_name"] == "ontology"
        assert data["rows"] == 1000
        assert data["validation_status"] == "valid"

    def test_post_corpus_validate_query_mapping_only(self, client):
        response = client.post("/api/corpus/validate", json={"dataset_name": "query_mapping"})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

        data = json_data["data"]
        assert data["dataset_name"] == "query_mapping"
        assert data["rows"] == 2640
        assert data["validation_status"] == "valid"

    def test_post_corpus_validate_invalid_name(self, client):
        response = client.post("/api/corpus/validate", json={"dataset_name": "unknown_corpus"})
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "error" in json_data
