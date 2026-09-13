"""
Knowledge Graph Ingestion Pipeline.

Orchestrates:
1. Pre-validation of raw and processed datasets (reporting invalid records).
2. Non-destructive Unicode Tamil normalization and cleaning with Pandas.
3. Mapping records into canonical Neo4j node labels and controlled relationship types.
4. Idempotent batch loading into Neo4j Aura via Neo4jRepository.
5. Preservation of classical source provenance (Tolkāppiyam, atikāram, iyal, sūtra).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from core.logger import logger
from core.exceptions import KnowledgeGraphError
from knowledge_graph.schema import NodeLabels, RelTypes, neo4j_schema_manager
from knowledge_graph.neo4j_repository import Neo4jRepository, neo4j_repository
from knowledge_graph.dataset_mapper import DatasetMapper, dataset_mapper


class KGIngestionPipeline:
    """
    End-to-end ingestion pipeline validating datasets and loading them
    into Neo4j Aura idempotently in high-throughput batches.
    """

    def __init__(
        self,
        repository: Optional[Neo4jRepository] = None,
        mapper: Optional[DatasetMapper] = None,
    ):
        self.repository = repository or neo4j_repository
        self.mapper = mapper or dataset_mapper

    def run(
        self,
        batch_size: int = 250,
        validate_only: bool = False,
        include_corpus: bool = True,
        include_ontology: bool = True,
        include_queries: bool = False,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the ingestion pipeline:
        1. Pre-validation of datasets.
        2. Extraction and mapping to KG structures.
        3. Batch upserts into Neo4j Aura.
        """
        start_time = time.perf_counter()
        logger.info("Starting Knowledge Graph Ingestion Pipeline...")

        # 1. Pre-validation Step
        logger.info("Step 1/3: Validating datasets and Unicode integrity...")
        validation_report = self.mapper.validate_all_datasets()
        logger.info(f"Validation finished with status: {validation_report['status']}")

        if validate_only:
            duration = round(time.perf_counter() - start_time, 2)
            return {
                "status": "VALIDATED_ONLY",
                "duration_seconds": duration,
                "validation_report": validation_report,
            }

        # Check database connectivity
        if not self.repository.is_available():
            raise KnowledgeGraphError(
                "Cannot proceed with ingestion: Neo4j Aura database is not connected or configured."
            )

        # Ensure schema constraints and indexes are established first
        logger.info("Ensuring Neo4j uniqueness constraints and indexes are active...")
        neo4j_schema_manager.setup_schema(database=database)

        # 2. Extract & Map Data
        logger.info("Step 2/3: Transforming datasets into KG nodes and relationships...")
        all_nodes: Dict[str, List[Dict[str, Any]]] = {}
        all_relationships: List[Dict[str, Any]] = []
        total_invalid = 0

        # A. Canonical Sūtra Corpus
        if include_corpus:
            corpus_mapped = self.mapper.map_canonical_corpus()
            for label, nodes in corpus_mapped["nodes"].items():
                all_nodes.setdefault(label, []).extend(nodes)
            all_relationships.extend(corpus_mapped["relationships"])
            total_invalid += len(corpus_mapped["invalid_records"])

        # B. Ontology Concepts & Entities (1,000 items)
        if include_ontology:
            onto_mapped = self.mapper.map_ontology_to_kg()
            for label, nodes in onto_mapped["nodes"].items():
                all_nodes.setdefault(label, []).extend(nodes)
            all_relationships.extend(onto_mapped["relationships"])
            total_invalid += len(onto_mapped["invalid_records"])

        # C. Query Mapping Patterns (2,640 items, optional/extended)
        if include_queries:
            qm_mapped = self.mapper.map_query_mappings_to_kg()
            for label, nodes in qm_mapped["nodes"].items():
                all_nodes.setdefault(label, []).extend(nodes)
            all_relationships.extend(qm_mapped["relationships"])
            total_invalid += len(qm_mapped["invalid_records"])

        # 3. Batch Loading into Neo4j Aura
        logger.info("Step 3/3: Ingesting nodes and relationships in batches...")
        nodes_upserted_by_label: Dict[str, int] = {}
        total_nodes = 0

        for label, nodes in all_nodes.items():
            res = self.repository.batch_upsert_nodes(
                label, nodes, batch_size=batch_size, database=database
            )
            nodes_upserted_by_label[label] = res["upserted"]
            total_nodes += res["upserted"]

        # Batch upsert relationships
        rel_res = self.repository.batch_upsert_relationships(
            all_relationships, batch_size=batch_size, database=database
        )
        total_rels = rel_res["upserted"]

        duration = round(time.perf_counter() - start_time, 2)
        logger.info(
            f"Ingestion completed in {duration}s: {total_nodes} nodes and {total_rels} relationships loaded."
        )

        return {
            "status": "COMPLETED",
            "duration_seconds": duration,
            "total_nodes_upserted": total_nodes,
            "nodes_by_label": nodes_upserted_by_label,
            "total_relationships_upserted": total_rels,
            "invalid_records_count": total_invalid,
            "validation_report": validation_report,
            "database": database or self.repository.service.database,
        }


# Singleton pipeline instance
kg_ingestion_pipeline = KGIngestionPipeline()


def main():
    """Standalone CLI entry point for running or testing ingestion."""
    parser = argparse.ArgumentParser(description="Knowledge Graph Ingestion Pipeline CLI")
    parser.add_argument("--validate-only", action="store_true", help="Only validate datasets and report status")
    parser.add_argument("--run", action="store_true", help="Execute full ingestion into Neo4j Aura")
    parser.add_argument("--batch-size", type=int, default=250, help="Batch size for UNWIND transactions (default: 250)")
    parser.add_argument("--include-queries", action="store_true", help="Also ingest 2640 query mapping patterns")
    args = parser.parse_args()

    pipeline = KGIngestionPipeline()

    if args.validate_only:
        res = pipeline.run(validate_only=True)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.run:
        res = pipeline.run(
            batch_size=args.batch_size,
            include_queries=args.include_queries,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        # Default action: validate only
        res = pipeline.run(validate_only=True)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
