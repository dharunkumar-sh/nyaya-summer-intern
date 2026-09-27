"""
Dedicated Neo4j Aura Database Service for the Flask Backend.

Encapsulates creation and management of the Neo4j driver, database selection,
connectivity verification, parameterized Cypher execution, transaction handling,
lightweight health checks, and graceful error handling without leaking credentials.
"""
from __future__ import annotations

import atexit
import os
import re
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from neo4j import GraphDatabase, Driver, Session, ManagedTransaction
from neo4j.exceptions import (
    ServiceUnavailable,
    AuthError,
    ClientError,
    TransientError,
    DatabaseError,
    Neo4jError,
)

from config import Neo4jConfig, sanitize_uri
from core.logger import logger
from core.exceptions import (
    KnowledgeGraphError,
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    CypherQueryError,
    DatabaseTransactionError,
)


def sanitize_text(text: str, secret: Optional[str] = None) -> str:
    """Masks secret substrings and credentials from error and diagnostic messages."""
    if not text:
        return ""
    cleaned = str(text)
    if secret and len(secret) > 2:
        cleaned = cleaned.replace(secret, "[REDACTED]")
    # Redact any URI user:pass patterns
    cleaned = re.sub(r"://([^@/]+)@", r"://***@", cleaned)
    return cleaned


