"""
JSON Parser for Classical Tamil Literature Ingestion.
Parses canonical Tolkāppiyam structures and modular multi-work literature schemas.
Preserves original Classical Tamil text and metadata non-destructively.
"""
from __future__ import annotations

import json
from typing import Optional, Dict, Any, List

from ingestion.parsers.base_parser import (
    BaseLiteratureParser,
    ParsedLiteratureData,
    generate_stable_slug,
)
from models.corpus import (
    LiteratureWork,
    LiterarySection,
    LiteraryPassage,
    Commentary,
    VerseLine,
    KnowledgeTriple,
)
from models.enums import HierarchyLevel
from utilities.tamil_text import normalize_tamil_text


class JsonLiteratureParser(BaseLiteratureParser):
    """Parses JSON content into structured literature entities."""

    def parse(
        self,
        content: str | bytes,
        filename: Optional[str] = None,
        default_work_id: Optional[str] = None,
        default_section_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ParsedLiteratureData:
        result = ParsedLiteratureData()

        if isinstance(content, bytes):
            text_content = content.decode("utf-8", errors="replace")
        else:
            text_content = str(content)

        try:
            raw_data = json.loads(text_content)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON syntax: {e}")
            return result

        # Check if canonical Tolkāppiyam structure
        if isinstance(raw_data, dict) and "corpus_metadata" in raw_data and "canonical_sutras" in raw_data:
            return self._parse_canonical_format(raw_data, filename)

        # Check if modular structured format: {"work": ..., "sections": ..., "passages": ...}
        if isinstance(raw_data, dict) and ("work" in raw_data or "passages" in raw_data or "sections" in raw_data):
            return self._parse_modular_format(raw_data, filename, default_work_id, default_section_id)

        # Check if raw array of passages
        if isinstance(raw_data, list):
            return self._parse_passages_list(raw_data, default_work_id, default_section_id)

        result.errors.append("Unrecognized JSON literature structure.")
        return result

    def _parse_canonical_format(self, data: dict, filename: Optional[str]) -> ParsedLiteratureData:
        result = ParsedLiteratureData()
        meta = data.get("corpus_metadata", {})
        canonical_sutras = data.get("canonical_sutras", [])

        work_id = "tolkappiyam"
        work = LiteratureWork(
            work_id=work_id,
            title_tamil=meta.get("tamil_name", "தொல்காப்பியம்"),
            title_english="Tolkāppiyam",
            author=meta.get("author", "Tolkāppiyar"),
            period=meta.get("period", "Classical Sangam / Pre-Sangam"),
            category="Grammar & Poetics",
            total_sections=meta.get("books_count", 3),
            total_passages=meta.get("total_sutras", len(canonical_sutras)),
            description="Canonical Classical Tamil treatise on orthography, phonology, morphology, syntax, and poetics.",
            level=HierarchyLevel.L0_CORPUS,
        )
        result.work = work

        # Sections
        section_map: Dict[str, LiterarySection] = {}
        for idx, book in enumerate(meta.get("books", []), start=1):
            sec_id = f"{work_id}-{book.get('id', str(idx))}"
            section = LiterarySection(
                id=sec_id,
                work_id=work_id,
                order_index=idx,
                name_tamil=book.get("name", ""),
                name_english=book.get("english", book.get("name", "")),
                section_type="atikāram",
                total_passages=book.get("sutra_count", 0),
                description=book.get("english", ""),
            )
            result.sections.append(section)
            # Map by both book id and book name
            section_map[book.get("id", "").lower()] = section
            section_map[book.get("name", "").split()[0].lower()] = section

        # Passages
        for idx, s in enumerate(canonical_sutras, start=1):
            p_num = s.get("sutra_number", idx)
            atikaram_name = s.get("atikaram", "general").lower()

            matched_sec = None
            for key, sec in section_map.items():
                if key in atikaram_name or atikaram_name in key:
                    matched_sec = sec
                    break

            sec_id = matched_sec.id if matched_sec else f"{work_id}-default"
            raw_text = s.get("tamil_text", "")

            # Non-destructive search projection
            search_proj = normalize_tamil_text(raw_text).lower()

            triples = [
                KnowledgeTriple(
                    subject=t.get("subject", ""),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                )
                for t in s.get("triples", [])
                if isinstance(t, dict) and t.get("subject") and t.get("predicate") and t.get("object")
            ]

            passage_id = s.get("id") or f"{sec_id}-{p_num:04d}"

            passage = LiteraryPassage(
                id=passage_id,
                work_id=work_id,
                section_id=sec_id,
                order_index=idx,
                passage_number=p_num,
                original_text=raw_text,
                normalized_search_text=search_proj,
                transliteration=s.get("transliteration"),
                english_translation=s.get("english_translation"),
                category=s.get("category"),
                tinai=s.get("tinai"),
                entities=s.get("entities", []),
                triples=triples,
                metadata={"iyal": s.get("iyal"), "nyaya_mapping": s.get("nyaya_mapping")},
            )
            result.passages.append(passage)

        return result

    def _parse_modular_format(
        self,
        data: dict,
        filename: Optional[str],
        default_work_id: Optional[str],
        default_section_id: Optional[str],
    ) -> ParsedLiteratureData:
        result = ParsedLiteratureData()

        # Parse Work
        work_raw = data.get("work")
        if work_raw:
            w_id = work_raw.get("work_id") or default_work_id or generate_stable_slug(work_raw.get("title_english", "work"))
            work = LiteratureWork(
                work_id=w_id,
                title_tamil=work_raw.get("title_tamil", "தமிழ் நூல்"),
                title_english=work_raw.get("title_english", "Tamil Work"),
                author=work_raw.get("author"),
                period=work_raw.get("period", "Classical Sangam"),
                category=work_raw.get("category", "Classical Literature"),
                total_sections=work_raw.get("total_sections", 0),
                total_passages=work_raw.get("total_passages", 0),
                description=work_raw.get("description"),
                metadata=work_raw.get("metadata", {}),
            )
            result.work = work
            current_work_id = w_id
        else:
            current_work_id = default_work_id or "imported-work"

        # Parse Sections
        sections_raw = data.get("sections", [])
        for idx, s in enumerate(sections_raw, start=1):
            s_id = s.get("id") or f"{current_work_id}-{generate_stable_slug(s.get('name_english', str(idx)))}"
            section = LiterarySection(
                id=s_id,
                work_id=current_work_id,
                order_index=s.get("order_index", idx),
                name_tamil=s.get("name_tamil", f"பகுதி {idx}"),
                name_english=s.get("name_english", f"Section {idx}"),
                section_type=s.get("section_type", "section"),
                parent_section_id=s.get("parent_section_id"),
                total_passages=s.get("total_passages", 0),
                description=s.get("description"),
                metadata=s.get("metadata", {}),
            )
            result.sections.append(section)

        # Parse Passages
        passages_raw = data.get("passages", [])
        for idx, p in enumerate(passages_raw, start=1):
            sec_id = p.get("section_id") or default_section_id or (result.sections[0].id if result.sections else f"{current_work_id}-sec-1")
            p_num = p.get("passage_number", idx)
            p_id = p.get("id") or f"{sec_id}-{p_num:04d}"
            raw_text = p.get("original_text") or p.get("tamil_text") or ""

            # Extract lines if provided
            lines = [
                VerseLine(
                    line_number=l.get("line_number", l_idx),
                    original_text=l.get("original_text", ""),
                    transliteration=l.get("transliteration"),
                )
                for l_idx, l in enumerate(p.get("lines", []), start=1)
                if isinstance(l, dict) and l.get("original_text")
            ]

            # Extract commentaries
            commentaries = []
            for c_idx, c in enumerate(p.get("commentaries", []), start=1):
                c_id = c.get("id") or f"{p_id}-comm-{generate_stable_slug(c.get('commentator', str(c_idx)))}"
                comm = Commentary(
                    id=c_id,
                    commentator=c.get("commentator", "Commentator"),
                    original_text=c.get("original_text", ""),
                    transliteration=c.get("transliteration"),
                    english_translation=c.get("english_translation"),
                    notes=c.get("notes"),
                )
                commentaries.append(comm)
                result.commentaries.append(comm)

            passage = LiteraryPassage(
                id=p_id,
                work_id=current_work_id,
                section_id=sec_id,
                order_index=p.get("order_index", idx),
                passage_number=p_num,
                original_text=raw_text,
                normalized_search_text=normalize_tamil_text(raw_text).lower() if raw_text else "",
                transliteration=p.get("transliteration"),
                english_translation=p.get("english_translation"),
                category=p.get("category"),
                tinai=p.get("tinai"),
                lines=lines,
                commentaries=commentaries,
                entities=p.get("entities", []),
                metadata=p.get("metadata", {}),
            )
            result.passages.append(passage)

        return result

    def _parse_passages_list(
        self,
        passages_list: list,
        default_work_id: Optional[str],
        default_section_id: Optional[str],
    ) -> ParsedLiteratureData:
        data = {"passages": passages_list}
        return self._parse_modular_format(data, None, default_work_id, default_section_id)
