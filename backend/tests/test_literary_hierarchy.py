"""
Unit & Integration Test Suite for Hierarchical Literary Structure in Neo4j.

Tests:
1. Canonical hierarchy mapping: Literature (L0) -> Work (L1) -> Section (L2, Book & Chapter) -> Passage (L3).
2. Dual Tamil text storage: original source text vs normalized searchable text.
3. Metadata retention: sutra/verse numbers, section/chapter names, source references, corpus info.
4. Deterministic provenance traversal: Passage back to exact classical source.
5. Repository methods:
   - get_passage_by_id
   - get_passages_by_work
   - get_passages_by_chapter
   - get_passage_by_verse
   - get_passage_by_source_id
   - get_source_hierarchy_for_passage
6. Live Neo4j Aura verification.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from knowledge_graph.schema import NodeLabels, RelTypes
from knowledge_graph.dataset_mapper import DatasetMapper, dataset_mapper
from knowledge_graph.neo4j_repository import Neo4jRepository, neo4j_repository
from ingestion.kg_ingestion_pipeline import KGIngestionPipeline
from services.neo4j_service import neo4j_service


# ==============================================================================
# 1. Literary Hierarchy Mapping & Dual Text Storage Tests
# ==============================================================================

class TestLiteraryHierarchyMapping:
    """Tests the canonical mapping of the classical Tamil hierarchy."""

    def test_multi_tier_hierarchy_nodes(self):
        """Validates that Literature, Work, Book Sections, and Chapter Sections are extracted."""
        mapped = dataset_mapper.map_canonical_corpus()
        nodes = mapped["nodes"]

        # Literature (L0)
        lits = nodes[NodeLabels.LITERATURE]
        assert len(lits) >= 1
        assert lits[0]["id"] == "lit_sangam"
        assert "Sangam Literature" in lits[0]["label"]

        # Work (L1)
        works = nodes[NodeLabels.WORK]
        assert len(works) >= 1
        assert works[0]["id"] == "work_tolkappiyam"
        assert "Tolkāppiyam" in works[0]["label"]

        # Section (L2): Both Books and Chapters
        sections = nodes[NodeLabels.SECTION]
        assert len(sections) >= 3
        sec_types = {s["metadata"].get("section_type") for s in sections}
        assert "Book" in sec_types
        assert "Chapter" in sec_types

        # Passages (L3)
        passages = nodes[NodeLabels.PASSAGE]
        assert len(passages) >= 6

    def test_dual_text_fields_and_metadata_preservation(self):
        """Validates that both raw and normalized Tamil texts and verse numbers are preserved."""
        mapped = dataset_mapper.map_canonical_corpus()
        passages = mapped["nodes"][NodeLabels.PASSAGE]
        first_p = passages[0]

        # Verify dual text fields
        assert "original_text" in first_p
        assert "normalized_text" in first_p
        assert len(first_p["original_text"]) > 0
        assert len(first_p["normalized_text"]) > 0
        assert first_p["text"] == first_p["normalized_text"]

        # Verify identifiers and numbering
        assert first_p["sutra_number"] == 3
        assert first_p["verse_number"] == 3
        assert first_p["passage_number"] == 3
        assert first_p["work_name"] == "Tolkāppiyam"
        assert first_p["section_name"] == "Poruḷatikāram"
        assert first_p["chapter_name"] == "Akattiṇaiyiyal"
        assert "source_reference" in first_p
        assert first_p["corpus_info"] == "Classical Tamil Sangam Corpus"

    def test_deterministic_traversal_relationships(self):
        """Validates deterministic relationship chains: HAS_WORK, HAS_SECTION, HAS_PASSAGE."""
        mapped = dataset_mapper.map_canonical_corpus()
        rels = mapped["relationships"]
        rel_types = {r["relation"] for r in rels}

        assert RelTypes.HAS_WORK in rel_types
        assert RelTypes.HAS_SECTION in rel_types
        assert RelTypes.HAS_PASSAGE in rel_types

        # Verify parent-child links
        has_work_edges = [r for r in rels if r["relation"] == RelTypes.HAS_WORK]
        assert any(r["source_id"] == "lit_sangam" and r["target_id"] == "work_tolkappiyam" for r in has_work_edges)

        has_section_edges = [r for r in rels if r["relation"] == RelTypes.HAS_SECTION]
        assert any(r["source_id"] == "work_tolkappiyam" for r in has_section_edges)

        has_passage_edges = [r for r in rels if r["relation"] == RelTypes.HAS_PASSAGE]
        assert any(r["target_id"] == "tol-porul-akam-003" for r in has_passage_edges)


# ==============================================================================
# 2. Neo4j Repository Retrieval Methods Tests (Mocked Service)
# ==============================================================================

class TestNeo4jRepositoryLiteraryQueries:
    """Tests the new repository query methods with mocked Neo4jService."""

    @pytest.fixture
    def mock_service(self):
        svc = MagicMock()
        svc.get_driver.return_value = MagicMock()
        return svc

    @pytest.fixture
    def repo(self, mock_service):
        return Neo4jRepository(service=mock_service)

    def test_get_passages_by_work(self, repo, mock_service):
        mock_service.execute_read.return_value = [
            {"passage": {"id": "tol-porul-akam-003", "sutra_number": 3, "work_name": "Tolkāppiyam"}},
            {"passage": {"id": "tol-porul-akam-004", "sutra_number": 4, "work_name": "Tolkāppiyam"}},
        ]
        results = repo.get_passages_by_work("Tolkāppiyam", limit=10)
        assert len(results) == 2
        assert results[0]["id"] == "tol-porul-akam-003"
        call_args = mock_service.execute_read.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MATCH (w:KGNode:Work)" in query
        assert "HAS_SECTION" in query
        assert params["work"] == "Tolkāppiyam"

    def test_get_passages_by_chapter(self, repo, mock_service):
        mock_service.execute_read.return_value = [
            {"passage": {"id": "tol-porul-akam-003", "chapter_name": "Akattiṇaiyiyal"}}
        ]
        results = repo.get_passages_by_chapter("Akattiṇaiyiyal", work_name_or_id="Tolkāppiyam")
        assert len(results) == 1
        assert results[0]["chapter_name"] == "Akattiṇaiyiyal"
        call_args = mock_service.execute_read.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "MATCH (sec:KGNode:Section)" in query
        assert params["chapter"] == "Akattiṇaiyiyal"

    def test_get_passage_by_verse(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "passage": {
                "id": "tol-porul-akam-003",
                "sutra_number": 3,
                "verse_number": 3,
                "text": "முதல்கரு உரிப்பொருள்",
            }
        }]
        res = repo.get_passage_by_verse(3, chapter="Akattiṇaiyiyal", work="Tolkāppiyam")
        assert res is not None
        assert res["id"] == "tol-porul-akam-003"
        assert res["verse_number"] == 3
        call_args = mock_service.execute_read.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "p.sutra_number = $verse_num" in query
        assert params["verse_num"] == 3

    def test_get_passage_by_source_id(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "passage": {
                "id": "tol-porul-akam-003",
                "source_id": "tol-porul-akam-003",
                "source_reference": "Tolkāppiyam Poruḷatikāram Akattiṇaiyiyal Sūtra 3",
            }
        }]
        res = repo.get_passage_by_source_id("tol-porul-akam-003")
        assert res is not None
        assert res["source_id"] == "tol-porul-akam-003"
        call_args = mock_service.execute_read.call_args[0]
        query, params = call_args[0], call_args[1]
        assert "p.source_id = $source_id" in query
        assert params["source_id"] == "tol-porul-akam-003"

    def test_get_source_hierarchy_for_passage(self, repo, mock_service):
        mock_service.execute_read.return_value = [{
            "passage_id": "tol-porul-akam-003",
            "passage_label": "Sūtra 3",
            "sutra_number": 3,
            "verse_number": 3,
            "original_text": "முதல்கரு உரிப்பொருள்",
            "normalized_text": "முதல்கரு உரிப்பொருள்",
            "work_name": "Tolkāppiyam",
            "section_name": "Poruḷatikāram",
            "chapter_name": "Akattiṇaiyiyal",
            "provenance_path": [
                {"id": "lit_sangam", "label": "Sangam Literature", "type": "Literature"},
                {"id": "work_tolkappiyam", "label": "Tolkāppiyam", "type": "Work"},
                {"id": "sec_book_porul", "label": "Poruḷatikāram", "type": "Section"},
                {"id": "sec_chap_porul_akattinai", "label": "Akattiṇaiyiyal", "type": "Section"},
                {"id": "tol-porul-akam-003", "label": "Sūtra 3", "type": "Passage"},
            ],
            "relationship_types": ["HAS_WORK", "HAS_SECTION", "HAS_SECTION", "HAS_PASSAGE"],
        }]
        res = repo.get_source_hierarchy_for_passage("tol-porul-akam-003")
        assert res is not None
        assert res["passage_id"] == "tol-porul-akam-003"
        assert len(res["provenance_path"]) == 5
        assert res["provenance_path"][0]["id"] == "lit_sangam"
        assert res["provenance_path"][1]["id"] == "work_tolkappiyam"
        assert "HAS_PASSAGE" in res["relationship_types"]


# ==============================================================================
# 3. Live Neo4j Aura Literary Structure Tests
# ==============================================================================

class TestNeo4jRepositoryLiteraryLiveAura:
    """Live verification of hierarchical structure against Neo4j Aura cluster."""

    @pytest.fixture(autouse=True)
    def check_aura_reachable(self):
        """Skip live test if Aura cluster cannot be reached."""
        if not neo4j_service.is_connected():
            pytest.skip("Neo4j Aura cluster unreachable; skipping live literary tests.")

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def ingest_canonical_corpus_live(cls):
        """Ensure canonical corpus is ingested with updated hierarchy."""
        pipeline = KGIngestionPipeline()
        pipeline.run(
            batch_size=100,
            include_corpus=True,
            include_ontology=False,
            include_queries=False,
        )

    def test_live_passage_retrieval_by_work(self):
        """Retrieves passages under Tolkāppiyam from live Aura."""
        passages = neo4j_repository.get_passages_by_work("Tolkāppiyam", limit=10)
        assert len(passages) >= 6
        first = passages[0]
        assert "sutra_number" in first or "verse_number" in first
        assert "text" in first

    def test_live_passage_retrieval_by_chapter(self):
        """Retrieves passages under Akattiṇaiyiyal chapter from live Aura."""
        passages = neo4j_repository.get_passages_by_chapter("Akattiṇaiyiyal", limit=10)
        assert len(passages) >= 1

    def test_live_passage_retrieval_by_verse(self):
        """Retrieves sūtra 3 by verse number from live Aura."""
        p = neo4j_repository.get_passage_by_verse(3)
        assert p is not None
        assert p["id"] == "tol-porul-akam-003"
        assert "முதல்கரு" in p.get("text", "") or "முதல்கரு" in p.get("original_text", "")

    def test_live_passage_retrieval_by_source_id(self):
        """Retrieves passage by source ID 'tol-porul-akam-003' from live Aura."""
        p = neo4j_repository.get_passage_by_source_id("tol-porul-akam-003")
        assert p is not None
        assert p["id"] == "tol-porul-akam-003"

    def test_live_source_hierarchy_traversal(self):
        """Verifies deterministic traversal from passage back to literature in live Aura."""
        res = neo4j_repository.get_source_hierarchy_for_passage("tol-porul-akam-003")
        assert res is not None
        assert res["passage_id"] == "tol-porul-akam-003"
        # Provenance path must contain at least Literature, Work, Section, Passage
        prov = res.get("provenance_path", [])
        assert len(prov) >= 3
        types = {n.get("type") for n in prov}
        assert "Literature" in types
        assert "Work" in types
        assert "Passage" in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
