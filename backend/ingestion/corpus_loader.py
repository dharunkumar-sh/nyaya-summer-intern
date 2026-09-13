"""
Corpus loader for Tolkāppiyam classical dataset.
Loads, indexes, and normalizes sūtras for fast memory access and querying.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.logger import logger
from core.exceptions import CorpusNotFoundError


class CorpusLoader:
    """Manages loading and indexing of canonical Tolkāppiyam text."""

    def __init__(self, file_path: Optional[Path] = None):
        if file_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.file_path = base_dir / "data" / "raw" / "tolkappiyam_canonical.json"
        else:
            self.file_path = Path(file_path)

        self._metadata: Dict[str, Any] = {}
        self._sutras: List[Dict[str, Any]] = []
        self._sutra_id_index: Dict[str, Dict[str, Any]] = {}
        self._tinai_index: Dict[str, List[Dict[str, Any]]] = {}

        self.load_corpus()

    def load_corpus(self) -> None:
        """Loads canonical JSON file into memory."""
        if not self.file_path.exists():
            logger.error(f"Corpus file does not exist at {self.file_path}")
            raise CorpusNotFoundError(f"Corpus file not found: {self.file_path}")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._metadata = data.get("corpus_metadata", {})
            self._sutras = data.get("canonical_sutras", [])

            # Build fast lookup indexes
            self._sutra_id_index = {s["id"]: s for s in self._sutras}
            self._tinai_index = {}
            for s in self._sutras:
                tinai = s.get("tinai", "General")
                self._tinai_index.setdefault(tinai, []).append(s)

            logger.info(
                f"Successfully loaded {len(self._sutras)} canonical sūtras from {self._metadata.get('name', 'Tolkāppiyam')}"
            )
        except Exception as e:
            logger.error(f"Failed to parse corpus JSON: {e}")
            raise CorpusNotFoundError(f"Failed to load corpus: {str(e)}")

    def get_metadata(self) -> Dict[str, Any]:
        """Returns corpus metadata."""
        return self._metadata

    def get_all_sutras(self) -> List[Dict[str, Any]]:
        """Returns all loaded sūtras."""
        return self._sutras

    def get_sutra_by_id(self, sutra_id: str) -> Optional[Dict[str, Any]]:
        """Lookup sūtra by unique identifier."""
        return self._sutra_id_index.get(sutra_id)

    def get_sutras_by_tinai(self, tinai: str) -> List[Dict[str, Any]]:
        """Returns sūtras classified under a specific ecological Tiṇai."""
        return self._tinai_index.get(tinai, [])

    def get_all_triples(self) -> List[Dict[str, str]]:
        """Aggregates all semantic triples across all sūtras."""
        triples = []
        for s in self._sutras:
            s_triples = s.get("triples", [])
            for t in s_triples:
                t_with_source = dict(t)
                t_with_source["source_sutra"] = s["id"]
                triples.append(t_with_source)
        return triples


# Singleton instance
corpus_loader = CorpusLoader()
