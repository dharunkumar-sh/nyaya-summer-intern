"""
Passage Embedding Pipeline for Classical Tamil Literature Knowledge Graph.

Coordinates:
1. Configurable multilingual embedding provider and model selection (SentenceTransformers, DenseNgram fallback).
2. Strict validation and skipping of empty, whitespace-only, or invalid passages.
3. Deterministic passage ID resolution guaranteeing idempotent regeneration without duplicates.
4. Passage text normalization with TamilNormalizer while strictly preserving original text, translation, and metadata.
5. Chunked batching with automatic retry and exponential backoff.
6. Storing embeddings with Passage nodes in Neo4j Aura (with vector index creation) and local .npz cache.
"""
from __future__ import annotations

import re
import time
import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from config import Config, Neo4jConfig
from core.logger import logger
from core.exceptions import KnowledgeGraphError
from preprocessing.tamil_normalizer import TamilNormalizer
from ingestion.corpus_loader import corpus_loader
from knowledge_graph.neo4j_repository import neo4j_repository, Neo4jRepository
from knowledge_graph.graph_builder import kg_instance
from .embeddings import SentenceTransformerEmbeddingGenerator, DenseNgramEmbeddingGenerator


# =============================================================================
# Pipeline Data Models
# =============================================================================

@dataclass
class ValidatedPassage:
    """A verified, validated literary passage record prepared for vectorization."""
    passage_id: str
    original_text: str
    normalized_text: str
    embedding_input_text: str
    translation: str = ""
    transliteration: str = ""
    sutra_number: Optional[int] = None
    section: str = ""
    chapter: str = ""
    tinai: str = "General"
    source: str = "Tolkāppiyam"
    source_reference: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SkippedPassage:
    """Diagnostics for an invalid or empty passage omitted from the pipeline."""
    raw_id: Optional[str]
    reason: str
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineReport:
    """Comprehensive execution report of the passage embedding pipeline run."""
    status: str
    total_input: int
    valid_passages: int
    skipped_passages: int
    skipped_details: List[Dict[str, Any]]
    batch_count: int
    batch_size: int
    embedding_model: str
    embedding_provider: str
    vector_dimension: int
    neo4j_updated: int
    neo4j_index_status: str
    local_cache_path: Optional[str]
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Passage Embedding Pipeline Service
# =============================================================================

