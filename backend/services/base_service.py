"""
Base Service Class providing shared patterns, logging, and error handling.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional


class BaseService:
    """Base class for all business logic services."""

    def __init__(self, service_name: Optional[str] = None):
        self.service_name = service_name or self.__class__.__name__
        self.logger = logging.getLogger(f"nyaya.service.{self.service_name}")

    def log_info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.logger.info(message, extra=extra)

    def log_warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.logger.warning(message, extra=extra)

    def log_error(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None):
        self.logger.error(message, exc_info=exc_info, extra=extra)
