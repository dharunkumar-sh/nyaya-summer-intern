"""
XML Parser for Classical Tamil Literature Ingestion.
Parses TEI-compatible or structured XML representations of literary works, sections, verses, and commentaries.
Preserves original Classical Tamil text and metadata non-destructively.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
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
from utilities.tamil_text import normalize_tamil_text


class XmlLiteratureParser(BaseLiteratureParser):
    """Parses XML documents into structured Classical Tamil literature models."""

    def parse(
        self,
        content: str | bytes,
        filename: Optional[str] = None,
        default_work_id: Optional[str] = None,
        default_section_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ParsedLiteratureData:
        result = ParsedLiteratureData()

        if isinstance(content, str):
            xml_bytes = content.encode("utf-8")
        else:
            xml_bytes = content

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            result.errors.append(f"Invalid XML syntax: {e}")
            return result

        # Check if root is <work> or contains <work> children
        work_elem = root if root.tag.lower() == "work" else root.find(".//work")

        work_id = default_work_id or "imported-work"
        if work_elem is not None:
            w_id = work_elem.get("id") or work_elem.get("work_id")
            if w_id:
                work_id = generate_stable_slug(w_id)
            work = LiteratureWork(
                work_id=work_id,
                title_tamil=work_elem.get("title_tamil", work_elem.get("name_tamil", "தமிழ் நூல்")),
                title_english=work_elem.get("title_english", work_elem.get("name_english", work_id.capitalize())),
                author=work_elem.get("author"),
                period=work_elem.get("period", "Classical Sangam"),
                category=work_elem.get("category", "Grammar & Poetics"),
                description=work_elem.get("description"),
            )
            result.work = work
        else:
            result.work = LiteratureWork(
                work_id=work_id,
                title_tamil="தமிழ் இலக்கியம்",
                title_english=work_id.capitalize(),
                period="Classical Sangam",
                category="Classical Literature",
            )

        # Parse Sections
        section_elems = root.findall(".//section")
        sections_map: Dict[str, LiterarySection] = {}

        if not section_elems:
            # Fallback to single default section
            sec_id = default_section_id or f"{work_id}-sec-1"
            sec = LiterarySection(
                id=sec_id,
                work_id=work_id,
                order_index=1,
                name_tamil="முதன்மைப் பகுதி",
                name_english="Primary Section",
                section_type="section",
            )
            sections_map[sec_id] = sec
            result.sections.append(sec)
        else:
            for s_idx, s_elem in enumerate(section_elems, start=1):
                raw_sec_id = s_elem.get("id") or s_elem.get("section_id") or str(s_idx)
                sec_id = f"{work_id}-{generate_stable_slug(raw_sec_id)}"
                sec = LiterarySection(
                    id=sec_id,
                    work_id=work_id,
                    order_index=s_idx,
                    name_tamil=s_elem.get("name_tamil", f"பகுதி {s_idx}"),
                    name_english=s_elem.get("name_english", f"Section {s_idx}"),
                    section_type=s_elem.get("type", s_elem.get("section_type", "section")),
                    description=s_elem.get("description"),
                )
                sections_map[sec_id] = sec
                result.sections.append(sec)

        # Parse Passages (either under sections or at root level)
        passage_elems = root.findall(".//passage")
        if not passage_elems:
            passage_elems = root.findall(".//sutra")
        if not passage_elems:
            passage_elems = root.findall(".//verse")

        order_seq = 0
        for p_elem in passage_elems:
            order_seq += 1
            num_str = p_elem.get("number") or p_elem.get("passage_number") or p_elem.get("sutra_number")
            try:
                p_num = int(num_str) if num_str else order_seq
            except ValueError:
                p_num = order_seq

            # Identify section
            sec_ref = p_elem.get("section_id") or p_elem.get("section")
            if sec_ref and f"{work_id}-{generate_stable_slug(sec_ref)}" in sections_map:
                sec_id = f"{work_id}-{generate_stable_slug(sec_ref)}"
            elif result.sections:
                sec_id = result.sections[0].id
            else:
                sec_id = f"{work_id}-sec-1"

            # Extract text preserving exact content
            text_elem = None
            for tag in ("text", "original_text", "tamil_text"):
                found = p_elem.find(tag)
                if found is not None:
                    text_elem = found
                    break

            if text_elem is not None and text_elem.text:
                raw_text = text_elem.text.strip("\r\n")
            elif p_elem.text and p_elem.text.strip():
                raw_text = p_elem.text.strip("\r\n")
            else:
                raw_text = ""

            if not raw_text:
                result.warnings.append(f"Passage {p_num}: Missing text content. Skipping.")
                continue

            p_id = p_elem.get("id") or f"{sec_id}-{p_num:04d}"

            # Extract lines if any
            lines = []
            for l_idx, l_elem in enumerate(p_elem.findall("line"), start=1):
                if l_elem.text:
                    lines.append(
                        VerseLine(
                            line_number=int(l_elem.get("number", l_idx)),
                            original_text=l_elem.text.strip("\r\n"),
                            transliteration=l_elem.get("transliteration"),
                        )
                    )

            # Extract translations and transliterations
            translit_elem = None
            for tag in ("transliteration", "roman"):
                found = p_elem.find(tag)
                if found is not None:
                    translit_elem = found
                    break
            translit = translit_elem.text.strip() if translit_elem is not None and translit_elem.text else p_elem.get("transliteration")

            trans_elem = None
            for tag in ("translation", "english"):
                found = p_elem.find(tag)
                if found is not None:
                    trans_elem = found
                    break
            translation = trans_elem.text.strip() if trans_elem is not None and trans_elem.text else p_elem.get("translation")

            # Extract commentaries
            commentaries = []
            comm_elems = p_elem.findall("commentary")
            if not comm_elems:
                comm_elems = p_elem.findall("urai")

            for c_idx, c_elem in enumerate(comm_elems, start=1):
                comm_author = c_elem.get("commentator") or c_elem.get("author") or "Commentator"
                comm_text = c_elem.text.strip() if c_elem.text else ""
                if comm_text:
                    c_id = f"{p_id}-comm-{generate_stable_slug(comm_author)}"
                    comm = Commentary(
                        id=c_id,
                        commentator=comm_author,
                        original_text=comm_text,
                        english_translation=c_elem.get("translation"),
                        notes=c_elem.get("notes"),
                    )
                    commentaries.append(comm)
                    result.commentaries.append(comm)

            passage = LiteraryPassage(
                id=p_id,
                work_id=work_id,
                section_id=sec_id,
                order_index=order_seq,
                passage_number=p_num,
                original_text=raw_text,
                normalized_search_text=normalize_tamil_text(raw_text).lower(),
                transliteration=translit,
                english_translation=translation,
                tinai=p_elem.get("tinai"),
                category=p_elem.get("category"),
                lines=lines,
                commentaries=commentaries,
            )
            result.passages.append(passage)

        result.work.total_sections = len(result.sections)
        result.work.total_passages = len(result.passages)
        return result