class PassageEmbeddingPipeline:
    """
    Production-grade batch embedding pipeline for literary Passage nodes.
    Supports configurable models, deterministic IDs, Neo4j vector indexing,
    and automatic retries with exponential backoff.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        vector_dim: Optional[int] = None,
        batch_size: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[float] = None,
        neo4j_repo: Optional[Neo4jRepository] = None,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        self.model_name = model_name or Config.EMBEDDING_MODEL_NAME
        self.provider = (provider or Config.EMBEDDING_PROVIDER).lower()
        self.vector_dim = vector_dim or Config.EMBEDDING_VECTOR_DIM
        self.batch_size = batch_size or Config.EMBEDDING_BATCH_SIZE
        self.max_retries = max_retries or Config.EMBEDDING_MAX_RETRIES
        self.retry_backoff = retry_backoff or Config.EMBEDDING_RETRY_BACKOFF

        self._neo4j_repo = neo4j_repo
        base_dir = Path(__file__).resolve().parent.parent
        self.cache_dir = Path(cache_dir) if cache_dir else base_dir / "data" / "processed"
        self.npz_path = self.cache_dir / "passage_embeddings.npz"
        self.manifest_path = self.cache_dir / "semantic_passage_manifest.json"

        # Initialize the configured embedding generator
        self._init_encoder()

    def _init_encoder(self) -> None:
        """Initializes the configured embedding generator."""
        if self.provider in ("sentence-transformers", "huggingface"):
            self.encoder = SentenceTransformerEmbeddingGenerator(
                model_name=self.model_name,
                fallback_dim=self.vector_dim,
            )
        elif self.provider in ("dense-ngram", "fallback"):
            self.encoder = DenseNgramEmbeddingGenerator(fixed_dim=self.vector_dim)
        else:
            logger.warning(
                f"Unknown embedding provider '{self.provider}'. Defaulting to SentenceTransformers."
            )
            self.encoder = SentenceTransformerEmbeddingGenerator(
                model_name=self.model_name,
                fallback_dim=self.vector_dim,
            )

    @property
    def repo(self) -> Neo4jRepository:
        if self._neo4j_repo is None:
            self._neo4j_repo = neo4j_repository
        return self._neo4j_repo

    # -------------------------------------------------------------------------
    # 1. Validation & Preprocessing
    # -------------------------------------------------------------------------

    def validate_passage(self, raw: Dict[str, Any]) -> Tuple[Optional[ValidatedPassage], Optional[SkippedPassage]]:
        """
        Validates a raw passage record.
        Rejects empty passages, whitespace-only text, null records, or invalid IDs.
        Constructs normalized text while strictly preserving original text and source metadata.
        """
        if not raw or not isinstance(raw, dict):
            return None, SkippedPassage(raw_id=None, reason="Record is null or not a dictionary")

        # 1. Extract and validate passage ID
        raw_id = raw.get("id") or raw.get("passage_id")
        sutra_num = raw.get("sutra_number")
        if sutra_num is not None:
            try:
                sutra_num = int(sutra_num)
            except (ValueError, TypeError):
                sutra_num = None

        passage_id = self._generate_deterministic_id(raw_id=raw_id, sutra_num=sutra_num, metadata=raw)
        if not passage_id:
            return None, SkippedPassage(raw_id=raw_id, reason="Missing or indeterminate passage ID")

        # 2. Extract and validate text content
        raw_text = (
            raw.get("tamil_text")
            or raw.get("original_text")
            or raw.get("text")
            or ""
        )
        if not isinstance(raw_text, str) or not raw_text.strip():
            return None, SkippedPassage(
                raw_id=passage_id,
                reason="Passage text is empty or contains only whitespace",
                snippet=str(raw_text)[:30],
            )

        cleaned_raw = raw_text.strip()
        if len(cleaned_raw) < 3:
            return None, SkippedPassage(
                raw_id=passage_id,
                reason=f"Passage text too short ({len(cleaned_raw)} chars)",
                snippet=cleaned_raw,
            )

        # 3. Unicode NFC Normalization for vector embedding
        normalized_text = TamilNormalizer.normalize(cleaned_raw)
        if not normalized_text.strip():
            return None, SkippedPassage(
                raw_id=passage_id,
                reason="Passage text empty after Unicode normalization",
                snippet=cleaned_raw,
            )

        # 4. Extract translations and source metadata
        translation = str(raw.get("english_translation") or raw.get("translation") or "").strip()
        transliteration = str(raw.get("transliteration") or "").strip()
        section = str(raw.get("atikaram") or raw.get("section") or raw.get("work_name") or "Poruḷatikāram").strip()
        chapter = str(raw.get("iyal") or raw.get("chapter_name") or raw.get("chapter") or "").strip()
        tinai = str(raw.get("tinai") or "General").strip()
        source = str(raw.get("source") or "Tolkāppiyam").strip()
        source_ref = str(
            raw.get("source_reference")
            or f"{source}, {section}{f', {chapter}' if chapter else ''}, Sūtra {sutra_num or passage_id.split('-')[-1]}"
        ).strip()

        # Build dense embedding input text (combining normalized Tamil text with English translation for cross-lingual alignment)
        embedding_input = normalized_text
        if translation:
            embedding_input = f"{normalized_text} [SEP] {translation}"

        # Preserved metadata dict (excluding duplicate raw content)
        meta = dict(raw.get("metadata") or {})
        for k in ("category", "entities", "triples", "nyaya_mapping", "corpus_info"):
            if k in raw and k not in meta:
                meta[k] = raw[k]

        validated = ValidatedPassage(
            passage_id=passage_id,
            original_text=cleaned_raw,
            normalized_text=normalized_text,
            embedding_input_text=embedding_input,
            translation=translation,
            transliteration=transliteration,
            sutra_number=sutra_num,
            section=section,
            chapter=chapter,
            tinai=tinai,
            source=source,
            source_reference=source_ref,
            metadata=meta,
        )

        return validated, None

    def _generate_deterministic_id(
        self,
        raw_id: Optional[Any],
        sutra_num: Optional[int],
        metadata: Dict[str, Any],
    ) -> Optional[str]:
        """Generates a stable, canonical deterministic passage ID."""
        if raw_id and isinstance(raw_id, str) and raw_id.strip():
            clean_id = raw_id.strip().lower()
            if clean_id.startswith("tol-porul-"):
                return clean_id
            if re.match(r"^s[uū]tra[-_]?\d+$", clean_id):
                num = re.search(r"\d+", clean_id).group()
                return f"tol-porul-akam-{int(num):03d}"

        # Derive from chapter and sutra number
        chapter = str(metadata.get("iyal") or metadata.get("chapter") or "").lower()
        if "mey" in chapter or "மெய்" in chapter:
            num = sutra_num if sutra_num is not None else 1
            return f"tol-porul-mey-{num:03d}"
        if sutra_num is not None:
            return f"tol-porul-akam-{sutra_num:03d}"

        if raw_id:
            return str(raw_id).strip().lower()

        # Deterministic SHA-256 hash fallback
        text = str(metadata.get("tamil_text") or metadata.get("text") or "")
        if text.strip():
            h = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]
            return f"tol-passage-{h}"

        return None

    # -------------------------------------------------------------------------
    # 2. Batch Embedding Generation with Exponential Backoff
    # -------------------------------------------------------------------------

    def generate_embeddings_with_retry(
        self,
        passages: List[ValidatedPassage],
    ) -> np.ndarray:
        """
        Generates dense vector embeddings for validated passages in batches
        with automatic retry and exponential backoff.
        """
        if not passages:
            return np.empty((0, self.vector_dim), dtype=np.float32)

        input_texts = [p.embedding_input_text for p in passages]
        all_embeddings: List[np.ndarray] = []

        total_batches = (len(input_texts) + self.batch_size - 1) // self.batch_size
        logger.info(
            f"PassageEmbeddingPipeline: Encoding {len(input_texts)} passages in {total_batches} batches "
            f"(batch_size={self.batch_size}, model={self.model_name})"
        )

        for batch_idx in range(total_batches):
            start = batch_idx * self.batch_size
            end = min(start + self.batch_size, len(input_texts))
            chunk = input_texts[start:end]

            batch_vecs = self._encode_chunk_with_backoff(chunk, batch_idx + 1, total_batches)
            all_embeddings.append(batch_vecs)

        combined = np.vstack(all_embeddings).astype(np.float32)
        return combined

    def _encode_chunk_with_backoff(
        self,
        texts: List[str],
        batch_num: int,
        total_batches: int,
    ) -> np.ndarray:
        """Encodes a single chunk of texts, retrying on transient errors with backoff."""
        attempt = 0
        current_delay = self.retry_backoff

        while attempt < self.max_retries:
            try:
                # Ensure fallback encoder is fitted if using n-gram generator
                if isinstance(self.encoder, DenseNgramEmbeddingGenerator) and not self.encoder.is_fitted:
                    self.encoder.fit(texts)

                vecs = self.encoder.encode(texts)
                return vecs
            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Batch {batch_num}/{total_batches} encoding attempt {attempt} failed: {e}. "
                    f"Retrying in {current_delay:.2f}s..."
                )
                if attempt >= self.max_retries:
                    logger.error(
                        f"Batch {batch_num}/{total_batches} failed after {self.max_retries} attempts: {e}."
                    )
                    raise KnowledgeGraphError(f"Embedding generation failed: {e}") from e
                time.sleep(current_delay)
                current_delay *= 2.0

        raise KnowledgeGraphError(f"Batch {batch_num} failed all retries.")

    # -------------------------------------------------------------------------
    # 3. Pipeline Execution & Storage Orchestration
    # -------------------------------------------------------------------------

    def run_pipeline(
        self,
        passages: Optional[List[Dict[str, Any]]] = None,
        update_neo4j: bool = True,
        save_local_cache: bool = True,
    ) -> PipelineReport:
        """
        Executes the end-to-end passage embedding pipeline:
        1. Validates input passages (filters empty/invalid records).
        2. Generates dense embeddings in batches with exponential backoff.
        3. Idempotently sets embeddings on Neo4j Passage nodes and verifies vector index.
        4. Saves local .npz and JSON manifest cache.
        5. Returns a structured PipelineReport with execution metrics.
        """
        t0 = time.perf_counter()

        # 1. Load source passages if not supplied
        raw_passages = passages if passages is not None else self._load_canonical_passages()
        total_input = len(raw_passages)

        # 2. Validation & Preprocessing
        valid_passages: List[ValidatedPassage] = []
        skipped_passages: List[SkippedPassage] = []

        for item in raw_passages:
            val, skip = self.validate_passage(item)
            if val is not None:
                valid_passages.append(val)
            elif skip is not None:
                skipped_passages.append(skip)

        logger.info(
            f"PassageEmbeddingPipeline: {len(valid_passages)} valid passages, "
            f"{len(skipped_passages)} skipped/invalid"
        )

        if not valid_passages:
            logger.warning("No valid passages found for embedding pipeline execution.")
            return PipelineReport(
                status="empty",
                total_input=total_input,
                valid_passages=0,
                skipped_passages=len(skipped_passages),
                skipped_details=[s.to_dict() for s in skipped_passages],
                batch_count=0,
                batch_size=self.batch_size,
                embedding_model=self.model_name,
                embedding_provider=self.provider,
                vector_dimension=self.vector_dim,
                neo4j_updated=0,
                neo4j_index_status="skipped",
                local_cache_path=None,
                elapsed_seconds=round(time.perf_counter() - t0, 3),
            )

        # 3. Batch Vector Encoding with Retry
        vectors = self.generate_embeddings_with_retry(valid_passages)
        actual_dim = int(vectors.shape[1]) if vectors.ndim == 2 else self.vector_dim

        # 4. Neo4j Aura Vector Storage & Index Registration
        neo4j_updated = 0
        neo4j_index_status = "disabled"

        if update_neo4j and self.repo.is_available():
            try:
                # Ensure Neo4j vector index exists with exact model dimensions
                idx_res = self.repo.ensure_passage_vector_index(
                    index_name=Neo4jConfig.VECTOR_INDEX_NAME,
                    dimensions=actual_dim,
                    similarity_function=Neo4jConfig.VECTOR_SIMILARITY_FUNCTION,
                    model_name=self.model_name,
                    encoder=self.encoder,
                )
                neo4j_index_status = idx_res.get("status", "ready")

                # Prepare batch items for Neo4j UNWIND
                neo4j_items = []
                for i, p in enumerate(valid_passages):
                    neo4j_items.append({
                        "passage_id": p.passage_id,
                        "embedding": vectors[i].tolist(),
                        "embedding_model": self.model_name,
                        "embedding_dim": actual_dim,
                    })

                upsert_res = self.repo.batch_set_passage_embeddings(
                    items=neo4j_items,
                    batch_size=self.batch_size,
                )
                neo4j_updated = upsert_res.get("updated", 0)
                logger.info(f"Neo4j updated {neo4j_updated} Passage nodes with embeddings")
            except Exception as e:
                logger.warning(f"Neo4j embedding storage failed: {e}. Pipeline will continue with local cache.")
                neo4j_index_status = f"error: {str(e)[:50]}"

        # 5. Local Cache (.npz and JSON manifest) Persistence
        local_cache_path: Optional[str] = None
        if save_local_cache:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                passage_ids = [p.passage_id for p in valid_passages]

                # Save compressed NumPy archive
                np.savez_compressed(
                    self.npz_path,
                    passage_ids=np.array(passage_ids),
                    embeddings=vectors,
                )

                # Save JSON manifest with preserved metadata
                manifest = {
                    "embedding_model": self.model_name,
                    "embedding_provider": self.provider,
                    "dimension": actual_dim,
                    "total_passages": len(valid_passages),
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "passages": [p.to_dict() for p in valid_passages],
                }
                with open(self.manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)

                local_cache_path = str(self.npz_path)
                logger.info(f"Persisted passage embeddings cache to {self.npz_path}")
            except Exception as e:
                logger.warning(f"Failed to save local embeddings cache: {e}")

        # 6. Update in-memory graph builder store
        for i, p in enumerate(valid_passages):
            if kg_instance.store.has_node(p.passage_id):
                node = kg_instance.store.get_node(p.passage_id)
                if node:
                    node.metadata["embedding"] = vectors[i].tolist()
                    node.metadata["embedding_model"] = self.model_name

        total_batches = (len(valid_passages) + self.batch_size - 1) // self.batch_size
        elapsed = round(time.perf_counter() - t0, 3)

        return PipelineReport(
            status="completed",
            total_input=total_input,
            valid_passages=len(valid_passages),
            skipped_passages=len(skipped_passages),
            skipped_details=[s.to_dict() for s in skipped_passages],
            batch_count=total_batches,
            batch_size=self.batch_size,
            embedding_model=self.model_name,
            embedding_provider=self.provider,
            vector_dimension=actual_dim,
            neo4j_updated=neo4j_updated,
            neo4j_index_status=neo4j_index_status,
            local_cache_path=local_cache_path,
            elapsed_seconds=elapsed,
        )

    def _load_canonical_passages(self) -> List[Dict[str, Any]]:
        """Loads canonical Tolkappiyam passages from processed corpus or raw canonical dataset."""
        processed_file = self.cache_dir / "preprocessed_corpus.json"
        if processed_file.exists():
            try:
                with open(processed_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"Could not load preprocessed_corpus.json: {e}")

        # Fallback to CorpusLoader
        return corpus_loader.get_all_sutras()


# Singleton pipeline instance
passage_embedding_pipeline = PassageEmbeddingPipeline()
