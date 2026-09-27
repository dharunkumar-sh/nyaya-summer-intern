"""
Rank-BM25 Lexical Retriever for tokenized Classical Tamil literary chunks and sūtras.
Integrates with the lightweight persistent LexicalSearchEngine.
"""
from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional, Union
from rank_bm25 import BM25Plus, BM25Okapi
from preprocessing.tokenizer import TamilTokenizer
from core.logger import logger
from .chunker import RetrievalChunk
from .lexical_search import LexicalSearchEngine, LexicalSearchResult, PassageDocument, lexical_search_engine


class BM25Retriever:
    """Performs BM25 keyword retrieval over sūtras, chunks, and literary passages."""

    def __init__(self, engine: Optional[LexicalSearchEngine] = None):
        self.engine = engine or lexical_search_engine
        self.bm25: Optional[BM25Plus] = None
        self.records: List[Any] = []
        self.chunks: List[RetrievalChunk] = []
        self.build_index()

    def build_index(self) -> None:
        """Indexes tokenized corpus sūtras (default initialization)."""
        # Lazy import to avoid circular dependency with ingestion package
        try:
            from ingestion.corpus_loader import corpus_loader
            sutras = corpus_loader.get_all_sutras()
        except Exception as e:
            logger.warning(f"Could not load sūtras via corpus_loader: {e}")
            sutras = []

        if not sutras and self.engine.documents:
            # Fallback to engine's documents formatted as dicts
            sutras = [
                {
                    "id": d.passage_id,
                    "tamil_text": d.text,
                    "transliteration": d.source_metadata.get("transliteration", ""),
                    "english_translation": d.source_metadata.get("translation", ""),
                    "atikaram": d.source_metadata.get("section", ""),
                    "iyal": d.source_metadata.get("chapter", ""),
                    "sutra_number": d.source_metadata.get("verse"),
                    "tinai": d.source_metadata.get("tinai", "General"),
                    "category": d.source_metadata.get("category", ""),
                    "entities": d.source_metadata.get("entities", []),
                    "triples": d.source_metadata.get("triples", []),
                }
                for d in self.engine.documents
                if d.source_metadata.get("document_level") == "passage"
            ]

        if not sutras:
            return

        tokenized_corpus = []
        for s in sutras:
            combined = " ".join([
                str(s.get("tamil_text", "")),
                str(s.get("english_translation", "")),
                str(s.get("transliteration", "")),
                str(s.get("tinai", "")),
                str(s.get("category", "")),
                " ".join(str(e) for e in s.get("entities", [])),
            ])
            tokens = [t.lower() for t in TamilTokenizer.tokenize_words(combined, remove_stopwords=False) if t.strip()]
            tokenized_corpus.append(tokens)

        self.bm25 = BM25Plus(tokenized_corpus)
        self.records = sutras
        logger.info(f"BM25 Index built over {len(self.records)} canonical sūtras")

    def index_chunks(self, chunks: List[RetrievalChunk]) -> None:
        """Indexes explicit RetrievalChunk records."""
        if not chunks:
            return

        tokenized_corpus = []
        for c in chunks:
            extra = ""
            if hasattr(c, "metadata") and isinstance(c.metadata, dict):
                extra = " ".join([
                    str(c.metadata.get("english_translation", "")),
                    str(c.metadata.get("transliteration", "")),
                    str(c.metadata.get("tinai", "")),
                    str(c.metadata.get("category", "")),
                    " ".join(str(e) for e in c.metadata.get("entities", [])),
                ])
            combined = f"{c.text} {extra}".strip()
            tokens = [t.lower() for t in TamilTokenizer.tokenize_words(combined, remove_stopwords=False) if t.strip()]
            tokenized_corpus.append(tokens)

        self.bm25 = BM25Plus(tokenized_corpus)
        self.chunks = chunks
        self.records = chunks
        logger.info(f"BM25 Index built over {len(self.chunks)} retrieval chunks")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
    ) -> List[Tuple[Any, float]]:
        """
        Retrieves top-K matching records (sūtras or chunks) with normalized BM25 scores.
        """
        if not self.bm25 or len(self.records) == 0:
            return []

        query_tokens = [t.lower() for t in TamilTokenizer.tokenize_words(query, remove_stopwords=False) if t.strip()]
        if not query_tokens:
            return []

        doc_scores = self.bm25.get_scores(query_tokens)

        # Normalize BM25 scores to [0, 1] range
        max_score = max(doc_scores) if max(doc_scores) > 0 else 1.0
        normalized_scores = [float(s / max_score) for s in doc_scores]

        indexed_scores = list(enumerate(normalized_scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Tuple[Any, float]] = []
        for idx, score in indexed_scores:
            rec = self.records[idx]

            # If filters are provided, evaluate on record metadata
            if filters:
                rec_meta = rec.metadata if isinstance(rec, RetrievalChunk) else rec
                if not LexicalSearchEngine._matches_filter(rec_meta, filters):
                    continue

            results.append((rec, round(score, 4)))
            if len(results) >= top_k:
                break

        return results

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
    ) -> List[Tuple[RetrievalChunk, float]]:
        """Specialized search returning RetrievalChunk objects."""
        raw_results = self.search(
            query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
        )
        chunk_results: List[Tuple[RetrievalChunk, float]] = []

        for item, score in raw_results:
            if isinstance(item, RetrievalChunk):
                chunk_results.append((item, score))
            elif isinstance(item, dict):
                # Wrap dict into RetrievalChunk for uniform return
                chunk = RetrievalChunk(
                    chunk_id=f"chk-{item.get('id', 'unk')}",
                    document_id=item.get("id", ""),
                    work="Tolkāppiyam",
                    section=item.get("atikaram", "Poruḷatikāram"),
                    passage_id=item.get("id", ""),
                    text=item.get("tamil_text", ""),
                    source=f"Tolkāppiyam {item.get('iyal', '')} Sūtra {item.get('sutra_number', '')}".strip(),
                    metadata=item,
                )
                chunk_results.append((chunk, score))

        return chunk_results

    def search_passages(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        primary_passages_only: bool = False,
    ) -> List[LexicalSearchResult]:
        """Directly leverages the LexicalSearchEngine to retrieve enriched passage results."""
        return self.engine.search(
            query=query,
            top_k=top_k,
            filters=filters,
            exact_terms=exact_terms,
            require_phrase=require_phrase,
            primary_passages_only=primary_passages_only,
        )
