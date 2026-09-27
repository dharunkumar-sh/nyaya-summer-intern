"""
Database Session and Transaction Context Managers.
Provides managed access to Neo4j sessions, read transactions, and write transactions.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any
from neo4j import Session, ManagedTransaction
from neo4j.exceptions import Neo4jError

from database.connection import get_db_manager

logger = logging.getLogger("nyaya.database")


@contextmanager
def managed_session(
    database: Optional[str] = None,
    default_access_mode: str = "WRITE",
) -> Generator[Session, None, None]:
    """
    Context manager yielding a Neo4j session.
    Automatically closes session upon exiting context.
    """
    manager = get_db_manager()
    driver = manager.get_driver()
    db = database or manager.database
    session = driver.session(database=db, default_access_mode=default_access_mode)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def read_transaction(database: Optional[str] = None) -> Generator[Session, None, None]:
    """Context manager for read-only query operations."""
    with managed_session(database=database, default_access_mode="READ") as session:
        yield session


@contextmanager
def write_transaction(database: Optional[str] = None) -> Generator[Session, None, None]:
    """Context manager for write operations with automated commit/rollback semantics."""
    with managed_session(database=database, default_access_mode="WRITE") as session:
        yield session
