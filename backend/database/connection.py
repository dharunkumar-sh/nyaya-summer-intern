"""
Neo4j Aura Database Connection Manager.
Handles driver lifecycle, connection pooling, and connection diagnostics.
"""
from __future__ import annotations

import logging
import re
import threading
from typing import Optional, Dict, Any
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError

from config.neo4j_config import Neo4jConfig, sanitize_uri

logger = logging.getLogger("nyaya.database")


class Neo4jConnectionManager:
    """
    Thread-safe connection manager for Neo4j Aura.
    Manages the driver lifecycle, connection pool configuration, and connectivity verification.
    """

    _instance: Optional[Neo4jConnectionManager] = None
    _lock = threading.Lock()

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        max_connection_pool_size: Optional[int] = None,
        max_connection_lifetime: Optional[int] = None,
        connection_timeout: Optional[float] = None,
        connection_acquisition_timeout: Optional[float] = None,
    ):
        self.uri = uri if uri is not None else Neo4jConfig.URI
        self.username = username if username is not None else Neo4jConfig.USERNAME
        self.password = password if password is not None else Neo4jConfig.PASSWORD
        self.database = database if database is not None else Neo4jConfig.DATABASE

        self.max_connection_pool_size = (
            max_connection_pool_size
            if max_connection_pool_size is not None
            else Neo4jConfig.MAX_CONNECTION_POOL_SIZE
        )
        self.max_connection_lifetime = (
            max_connection_lifetime
            if max_connection_lifetime is not None
            else Neo4jConfig.MAX_CONNECTION_LIFETIME
        )
        self.connection_timeout = (
            connection_timeout
            if connection_timeout is not None
            else Neo4jConfig.CONNECTION_TIMEOUT
        )
        self.connection_acquisition_timeout = (
            connection_acquisition_timeout
            if connection_acquisition_timeout is not None
            else Neo4jConfig.CONNECTION_ACQUISITION_TIMEOUT
        )

        self._driver: Optional[Driver] = None
        self._driver_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> Neo4jConnectionManager:
        """Singleton accessor for the connection manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def is_configured(self) -> bool:
        """Returns True if URI, username, and password are non-empty."""
        return bool(self.uri and self.username and self.password)

    def get_driver(self) -> Driver:
        """
        Lazily creates and returns the configured Neo4j driver with thread safety.
        Raises RuntimeError if required configuration is missing.
        """
        if not self.is_configured:
            raise RuntimeError(
                "Neo4j driver cannot be initialized: missing URI, username, or password in configuration."
            )

        if self._driver is None:
            with self._driver_lock:
                if self._driver is None:
                    sanitized = sanitize_uri(self.uri)
                    logger.info(f"Initializing Neo4j driver pool to {sanitized} (db={self.database})")
                    self._driver = GraphDatabase.driver(
                        self.uri,
                        auth=(self.username, self.password),
                        max_connection_lifetime=self.max_connection_lifetime,
                        max_connection_pool_size=self.max_connection_pool_size,
                        connection_timeout=self.connection_timeout,
                        connection_acquisition_timeout=self.connection_acquisition_timeout,
                    )
        return self._driver

    def verify_connectivity(self) -> Dict[str, Any]:
        """
        Verifies connectivity to the database and returns a safe diagnostic status dict.
        Does not leak raw credentials.
        """
        if not self.is_configured:
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "Neo4j Aura credentials are not configured",
                "database": self.database,
                "uri": sanitize_uri(self.uri),
            }

        try:
            driver = self.get_driver()
            driver.verify_connectivity()
            return {
                "connected": True,
                "status": "HEALTHY",
                "message": "Successfully connected to Neo4j database",
                "database": self.database,
                "uri": sanitize_uri(self.uri),
            }
        except AuthError as e:
            return {
                "connected": False,
                "status": "AUTH_FAILED",
                "message": "Authentication failed for Neo4j Aura",
                "database": self.database,
                "uri": sanitize_uri(self.uri),
            }
        except ServiceUnavailable as e:
            return {
                "connected": False,
                "status": "UNAVAILABLE",
                "message": f"Neo4j Aura service unavailable: {str(e)[:100]}",
                "database": self.database,
                "uri": sanitize_uri(self.uri),
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "ERROR",
                "message": f"Connection check failed: {str(e)[:100]}",
                "database": self.database,
                "uri": sanitize_uri(self.uri),
            }

    def close(self) -> None:
        """Closes the underlying driver and releases connection pool resources."""
        with self._driver_lock:
            if self._driver is not None:
                try:
                    self._driver.close()
                    logger.info("Neo4j driver connection pool closed successfully.")
                except Exception as e:
                    logger.warning(f"Error while closing Neo4j driver: {e}")
                finally:
                    self._driver = None


def get_db_manager() -> Neo4jConnectionManager:
    """Helper function to obtain the default connection manager instance."""
    return Neo4jConnectionManager.get_instance()
