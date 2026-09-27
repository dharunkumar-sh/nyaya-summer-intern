"""
CSV Parser for Classical Tamil Literature Ingestion.
Parses tabular representations of verses, sūtras, translations, and commentaries.
Preserves original Classical Tamil text and metadata non-destructively.
"""
from __future__ import annotations

import csv
import io
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
)
from utilities.tamil_text import normalize_tamil_text


class CsvLiteratureParser(BaseLiteratureParser):
    """Parses tabular CSV datasets into structured Classical Tamil literature entities."""

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
            text_content = content.decode("utf-8-sig", errors="replace")
        else:
            text_content = str(content)

        if not text_content.strip():
            result.errors.append("CSV content is empty.")
            return result

        reader = csv.DictReader(io.StringIO(text_content))
        if not reader.fieldnames:
            result.errors.append("CSV header row missing or empty.")
            return result

        # Normalize field names to lowercase stripped
        field_map = {fn.strip().lower(): fn for fn in reader.fieldnames if fn}

        def get_col(row: dict, *candidates: str) -> Optional[str]:
            for cand in candidates:
                if cand in field_map:
                    val = row.get(field_map[cand])
                    if val is not None and str(val).strip():
                        return str(val).strip()
            return None

        work_id = default_work_id or "imported-literature"
        sections_by_id: Dict[str, LiterarySection] = {}
        passages_list: List[LiteraryPassage] = []

        work_title_tamil = options.get("work_title_tamil") if options else None
        work_title_english = options.get("work_title_english") if options else None

        for row_idx, row in enumerate(reader, start=1):
            row_work = get_col(row, "work_id", "work", "work_title", "title")
            if row_work:
                work_id = generate_stable_slug(row_work)
                if not work_title_english:
                    work_title_english = row_work

            sec_name = get_col(row, "section_name", "section", "section_id", "atikaram", "iyal") or default_section_id or "general"
            sec_id = f"{work_id}-{generate_stable_slug(sec_name)}"

            if sec_id not in sections_by_id:
                section = LiterarySection(
                    id=sec_id,
                    work_id=work_id,
                    order_index=len(sections_by_id) + 1,
                    name_tamil=get_col(row, "section_tamil", "section_name_tamil") or sec_name,
                    name_english=sec_name,
                    section_type=get_col(row, "section_type") or "section",
                )
                sections_by_id[sec_id] = section

            p_num_str = get_col(row, "passage_number", "sutra_number", "verse_number", "number")
            try:
                p_num = int(p_num_str) if p_num_str else row_idx
            except ValueError:
                p_num = row_idx

            raw_text = get_col(row, "original_text", "tamil_text", "text", "verse_text", "sutra_text") or ""
            if not raw_text:
                result.warnings.append(f"Row {row_idx}: Empty text encountered. Skipping.")
                continue

            custom_id = get_col(row, "id", "passage_id")
            passage_id = custom_id or f"{sec_id}-{p_num:04d}"

            translit = get_col(row, "transliteration", "translit")
            translation = get_col(row, "english_translation", "translation", "english")
            tinai = get_col(row, "tinai", "landscape")
            category = get_col(row, "category", "subject")

            # Extract commentary if row provides commentary columns
            commentaries = []
            comm_text = get_col(row, "commentary", "commentary_text", "urai")
            if comm_text:
                commentator = get_col(row, "commentator", "uraiyasiriyar") or "Traditional Commentator"
                comm_id = f"{passage_id}-comm-{generate_stable_slug(commentator)}"
                comm = Commentary(
                    id=comm_id,
                    commentator=commentator,
                    original_text=comm_text,
                    english_translation=get_col(row, "commentary_translation"),
                )
                commentaries.append(comm)
                result.commentaries.append(comm)

            passage = LiteraryPassage(
                id=passage_id,
                work_id=work_id,
                section_id=sec_id,
                order_index=row_idx,
                passage_number=p_num,
                original_text=raw_text,
                normalized_search_text=normalize_tamil_text(raw_text).lower(),
                transliteration=translit,
                english_translation=translation,
                category=category,
                tinai=tinai,
                commentaries=commentaries,
            )
            passages_list.append(passage)

        result.work = LiteratureWork(
            work_id=work_id,
            title_tamil=work_title_tamil or "தமிழ் இலக்கியம்",
            title_english=work_title_english or work_id.capitalize(),
            period="Classical Sangam",
            category="Classical Literature",
            total_sections=len(sections_by_id),
            total_passages=len(passages_list),
        )
        result.sections = list(sections_by_id.values())
        result.passages = passages_list

        return result
