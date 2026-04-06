"""
Database infrastructure for the learning system.

Provides a singleton LearningDB class with thread-safe SQLite connections
using WAL mode for improved concurrency.
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional


class LearningDB:
    """
    Singleton database factory for learning system.

    Provides thread-safe SQLite connections with WAL mode enabled
    for better concurrency. All databases are stored in context/memory/.
    """

    _instance: Optional["LearningDB"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LearningDB":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._db_dir = Path("context/memory")
        self._connections: dict[str, sqlite3.Connection] = {}
        self._conn_lock = threading.Lock()

        # Ensure database directory exists
        self._db_dir.mkdir(parents=True, exist_ok=True)

    def get_connection(self, db_name: str) -> sqlite3.Connection:
        """
        Get or create a connection to the specified database.

        Args:
            db_name: Name of the database file (e.g., 'test.db')

        Returns:
            sqlite3.Connection with WAL mode enabled
        """
        with self._conn_lock:
            if db_name in self._connections:
                conn = self._connections[db_name]
                # Verify connection is still valid
                try:
                    conn.execute("SELECT 1")
                    return conn
                except (sqlite3.OperationalError, sqlite3.DatabaseError):
                    # Connection is closed or invalid, remove it
                    del self._connections[db_name]

            # Create new connection
            db_path = self._db_dir / db_name
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row

            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")

            self._connections[db_name] = conn
            return conn

    def close_connection(self, db_name: str) -> None:
        """Close and remove a connection from the pool."""
        with self._conn_lock:
            if db_name in self._connections:
                try:
                    self._connections[db_name].close()
                except Exception:
                    pass
                del self._connections[db_name]

    def close_all(self) -> None:
        """Close all active connections."""
        with self._conn_lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()

    @property
    def db_dir(self) -> Path:
        """Return the database directory path."""
        return self._db_dir


# Singleton instance for convenience
_db_instance: Optional[LearningDB] = None
_instance_lock = threading.Lock()


def get_db() -> LearningDB:
    """Get the singleton LearningDB instance."""
    global _db_instance
    if _db_instance is None:
        with _instance_lock:
            if _db_instance is None:
                _db_instance = LearningDB()
    return _db_instance
