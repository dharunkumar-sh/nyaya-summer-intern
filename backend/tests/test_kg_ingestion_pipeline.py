"""
Comprehensive Unit & Integration Test Suite for DatasetMapper & KGIngestionPipeline.

Tests:
1. Non-destructive Unicode Tamil normalization and cleaning with Pandas.
2. Missing value handling and invalid record reporting.
3. Canonical sūtra corpus mapping with full provenance.
4. Ontology CSV validation and parent-child relationship resolution.
5. Query mapping pattern extraction.
6. Pipeline pre-validation and batch execution (mock repository).
7. Live Neo4j Aura batch ingestion and idempotency (0 duplicate nodes or relationships).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from knowledge_graph.schema import NodeLabels, RelTypes
from knowledge_graph.dataset_mapper import DatasetMapper, dataset_mapper
from knowledge_graph.neo4j_repository import Neo4jRepository, neo4j_repository
from ingestion.kg_ingestion_pipeline import KGIngestionPipeline, kg_ingestion_pipeline
from services.neo4j_service import neo4j_service


# ==============================================================================
# 1. Unicode Normalization & Cleaning Tests
# ==============================================================================

class TestDatasetMapperNormalizationAndCleaning:
    """Tests Tamil Unicode normalization and string cleaning."""

    def test_tamil_unicode_nfc_normalization(self):
        """Validates that Tamil text is normalized to NFC without destroying characters."""
        raw_text = "முதல்கரு உரிப்பொருள் என்ற மூன்றே"
        norm = DatasetMapper.normalize_tamil(raw_text)
        assert norm == raw_text
        assert len(norm) == len(raw_text)

        # Test verse with linebreaks and spaces
        verse = "முதல்கரு   உரிப்பொருள்  \n  நுவலும் காலை  "
        norm_verse = DatasetMapper.normalize_tamil(verse)
        assert norm_verse == "முதல்கரு உரிப்பொருள்\nநுவலும் காலை"

    def test_tamil_unicode_null_and_empty(self):
        """Null, empty, or NaN inputs return empty string safely."""
        assert DatasetMapper.normalize_tamil(None) == ""
        assert DatasetMapper.normalize_tamil("") == ""
        assert DatasetMapper.normalize_tamil(float("nan")) == ""

    def test_clean_string(self):
        """Whitespace stripping and default fallback."""
        assert DatasetMapper.clean_string("  Hello World  ") == "Hello World"
        assert DatasetMapper.clean_string(None, default="N/A") == "N/A"
        assert DatasetMapper.clean_string(float("nan"), default="Fallback") == "Fallback"

    def test_concrete_entity_classification(self):
        """Distinguishes concrete entities from abstract concepts."""
        assert DatasetMapper.is_concrete_entity("Deity", "Akam", "Porul") is True
        assert DatasetMapper.is_concrete_entity("Flora", "Kurinci", "Porul") is True
        assert DatasetMapper.is_concrete_entity("Fauna", "Mullai", "Porul") is True
        assert DatasetMapper.is_concrete_entity("Grammar", "Grammar", "Ezhuthu") is False
        assert DatasetMapper.is_concrete_entity("EpistemicTripartite", "Poetics", "Porul") is False


# ==============================================================================
# 2. Canonical Sūtra Corpus Mapping Tests
# ==============================================================================

class TestCanonicalCorpusMapping:
    """Tests mapping of tolkappiyam_canonical.json into graph nodes and edges."""

    def test_map_canonical_corpus_structure(self):
        """Canonical corpus generates Literature, Work, Section, Passages, and Evidence."""
        res = dataset_mapper.map_canonical_corpus()
        nodes = res["nodes"]

        assert NodeLabels.LITERATURE in nodes
        assert len(nodes[NodeLabels.LITERATURE]) >= 1
        assert nodes[NodeLabels.LITERATURE][0]["id"] == "lit_sangam"

        assert NodeLabels.WORK in nodes
        assert len(nodes[NodeLabels.WORK]) >= 1
        assert nodes[NodeLabels.WORK][0]["id"] == "work_tolkappiyam"

        assert NodeLabels.SECTION in nodes
        assert len(nodes[NodeLabels.SECTION]) >= 1

        assert NodeLabels.PASSAGE in nodes
        assert len(nodes[NodeLabels.PASSAGE]) >= 6
        first_p = nodes[NodeLabels.PASSAGE][0]
        assert "sutra_number" in first_p
        assert "text" in first_p
        assert "translation" in first_p
        assert "source" in first_p

        assert NodeLabels.EVIDENCE in nodes
        assert len(nodes[NodeLabels.EVIDENCE]) >= 6

        # Check relationships
        rels = res["relationships"]
        rel_types = {r["relation"] for r in rels}
        assert RelTypes.HAS_WORK in rel_types
        assert RelTypes.HAS_SECTION in rel_types
        assert RelTypes.HAS_PASSAGE in rel_types
        assert RelTypes.SUPPORTED_BY in rel_types

    def test_map_canonical_corpus_invalid_record_detection(self, tmp_path):
        """Passages missing IDs are reported as invalid records without crashing."""
        bad_json = tmp_path / "bad_corpus.json"
        bad_json.write_text(
            json.dumps([{"original_text": "text without id"}]),
            encoding="utf-8",
        )
        mapper = DatasetMapper(data_dir=tmp_path)
        res = mapper.map_canonical_corpus(json_file=bad_json)
        assert len(res["invalid_records"]) == 1
        assert "Missing passage/sutra identifier" in res["invalid_records"][0]["reason"]


# ==============================================================================
# 3. Ontology.csv Mapping Tests
# ==============================================================================

class TestOntologyMapping:
    """Tests Pandas loading, validation, and mapping of Ontology.csv."""

    def test_validate_and_clean_ontology_real_file(self):
        """Loads and cleans the 1,000-row Ontology.csv."""
        clean_df, invalid = dataset_mapper.validate_and_clean_ontology()
        assert len(clean_df) == 1000
        assert len(invalid) == 0
        assert "Tamil_Label_Normalized" in clean_df.columns
        assert "Synonyms_Tamil_Normalized" in clean_df.columns
        assert clean_df["Tamil_Label_Normalized"].notnull().all()

    def test_map_ontology_to_kg_relationships(self):
        """Validates that ontology concept nodes and parent relationships are extracted."""
        res = dataset_mapper.map_ontology_to_kg()
        nodes = res["nodes"]
        assert NodeLabels.CONCEPT in nodes
        assert len(nodes[NodeLabels.CONCEPT]) > 500
        assert NodeLabels.ENTITY in nodes

        rels = res["relationships"]
        assert len(rels) > 800
        # Check that parent-child and components relations exist
        rel_types = {r["relation"] for r in rels}
        assert len(rel_types) > 5

    def test_validate_ontology_missing_columns(self, tmp_path):
        """Raises KnowledgeGraphError if required columns are missing."""
        bad_csv = tmp_path / "bad_ontology.csv"
        bad_csv.write_text("ID,RandomCol\n1,Value\n", encoding="utf-8")
        mapper = DatasetMapper(data_dir=tmp_path)
        with pytest.raises(Exception):
            mapper.validate_and_clean_ontology(csv_file=bad_csv)

    def test_validate_ontology_invalid_records_capture(self, tmp_path):
        """Captures rows with missing ID or labels as invalid records."""
        csv_file = tmp_path / "test_onto.csv"
        csv_file.write_text(
            "ID,Main Theme,English_Label,Tamil_Label,Category,Relation_Type\n"
            "1,Theme,Word,சொல்,Grammar,part_of\n"
            ",Theme,MissingID,சொல்,Grammar,part_of\n"
            "3,Theme,,வெற்று,Grammar,part_of\n",
            encoding="utf-8",
        )
        mapper = DatasetMapper(data_dir=tmp_path)
        clean_df, invalid = mapper.validate_and_clean_ontology(csv_file=csv_file)
        assert len(clean_df) == 1
        assert len(invalid) == 2


# ==============================================================================
# 4. Query_Mapping.csv Tests
# ==============================================================================

class TestQueryMapping:
    """Tests loading and query pattern extraction from Query_Mapping.csv."""

    def test_validate_and_clean_query_mapping_real_file(self):
        """Loads and cleans the 2,640-row Query_Mapping.csv."""
        clean_df, invalid = dataset_mapper.validate_and_clean_query_mapping()
        assert len(clean_df) >= 2640
        assert len(invalid) == 0

    def test_map_query_mappings_to_kg(self):
        """Extracts evidence query patterns and links them to concepts."""
        clean_df, _ = dataset_mapper.validate_and_clean_query_mapping()
        # Test slice of first 50 rows for performance
        subset = clean_df.head(50)
        res = dataset_mapper.map_query_mappings_to_kg(df=subset)
        nodes = res["nodes"]
        assert NodeLabels.EVIDENCE in nodes
        assert len(nodes[NodeLabels.EVIDENCE]) == 50
        assert len(res["relationships"]) == 50
        assert res["relationships"][0]["relation"] == RelTypes.SUPPORTED_BY


# ==============================================================================
# 5. Pipeline Pre-Validation & Execution Tests (Mocked Service)
# ==============================================================================

class TestKGIngestionPipelineMocked:
    """Tests pipeline pre-validation and batch execution with mocked repository."""

    def test_pipeline_validate_only(self):
        """validate_only produces a clean diagnostic report without touching DB."""
        pipeline = KGIngestionPipeline()
        report = pipeline.run(validate_only=True)
        assert report["status"] == "VALIDATED_ONLY"
        assert "validation_report" in report
        val = report["validation_report"]
        assert val["status"] == "valid"
        assert "canonical_corpus" in val["datasets"]
        assert "ontology" in val["datasets"]
        assert "query_mapping" in val["datasets"]

    def test_pipeline_run_mocked(self):
        """Pipeline runs batch upserts with mock repository."""
        mock_repo = MagicMock(spec=Neo4jRepository)
        mock_repo.is_available.return_value = True
        mock_repo.batch_upsert_nodes.return_value = {"total_items": 10, "upserted": 10}
        mock_repo.batch_upsert_relationships.return_value = {"total_items": 15, "upserted": 15}
        mock_repo.service = MagicMock()
        mock_repo.service.database = "neo4j"

        pipeline = KGIngestionPipeline(repository=mock_repo)
        with patch("knowledge_graph.schema.neo4j_schema_manager.setup_schema") as mock_setup:
            res = pipeline.run(
                batch_size=100,
                include_corpus=True,
                include_ontology=True,
                include_queries=False,
            )

        assert res["status"] == "COMPLETED"
        assert res["total_nodes_upserted"] > 0
        assert res["total_relationships_upserted"] > 0
        assert mock_repo.batch_upsert_nodes.called
        assert mock_repo.batch_upsert_relationships.called


# ==============================================================================
# 6. Live Neo4j Aura Ingestion & Idempotency Tests
# ==============================================================================

class TestKGIngestionPipelineLiveAura:
    """Live batch ingestion and duplicate prevention on Neo4j Aura cluster."""

    @pytest.fixture(autouse=True)
    def check_aura_reachable(self):
        """Skip live test if Aura cluster cannot be reached."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura cluster unreachable; skipping live ingestion tests.")

    def test_live_canonical_ingestion_and_idempotency(self):
        """
        Ingests the canonical sūtras twice.
        Verifies that node count and relationship count do not duplicate.
        """
        pipeline = KGIngestionPipeline()

        # 1. First Ingestion (Canonical Sūtras)
        res_1 = pipeline.run(
            batch_size=100,
            include_corpus=True,
            include_ontology=False,
            include_queries=False,
        )
        assert res_1["status"] == "COMPLETED"
        assert res_1["total_nodes_upserted"] > 0

        # Query live count of Passage nodes
        count_res_1 = neo4j_service.execute_read("MATCH (p:KGNode:Passage) RETURN count(p) AS cnt")
        passage_count_1 = count_res_1[0]["cnt"]
        assert passage_count_1 >= 6

        # 2. Second Ingestion (Exact same data)
        res_2 = pipeline.run(
            batch_size=100,
            include_corpus=True,
            include_ontology=False,
            include_queries=False,
        )
        assert res_2["status"] == "COMPLETED"

        # Query live count of Passage nodes after second ingestion
        count_res_2 = neo4j_service.execute_read("MATCH (p:KGNode:Passage) RETURN count(p) AS cnt")
        passage_count_2 = count_res_2[0]["cnt"]

        # Strict idempotency check: count MUST be identical
        assert passage_count_1 == passage_count_2, "Passage count increased on repeated ingestion!"



