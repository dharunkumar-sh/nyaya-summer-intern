"""
Unified RAG Retrieval Engine for Classical Tamil Literary Knowledge.

Coordinates:
- PassageChunker (source-traceable chunks)
- SentenceTransformerEmbeddingGenerator (dense embeddings + fallback)
- FAISSVectorIndex (exact cosine similarity search)
- BM25Retriever (lexical keyword search)
- Source and Entity-based lookup indices
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import numpy as np

from core.logger import logger
from ingestion.corpus_loader import corpus_loader
from .chunker import RetrievalChunk, PassageChunker
from .embeddings import SentenceTransformerEmbeddingGenerator, cosine_similarity
from .faiss_index import FAISSVectorIndex
from .bm25 import BM25Retriever


class RAGRetrievalEngine:
    """
    RAG retrieval engine executing semantic, lexical, source-based, and entity-based queries
    while strictly preserving source citations and provenance.
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        auto_index: bool = True,
    ):
        self.encoder = SentenceTransformerEmbeddingGenerator(model_name=embedding_model)
        self.faiss_index: Optional[FAISSVectorIndex] = None
        self.bm25_retriever = BM25Retriever()
        self.chunks: List[RetrievalChunk] = []

        # Fast lookup indexes
        self._doc_id_to_chunks: Dict[str, List[RetrievalChunk]] = {}
        self._entity_to_chunks: Dict[str, List[RetrievalChunk]] = {}

        if auto_index:
            self.index_corpus()

    def index_corpus(self, passages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Indexes corpus passages into FAISS and BM25.
        Uses preprocessed corpus if available, otherwise canonical sūtras.
        """
        if passages is None:
            # Check for preprocessed corpus file first
            processed_file = Path(__file__).resolve().parent.parent / "data" / "processed" / "preprocessed_corpus.json"
            if processed_file.exists():
                try:
                    with open(processed_file, "r", encoding="utf-8") as f:
                        passages = json.load(f)
                    logger.info(f"Loaded {len(passages)} passages from preprocessed_corpus.json")
                except Exception as e:
                    logger.warning(f"Could not load preprocessed corpus: {e}")
                    passages = corpus_loader.get_all_sutras()
            else:
                passages = corpus_loader.get_all_sutras()

        # 1. Chunking
        self.chunks = PassageChunker.chunk_corpus(passages, chunk_by_verse_lines=True)
        if not self.chunks:
            logger.warning("No chunks generated during RAG indexing")
            return {"total_chunks": 0, "status": "empty"}

        # 2. Dense Embeddings & FAISS
        texts = [c.text for c in self.chunks]
        self.encoder.fit(texts)
        embeddings = self.encoder.encode(texts)

        self.faiss_index = FAISSVectorIndex(dimension=embeddings.shape[1])
        self.faiss_index.add_chunks(self.chunks, embeddings)

        # 3. BM25 Lexical Index
        self.bm25_retriever.index_chunks(self.chunks)

        # 4. Inverted Indices for Source and Entity Lookup
        self._doc_id_to_chunks.clear()
        self._entity_to_chunks.clear()

        for chunk in self.chunks:
            # Source / Document index
            doc_id = chunk.document_id
            self._doc_id_to_chunks.setdefault(doc_id, []).append(chunk)

            # Entity index
            entities = chunk.metadata.get("entities", [])
            for ent in entities:
                ent_clean = str(ent).strip().lower()
                self._entity_to_chunks.setdefault(ent_clean, []).append(chunk)

        stats = {
            "total_chunks": len(self.chunks),
            "unique_documents": len(self._doc_id_to_chunks),
            "unique_entities": len(self._entity_to_chunks),
            "vector_dimension": embeddings.shape[1],
            "faiss_total": self.faiss_index.size(),
            "status": "ready",
        }
        logger.info(f"RAG Indexing complete: {stats}")
        return stats

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes dense vector similarity search via FAISS and cosine similarity.
        Guarantees source references in every result item. Supports optional metadata filtering.
        """
        if not self.faiss_index or self.faiss_index.size() == 0:
            return []

        q_vec = self.encoder.encode_one(query)
        search_k = top_k * 3 if filters else top_k
        faiss_results = self.faiss_index.search(q_vec, top_k=search_k)

        formatted_results: List[Dict[str, Any]] = []
        for chunk, score in faiss_results:
            if filters and not LexicalSearchEngine._matches_filter(chunk, filters):
                continue

            formatted_results.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "work": chunk.work,
                "section": chunk.section,
                "passage_id": chunk.passage_id,
                "text": chunk.text,
                "source": chunk.source,
                "score": score,
                "cosine_similarity": score,
                "retrieval_method": "semantic_faiss",
                "metadata": chunk.metadata,
            })
            if len(formatted_results) >= top_k:
                break

        return formatted_results

    def semantic_passage_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search over persisted passage documents with rich source metadata.
        """
        from .semantic_search import semantic_search_engine
        results = semantic_search_engine.search(query=query, top_k=top_k, filters=filters)
        return [r.to_dict() for r in results]

    def bm25_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes lexical keyword search using BM25 with metadata filtering and phrase support.
        Guarantees source references in every result item.
        """
        raw_results = self.bm25_retriever.search_chunks(
            query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
        )

        formatted_results: List[Dict[str, Any]] = []
        for chunk, score in raw_results:
            formatted_results.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "work": chunk.work,
                "section": chunk.section,
                "passage_id": chunk.passage_id,
                "text": chunk.text,
                "source": chunk.source,
                "score": score,
                "bm25_score": score,
                "retrieval_method": "lexical_bm25",
                "metadata": chunk.metadata,
            })

        return formatted_results

    def lexical_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        primary_passages_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Direct lexical search returning passage ID, text, source metadata, and normalized BM25 score.
        """
        from .lexical_search import lexical_search_engine
        results = lexical_search_engine.search(
            query=query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            primary_passages_only=primary_passages_only,
        )
        return [r.to_dict() for r in results]

    def retrieve_by_source(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all chunks originating from a specific sūtra ID or document ID.
        """
        clean_id = source_id.strip()
        matched_chunks = self._doc_id_to_chunks.get(clean_id, [])

        if not matched_chunks:
            # Substring match if exact match fails
            matched_chunks = [
                c for c in self.chunks
                if clean_id.lower() in c.document_id.lower() or clean_id.lower() in c.source.lower()
            ]

        return [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "work": c.work,
                "section": c.section,
                "passage_id": c.passage_id,
                "text": c.text,
                "source": c.source,
                "retrieval_method": "source_lookup",
                "metadata": c.metadata,
            }
            for c in matched_chunks
        ]

    def retrieve_by_entity(self, entity: str) -> List[Dict[str, Any]]:
        """
        Retrieves all chunks mentioning or classified under the specified entity.
        """
        clean_entity = entity.strip().lower()
        matched_chunks = self._entity_to_chunks.get(clean_entity, [])

        if not matched_chunks:
            # Substring search in text or entity list
            matched_chunks = [
                c for c in self.chunks
                if clean_entity in c.text.lower()
                or any(clean_entity in str(e).lower() for e in c.metadata.get("entities", []))
            ]

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for c in matched_chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                deduped.append(c)

        return [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "work": c.work,
                "section": c.section,
                "passage_id": c.passage_id,
                "text": c.text,
                "source": c.source,
                "retrieval_method": "entity_lookup",
                "matched_entity": entity,
                "metadata": c.metadata,
            }
            for c in deduped
        ]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """
        Fuses semantic FAISS and lexical BM25 results using Reciprocal Rank Fusion (RRF).
        """
        sem_results = self.semantic_search(query, top_k=top_k * 2)
        lex_results = self.bm25_search(query, top_k=top_k * 2)

        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60.0

        for rank, item in enumerate(sem_results):
            cid = item["chunk_id"]
            chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + semantic_weight * (1.0 / (rrf_k + rank + 1))

        for rank, item in enumerate(lex_results):
            cid = item["chunk_id"]
            if cid not in chunk_map:
                chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + bm25_weight * (1.0 / (rrf_k + rank + 1))

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for cid, score in ranked[:top_k]:
            item = dict(chunk_map[cid])
            item["score"] = round(score, 5)
            item["retrieval_method"] = "hybrid_rrf"
            results.append(item)

        return results

    def hybrid_passage_search(
        self,
        query: str,
        top_k: int = 5,
        lexical_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        rerank: bool = False,
        rerank_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Unified hybrid search combining BM25 lexical and dense semantic retrieval over passages
        with configurable weights, optional second-stage re-ranking, and transparent score breakdowns.
        """
        from .hybrid_search import hybrid_search_service
        results = hybrid_search_service.search(
            query=query,
            top_k=top_k,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            rerank=rerank,
            rerank_weights=rerank_weights,
        )
        return [r.to_dict() for r in results]

    def rerank_passages(
        self,
        candidates: List[Any],
        query: str,
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Directly executes deterministic second-stage re-ranking over candidate passages.
        """
        from .reranker import passage_reranker
        results = passage_reranker.rerank(
            candidates=candidates,
            query=query,
            top_k=top_k,
            weights=weights,
            filters=filters,
        )
        return [r.to_dict() for r in results]

    def graph_hybrid_passage_search(
        self,
        query: str,
        top_k: int = 5,
        max_graph_depth: int = 2,
        lexical_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Executes unified Graph-Augmented Hybrid Search combining BM25 lexical,
        dense semantic, and Neo4j Knowledge Graph contextual relevance.
        """
        from .graph_hybrid_search import graph_hybrid_search_service
        results = graph_hybrid_search_service.search(
            query=query,
            top_k=top_k,
            max_graph_depth=max_graph_depth,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            graph_weight=graph_weight,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            rerank_first_stage=rerank,
        )
        return [r.to_dict() for r in results]

    def get_statistics(self) -> Dict[str, Any]:
        """Returns diagnostic statistics of the RAG retrieval engine."""
        return {
            "total_chunks": len(self.chunks),
            "indexed_documents": len(self._doc_id_to_chunks),
            "indexed_entities": len(self._entity_to_chunks),
            "vector_dimension": self.faiss_index.dimension if self.faiss_index else 0,
            "faiss_total_vectors": self.faiss_index.size() if self.faiss_index else 0,
            "embedding_model": getattr(self.encoder, "model_name", "DenseNgramEmbeddingGenerator"),
        }

    def hybrid_rag_retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: int = 2,
        semantic_weight: Optional[float] = None,
        lexical_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        enrich_graph_context: bool = True,
        as_dict: bool = True,
    ) -> Any:
        """
        Executes the unified Hybrid RAG retrieval pipeline combining three channels:
        - Channel A: Semantic vector retrieval (Neo4j vector index / FAISS fallback)
        - Channel B: Keyword / entity retrieval via BM25
        - Channel C: Graph traversal retrieval seeded from query KG entities

        This is a retrieve-only operation. It returns grounded evidence from the
        corpus and knowledge graph and does not generate or infer any content.

        Args:
            query: Raw user query (Tamil, English, or mixed-language).
            top_k: Number of top evidence items to return.
            filters: Optional metadata filters (work, section, chapter, sutra_number).
            max_graph_depth: Graph traversal hop depth (clamped to 1-3).
            semantic_weight: Optional per-call override for semantic channel weight.
            lexical_weight: Optional per-call override for lexical channel weight.
            graph_weight: Optional per-call override for graph traversal weight.
            enrich_graph_context: Populate graph_path and graph_context on each item.
            as_dict: If True (default), returns JSON-serializable dict. If False,
                     returns the typed EvidenceCollection object.

        Returns:
            EvidenceCollection.to_dict() by default, or EvidenceCollection if as_dict=False.
        """
        from .hybrid_rag_pipeline import hybrid_rag_pipeline
        collection = hybrid_rag_pipeline.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
            max_graph_depth=max_graph_depth,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            graph_weight=graph_weight,
            enrich_graph_context=enrich_graph_context,
        )
        return collection.to_dict() if as_dict else collection

    def build_structured_context(
        self,
        query: str,
        evidence_items: Optional[Union[List[Any], Any]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        max_passages: int = 5,
        max_context_chars: int = 4000,
        max_relationships_per_passage: int = 8,
        min_relevance_threshold: float = 0.30,
        min_evidence_count: int = 1,
        as_dict: bool = True,
    ) -> Any:
        """
        Transforms ranked retrieval results into a compact, structured context
        tailored for answer generation with exact source citations and Neo4j relationships.
        If evidence is insufficient, returns an explicit insufficient-evidence state.
        """
        from .structured_context_builder import structured_context_builder

        if evidence_items is None:
            from .hybrid_rag_pipeline import hybrid_rag_pipeline
            collection = hybrid_rag_pipeline.retrieve(query=query, top_k=top_k, filters=filters)
            evidence_items = collection.items

        context = structured_context_builder.build_context(
            query=query,
            evidence_items=evidence_items,
            max_passages=max_passages,
            max_context_chars=max_context_chars,
            max_relationships_per_passage=max_relationships_per_passage,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
        )
        return context.to_dict() if as_dict else context

    def answer_query(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        max_graph_depth: Optional[int] = None,
        max_context_chars: int = 4000,
        max_relationships: int = 8,
        min_relevance_threshold: float = 0.25,
        min_evidence_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end grounded QA returning final answer, evidence, sources,
        confidence, and reasoning metadata.
        """
        from .hybrid_rag_pipeline import hybrid_rag_pipeline
        return hybrid_rag_pipeline.answer_query(
            query=query,
            top_k=top_k,
            filters=filters,
            max_graph_depth=max_graph_depth,
            max_context_chars=max_context_chars,
            max_relationships=max_relationships,
            min_relevance_threshold=min_relevance_threshold,
            min_evidence_count=min_evidence_count,
        )


# Global singleton instance
rag_engine = RAGRetrievalEngine()