class Neo4jService:
    """
    Dedicated reusable database service managing the Neo4j Aura driver lifecycle,
    database selection, session execution, connection pooling, and health diagnostics.
    """

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
        self._default_database = database if database is not None else (Neo4jConfig.DATABASE or "neo4j")

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
        self._connectivity_cache: Optional[Dict[str, Any]] = None
        self._connectivity_cache_time: float = 0.0

    @property
    def database(self) -> str:
        """Returns the default active database name."""
        return self._default_database

    @property
    def masked_uri(self) -> str:
        """Returns safe URI without credentials."""
        return sanitize_uri(self.uri)

    def set_default_database(self, database_name: str) -> None:
        """Selects the active default database."""
        if not database_name:
            raise ValueError("Database name cannot be empty")
        self._default_database = database_name
        logger.info(f"Set active Neo4j database to: '{database_name}'")

    def get_default_database(self) -> str:
        """Returns the active default database name."""
        return self._default_database

    def get_driver(self) -> Optional[Driver]:
        """
        Lazy-initializes and returns the reusable Neo4j driver singleton.
        Maintains an active connection pool across multiple requests.
        """
        if self._driver is not None:
            return self._driver

        if not self.uri or not self.username or not self.password:
            logger.info("Neo4j Aura credentials not fully configured; driver not initialized.")
            return None

        try:
            # Under automated tests, use a short connection timeout to avoid blocking
            is_testing = (
                os.getenv("FLASK_ENV") == "testing"
                or os.getenv("TESTING") == "true"
            )
            timeout = 2.0 if is_testing else self.connection_timeout

            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=self.max_connection_lifetime,
                max_connection_pool_size=self.max_connection_pool_size,
                connection_timeout=timeout,
                connection_acquisition_timeout=self.connection_acquisition_timeout,
            )
            logger.info(f"Initialized reusable Neo4j Aura Driver connection pool for {self.masked_uri}")
            return self._driver
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            logger.error(f"Failed to create Neo4j Aura driver: {safe_err}")
            self._driver = None
            return None

    def verify_connectivity(self, database: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Pings Neo4j Aura using official driver verify_connectivity() functionality.
        Returns a diagnostic dictionary without exposing credentials.
        Caches results for 5.0 seconds to eliminate DNS lookup latency spikes on repeated requests.
        """
        now = time.time()
        if not force_refresh and self._connectivity_cache is not None:
            if now - self._connectivity_cache_time < 5.0:
                return self._connectivity_cache

        target_db = database or self._default_database
        driver = self.get_driver()
        if driver is None:
            res = {
                "status": "DISCONNECTED",
                "connected": False,
                "uri": self.masked_uri,
                "database": target_db,
                "error": "Driver not initialized (missing or unconfigured credentials)",
            }
            self._connectivity_cache = res
            self._connectivity_cache_time = now
            return res

        start_time = time.perf_counter()
        try:
            driver.verify_connectivity()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            server_info = driver.get_server_info()
            res = {
                "status": "CONNECTED",
                "connected": True,
                "uri": self.masked_uri,
                "database": target_db,
                "latency_ms": latency_ms,
                "server_agent": server_info.agent,
                "protocol_version": server_info.protocol_version,
            }
        except AuthError as e:
            safe_err = sanitize_text(str(e), self.password)
            logger.error(f"Neo4j Authentication failed: {safe_err}")
            res = {
                "status": "AUTH_FAILED",
                "connected": False,
                "uri": self.masked_uri,
                "database": target_db,
                "error": "Authentication failed: invalid Neo4j Aura credentials",
            }
        except ServiceUnavailable as e:
            safe_err = sanitize_text(str(e), self.password)
            logger.warning(f"Neo4j Aura instance unreachable: {safe_err}")
            res = {
                "status": "UNREACHABLE",
                "connected": False,
                "uri": self.masked_uri,
                "database": target_db,
                "error": "Service unavailable: Neo4j Aura cluster unreachable or paused",
            }
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            logger.error(f"Neo4j connectivity check error: {safe_err}")
            res = {
                "status": "ERROR",
                "connected": False,
                "uri": self.masked_uri,
                "database": target_db,
                "error": "Failed to connect to Neo4j Aura",
            }

        self._connectivity_cache = res
        self._connectivity_cache_time = now
        return res

    def startup_check(self, raise_on_failure: bool = False) -> Dict[str, Any]:
        """
        Performs a startup connectivity verification for the Flask application.
        Logs status and optionally raises DatabaseConnectionError on failure.
        """
        logger.info(f"Performing Neo4j startup connectivity check for {self.masked_uri}...")
        result = self.verify_connectivity()

        if result.get("connected"):
            logger.info(
                f"Neo4j Aura startup check PASSED: {result.get('server_agent')} "
                f"({result.get('latency_ms')}ms latency) on database '{result.get('database')}'"
            )
        else:
            logger.warning(
                f"Neo4j Aura startup check: {result.get('status')} - {result.get('error')}"
            )
            if raise_on_failure:
                raise DatabaseConnectionError(
                    f"Neo4j startup check failed: {result.get('error')}",
                    details=result,
                )

        return result

    def health_check(self) -> Dict[str, Any]:
        """
        Exposes a lightweight health-check method for API monitoring and diagnostics.
        Returns connectivity status, latency, database name, and pool capacity.
        """
        diagnostics = self.verify_connectivity()
        diagnostics["pool_size"] = self.max_connection_pool_size
        diagnostics["max_connection_lifetime"] = self.max_connection_lifetime
        return diagnostics

    def is_connected(self) -> bool:
        """Returns True if the driver is initialized and can verify connectivity."""
        try:
            return bool(self.verify_connectivity().get("connected", False))
        except Exception:
            return False

    def get_safe_connection_health(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs a strictly sanitized connectivity verification for Neo4j Aura.
        Guarantees that URI, username, password, internal stack traces, or credentials
        are never exposed in responses.
        """
        target_db = database or self._default_database

        if not self.uri or not self.username or not self.password:
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": "not_configured",
                "database": target_db,
                "message": "Neo4j database credentials are not configured in the environment.",
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }

        driver = self.get_driver()
        if driver is None:
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": "initialization_failed",
                "database": target_db,
                "message": "Failed to initialize Neo4j database driver.",
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }

        start_time = time.perf_counter()
        try:
            driver.verify_connectivity()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            server_info = driver.get_server_info()
            protocol = server_info.protocol_version
            if isinstance(protocol, (tuple, list)):
                protocol_str = ".".join(str(p) for p in protocol)
            else:
                protocol_str = str(protocol) if protocol else None

            return {
                "connected": True,
                "connection_status": "connected",
                "database_status": "online",
                "database": target_db,
                "message": "Neo4j Aura database is healthy, reachable, and operational.",
                "latency_ms": latency_ms,
                "server_agent": str(server_info.agent) if server_info.agent else "Neo4j",
                "protocol_version": protocol_str,
            }
        except AuthError:
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": "authentication_failed",
                "database": target_db,
                "message": "Authentication failed: invalid Neo4j database username or password.",
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }
        except ServiceUnavailable as e:
            err_lower = str(e).lower()
            is_timeout = "timeout" in err_lower or "timed out" in err_lower
            db_status = "timeout" if is_timeout else "unreachable"
            msg = (
                "Connection timed out: Neo4j database did not respond within the allocated timeout period."
                if is_timeout
                else "Neo4j database is currently unreachable or paused."
            )
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": db_status,
                "database": target_db,
                "message": msg,
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }
        except (DatabaseError, Neo4jError) as e:
            err_lower = str(e).lower()
            if "database" in err_lower and ("not found" in err_lower or "offline" in err_lower):
                db_status = "database_unavailable"
                msg = f"The requested Neo4j database '{target_db}' is unavailable or does not exist."
            else:
                db_status = "database_error"
                msg = "A database error occurred while communicating with Neo4j Aura."
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": db_status,
                "database": target_db,
                "message": msg,
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }
        except Exception:
            return {
                "connected": False,
                "connection_status": "disconnected",
                "database_status": "error",
                "database": target_db,
                "message": "An unexpected error occurred while communicating with Neo4j database.",
                "latency_ms": None,
                "server_agent": None,
                "protocol_version": None,
            }

    @contextmanager
    def get_session(
        self, database: Optional[str] = None
    ) -> Generator[Session, None, None]:
        """Context manager providing a safe, managed Neo4j Session from the connection pool."""
        driver = self.get_driver()
        if driver is None:
            raise DatabaseConnectionError("Cannot open session: Neo4j Aura driver is not connected")

        db = database or self._default_database
        try:
            session = driver.session(database=db)
        except AuthError:
            raise DatabaseAuthenticationError("Neo4j database authentication failed")
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            raise DatabaseConnectionError(f"Failed to open Neo4j session: {safe_err}")

        try:
            yield session
        finally:
            try:
                session.close()
            except Exception:
                pass

    def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a read Cypher transaction with parameters and automatic retry.
        Returns a list of structured dictionary records.
        """
        params = parameters if parameters is not None else {}
        try:
            with self.get_session(database=database) as session:
                def work(tx: ManagedTransaction):
                    result = tx.run(query, params)
                    return [record.data() for record in result]

                return session.execute_read(work)
        except AuthError as e:
            raise DatabaseAuthenticationError(
                "Neo4j authentication failed during read transaction"
            )
        except ServiceUnavailable as e:
            raise DatabaseConnectionError(
                "Neo4j service unavailable during read transaction"
            )
        except ClientError as e:
            safe_err = sanitize_text(str(e), self.password)
            raise CypherQueryError(f"Cypher read error: {safe_err}")
        except TransientError as e:
            safe_err = sanitize_text(str(e), self.password)
            raise DatabaseTransactionError(f"Transient read transaction failure: {safe_err}")
        except KnowledgeGraphError:
            raise
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            raise KnowledgeGraphError(f"Neo4j read transaction failed: {safe_err}")

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a write Cypher transaction with parameters and automatic retry on transient errors.
        Returns a list of structured dictionary records.
        """
        params = parameters if parameters is not None else {}
        try:
            with self.get_session(database=database) as session:
                def work(tx: ManagedTransaction):
                    result = tx.run(query, params)
                    return [record.data() for record in result]

                return session.execute_write(work)
        except AuthError as e:
            raise DatabaseAuthenticationError(
                "Neo4j authentication failed during write transaction"
            )
        except ServiceUnavailable as e:
            raise DatabaseConnectionError(
                "Neo4j service unavailable during write transaction"
            )
        except ClientError as e:
            safe_err = sanitize_text(str(e), self.password)
            raise CypherQueryError(f"Cypher write error: {safe_err}")
        except TransientError as e:
            safe_err = sanitize_text(str(e), self.password)
            raise DatabaseTransactionError(f"Transient write transaction failure: {safe_err}")
        except KnowledgeGraphError:
            raise
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            raise KnowledgeGraphError(f"Neo4j write transaction failed: {safe_err}")

    def run_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes an auto-commit parameterized Cypher query and returns structured results.
        """
        params = parameters if parameters is not None else {}
        try:
            with self.get_session(database=database) as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except AuthError:
            raise DatabaseAuthenticationError("Neo4j authentication failed")
        except ServiceUnavailable:
            raise DatabaseConnectionError("Neo4j database unavailable")
        except ClientError as e:
            safe_err = sanitize_text(str(e), self.password)
            raise CypherQueryError(f"Cypher execution error: {safe_err}")
        except Exception as e:
            safe_err = sanitize_text(str(e), self.password)
            raise KnowledgeGraphError(f"Cypher query failed: {safe_err}")

    @contextmanager
    def transaction(
        self, mode: str = "read", database: Optional[str] = None
    ) -> Generator[Any, None, None]:
        """
        Context manager for explicit transaction execution.
        Rolls back on error, commits on successful completion.
        """
        with self.get_session(database=database) as session:
            tx = session.begin_transaction()
            try:
                yield tx
                tx.commit()
            except Exception as e:
                try:
                    tx.rollback()
                except Exception:
                    pass
                safe_err = sanitize_text(str(e), self.password)
                raise DatabaseTransactionError(f"Transaction failed and was rolled back: {safe_err}")

    def close(self) -> None:
        """Closes the Neo4j driver and releases all pooled connections gracefully."""
        if self._driver is not None:
            driver_to_close = self._driver
            self._driver = None
            try:
                driver_to_close.close()
            except Exception:
                pass


# Singleton service instance used across the backend
neo4j_service = Neo4jService()

# Gracefully close connection pool on Python process exit
try:
    atexit.register(neo4j_service.close)
except Exception:
    pass