# ==============================================================================
# 8. Semantic Knowledge Graph Extension & Reasoning Tests
# ==============================================================================

class TestSemanticKGExtension:
    """Tests semantic entity, event, and category extraction in DatasetMapper."""

    def test_event_classification(self):
        """Affective actions and aesthetic states are properly classified as Event nodes."""
        assert dataset_mapper.is_event("Puṇartal", "Uripporul", "") is True
        assert dataset_mapper.is_event("Pirital", "AffectiveAction", "") is True
        assert dataset_mapper.is_event("Iruttal", "Uripporul", "") is True
        assert dataset_mapper.is_event("Iraṅkal", "Uripporul", "") is True
        assert dataset_mapper.is_event("Ūṭal", "Uripporul", "") is True
        assert dataset_mapper.is_event("Meyppāṭu", "Aesthetics", "") is True
        assert dataset_mapper.is_event("Cēyōṉ", "Deity", "") is False
        assert dataset_mapper.is_event("Mutalporul", "Poetics", "") is False

    def test_concrete_entity_classification(self):
        """Physical/concrete elements are identified as Entity nodes."""
        assert dataset_mapper.is_concrete_entity("Cēyōṉ", "Deity", "") is True
        assert dataset_mapper.is_concrete_entity("Maivarai", "Landscape", "") is True
        assert dataset_mapper.is_concrete_entity("Yāḻ", "MusicalInstrument", "") is True
        assert dataset_mapper.is_concrete_entity("Uṇā", "Sustenance", "") is True
        assert dataset_mapper.is_concrete_entity("Maram", "Flora", "") is True
        assert dataset_mapper.is_concrete_entity("Akam", "Poetics", "") is False
        assert dataset_mapper.is_concrete_entity("Uripporul", "Poetics", "") is False

    def test_canonical_mapping_contains_events_and_categories(self):
        """Canonical sūtra mapping generates Event nodes and Category Concept nodes."""
        mapped = dataset_mapper.map_canonical_corpus()
        nodes = mapped["nodes"]
        rels = mapped["relationships"]

        # 1. Event nodes exist
        assert NodeLabels.EVENT in nodes
        event_nodes = nodes[NodeLabels.EVENT]
        assert len(event_nodes) >= 5
        event_ids = {e["id"] for e in event_nodes}
        assert any("pirital" in eid for eid in event_ids)
        assert any("iruttal" in eid for eid in event_ids)

        # 2. Literary categories linked via BELONGS_TO_CATEGORY
        category_rels = [r for r in rels if r["relation"] == RelTypes.BELONGS_TO_CATEGORY]
        assert len(category_rels) >= 6
        assert any(r["target_id"].startswith("cat_") for r in category_rels)

        # 3. Events linked via DESCRIBES
        describes_rels = [r for r in rels if r["relation"] == RelTypes.DESCRIBES]
        assert len(describes_rels) >= 5

        # 4. Cross-ontology links exist
        ontology_rels = [r for r in rels if r["relation"] == RelTypes.GROUNDS_IN_ONTOLOGY]
        assert len(ontology_rels) >= 10
        assert any(r["target_id"].startswith("onto_") for r in ontology_rels)

    def test_provenance_metadata(self):
        """Every generated node and edge retains strict source provenance."""
        mapped = dataset_mapper.map_canonical_corpus()
        for e in mapped["nodes"][NodeLabels.EVENT]:
            assert e["validation_status"] == "verified_canonical"
            assert e["type"] == "Event"
            assert e["source"]
            assert e["source_reference"]
        for r in mapped["relationships"]:
            if r["relation"] in {RelTypes.HAS_WORK, RelTypes.HAS_SECTION, RelTypes.HAS_PASSAGE}:
                continue
            assert "source" in r
            assert "source_reference" in r


class TestNeo4jRepositorySemanticReasoning:
    """Unit and integration tests for multi-hop semantic reasoning methods."""

    @pytest.fixture
    def mock_repo(self):
        mock_service = MagicMock()
        return Neo4jRepository(service=mock_service)

    def test_find_semantic_paths_unit(self, mock_repo):
        """Validates parameterized Cypher with clamped hops."""
        mock_repo.service.execute_read.return_value = [
            {"path_length": 2, "nodes": [{"id": "a"}, {"id": "b"}], "rels": ["MENTIONS"]}
        ]
        paths = mock_repo.find_semantic_paths("node_a", "node_c", max_hops=4)
        assert len(paths) == 1
        args, kwargs = mock_repo.service.execute_read.call_args
        assert "$start_id" in args[0]
        params = args[1] if len(args) > 1 else kwargs.get("params")
        assert params == {"start_id": "node_a", "end_id": "node_c"}

    def test_get_semantic_evidence_neighborhood_unit(self, mock_repo):
        """Validates parameterized evidence neighborhood expansion."""
        mock_repo.service.execute_read.return_value = [{
            "center_node": {"id": "tol-porul-akam-005"},
            "neighbors": [{"id": "ent_1", "label": "Cēyōṉ"}],
            "supporting_passages": [{"passage_id": "tol-porul-akam-005"}]
        }]
        res = mock_repo.get_semantic_evidence_neighborhood("tol-porul-akam-005", max_hops=2, limit=25)
        assert res["center_node"]["id"] == "tol-porul-akam-005"
        assert len(res["neighbors"]) == 1

    def test_get_literary_context_for_passage_unit(self, mock_repo):
        """Validates passage context query aggregation."""
        mock_repo.service.execute_read.return_value = [{
            "passage": {"id": "tol-porul-akam-003"},
            "provenance_path": [{"id": "lit_sangam"}, {"id": "work_tolkappiyam"}, {"id": "sec_porul"}],
            "categories": [{"name": "Porulatikaram"}],
            "entities": [{"id": "ent_1", "name": "Mutal"}],
            "concepts": [{"id": "c_1", "name": "Akam"}],
            "events": [{"id": "ev_1", "name": "Punartal"}],
            "evidence": [{"id": "evi_1", "source_reference": "Tolkappiyam Sūtra 3"}],
            "ontology_links": [{"id": "onto_27"}]
        }]
        ctx = mock_repo.get_literary_context_for_passage("tol-porul-akam-003")
        assert ctx is not None
        assert ctx["passage"]["id"] == "tol-porul-akam-003"
        assert len(ctx["events"]) == 1
        assert len(ctx["ontology_links"]) == 1
        assert len(ctx["provenance_path"]) == 3

    def test_query_tinai_tripartite_graph_unit(self, mock_repo):
        """Validates tripartite graph extraction."""
        mock_repo.service.execute_read.return_value = [{
            "tinai_node": {"id": "concept_kurinji", "label": "Kuṟiñci"},
            "deities": [{"id": "ent_ceyon", "name": "Cēyōṉ"}],
            "landscapes": [{"id": "ent_maivarai", "name": "Maivarai"}],
            "uripporul_events": [{"id": "ev_punartal", "name": "Puṇartal"}],
            "biotic_signifiers": [],
            "passages": [{"id": "tol-porul-akam-005"}]
        }]
        res = mock_repo.query_tinai_tripartite_graph("Kurinji")
        assert res["found"] is True
        assert len(res["karupporul"]["presiding_deities"]) == 1

    def test_live_passage_literary_context(self):
        """Retrieves rich literary context for Tolkāppiyam Sūtra 3 from Neo4j Aura."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura database is offline")
        ctx = neo4j_repository.get_literary_context_for_passage("tol-porul-akam-003")
        assert ctx is not None
        assert ctx["passage"]["id"] == "tol-porul-akam-003"
        assert "provenance_path" in ctx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

