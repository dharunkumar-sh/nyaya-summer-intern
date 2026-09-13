"""
Domain-specific exceptions for Classical Tamil Neuro-Symbolic Reasoner.
"""


class ReasonerException(Exception):
    """Base exception for all reasoner errors."""

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class CorpusNotFoundError(ReasonerException):
    """Raised when sūtra or corpus dataset cannot be located."""

    def __init__(self, message: str = "Corpus data or sūtra record not found"):
        super().__init__(message, status_code=404)


class InvalidQueryError(ReasonerException):
    """Raised when the incoming research inquiry is malformed or empty."""

    def __init__(self, message: str = "Inquiry string cannot be empty or invalid"):
        super().__init__(message, status_code=422)


class NyayaInferenceError(ReasonerException):
    """Raised when syllogistic derivation fails to ground middle ground."""

    def __init__(self, message: str = "Pañcāvayava inference failed to ground premise"):
        super().__init__(message, status_code=500)


class HetvabhasaFallacyError(ReasonerException):
    """Raised when reasoning contains critical unresolvable fallacy."""

    def __init__(self, fallacy_type: str, message: str):
        super().__init__(
            f"Hetvābhāsa Fallacy detected ({fallacy_type}): {message}",
            status_code=422,
            details={"fallacy_type": fallacy_type},
        )


class KnowledgeGraphError(ReasonerException):
    """Raised on graph construction or querying failure."""

    def __init__(self, message: str = "Knowledge graph query error", status_code: int = 500, details: dict = None):
        super().__init__(message, status_code=status_code, details=details)


class DatabaseConnectionError(KnowledgeGraphError):
    """Raised when connecting to Neo4j database fails or service is unavailable."""

    def __init__(self, message: str = "Neo4j database connection failed", details: dict = None):
        super().__init__(message, status_code=503, details=details)


class DatabaseAuthenticationError(KnowledgeGraphError):
    """Raised when Neo4j authentication fails."""

    def __init__(self, message: str = "Neo4j database authentication failed", details: dict = None):
        super().__init__(message, status_code=503, details=details)


class CypherQueryError(KnowledgeGraphError):
    """Raised when a Cypher query execution or constraint validation fails."""

    def __init__(self, message: str = "Cypher query execution failed", details: dict = None):
        super().__init__(message, status_code=400, details=details)


class DatabaseTransactionError(KnowledgeGraphError):
    """Raised when a database transaction fails or rollbacks."""

    def __init__(self, message: str = "Database transaction failed", details: dict = None):
        super().__init__(message, status_code=500, details=details)


class RetrievalError(ReasonerException):
    """Raised when retrieval index fails to rank evidence."""

    def __init__(self, message: str = "Hybrid retrieval engine failure"):
        super().__init__(message, status_code=500)
