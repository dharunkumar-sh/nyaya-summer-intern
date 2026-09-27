"""
Error Handling Package for Classical Tamil Corpus and Literature Subsystems.
"""
from errors.exceptions import (
    BaseAppException,
    CorpusNotFoundError,
    SutraNotFoundError,
    AtikaramNotFoundError,
    IyalNotFoundError,
    LiteratureWorkNotFoundError,
    InvalidFilterError,
    DatabaseConnectionError,
    DatabaseOperationError,
    SectionNotFoundError,
    PassageNotFoundError,
    CommentaryNotFoundError,
)
from errors.handlers import register_error_handlers

__all__ = [
    "BaseAppException",
    "CorpusNotFoundError",
    "SutraNotFoundError",
    "AtikaramNotFoundError",
    "IyalNotFoundError",
    "LiteratureWorkNotFoundError",
    "InvalidFilterError",
    "DatabaseConnectionError",
    "DatabaseOperationError",
    "SectionNotFoundError",
    "PassageNotFoundError",
    "CommentaryNotFoundError",
    "register_error_handlers",
]
