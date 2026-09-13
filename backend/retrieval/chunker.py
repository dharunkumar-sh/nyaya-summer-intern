"""
Passage chunker for Classical Tamil literary texts.

Transforms ProcessedPassages and canonical sūtras into granular, source-traceable
retrieval chunks preserving all provenance metadata.

Chunk Schema Contract
---------------------
- chunk_id: str
- document_id: str
- work: str
- section: str
- passage_id: str
- text: str
- source: str
- metadata: dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class RetrievalChunk:
    """
    Standard RAG retrieval chunk retaining full provenance.
    """
    chunk_id: str
    document_id: str
    work: str
    section: str
    passage_id: str
    text: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Returns serializable dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "work": self.work,
            "section": self.section,
            "passage_id": self.passage_id,
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata,
        }


class PassageChunker:
    """
    Segments classical Tamil literary passages into retrieval chunks.
    Ensures that every chunk retains source citations and metadata.
    """

    @classmethod
    def chunk_passage(
        cls,
        passage: Dict[str, Any],
        chunk_by_verse_lines: bool = False,
    ) -> List[RetrievalChunk]:
        """
        Extracts chunks from a single passage or sūtra.
        If chunk_by_verse_lines is True and multiple lines exist, chunks each verse line.
        Otherwise, creates a primary chunk for the whole sūtra/passage.
        """
        doc_id = passage.get("document_id") or passage.get("id", "doc_unknown")
        work = passage.get("work", "Tolkāppiyam")
        section = passage.get("section") or passage.get("atikaram", "Poruḷatikāram")
        chapter = passage.get("chapter") or passage.get("iyal", "Akattiṇaiyiyal")
        passage_id = passage.get("passage_id") or doc_id

        # Human-readable full source citation
        sutra_num = passage.get("metadata", {}).get("sutra_number") or passage.get("sutra_number", "")
        citation_num = f" Sūtra {sutra_num}" if sutra_num else ""
        source_citation = f"{work} {section} {chapter}{citation_num}".strip()

        # Extract text & metadata
        full_text = (
            passage.get("normalized_text")
            or passage.get("original_text")
            or passage.get("tamil_text", "")
        ).strip()
        translation = (
            passage.get("metadata", {}).get("english_translation")
            or passage.get("english_translation", "")
        )
        tinai = passage.get("metadata", {}).get("tinai") or passage.get("tinai", "General")
        category = passage.get("metadata", {}).get("category") or passage.get("category", "General")
        entities = passage.get("metadata", {}).get("entities") or passage.get("entities", [])
        triples = passage.get("metadata", {}).get("triples") or passage.get("triples", [])

        chunks: List[RetrievalChunk] = []

        # 1. Primary Sūtra / Passage-level Chunk
        primary_chunk = RetrievalChunk(
            chunk_id=f"chk-{doc_id}-primary",
            document_id=doc_id,
            work=work,
            section=f"{section} • {chapter}",
            passage_id=passage_id,
            text=full_text,
            source=source_citation,
            metadata={
                "chunk_type": "passage",
                "work": work,
                "section": section,
                "chapter": chapter,
                "verse": sutra_num,
                "tinai": tinai,
                "category": category,
                "entities": entities,
                "triples": triples,
                "translation": translation,
                "sutra_number": sutra_num,
                "tokens": passage.get("tokens", []),
            },
        )
        chunks.append(primary_chunk)

        # 2. Granular verse-line chunks (if requested and lines exist)
        if chunk_by_verse_lines:
            verse_lines = passage.get("verse_lines") or [line.strip() for line in full_text.split("\n") if line.strip()]
            if len(verse_lines) > 1:
                for idx, line in enumerate(verse_lines):
                    line_chunk = RetrievalChunk(
                        chunk_id=f"chk-{doc_id}-line-{idx + 1}",
                        document_id=doc_id,
                        work=work,
                        section=f"{section} • {chapter}",
                        passage_id=passage_id,
                        text=line,
                        source=f"{source_citation} (Line {idx + 1})",
                        metadata={
                            "chunk_type": "line",
                            "work": work,
                            "section": section,
                            "chapter": chapter,
                            "verse": sutra_num,
                            "line_number": idx + 1,
                            "parent_chunk_id": primary_chunk.chunk_id,
                            "tinai": tinai,
                            "category": category,
                            "entities": entities,
                            "translation": translation,
                        },
                    )
                    chunks.append(line_chunk)

        return chunks

    @classmethod
    def chunk_corpus(
        cls,
        passages: List[Dict[str, Any]],
        chunk_by_verse_lines: bool = False,
    ) -> List[RetrievalChunk]:
        """
        Chunks an entire corpus of passages or canonical sūtras.
        """
        all_chunks: List[RetrievalChunk] = []
        for p in passages:
            chunks = cls.chunk_passage(p, chunk_by_verse_lines=chunk_by_verse_lines)
            all_chunks.extend(chunks)
        return all_chunks
