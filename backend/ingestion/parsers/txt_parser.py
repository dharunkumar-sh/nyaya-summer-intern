"""
Plain Text (TXT) Parser for Classical Tamil Literature Ingestion.
Parses structured text corpora with section headers, numbered passages, and commentary markers.
Preserves original Classical Tamil text and metrical structure non-destructively.
"""
from __future__ import annotations

import re
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
)
from utilities.tamil_text import normalize_tamil_text, is_tamil_text


class TxtLiteratureParser(BaseLiteratureParser):
    """Parses formatted plain text documents into structured Classical Tamil literature entities."""

    WORK_HEADER_RE = re.compile(r"^(?:={3,}\s*WORK:?|\[WORK:?)\s*(.+?)(?:\s*={3,}|\])$", re.IGNORECASE)
    SEC_HEADER_RE = re.compile(r"^(?:={3,}\s*SECTION:?|\[SECTION:?)\s*(.+?)(?:\s*={3,}|\])$", re.IGNORECASE)
    PASSAGE_MARKER_RE = re.compile(r"^(?:-{3,}\s*PASSAGE:?\s*(\d+)(?:\s*-{3,})?|\[PASSAGE:?\s*(\d+)\]|(\d+)\.\s*(.+))$", re.IGNORECASE)
    COMM_MARKER_RE = re.compile(r"^\[(?:COMMENTARY|URAI)(?::\s*([^\]]+))?\]\s*(.*)$", re.IGNORECASE)
    TRANS_MARKER_RE = re.compile(r"^\[(?:TRANSLATION|ENGLISH)(?::\s*([^\]]+))?\]\s*(.*)$", re.IGNORECASE)
    TRANSLIT_MARKER_RE = re.compile(r"^\[(?:TRANSLITERATION|ROMAN)(?::\s*([^\]]+))?\]\s*(.*)$", re.IGNORECASE)
    TINAI_MARKER_RE = re.compile(r"^\[TINAI(?::\s*([^\]]+))?\]\s*(.*)$", re.IGNORECASE)

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
            text = content.decode("utf-8", errors="replace")
        else:
            text = str(content)

        lines = text.splitlines()
        if not lines:
            result.errors.append("Text content is empty.")
            return result

        current_work_id = default_work_id or "imported-work"
        current_work_title = "Classical Tamil Work"
        current_work_tamil = "செவ்விலக்கியம்"

        current_sec_id = default_section_id or f"{current_work_id}-sec-1"
        current_sec_name = "Primary Section"
        current_sec_tamil = "முதன்மைப் பகுதி"

        sections_map: Dict[str, LiterarySection] = {}
        passages: List[LiteraryPassage] = []

        current_passage_num = 1
        current_passage_lines: List[str] = []
        current_translation: Optional[str] = None
        current_translit: Optional[str] = None
        current_tinai: Optional[str] = None
        current_commentaries: List[Commentary] = []

        def flush_passage():
            nonlocal current_passage_lines, current_translation, current_translit, current_tinai, current_commentaries
            if not current_passage_lines:
                return

            raw_text = "\n".join(current_passage_lines).strip()
            if not raw_text:
                return

            if current_sec_id not in sections_map:
                sections_map[current_sec_id] = LiterarySection(
                    id=current_sec_id,
                    work_id=current_work_id,
                    order_index=len(sections_map) + 1,
                    name_tamil=current_sec_tamil,
                    name_english=current_sec_name,
                    section_type="section",
                )

            p_id = f"{current_sec_id}-{current_passage_num:04d}"

            verse_lines = [
                VerseLine(line_number=i, original_text=l)
                for i, l in enumerate(current_passage_lines, start=1)
                if l.strip()
            ]

            passage = LiteraryPassage(
                id=p_id,
                work_id=current_work_id,
                section_id=current_sec_id,
                order_index=len(passages) + 1,
                passage_number=current_passage_num,
                original_text=raw_text,
                normalized_search_text=normalize_tamil_text(raw_text).lower(),
                transliteration=current_translit,
                english_translation=current_translation,
                tinai=current_tinai,
                lines=verse_lines,
                commentaries=list(current_commentaries),
            )
            passages.append(passage)

            # Reset
            current_passage_lines = []
            current_translation = None
            current_translit = None
            current_tinai = None
            current_commentaries = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 1. Work Header
            work_match = self.WORK_HEADER_RE.match(line_str)
            if work_match:
                flush_passage()
                work_info = work_match.group(1).split("|")
                current_work_id = generate_stable_slug(work_info[0].strip())
                current_work_title = work_info[0].strip()
                if len(work_info) > 1:
                    current_work_tamil = work_info[1].strip()
                continue

            # 2. Section Header
            sec_match = self.SEC_HEADER_RE.match(line_str)
            if sec_match:
                flush_passage()
                sec_info = sec_match.group(1).split("|")
                current_sec_name = sec_info[0].strip()
                current_sec_id = f"{current_work_id}-{generate_stable_slug(current_sec_name)}"
                current_sec_tamil = sec_info[1].strip() if len(sec_info) > 1 else current_sec_name
                if current_sec_id not in sections_map:
                    sections_map[current_sec_id] = LiterarySection(
                        id=current_sec_id,
                        work_id=current_work_id,
                        order_index=len(sections_map) + 1,
                        name_tamil=current_sec_tamil,
                        name_english=current_sec_name,
                        section_type="section",
                    )
                continue

            # 3. Passage Marker
            pas_match = self.PASSAGE_MARKER_RE.match(line_str)
            if pas_match:
                flush_passage()
                # Determine passage number
                num_str = pas_match.group(1) or pas_match.group(2) or pas_match.group(3)
                if num_str:
                    try:
                        current_passage_num = int(num_str)
                    except ValueError:
                        current_passage_num = len(passages) + 1
                else:
                    current_passage_num = len(passages) + 1

                # If group 4 exists (e.g. "1. Tamil verse text on same line")
                if pas_match.group(4):
                    current_passage_lines.append(pas_match.group(4).strip())
                continue

            # 4. Translation marker
            trans_match = self.TRANS_MARKER_RE.match(line_str)
            if trans_match:
                val = trans_match.group(2) or trans_match.group(1) or ""
                current_translation = val.strip()
                continue

            # 5. Transliteration marker
            translit_match = self.TRANSLIT_MARKER_RE.match(line_str)
            if translit_match:
                val = translit_match.group(2) or translit_match.group(1) or ""
                current_translit = val.strip()
                continue

            # 6. Tinai marker
            tinai_match = self.TINAI_MARKER_RE.match(line_str)
            if tinai_match:
                val = tinai_match.group(2) or tinai_match.group(1) or ""
                current_tinai = val.strip()
                continue

            # 7. Commentary marker
            comm_match = self.COMM_MARKER_RE.match(line_str)
            if comm_match:
                commentator = comm_match.group(1) or "Urai"
                comm_text = comm_match.group(2) or ""
                comm_id = f"{current_sec_id}-{current_passage_num:04d}-comm-{generate_stable_slug(commentator)}"
                comm = Commentary(
                    id=comm_id,
                    commentator=commentator.strip(),
                    original_text=comm_text.strip(),
                )
                current_commentaries.append(comm)
                result.commentaries.append(comm)
                continue

            # Regular verse line preserving original text
            current_passage_lines.append(line)

        flush_passage()

        if not sections_map:
            sec_id = f"{current_work_id}-default"
            sections_map[sec_id] = LiterarySection(
                id=sec_id,
                work_id=current_work_id,
                order_index=1,
                name_tamil=current_sec_tamil,
                name_english=current_sec_name,
                section_type="section",
            )

        result.work = LiteratureWork(
            work_id=current_work_id,
            title_tamil=current_work_tamil,
            title_english=current_work_title,
            period="Classical Sangam",
            category="Classical Literature",
            total_sections=len(sections_map),
            total_passages=len(passages),
        )
        result.sections = list(sections_map.values())
        result.passages = passages
        return result
