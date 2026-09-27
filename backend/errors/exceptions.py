"""
Centralized Domain Exceptions for Classical Tamil Corpus and Literature Subsystems.
"""
from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """Base application exception for standardized HTTP error reporting."""

    def __init__(
        self,
        message: str = "An internal application error occurred",
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class CorpusNotFoundError(BaseAppException):
    """Raised when the primary canonical corpus cannot be located or loaded."""

    def __init__(self, message: str = "Classical Tamil corpus data not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, error_code="CORPUS_NOT_FOUND", details=details)


class SutraNotFoundError(BaseAppException):
    """Raised when a specific requested sūtra identifier does not exist."""

    def __init__(self, sutra_id: str):
        super().__init__(
            message=f"Sūtra with ID '{sutra_id}' was not found in the corpus",
            status_code=404,
            error_code="SUTRA_NOT_FOUND",
            details={"sutra_id": sutra_id},
        )


class AtikaramNotFoundError(BaseAppException):
    """Raised when an invalid atikaram book name or identifier is queried."""

    def __init__(self, atikaram: str):
        super().__init__(
            message=f"Atikāram '{atikaram}' was not found. Valid options: eluttu, col, porul",
            status_code=404,
            error_code="ATIKARAM_NOT_FOUND",
            details={"atikaram": atikaram},
        )


class IyalNotFoundError(BaseAppException):
    """Raised when a specified iyal (chapter) is not found."""

    def __init__(self, iyal: str, atikaram: Optional[str] = None):
        msg = f"Iyal '{iyal}' not found"
        if atikaram:
            msg += f" in atikāram '{atikaram}'"
        super().__init__(
            message=msg,
            status_code=404,
            error_code="IYAL_NOT_FOUND",
            details={"iyal": iyal, "atikaram": atikaram},
        )


class LiteratureWorkNotFoundError(BaseAppException):
    """Raised when a requested literature work or treatise does not exist."""

    def __init__(self, work_id: str):
        super().__init__(
            message=f"Literature work '{work_id}' not found",
            status_code=404,
            error_code="WORK_NOT_FOUND",
            details={"work_id": work_id},
        )


class InvalidFilterError(BaseAppException):
    """Raised when query parameters or filters fail validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, error_code="INVALID_FILTER", details=details)


class DatabaseConnectionError(BaseAppException):
    """Raised when connection to Neo4j or persistent store fails."""

    def __init__(self, message: str = "Database connection unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=503, error_code="DATABASE_UNAVAILABLE", details=details)


class DatabaseOperationError(BaseAppException):
    """Raised when a database query or transaction encounters a failure."""

    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class SectionNotFoundError(BaseAppException):
    """Raised when a specified section cannot be found."""

    def __init__(self, section_id: str):
        super().__init__(
            message=f"Section '{section_id}' not found",
            status_code=404,
            error_code="SECTION_NOT_FOUND",
            details={"section_id": section_id},
        )


class PassageNotFoundError(BaseAppException):
    """Raised when a requested passage or verse does not exist."""

    def __init__(self, passage_id: str):
        super().__init__(
            message=f"Passage with ID '{passage_id}' not found",
            status_code=404,
            error_code="PASSAGE_NOT_FOUND",
            details={"passage_id": passage_id},
        )


class CommentaryNotFoundError(BaseAppException):
    """Raised when a requested commentary does not exist on a passage."""

    def __init__(self, commentary_id: str, passage_id: Optional[str] = None):
        msg = f"Commentary '{commentary_id}' not found"
        if passage_id:
            msg += f" on passage '{passage_id}'"
        super().__init__(
            message=msg,
            status_code=404,
            error_code="COMMENTARY_NOT_FOUND",
            details={"commentary_id": commentary_id, "passage_id": passage_id},
        )

