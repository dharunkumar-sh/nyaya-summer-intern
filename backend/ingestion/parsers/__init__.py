"""
Parsers Package for Classical Tamil Literature Ingestion.
Supports structured corpus input through JSON, CSV, TXT, and XML.
"""
from typing import Dict, Type
from ingestion.parsers.base_parser import (
    BaseLiteratureParser,
    ParsedLiteratureData,
    generate_stable_slug,
)
from ingestion.parsers.json_parser import JsonLiteratureParser
from ingestion.parsers.csv_parser import CsvLiteratureParser
from ingestion.parsers.txt_parser import TxtLiteratureParser
from ingestion.parsers.xml_parser import XmlLiteratureParser

PARSER_REGISTRY: Dict[str, Type[BaseLiteratureParser]] = {
    "json": JsonLiteratureParser,
    "csv": CsvLiteratureParser,
    "txt": TxtLiteratureParser,
    "text": TxtLiteratureParser,
    "xml": XmlLiteratureParser,
}


def get_parser_for_format(format_name: str) -> BaseLiteratureParser:
    """Returns an instantiated parser corresponding to the file format."""
    normalized = format_name.strip().lower().lstrip(".")
    parser_cls = PARSER_REGISTRY.get(normalized)
    if not parser_cls:
        raise ValueError(
            f"Unsupported literature ingestion format '{format_name}'. "
            f"Supported formats: {list(PARSER_REGISTRY.keys())}"
        )
    return parser_cls()


__all__ = [
    "BaseLiteratureParser",
    "ParsedLiteratureData",
    "generate_stable_slug",
    "JsonLiteratureParser",
    "CsvLiteratureParser",
    "TxtLiteratureParser",
    "XmlLiteratureParser",
    "get_parser_for_format",
    "PARSER_REGISTRY",
]
