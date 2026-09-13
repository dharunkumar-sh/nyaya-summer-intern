"""
Lightweight Lexical Search Engine for Classical Tamil Literary Passages.

Pure Python implementation using BM25 without Valkey or any external search database.
Operates on the project's actual literary dataset (Tolkāppiyam sūtras and passages).
Features:
- BM25Plus / BM25Okapi scoring with term coordination factors
- Exact term and multi-keyword token matching
- Phrase-like matching (quoted phrases and contiguous token sequences)
- Rich metadata indexing: work, section, chapter, verse, entity, concept, source identifiers
- Comprehensive metadata filtering (exact, substring, list membership, ranges)
- Normalized BM25 scores in [0.0, 1.0]
- Local disk persistence (JSON-based) and fast application startup loading
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from rank_bm25 import BM25Plus, BM25Okapi
from core.logger import logger
from preprocessing.tamil_normalizer import TamilNormalizer
from preprocessing.tokenizer import TamilTokenizer


@dataclass
class PassageDocument:
    """
    Indexed literary passage document preserving full structural and semantic provenance.
    """
    passage_id: str
    text: str
    tokens: List[str]
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "tokens": self.tokens,
            "source_metadata": self.source_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PassageDocument:
        return cls(
            passage_id=data["passage_id"],
            text=data["text"],
            tokens=data.get("tokens", []),
            source_metadata=data.get("source_metadata", {}),
        )


@dataclass
class LexicalSearchResult:
    """
    Individual search result with passage details, source metadata, and normalized score.
    """
    passage_id: str
    text: str
    source_metadata: Dict[str, Any]
    score: float
    raw_score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)
    phrase_matched: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "source_metadata": self.source_metadata,
            "score": round(self.score, 4),
            "raw_score": round(self.raw_score, 4),
            "matched_terms": self.matched_terms,
            "phrase_matched": self.phrase_matched,
            "retrieval_method": "lexical_bm25",
        }


class LexicalSearchEngine:
    """
    In-memory, persistent lexical search engine powered by BM25.
    """

    DEFAULT_CACHE_FILENAME = "lexical_bm25_index.json"

    def __init__(
        self,
        corpus_path: Optional[Union[str, Path]] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        auto_initialize: bool = True,
        k1: float = 1.5,
        b: float = 0.75,
        delta: float = 1.0,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.corpus_path = Path(corpus_path) if corpus_path else base_dir / "data" / "processed" / "preprocessed_corpus.json"
        self.raw_canonical_path = base_dir / "data" / "raw" / "tolkappiyam_canonical.json"
        self.cache_dir = Path(cache_dir) if cache_dir else base_dir / "data" / "processed"
        self.cache_path = self.cache_dir / self.DEFAULT_CACHE_FILENAME

        self.k1 = k1
        self.b = b
        self.delta = delta

        self.documents: List[PassageDocument] = []
        self._doc_id_map: Dict[str, PassageDocument] = {}
        self.bm25: Optional[BM25Plus] = None
        self._corpus_tokens: List[List[str]] = []
        self._corpus_hash: str = ""

        if auto_initialize:
            self.initialize()

    # =========================================================================
    # Corpus Ingestion & Metadata Construction
    # =========================================================================

    def _compute_dataset_hash(self) -> str:
        """Computes SHA256 checksum of the source dataset files for cache validation."""
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
                logger.warning(f"Could not parse preprocessed_corpus.json: {e}")

        if self.raw_canonical_path.exists():
            try:
                with open(self.raw_canonical_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, dict):
                    return raw_data.get("canonical_sutras", [])
                elif isinstance(raw_data, list):
                    return raw_data
            except Exception as e:
                logger.error(f"Could not parse tolkappiyam_canonical.json: {e}")

        return []

    def _extract_concepts_from_record(self, rec: Dict[str, Any]) -> List[str]:
        """Extracts unique concepts from metadata category, triples, and entities."""
        concepts: Set[str] = set()
        meta = rec.get("metadata", {})

        # 1. Literary Category
        cat = meta.get("category") or rec.get("category")
        if cat:
            concepts.add(str(cat).strip())

        # 2. Tiṇai
        tinai = meta.get("tinai") or rec.get("tinai")
        if tinai and tinai != "General":
            concepts.add(f"{tinai} Tiṇai")
            concepts.add(str(tinai).strip())

        # 3. Triples (Subjects, Objects, Predicates)
        triples = meta.get("triples") or rec.get("triples") or []
        for t in triples:
            if isinstance(t, dict):
                subj = t.get("subject")
                obj = t.get("object")
                pred = t.get("predicate")
                if subj:
                    concepts.add(str(subj).strip())
                if obj:
                    clean_obj = str(obj).split("(")[0].strip()
                    if clean_obj:
                        concepts.add(clean_obj)
                    concepts.add(str(obj).strip())
                if pred:
                    concepts.add(str(pred).strip())

        # 4. Nyaya logic mapping members
        nyaya = meta.get("nyaya_mapping") or rec.get("nyaya_mapping") or {}
        if isinstance(nyaya, dict):
            if nyaya.get("member"):
                concepts.add(f"Nyaya:{nyaya['member']}")
            if nyaya.get("pramana"):
                concepts.add(f"Pramana:{nyaya['pramana']}")

        return sorted(list(concepts))

    def _create_passage_documents(
        self, passages: List[Dict[str, Any]], include_verse_lines: bool = False
    ) -> List[PassageDocument]:
        """
        Transforms raw passage dicts into rich PassageDocument instances.
        Creates primary passage documents and optional granular verse-line documents.
        """
        docs: List[PassageDocument] = []

        for p in passages:
            meta = p.get("metadata", {})
            doc_id = p.get("document_id") or p.get("id") or p.get("passage_id", "doc_unknown")
            work = p.get("work", "Tolkāppiyam")
            section = p.get("section") or p.get("atikaram", "Poruḷatikāram")
            chapter = p.get("chapter") or p.get("iyal", "Akattiṇaiyiyal")
            sutra_num = meta.get("sutra_number") or p.get("sutra_number")
            verse_val = int(sutra_num) if sutra_num is not None and str(sutra_num).isdigit() else sutra_num

            # Dual text extraction
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
            concepts = self._extract_concepts_from_record(p)
            triples = meta.get("triples") or p.get("triples", [])
            verse_lines = p.get("verse_lines") or [line.strip() for line in norm_text.split("\n") if line.strip()]

            source_ref = f"{work} {section} {chapter}"
            if verse_val:
                source_ref += f" Sūtra {verse_val}"

            # Tokenize passage text
            tokens = p.get("tokens")
            if not tokens:
                tokens = TamilTokenizer.tokenize_words(norm_text, remove_stopwords=False)
            norm_tokens = [TamilNormalizer.normalize(t).lower() for t in tokens if t.strip()]

            # 1. Primary Sūtra / Passage Document
            primary_source_metadata = {
                "work": work,
                "section": section,
                "chapter": chapter,
                "verse": verse_val,
                "sutra_number": verse_val,
                "entity": list(entities),
                "entities": list(entities),
                "concept": concepts,
                "concepts": concepts,
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
                "document_level": "passage",
            }

            primary_doc = PassageDocument(
                passage_id=doc_id,
                text=norm_text,
                tokens=norm_tokens,
                source_metadata=primary_source_metadata,
            )
            docs.append(primary_doc)

            # 2. Granular verse-line documents
            if include_verse_lines and len(verse_lines) > 1:
                for idx, line in enumerate(verse_lines, start=1):
                    line_norm = TamilNormalizer.normalize(line).strip()
                    line_tokens = [
                        TamilNormalizer.normalize(t).lower()
                        for t in TamilTokenizer.tokenize_words(line_norm, remove_stopwords=False)
                        if t.strip()
                    ]
                    line_id = f"{doc_id}-line-{idx}"
                    line_source = f"{source_ref} (Line {idx})"

                    line_metadata = dict(primary_source_metadata)
                    line_metadata.update({
                        "verse": verse_val,
                        "line_number": idx,
                        "parent_passage_id": doc_id,
                        "source_identifier": line_id,
                        "source_reference": line_source,
                        "source": line_source,
                        "document_level": "verse_line",
                    })

                    line_doc = PassageDocument(
                        passage_id=line_id,
                        text=line_norm,
                        tokens=line_tokens,
                        source_metadata=line_metadata,
                    )
                    docs.append(line_doc)

        return docs

    # =========================================================================
    # Index Building, Persistence & Startup Cache
    # =========================================================================

    def build_index(
        self,
        documents: Optional[List[PassageDocument]] = None,
        include_verse_lines: bool = False,
    ) -> None:
        """
        Builds the BM25 index over provided or loaded passage documents.
        """
        if documents is not None:
            self.documents = documents
        else:
            raw_passages = self._load_raw_passages()
            self.documents = self._create_passage_documents(
                raw_passages, include_verse_lines=include_verse_lines
            )

        if not self.documents:
            logger.warning("LexicalSearchEngine: No passage documents to index")
            self.bm25 = None
            self._corpus_tokens = []
            self._doc_id_map.clear()
            return

        self._doc_id_map = {doc.passage_id: doc for doc in self.documents}
        self._corpus_tokens = [doc.tokens for doc in self.documents]

        # Use BM25Plus: guarantees lower-bound IDF on rare/frequent terms and avoids 0 scores
        self.bm25 = BM25Plus(self._corpus_tokens, k1=self.k1, b=self.b, delta=self.delta)
        self._corpus_hash = self._compute_dataset_hash()

        logger.info(
            f"LexicalSearchEngine: Built BM25 index over {len(self.documents)} passage documents "
            f"(Checksum: {self._corpus_hash[:10]}...)"
        )

    def save_index(self, filepath: Optional[Union[str, Path]] = None) -> Path:
        """
        Serializes documents and metadata to disk for instant cold startup.
        """
        dest = Path(filepath) if filepath else self.cache_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": "1.0.0",
            "corpus_hash": self._corpus_hash or self._compute_dataset_hash(),
            "k1": self.k1,
            "b": self.b,
            "delta": self.delta,
            "total_documents": len(self.documents),
            "documents": [doc.to_dict() for doc in self.documents],
        }

        with open(dest, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"LexicalSearchEngine: Saved persistent BM25 index to {dest}")
        return dest

    def load_index(self, filepath: Optional[Union[str, Path]] = None) -> bool:
        """
        Loads the pre-built BM25 index from disk cache.
        Returns True if successfully loaded and verified against corpus hash.
        """
        src = Path(filepath) if filepath else self.cache_path
        if not src.exists():
            return False

        try:
            with open(src, "r", encoding="utf-8") as f:
                payload = json.load(f)

            cached_hash = payload.get("corpus_hash", "")
            current_hash = self._compute_dataset_hash()

            # Invalidate cache if source corpus dataset was modified
            if cached_hash and current_hash and cached_hash != current_hash:
                logger.info("LexicalSearchEngine: Cache is stale (source dataset changed), rebuilding index...")
                return False

            raw_docs = payload.get("documents", [])
            if not raw_docs:
                return False

            self.documents = [PassageDocument.from_dict(d) for d in raw_docs]
            self._doc_id_map = {doc.passage_id: doc for doc in self.documents}
            self._corpus_tokens = [doc.tokens for doc in self.documents]

            self.k1 = payload.get("k1", self.k1)
            self.b = payload.get("b", self.b)
            self.delta = payload.get("delta", self.delta)
            self.bm25 = BM25Plus(self._corpus_tokens, k1=self.k1, b=self.b, delta=self.delta)
            self._corpus_hash = cached_hash

            logger.info(
                f"LexicalSearchEngine: Successfully restored persistent index with "
                f"{len(self.documents)} passage documents from {src}"
            )
            return True
        except Exception as e:
            logger.warning(f"LexicalSearchEngine: Failed to load index cache from {src}: {e}")
            return False

    def initialize(self) -> None:
        """
        Initializes the engine at application startup:
        Loads existing persistent cache if available, or rebuilds and caches once.
        """
        if not self.load_index():
            self.build_index()
            try:
                self.save_index()
            except Exception as e:
                logger.warning(f"LexicalSearchEngine: Could not persist cache: {e}")

    # =========================================================================
    # Metadata Filtering
    # =========================================================================

    @staticmethod
    def _matches_filter(doc_meta: Any, filters: Dict[str, Any]) -> bool:
        """
        Evaluates whether a passage document matches all given metadata filter criteria.
        """
        if not filters:
            return True

        # Normalize doc_meta whether it is a dict, RetrievalChunk, or other object
        if hasattr(doc_meta, "metadata") and not isinstance(doc_meta, dict):
            chunk = doc_meta
            chunk_meta = dict(chunk.metadata) if isinstance(chunk.metadata, dict) else {}
            doc_meta = dict(chunk_meta)
            doc_meta.setdefault("work", getattr(chunk, "work", ""))
            doc_meta.setdefault("section", getattr(chunk, "section", ""))
            doc_meta.setdefault("source_identifier", getattr(chunk, "document_id", ""))
            doc_meta.setdefault("source_id", getattr(chunk, "document_id", ""))
            doc_meta.setdefault("source", getattr(chunk, "source", ""))
            doc_meta.setdefault("text", getattr(chunk, "text", ""))
        elif not isinstance(doc_meta, dict):
            doc_meta = getattr(doc_meta, "__dict__", {})

        for key, filter_val in filters.items():
            if filter_val is None or filter_val == "":
                continue

            norm_key = key.lower().strip()
            if norm_key in ("source_id", "source_identifier", "passage_id", "document_id"):
                doc_val = (
                    doc_meta.get("source_identifier")
                    or doc_meta.get("source_id")
                    or doc_meta.get("passage_id")
                    or doc_meta.get("document_id")
                    or ""
                )
                val_str = str(filter_val).strip().lower()
                if val_str not in str(doc_val).lower():
                    return False

            elif norm_key in ("verse", "sutra_number", "verse_number"):
                doc_verse = doc_meta.get("verse") or doc_meta.get("sutra_number")
                if isinstance(filter_val, (list, tuple, set)):
                    if doc_verse not in filter_val and str(doc_verse) not in [str(x) for x in filter_val]:
                        return False
                else:
                    if str(doc_verse).lower() != str(filter_val).lower():
                        return False

            elif norm_key in ("chapter", "iyal"):
                doc_val = str(doc_meta.get("chapter") or doc_meta.get("iyal") or "").strip().lower()
                if not doc_val and "section" in doc_meta:
                    doc_val = str(doc_meta["section"]).strip().lower()
                filter_clean = str(filter_val).strip().lower()
                if filter_clean not in doc_val:
                    return False

            elif norm_key in ("section", "atikaram"):
                doc_val = str(doc_meta.get("section") or doc_meta.get("atikaram") or "").strip().lower()
                filter_clean = str(filter_val).strip().lower()
                if filter_clean not in doc_val:
                    return False

            elif norm_key in ("entity", "entities"):
                doc_entities = doc_meta.get("entity") or doc_meta.get("entities") or []
                doc_ents_lower = [str(e).lower() for e in doc_entities]
                if isinstance(filter_val, (list, tuple, set)):
                    for req_ent in filter_val:
                        req_clean = str(req_ent).strip().lower()
                        if not any(req_clean in e for e in doc_ents_lower):
                            return False
                else:
                    filter_clean = str(filter_val).strip().lower()
                    if not any(filter_clean in e for e in doc_ents_lower):
                        return False

            elif norm_key in ("concept", "concepts"):
                doc_concepts = doc_meta.get("concept") or doc_meta.get("concepts") or []
                doc_concepts_lower = [str(c).lower() for c in doc_concepts]
                if isinstance(filter_val, (list, tuple, set)):
                    for req_c in filter_val:
                        req_clean = str(req_c).strip().lower()
                        if not any(req_clean in c for c in doc_concepts_lower):
                            return False
                else:
                    filter_clean = str(filter_val).strip().lower()
                    if not any(filter_clean in c for c in doc_concepts_lower):
                        return False

            elif norm_key in ("work", "tinai", "category"):
                doc_val = str(doc_meta.get(norm_key, "")).strip().lower()
                if isinstance(filter_val, (list, tuple, set)):
                    if not any(str(v).strip().lower() in doc_val for v in filter_val):
                        return False
                else:
                    filter_clean = str(filter_val).strip().lower()
                    if filter_clean not in doc_val:
                        return False

            elif norm_key == "document_level":
                doc_level = doc_meta.get("document_level", "passage")
                if str(doc_level).lower() != str(filter_val).lower():
                    return False

            else:
                doc_field = doc_meta.get(key)
                if doc_field is None:
                    return False
                if str(filter_val).lower() not in str(doc_field).lower():
                    return False

        return True

    # =========================================================================
    # Phrase & Exact Matching Helpers
    # =========================================================================

    @staticmethod
    def _extract_quoted_phrases(query: str) -> Tuple[List[str], str]:
        """Extracts exact quoted phrases from a query string, returning phrases and remaining text."""
        phrases: List[str] = []
        pattern = r'"([^"]+)"|\'([^\']+)\''
        matches = re.findall(pattern, query)
        for m in matches:
            phrase = m[0] or m[1]
            if phrase.strip():
                phrases.append(phrase.strip())

        cleaned_query = re.sub(pattern, " ", query).strip()
        return phrases, cleaned_query

    @staticmethod
    def _check_phrase_in_text(phrase: str, text: str) -> bool:
        """Checks if a phrase appears as a normalized substring in text."""
        norm_phrase = TamilNormalizer.normalize(phrase).strip().lower()
        norm_text = TamilNormalizer.normalize(text).strip().lower()
        norm_phrase = re.sub(r"\s+", " ", norm_phrase)
        norm_text = re.sub(r"\s+", " ", norm_text)
        return norm_phrase in norm_text

    # =========================================================================
    # Search Execution
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        exact_terms: Optional[List[str]] = None,
        require_phrase: bool = False,
        primary_passages_only: bool = False,
    ) -> List[LexicalSearchResult]:
        """
        Executes BM25 lexical search over indexed classical Tamil literary passages.
        """
        if not self.bm25 or not self.documents:
            return []

        clean_query = query.strip()
        if not clean_query and not exact_terms and not filters:
            return []

        # 1. Parse quoted phrases and free-text terms
        quoted_phrases, remaining_query = self._extract_quoted_phrases(clean_query)
        all_terms_query = remaining_query + " " + " ".join(quoted_phrases)

        # Tokenize query
        raw_query_tokens = TamilTokenizer.tokenize_words(all_terms_query, remove_stopwords=False)
        query_tokens = [
            TamilNormalizer.normalize(t).lower()
            for t in raw_query_tokens
            if t.strip()
        ]

        # Tokenize exact terms if provided
        exact_token_filters: List[str] = []
        if exact_terms:
            for term in exact_terms:
                t_clean = TamilNormalizer.normalize(term).strip().lower()
                if t_clean:
                    exact_token_filters.append(t_clean)
                    if t_clean not in query_tokens:
                        query_tokens.append(t_clean)

        if not query_tokens and not filters:
            return []

        # 2. Compute BM25 raw scores across entire corpus
        if query_tokens:
            doc_scores = self.bm25.get_scores(query_tokens)
        else:
            doc_scores = [1.0] * len(self.documents)

        # 3. Post-score adjustment: Coordination bonus, exact terms, and phrase matching
        scored_candidates: List[Tuple[PassageDocument, float, float, List[str], bool]] = []
        max_raw_score = 0.0

        for idx, doc in enumerate(self.documents):
            # Apply metadata filters
            if primary_passages_only and doc.source_metadata.get("document_level") != "passage":
                continue

            if filters and not self._matches_filter(doc.source_metadata, filters):
                continue

            doc_tokens_set = set(doc.tokens)

            # Check exact term requirements
            if exact_token_filters:
                if not all(term in doc_tokens_set or any(term in t for t in doc.tokens) for term in exact_token_filters):
                    continue

            # Check matched query terms
            matched_terms = [t for t in query_tokens if t in doc_tokens_set or any(t in dt for dt in doc.tokens)]

            # Check phrase matching
            phrase_matched = False
            if quoted_phrases:
                phrase_matches = [
                    self._check_phrase_in_text(phrase, doc.text)
                    for phrase in quoted_phrases
                ]
                phrase_matched = all(phrase_matches) if phrase_matches else False
                if require_phrase and not phrase_matched:
                    continue
            elif len(query_tokens) >= 2 and clean_query:
                phrase_matched = self._check_phrase_in_text(clean_query, doc.text)
                if require_phrase and not phrase_matched:
                    continue

            raw_score = float(doc_scores[idx])

            # Apply term coordination factor (reward documents covering more distinct query terms)
            if query_tokens and len(query_tokens) > 1:
                coverage_ratio = len(matched_terms) / len(set(query_tokens))
                raw_score *= (0.5 + 0.5 * coverage_ratio)

            # Boost for phrase match
            if phrase_matched:
                raw_score *= 1.5

            if raw_score > 0.0 or exact_token_filters or filters:
                if raw_score > max_raw_score:
                    max_raw_score = raw_score
                scored_candidates.append((doc, raw_score, 0.0, matched_terms, phrase_matched))

        if not scored_candidates:
            return []

        # 4. Normalize BM25 score to [0.0, 1.0] range
        results: List[LexicalSearchResult] = []
        normalizer = max_raw_score if max_raw_score > 0 else 1.0

        for doc, raw_score, _, matched_terms, phrase_matched in scored_candidates:
            normalized_score = min(1.0, max(0.0, raw_score / normalizer))
            results.append(
                LexicalSearchResult(
                    passage_id=doc.passage_id,
                    text=doc.text,
                    source_metadata=doc.source_metadata,
                    score=round(normalized_score, 4),
                    raw_score=round(raw_score, 4),
                    matched_terms=matched_terms,
                    phrase_matched=phrase_matched,
                )
            )

        # 5. Sort by normalized score descending, then passage_id ascending for stability
        results.sort(key=lambda r: (-r.score, r.passage_id))
        return results[:top_k]

    def get_document_by_id(self, passage_id: str) -> Optional[PassageDocument]:
        """Retrieves an indexed document by its unique passage ID."""
        return self._doc_id_map.get(passage_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Returns statistics on the indexed literary corpus."""
        unique_works = set(d.source_metadata.get("work") for d in self.documents if d.source_metadata.get("work"))
        unique_sections = set(d.source_metadata.get("section") for d in self.documents if d.source_metadata.get("section"))
        unique_chapters = set(d.source_metadata.get("chapter") for d in self.documents if d.source_metadata.get("chapter"))
        unique_entities = set()
        unique_concepts = set()

        for d in self.documents:
            for e in d.source_metadata.get("entities", []):
                unique_entities.add(str(e))
            for c in d.source_metadata.get("concepts", []):
                unique_concepts.add(str(c))

        return {
            "total_documents": len(self.documents),
            "primary_passages": sum(1 for d in self.documents if d.source_metadata.get("document_level") == "passage"),
            "verse_line_passages": sum(1 for d in self.documents if d.source_metadata.get("document_level") == "verse_line"),
            "unique_works": len(unique_works),
            "unique_sections": len(unique_sections),
            "unique_chapters": len(unique_chapters),
            "unique_entities": len(unique_entities),
            "unique_concepts": len(unique_concepts),
            "corpus_hash": self._corpus_hash[:12] if self._corpus_hash else "",
            "bm25_model": "BM25Plus",
            "k1": self.k1,
            "b": self.b,
            "delta": self.delta,
            "persistent_cache": str(self.cache_path),
            "cache_exists": self.cache_path.exists(),
        }


# Singleton search engine instance initialized on startup
lexical_search_engine = LexicalSearchEngine()
