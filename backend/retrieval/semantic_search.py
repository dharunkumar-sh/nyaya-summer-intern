"""
Multilingual Semantic Search Engine for Classical Tamil Literature.

Uses multilingual sentence embeddings (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
with deterministic dense n-gram fallback to provide semantic search for both Tamil and English queries.
Passage embeddings are persisted locally in compressed NumPy format (.npz) alongside a JSON manifest,
ensuring cold startup in milliseconds without re-encoding the corpus unnecessarily.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from core.logger import logger
from preprocessing.tamil_normalizer import TamilNormalizer
from .embeddings import SentenceTransformerEmbeddingGenerator, cosine_similarity
from .lexical_search import LexicalSearchEngine


@dataclass
class SemanticPassageDocument:
    """
    Passage document prepared for cross-lingual semantic embedding and retrieval.
    """
    passage_id: str
    text: str
    embedding_text: str
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "embedding_text": self.embedding_text,
            "source_metadata": self.source_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticPassageDocument:
        return cls(
            passage_id=data["passage_id"],
            text=data["text"],
            embedding_text=data.get("embedding_text", data["text"]),
            source_metadata=data.get("source_metadata", {}),
        )


@dataclass
class SemanticSearchResult:
    """
    Search result returned by the semantic search engine.
    """
    passage_id: str
    text: str
    source_metadata: Dict[str, Any]
    score: float
    cosine_similarity: float
    retrieval_method: str = "semantic_embedding"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "source_metadata": self.source_metadata,
            "score": round(self.score, 4),
            "cosine_similarity": round(self.cosine_similarity, 4),
            "retrieval_method": self.retrieval_method,
        }


class SemanticSearchEngine:
    """
    High-performance, persistent multilingual semantic search engine.
    """

    DEFAULT_NPZ_FILENAME = "passage_embeddings.npz"
    DEFAULT_MANIFEST_FILENAME = "semantic_passage_manifest.json"

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        corpus_path: Optional[Union[str, Path]] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        auto_initialize: bool = True,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.model_name = model_name
        self.corpus_path = Path(corpus_path) if corpus_path else base_dir / "data" / "processed" / "preprocessed_corpus.json"
        self.raw_canonical_path = base_dir / "data" / "raw" / "tolkappiyam_canonical.json"
        self.cache_dir = Path(cache_dir) if cache_dir else base_dir / "data" / "processed"
        self.npz_path = self.cache_dir / self.DEFAULT_NPZ_FILENAME
        self.manifest_path = self.cache_dir / self.DEFAULT_MANIFEST_FILENAME

        self.encoder = SentenceTransformerEmbeddingGenerator(model_name=model_name)
        self.documents: List[SemanticPassageDocument] = []
        self.embeddings: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self._doc_id_map: Dict[str, SemanticPassageDocument] = {}
        self._corpus_hash: str = ""

        if auto_initialize:
            self.initialize()

    # =========================================================================
    # Checksum & Dataset Loading
    # =========================================================================

    def _compute_dataset_hash(self) -> str:
        """Computes SHA256 checksum of source corpus dataset for cache validation."""
        hasher = hashlib.sha256()
        target_path = self.corpus_path if self.corpus_path.exists() else self.raw_canonical_path
        if target_path.exists():
            with open(target_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        return hasher.hexdigest()

    def _load_raw_passages(self) -> List[Dict[str, Any]]:
        """Loads passages from preprocessed_corpus.json or tolkappiyam_canonical.json."""
        if self.corpus_path.exists():
            try:
                with open(self.corpus_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.warning(f"Could not load preprocessed_corpus.json: {e}")

        if self.raw_canonical_path.exists():
            try:
                with open(self.raw_canonical_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, dict):
                    return raw_data.get("canonical_sutras", [])
                elif isinstance(raw_data, list):
                    return raw_data
            except Exception as e:
                logger.error(f"Could not load tolkappiyam_canonical.json: {e}")

        return []

    def _create_passage_documents(self, passages: List[Dict[str, Any]]) -> List[SemanticPassageDocument]:
        """
        Creates SemanticPassageDocument instances with bilingual text (Tamil text + English translation)
        to maximize semantic alignment for both Tamil and English inquiries.
        """
        docs: List[SemanticPassageDocument] = []

        for p in passages:
            meta = p.get("metadata", {})
            doc_id = p.get("document_id") or p.get("id") or p.get("passage_id", "doc_unknown")
            work = p.get("work", "Tolkāppiyam")
            section = p.get("section") or p.get("atikaram", "Poruḷatikāram")
            chapter = p.get("chapter") or p.get("iyal", "Akattiṇaiyiyal")
            sutra_num = meta.get("sutra_number") or p.get("sutra_number")
            verse_val = int(sutra_num) if sutra_num is not None and str(sutra_num).isdigit() else sutra_num

            raw_text = (
                p.get("original_text")
                or p.get("tamil_text")
                or p.get("text", "")
            ).strip()
            norm_text = (
                p.get("normalized_text")
                or TamilNormalizer.normalize(raw_text)
            ).strip()

            translation = meta.get("english_translation") or p.get("english_translation", "")
            transliteration = meta.get("transliteration") or p.get("transliteration", "")
            tinai = meta.get("tinai") or p.get("tinai", "General")
            category = meta.get("category") or p.get("category", "General")
            entities = meta.get("entities") or p.get("entities", [])
            triples = meta.get("triples") or p.get("triples", [])
            verse_lines = p.get("verse_lines") or [line.strip() for line in norm_text.split("\n") if line.strip()]

            # Extract concepts
            concepts: Set[str] = set()
            if category:
                concepts.add(str(category).strip())
            if tinai and tinai != "General":
                concepts.add(f"{tinai} Tiṇai")
                concepts.add(str(tinai).strip())
            for t in triples:
                if isinstance(t, dict):
                    if t.get("subject"):
                        concepts.add(str(t["subject"]).strip())
                    if t.get("object"):
                        clean_obj = str(t["object"]).split("(")[0].strip()
                        if clean_obj:
                            concepts.add(clean_obj)
                        concepts.add(str(t["object"]).strip())
                    if t.get("predicate"):
                        concepts.add(str(t["predicate"]).strip())

            source_ref = f"{work} {section} {chapter}"
            if verse_val:
                source_ref += f" Sūtra {verse_val}"

            # Bilingual representation for cross-lingual multilingual embedding
            embedding_parts = [norm_text]
            if translation:
                embedding_parts.append(translation)
            if category and category != "General":
                embedding_parts.append(category)
            if entities:
                embedding_parts.append("Entities: " + ", ".join(entities))

            embedding_text = "\n".join(embedding_parts)

            source_metadata = {
                "work": work,
                "section": section,
                "chapter": chapter,
                "verse": verse_val,
                "sutra_number": verse_val,
                "entity": list(entities),
                "entities": list(entities),
                "concept": sorted(list(concepts)),
                "concepts": sorted(list(concepts)),
                "source_identifier": doc_id,
                "source_id": doc_id,
                "source_reference": source_ref,
                "source": source_ref,
                "tinai": tinai,
                "category": category,
                "verse_lines": verse_lines,
                "translation": translation,
                "transliteration": transliteration,
                "triples": triples,
            }

            doc = SemanticPassageDocument(
                passage_id=doc_id,
                text=norm_text,
                embedding_text=embedding_text,
                source_metadata=source_metadata,
            )
            docs.append(doc)

        return docs

    # =========================================================================
    # Index Building & Persistence
    # =========================================================================

    def build_index(self, documents: Optional[List[SemanticPassageDocument]] = None) -> None:
        """
        Generates dense embeddings for each passage document and persists them locally.
        """
        if documents is not None:
            self.documents = documents
        else:
            raw_passages = self._load_raw_passages()
            self.documents = self._create_passage_documents(raw_passages)

        if not self.documents:
            logger.warning("SemanticSearchEngine: No documents to embed")
            self.embeddings = np.empty((0, 0), dtype=np.float32)
            self._doc_id_map.clear()
            return

        self._doc_id_map = {doc.passage_id: doc for doc in self.documents}

        texts_to_embed = [doc.embedding_text for doc in self.documents]
        self.encoder.fit(texts_to_embed)
        raw_embeddings = self.encoder.encode(texts_to_embed)

        # Ensure L2 unit normalization for exact cosine similarity
        norms = np.linalg.norm(raw_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.embeddings = (raw_embeddings / norms).astype(np.float32)

        self._corpus_hash = self._compute_dataset_hash()
        logger.info(
            f"SemanticSearchEngine: Generated embeddings for {len(self.documents)} passages "
            f"(dim: {self.embeddings.shape[1]}, Checksum: {self._corpus_hash[:10]}...)"
        )

    def save_embeddings(
        self,
        npz_path: Optional[Union[str, Path]] = None,
        manifest_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Path]:
        """
        Persists passage embeddings (.npz) and manifest metadata (.json) to disk.
        """
        target_npz = Path(npz_path) if npz_path else self.npz_path
        target_manifest = Path(manifest_path) if manifest_path else self.manifest_path

        target_npz.parent.mkdir(parents=True, exist_ok=True)
        target_manifest.parent.mkdir(parents=True, exist_ok=True)

        # 1. Save embeddings matrix in compressed NumPy format
        np.savez_compressed(
            target_npz,
            embeddings=self.embeddings,
            passage_ids=np.array([d.passage_id for d in self.documents]),
        )

        # 2. Save manifest metadata
        manifest = {
            "version": "1.0.0",
            "model_name": self.model_name,
            "dimension": int(self.embeddings.shape[1]) if self.embeddings.ndim == 2 and self.embeddings.shape[0] > 0 else 0,
            "corpus_hash": self._corpus_hash or self._compute_dataset_hash(),
            "total_passages": len(self.documents),
            "documents": [d.to_dict() for d in self.documents],
        }

        with open(target_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        logger.info(f"SemanticSearchEngine: Saved embeddings to {target_npz} and manifest to {target_manifest}")
        return target_npz, target_manifest

    def load_embeddings(
        self,
        npz_path: Optional[Union[str, Path]] = None,
        manifest_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        Restores cached embeddings and passage metadata from disk without regenerating.
        Returns True if successfully restored and verified.
        """
        src_npz = Path(npz_path) if npz_path else self.npz_path
        src_manifest = Path(manifest_path) if manifest_path else self.manifest_path

        if not src_npz.exists() or not src_manifest.exists():
            return False

        try:
            with open(src_manifest, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            cached_hash = manifest.get("corpus_hash", "")
            current_hash = self._compute_dataset_hash()

            if cached_hash and current_hash and cached_hash != current_hash:
                logger.info("SemanticSearchEngine: Dataset modified, embeddings cache is stale.")
                return False

            # Load compressed NumPy arrays
            with np.load(src_npz, allow_pickle=False) as npz_data:
                loaded_embeddings = npz_data["embeddings"]

            raw_docs = manifest.get("documents", [])
            if not raw_docs or loaded_embeddings.shape[0] != len(raw_docs):
                return False

            self.documents = [SemanticPassageDocument.from_dict(d) for d in raw_docs]
            self._doc_id_map = {doc.passage_id: doc for doc in self.documents}
            self.embeddings = loaded_embeddings.astype(np.float32)
            self._corpus_hash = cached_hash

            # Ensure encoder vocabulary / projector is fitted to match document embeddings
            self.encoder.fit([d.embedding_text for d in self.documents])

            logger.info(
                f"SemanticSearchEngine: Successfully restored cached embeddings for "
                f"{len(self.documents)} passages from {src_npz} (dim: {self.embeddings.shape[1]})"
            )
            return True
        except Exception as e:
            logger.warning(f"SemanticSearchEngine: Failed to load cached embeddings: {e}")
            return False

    def initialize(self) -> None:
        """
        Cold startup initializer:
        Restores existing cached embeddings if valid; otherwise generates and caches once.
        """
        if not self.load_embeddings():
            self.build_index()
            try:
                self.save_embeddings()
            except Exception as e:
                logger.warning(f"SemanticSearchEngine: Could not persist embeddings: {e}")

    # =========================================================================
    # Runtime Semantic Retrieval
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticSearchResult]:
        """
        Executes runtime semantic search for Tamil or English queries using cosine similarity.

        Args:
            query: Query string in Tamil or English.
            top_k: Number of highest ranking passages to return.
            filters: Optional metadata filtering criteria.

        Returns:
            List of SemanticSearchResult with passage_id, text, source_metadata,
            and normalized similarity score in [0.0, 1.0].
        """
        if self.embeddings.shape[0] == 0 or not self.documents:
            return []

        clean_query = query.strip()
        if not clean_query and not filters:
            return []

        # 1. Generate query embedding at runtime
        if clean_query:
            raw_q_vec = self.encoder.encode_one(clean_query)
            # L2-normalize query vector
            q_norm = np.linalg.norm(raw_q_vec)
            if q_norm > 0:
                q_vec = (raw_q_vec / q_norm).astype(np.float32)
            else:
                q_vec = raw_q_vec.astype(np.float32)

            # 2. Cosine similarity via inner product: Q . D^T
            raw_scores = np.dot(self.embeddings, q_vec)
        else:
            raw_scores = np.ones(len(self.documents), dtype=np.float32)

        # 3. Filter and map candidates
        candidates: List[SemanticSearchResult] = []
        for idx, doc in enumerate(self.documents):
            # Evaluate metadata filters
            if filters and not LexicalSearchEngine._matches_filter(doc.source_metadata, filters):
                continue

            cos_sim = float(np.clip(raw_scores[idx], -1.0, 1.0))
            # Affine normalization: [-1.0, 1.0] -> [0.0, 1.0]
            norm_score = float(np.clip((cos_sim + 1.0) / 2.0, 0.0, 1.0))

            candidates.append(
                SemanticSearchResult(
                    passage_id=doc.passage_id,
                    text=doc.text,
                    source_metadata=doc.source_metadata,
                    score=round(norm_score, 4),
                    cosine_similarity=round(cos_sim, 4),
                )
            )

        # 4. Sort descending by score
        candidates.sort(key=lambda r: (-r.score, r.passage_id))
        return candidates[:top_k]

    def get_document_by_id(self, passage_id: str) -> Optional[SemanticPassageDocument]:
        """Retrieves an indexed document by passage ID."""
        return self._doc_id_map.get(passage_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Returns statistics on the semantic search index."""
        return {
            "total_passages": len(self.documents),
            "vector_dimension": int(self.embeddings.shape[1]) if self.embeddings.ndim == 2 and self.embeddings.shape[0] > 0 else 0,
            "model_name": self.model_name,
            "corpus_hash": self._corpus_hash[:12] if self._corpus_hash else "",
            "npz_cache_path": str(self.npz_path),
            "manifest_path": str(self.manifest_path),
            "cache_exists": self.npz_path.exists() and self.manifest_path.exists(),
        }


# Global singleton instance initialized on startup
semantic_search_engine = SemanticSearchEngine()
