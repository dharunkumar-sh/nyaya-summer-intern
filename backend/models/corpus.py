"""
Domain Models for Classical Tamil Corpus, Literature, and Ontological Structures.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from models.enums import AtikaramType, TinaiType, HierarchyLevel


class KnowledgeTriple(BaseModel):
    """Tripartite semantic relationship extracted from canonical literary text."""
    subject: str = Field(..., description="Entity or conceptual subject of relation")
    predicate: str = Field(..., description="Ontological or poetic predicate relation")
    object: str = Field(..., description="Target object or concept")


class NyayaMapping(BaseModel):
    """Epistemic mapping of literature rule into Nyāya epistemological structure."""
    member: Optional[str] = Field(None, description="Pañcāvayava syllogistic component (Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana)")
    pramana: Optional[str] = Field(None, description="Epistemic warrant (Pratyakṣa, Anumāna, Upamāna, Śabda)")
    axiom: Optional[str] = Field(None, description="Formalized symbolic proposition")


class Sutra(BaseModel):
    """Individual Classical Tamil Sūtra (Aphorism / Verse)."""
    id: str = Field(..., description="Unique persistent identifier, e.g. tol-porul-akam-003")
    sutra_number: int = Field(..., description="Ordinal sūtra number within context")
    atikaram: str = Field(..., description="Parent Atikāram name or identifier")
    iyal: str = Field(..., description="Parent Iyal (chapter) name")
    tamil_text: str = Field(..., description="Original Tamil script poetic verse")
    transliteration: Optional[str] = Field(None, description="ISO 15919 transliteration")
    english_translation: Optional[str] = Field(None, description="Scholarly English translation")
    category: Optional[str] = Field(None, description="Literary, grammatical or philosophical categorization")
    tinai: Optional[str] = Field(None, description="Poetic landscape or context (Akam/Puram)")
    entities: List[str] = Field(default_factory=list, description="Extracted domain entities")
    triples: List[KnowledgeTriple] = Field(default_factory=list, description="Extracted knowledge triples")
    nyaya_mapping: Optional[NyayaMapping] = Field(None, description="Nyāya epistemological alignment")


class Iyal(BaseModel):
    """Iyal (Chapter) within an Atikāram."""
    id: str = Field(..., description="Normalized identifier for the Iyal")
    name: str = Field(..., description="Tamil / Romanized title of the Iyal")
    atikaram_id: str = Field(..., description="Parent Atikāram ID")
    sutra_count: int = Field(0, description="Total number of sūtras contained")
    sutras: List[Sutra] = Field(default_factory=list, description="Member sūtras")


class Atikaram(BaseModel):
    """Atikāram (Book / Major Section) of Tolkāppiyam."""
    id: str = Field(..., description="Identifier: eluttu, col, porul")
    name: str = Field(..., description="Full book title in Tamil and English")
    english: str = Field(..., description="English scholarly title")
    sutra_count: int = Field(..., description="Canonical number of sūtras")
    iyals: List[str] = Field(default_factory=list, description="Ordered list of chapter names")


class TinaiLandscape(BaseModel):
    """Tiṇai Poetic Matrix representation."""
    tinai: str = Field(..., description="Landscape name (e.g. Kuriñci)")
    landscape: str = Field(..., description="Geographical ecology (e.g. Mountainous)")
    season: str = Field(..., description="Climatic season (Kalam)")
    time_of_day: str = Field(..., description="Time of day (Yāmam, etc.)")
    deity: str = Field(..., description="Presiding deity (Ceyōṉ, etc.)")
    primary_sentiment: str = Field(..., description="Uripporuḷ (psychological mood)")
    associated_sutras: List[str] = Field(default_factory=list, description="Identifiers of grounding sūtras")


class CorpusMetadata(BaseModel):
    """Global Corpus Metadata for Tolkāppiyam."""
    name: str = Field(..., description="Full corpus title")
    period: str = Field(..., description="Historical composition period")
    total_sutras: int = Field(..., description="Total canonical sūtra count")
    books_count: int = Field(..., description="Number of constituent books (atikārams)")
    books: List[Atikaram] = Field(default_factory=list, description="Book manifests")


class ProvenanceRecord(BaseModel):
    """Provenance and audit metadata for ingested Classical Tamil literary sources."""
    source_filename: Optional[str] = Field(None, description="Original source file name or identifier")
    file_format: str = Field(..., description="Source format: json, csv, txt, xml")
    checksum: str = Field(..., description="SHA-256 cryptographic checksum of original raw content")
    ingested_at: str = Field(..., description="ISO 8601 UTC timestamp of ingestion")
    editor_or_compiler: Optional[str] = Field(None, description="Scholarly editor or critical edition compiler")
    edition: Optional[str] = Field(None, description="Critical edition publication detail")
    source_url: Optional[str] = Field(None, description="Digital archive source URL or repository origin")
    raw_content_length: int = Field(0, description="Byte length of pristine ingested payload")


class Commentary(BaseModel):
    """Classical or modern commentary (Urai) associated with a passage or verse."""
    id: str = Field(..., description="Stable commentary identifier, e.g. comm-ilampuranam-003")
    commentator: str = Field(..., description="Commentator name (e.g. Iḷampūraṇar, Cēṉāvaraiyar, Naccināṟkkiṉiyar, Parimēlaḻakar)")
    original_text: str = Field(..., description="Pristine, unmodified Classical Tamil commentary text")
    transliteration: Optional[str] = Field(None, description="ISO 15919 transliteration of commentary")
    english_translation: Optional[str] = Field(None, description="Scholarly English translation of commentary")
    notes: Optional[str] = Field(None, description="Philological and semantic footnotes")


class VerseLine(BaseModel):
    """Individual line (Aṭi) within a Classical Tamil metrical verse (Ceyyuḷ / Pāṭal)."""
    line_number: int = Field(..., description="1-indexed line order within verse")
    original_text: str = Field(..., description="Pristine Tamil line preserving metrical structure and sandhi")
    transliteration: Optional[str] = Field(None, description="Transliteration of line")


class LiteraryPassage(BaseModel):
    """
    Individual Classical Tamil passage, verse (ceyyuḷ), or aphorism (sūtra).
    Preserves original, unmodified literary text alongside non-destructive search projections.
    """
    id: str = Field(..., description="Stable deterministic identifier, e.g. tolkappiyam-porul-003")
    work_id: str = Field(..., description="Foreign key to parent LiteraryWork")
    section_id: str = Field(..., description="Foreign key to parent LiterarySection")
    order_index: int = Field(..., description="Sequential ordinal position within the section")
    passage_number: int = Field(..., description="Canonically recognized verse or sūtra number")
    original_text: str = Field(..., description="Pristine unmodified Classical Tamil source text")
    normalized_search_text: Optional[str] = Field(None, description="Non-destructive NFC normalized search projection")
    transliteration: Optional[str] = Field(None, description="ISO 15919 transliteration")
    english_translation: Optional[str] = Field(None, description="Scholarly English translation")
    category: Optional[str] = Field(None, description="Literary, grammatical, or philosophical classification")
    tinai: Optional[str] = Field(None, description="Poetic landscape or thematic context (Akam/Puram)")
    lines: List[VerseLine] = Field(default_factory=list, description="Constituent metrical lines")
    commentaries: List[Commentary] = Field(default_factory=list, description="Associated commentaries")
    entities: List[str] = Field(default_factory=list, description="Extracted domain entities")
    triples: List[KnowledgeTriple] = Field(default_factory=list, description="Extracted knowledge triples")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extensible metadata")
    provenance: Optional[ProvenanceRecord] = Field(None, description="Source provenance record")


class LiterarySection(BaseModel):
    """
    Section or division within a Classical Tamil work (Atikāram, Iyal, Kāṇṭam, Paṭalam).
    """
    id: str = Field(..., description="Stable section identifier, e.g. tolkappiyam-porul")
    work_id: str = Field(..., description="Foreign key to parent LiteraryWork")
    order_index: int = Field(..., description="Sequential ordinal position of section")
    name_tamil: str = Field(..., description="Section title in Tamil script, e.g. பொருளதிகாரம்")
    name_english: str = Field(..., description="Section title in English/Romanized, e.g. Poruḷatikāram")
    section_type: str = Field("atikāram", description="Division type (atikāram, iyal, kāṇṭam, paṭalam)")
    parent_section_id: Optional[str] = Field(None, description="Optional parent section ID for nested divisions")
    total_passages: int = Field(0, description="Total passages or sūtras in this section")
    description: Optional[str] = Field(None, description="Descriptive summary of section scope")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible section attributes")


class LiteratureWork(BaseModel):
    """Extensible model representing a Classical Tamil Literary Treatise or Anthology."""
    work_id: str = Field(..., description="Unique slug identifier for work (e.g. tolkappiyam, tirukkural)")
    title_tamil: str = Field(..., description="Tamil title (தொல்காப்பியம்)")
    title_english: str = Field(..., description="English transliterated title")
    author: Optional[str] = Field(None, description="Author / Commentator")
    period: str = Field(..., description="Historical epoch (e.g. Pre-Sangam, Sangam)")
    category: str = Field("Grammar & Poetics", description="Literary classification")
    total_sections: int = Field(0, description="Total major divisions (books/canto)")
    total_passages: int = Field(0, description="Total aphorisms or verses")
    description: Optional[str] = Field(None, description="Detailed treatise summary")
    level: HierarchyLevel = Field(HierarchyLevel.L0_CORPUS, description="Hierarchy anchor level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata")
    provenance: Optional[ProvenanceRecord] = Field(None, description="Source provenance record")
