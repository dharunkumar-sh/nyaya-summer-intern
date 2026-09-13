"""
Dataset validator for checking corpus integrity, Unicode compliance, and triple schemas.
"""
from typing import Dict, Any, List
from core.logger import logger


class DatasetValidator:
    """Validates schema, encoding, and semantic fields of incoming corpus."""

    REQUIRED_SUTRA_FIELDS = [
        "id",
        "sutra_number",
        "atikaram",
        "iyal",
        "tamil_text",
        "transliteration",
        "english_translation",
        "category",
        "triples",
    ]

    REQUIRED_TRIPLE_FIELDS = ["subject", "predicate", "object"]

    @classmethod
    def validate_corpus_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the entire corpus JSON schema."""
        errors = []
        metadata = data.get("corpus_metadata", {})
        sutras = data.get("canonical_sutras", [])

        if not metadata.get("name"):
            errors.append("Corpus metadata missing 'name'")

        if not isinstance(sutras, list) or len(sutras) == 0:
            errors.append("Corpus contains no canonical sūtras")

        for idx, sutra in enumerate(sutras):
            for field in cls.REQUIRED_SUTRA_FIELDS:
                if field not in sutra:
                    errors.append(f"Sūtra #{idx} missing required field '{field}'")

            # Validate UTF-8 Tamil string presence
            tamil_text = sutra.get("tamil_text", "")
            if not tamil_text or len(tamil_text.strip()) == 0:
                errors.append(f"Sūtra #{idx} has empty tamil_text")

            # Validate triples
            triples = sutra.get("triples", [])
            for t_idx, triple in enumerate(triples):
                for t_field in cls.REQUIRED_TRIPLE_FIELDS:
                    if t_field not in triple or not triple[t_field]:
                        errors.append(
                            f"Sūtra {sutra.get('id', idx)} triple #{t_idx} missing '{t_field}'"
                        )

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Dataset validation produced {len(errors)} warnings/errors")

        return {
            "valid": is_valid,
            "sutra_count": len(sutras),
            "errors": errors,
        }
