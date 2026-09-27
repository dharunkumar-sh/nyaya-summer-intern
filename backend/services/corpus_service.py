"""
Corpus Service for Classical Tamil Literature (Tolkāppiyam).
Provides business logic for loading, indexing, searching, filtering, and analyzing sūtras.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from config.settings import Config
from errors.exceptions import CorpusNotFoundError, SutraNotFoundError, AtikaramNotFoundError, IyalNotFoundError
from models.corpus import CorpusMetadata, Atikaram, Sutra, TinaiLandscape
from models.enums import AtikaramType, TinaiType
from schemas.corpus_schemas import (
    PaginationMeta,
    CorpusStatisticsResponse,
    AtikaramSummaryResponse,
    IyalSummaryResponse,
    TinaiLandscapeResponse,
)
from services.base_service import BaseService
from utilities.pagination import paginate_items
from utilities.tamil_text import normalize_tamil_text


class CorpusService(BaseService):
    """Encapsulates all domain operations on the canonical Tolkāppiyam corpus."""

    _instance: Optional[CorpusService] = None

    def __init__(self, corpus_path: Optional[Path] = None):
        super().__init__(service_name="CorpusService")
        self.corpus_path = corpus_path or Config.CORPUS_FILE
        self._metadata: Optional[CorpusMetadata] = None
        self._sutras: List[Sutra] = []
        self._sutras_by_id: Dict[str, Sutra] = {}
        self._atikarams: Dict[str, Atikaram] = {}
        self._load_corpus()

    @classmethod
    def get_instance(cls) -> CorpusService:
        """Singleton accessor for CorpusService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_corpus(self) -> None:
        """Loads and parses canonical corpus file into domain models."""
        target_path = Path(self.corpus_path)
        if not target_path.exists():
            # Try alternate fallback locations within repository
            fallback = Path(__file__).resolve().parent.parent / "data" / "raw" / "tolkappiyam_canonical.json"
            if fallback.exists():
                target_path = fallback
            else:
                self.log_error(f"Canonical corpus file not found at {target_path}")
                raise CorpusNotFoundError(f"Corpus file not found at {target_path}")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            meta_data = raw_data.get("corpus_metadata", {})
            self._metadata = CorpusMetadata(**meta_data)

            # Store Atikaram models mapped by ID and name
            self._atikarams = {}
            for book in self._metadata.books:
                self._atikarams[book.id.lower()] = book
                # Also index by base name (e.g. 'poruḷatikāram')
                clean_name = book.name.split()[0].lower()
                self._atikarams[clean_name] = book

            # Parse Sutras
            self._sutras = []
            self._sutras_by_id = {}
            for raw_sutra in raw_data.get("canonical_sutras", []):
                sutra = Sutra(**raw_sutra)
                self._sutras.append(sutra)
                self._sutras_by_id[sutra.id] = sutra

            self.log_info(
                f"Successfully loaded {len(self._sutras)} canonical sūtras and "
                f"{len(self._metadata.books)} atikārams from {target_path}"
            )
        except Exception as e:
            self.log_error(f"Failed to parse corpus JSON: {e}", exc_info=True)
            raise CorpusNotFoundError(f"Failed to load corpus dataset: {e}")

    def get_metadata(self) -> CorpusMetadata:
        """Returns global corpus metadata."""
        if self._metadata is None:
            self._load_corpus()
        return self._metadata

    def get_atikarams(self) -> List[AtikaramSummaryResponse]:
        """Returns list of the three Tolkāppiyam atikārams."""
        meta = self.get_metadata()
        return [
            AtikaramSummaryResponse(
                id=book.id,
                name=book.name,
                english=book.english,
                sutra_count=book.sutra_count,
                iyals=book.iyals,
            )
            for book in meta.books
        ]

    def get_atikaram(self, atikaram_id: str) -> Atikaram:
        """Resolves atikaram by ID ('eluttu', 'col', 'porul') or name."""
        key = atikaram_id.strip().lower()
        if key in self._atikarams:
            return self._atikarams[key]
        # Check prefix or partial match
        for k, v in self._atikarams.items():
            if key in k or k in key:
                return v
        raise AtikaramNotFoundError(atikaram_id)

    def get_iyals(self, atikaram_id: Optional[str] = None) -> List[IyalSummaryResponse]:
        """Returns list of iyals, optionally filtered by atikāram."""
        results = []
        if atikaram_id:
            atikaram = self.get_atikaram(atikaram_id)
            target_books = [atikaram]
        else:
            meta = self.get_metadata()
            target_books = meta.books

        for book in target_books:
            for iyal_name in book.iyals:
                # Count sūtras in this iyal
                matching = [s for s in self._sutras if s.iyal.lower() == iyal_name.lower()]
                results.append(
                    IyalSummaryResponse(
                        name=iyal_name,
                        atikaram=book.name,
                        sutra_count=len(matching),
                    )
                )
        return results

    def get_sutras(
        self,
        atikaram: Optional[str] = None,
        iyal: Optional[str] = None,
        tinai: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Sutra], PaginationMeta]:
        """
        Retrieves sūtras filtered by atikaram, iyal, tiṇai, category, and free-text search query.
        Returns paginated slice and pagination metadata.
        """
        filtered = self._sutras

        if atikaram:
            normalized_atikaram = atikaram.strip().lower()
            filtered = [
                s for s in filtered
                if normalized_atikaram in s.atikaram.lower()
                or (s.id.startswith(f"tol-{normalized_atikaram}"))
            ]

        if iyal:
            normalized_iyal = iyal.strip().lower()
            filtered = [s for s in filtered if normalized_iyal in s.iyal.lower()]

        if tinai:
            normalized_tinai = tinai.strip().lower()
            filtered = [s for s in filtered if s.tinai and normalized_tinai in s.tinai.lower()]

        if category:
            normalized_cat = category.strip().lower()
            filtered = [s for s in filtered if s.category and normalized_cat in s.category.lower()]

        if search:
            query = normalize_tamil_text(search).lower()
            filtered = [
                s for s in filtered
                if query in normalize_tamil_text(s.tamil_text).lower()
                or (s.transliteration and query in s.transliteration.lower())
                or (s.english_translation and query in s.english_translation.lower())
                or any(query in entity.lower() for entity in s.entities)
            ]

        return paginate_items(filtered, page=page, page_size=page_size)

    def get_sutra_by_id(self, sutra_id: str) -> Sutra:
        """Retrieves single sūtra by unique identifier."""
        if sutra_id in self._sutras_by_id:
            return self._sutras_by_id[sutra_id]

        # Case-insensitive or normalized check
        for sid, sutra in self._sutras_by_id.items():
            if sid.lower() == sutra_id.strip().lower():
                return sutra

        raise SutraNotFoundError(sutra_id)

    def get_tinai_landscapes(self) -> List[TinaiLandscapeResponse]:
        """
        Returns Classical Tamil Tiṇai poetic landscapes with ecological determinants
        and associated grounding sūtra counts.
        """
        landscapes_def = [
            {
                "tinai": "Kuriñci",
                "landscape": "Mountainous & Punarcci (Union)",
                "season": "Kūtir (Cold) / Muṉpaṉi (Early Dew)",
                "time_of_day": "Yāmam (Midnight)",
                "deity": "Cēyōṉ (Murugan)",
                "primary_sentiment": "Punarcci (Erotic union of lovers)",
            },
            {
                "tinai": "Mullai",
                "landscape": "Pastoral / Forested & Iruttal (Patient Waiting)",
                "season": "Kār (Monsoon rainy season)",
                "time_of_day": "Mālai (Dusk / Evening)",
                "deity": "Māyōṉ (Vishnu / Krishna)",
                "primary_sentiment": "Iruttal (Anxious / patient waiting of the heroine)",
            },
            {
                "tinai": "Marutam",
                "landscape": "Agricultural / Riverine & Ūṭal (Lovers' Feud)",
                "season": "All seasons (Vaikṟai / Dawn)",
                "time_of_day": "Vaikṟai (Pre-dawn)",
                "deity": "Vēntaṉ (Indra)",
                "primary_sentiment": "Ūṭal (Lovers' quarrel due to courtesan dalliance)",
            },
            {
                "tinai": "Neytal",
                "landscape": "Littoral / Coastal & Iraṅkal (Lamentation)",
                "season": "All seasons",
                "time_of_day": "Eṟpāṭu (Sunset)",
                "deity": "Varuṇaṉ (Sea God)",
                "primary_sentiment": "Iraṅkal (Grief-stricken lament over parted partner)",
            },
            {
                "tinai": "Pālai",
                "landscape": "Arid / Desert Wasteland & Pirital (Separation)",
                "season": "Iḷavēṉil (Early Summer) / Mutuvēṉil (Late Summer)",
                "time_of_day": "Naṇpakal (Scorching Midday)",
                "deity": "Koṟṟavai (Mother Goddess / Warrior Goddess)",
                "primary_sentiment": "Pirital (Agonizing separation, voyage for wealth/duty)",
            },
        ]

        responses = []
        for l in landscapes_def:
            t_name = l["tinai"]
            matching_sutras = [
                s.id for s in self._sutras
                if s.tinai and t_name.lower() in s.tinai.lower()
            ]
            responses.append(
                TinaiLandscapeResponse(
                    tinai=t_name,
                    landscape=l["landscape"],
                    season=l["season"],
                    time_of_day=l["time_of_day"],
                    deity=l["deity"],
                    primary_sentiment=l["primary_sentiment"],
                    associated_sutras_count=len(matching_sutras),
                )
            )
        return responses

    def get_statistics(self) -> CorpusStatisticsResponse:
        """Computes comprehensive structural statistics of the corpus."""
        meta = self.get_metadata()

        atikaram_counts: Dict[str, int] = {}
        tinai_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}

        for sutra in self._sutras:
            # Atikaram
            atikaram_counts[sutra.atikaram] = atikaram_counts.get(sutra.atikaram, 0) + 1
            # Tinai
            if sutra.tinai:
                tinai_counts[sutra.tinai] = tinai_counts.get(sutra.tinai, 0) + 1
            # Category
            if sutra.category:
                category_counts[sutra.category] = category_counts.get(sutra.category, 0) + 1

        return CorpusStatisticsResponse(
            total_sutras=meta.total_sutras,
            books_count=meta.books_count,
            atikaram_breakdown=atikaram_counts,
            tinai_breakdown=tinai_counts,
            category_breakdown=category_counts,
            indexed_sutras_count=len(self._sutras),
        )


def get_corpus_service() -> CorpusService:
    """Helper function to obtain default CorpusService instance."""
    return CorpusService.get_instance()
