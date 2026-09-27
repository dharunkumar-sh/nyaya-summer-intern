"""
Centralized Flask Exception Handlers.
Translates all exceptions into consistent, schema-compliant JSON error responses.
"""
import logging
from flask import Flask
from pydantic import ValidationError

from errors.exceptions import BaseAppException
from core.exceptions import ReasonerException
from utilities.response_envelope import api_error

logger = logging.getLogger("nyaya.errors")


def register_error_handlers(app: Flask) -> None:
    """Registers global exception handlers on the Flask application."""

    @app.errorhandler(BaseAppException)
    def handle_base_app_exception(error: BaseAppException):
        logger.warning(f"Application error [{error.error_code}]: {error.message}")
        return api_error(
            message=error.message,
            error_code=error.error_code,
            details=error.details,
            status_code=error.status_code,
        )

    @app.errorhandler(ReasonerException)
    def handle_reasoner_exception(error: ReasonerException):
        logger.warning(f"Reasoner domain error: {error.message}")
        return api_error(
            message=error.message,
            error_code=error.__class__.__name__,
            details=error.details,
            status_code=error.status_code,
        )

    @app.errorhandler(ValidationError)
    def handle_pydantic_validation_error(error: ValidationError):
        logger.warning(f"Schema validation error: {error}")
        return api_error(
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"validation_errors": error.errors()},
            status_code=422,
        )

    @app.errorhandler(404)
    def handle_404(error):
        return api_error(
            message="The requested endpoint or resource was not found",
            error_code="NOT_FOUND",
            status_code=404,
        )

    @app.errorhandler(405)
    def handle_405(error):
        return api_error(
            message="Method not allowed for this endpoint",
            error_code="METHOD_NOT_ALLOWED",
            status_code=405,
        )

    @app.errorhandler(500)
    def handle_500(error):
        logger.error(f"Unhandled internal server error: {error}", exc_info=True)
        return api_error(
            message="An unexpected internal server error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )
