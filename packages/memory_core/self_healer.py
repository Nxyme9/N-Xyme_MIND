#!/usr/bin/env python3
"""
Self-Healer — Detect and fix corrupted embeddings and stale entries.

Provides:
- heal_corrupted_embeddings(): Find and fix corrupted embeddings
- heal_stale_entries(): Remove entries for deleted files
- heal_orphaned_chunks(): Remove chunks without parent files
- heal_all(): Run all healing operations
- get_healing_report(): Return detailed healing report

Corruption detection: wrong embedding dimensions, NaN/Inf values, empty vectors
Stale detection: file_path in registry but file doesn't exist on disk
Orphan detection: chunks in file_chunks but no corresponding file in registry
"""

import logging
import math
import os
import sqlite3
from pathlib import Path
from typing import Optional

import chromadb

from packages.common.self_healer_base import SelfHealerBase

# Constants
EMBED_DIM = 768
COLLECTION_NAME = "file_embeddings"
SQLITE_TABLE = "file_chunks"
REGISTRY_TABLE = "file_registry"

# Whitelist for table names (SQL injection defense)
ALLOWED_TABLES = {SQLITE_TABLE, REGISTRY_TABLE}


def _validate_table_name(table_name: str) -> str:
    """Validate table name against whitelist.

    Args:
        table_name: Table name to validate

    Returns:
        Validated table name

    Raises:
        ValueError: If table name is not in whitelist
    """
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}. Allowed: {ALLOWED_TABLES}")
    return table_name


# Configure logging to daemon.log
daemon_logger = logging.getLogger("self_healer")
daemon_logger.setLevel(logging.INFO)
handler = logging.FileHandler("daemon.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
daemon_logger.addHandler(handler)


class SelfHealer:
    """Heals corrupted embeddings and stale entries in the memory system."""

    def __init__(self, db_path: str, chroma_path: str):
        """Initialize SelfHealer with paths.

        Args:
            db_path: Path to SQLite registry database (e.g., 'context/memory/file_registry.db')
            chroma_path: Path to ChromaDB storage (e.g., 'context/memory/file_chroma')
        """
        # Resolve paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        self._db_path = project_root / db_path
        self._chroma_path = project_root / chroma_path
        # SQLite for chunks is in the chroma_path directory
        self._sqlite_path = self._chroma_path / "file_chunks.db"

        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._chroma_collection: Optional[chromadb.Collection] = None

        # Healing report accumulation
        self._report = {
            "issues_found": 0,
            "issues_fixed": 0,
            "errors": [],
            "actions_taken": [],
        }

    def _get_chroma_collection(self) -> chromadb.Collection:
        """Get or initialize ChromaDB collection."""
        if self._chroma_collection is not None:
            return self._chroma_collection

        self._chroma_client = chromadb.PersistentClient(path=str(self._chroma_path))
        self._chroma_collection = self._chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return self._chroma_collection

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        conn = sqlite3.connect(str(self._sqlite_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _get_registry_conn(self) -> sqlite3.Connection:
        """Get registry SQLite connection."""
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _is_corrupted_embedding(self, embedding: list) -> bool:
        """Check if an embedding is corrupted.

        Args:
            embedding: Embedding vector to check

        Returns:
            True if corrupted (wrong dim, NaN, Inf, empty)
        """
        if not embedding:
            return True

        # Handle numpy arrays if present
        try:
            import numpy as np

            arr = np.array(embedding)
            if arr.size == 0:
                return True
            if arr.ndim > 1:
                arr = arr.flatten()
            if len(arr) != EMBED_DIM:
                return True
            # Check for NaN/Inf using numpy
            if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
                return True
        except ImportError:
            # Fallback to pure Python
            if len(embedding) != EMBED_DIM:
                return True
            for val in embedding:
                try:
                    if math.isnan(val) or math.isinf(val):
                        return True
                except (TypeError, ValueError):
                    # Non-numeric value
                    return True

        return False

    def heal_corrupted_embeddings(self) -> dict:
        """Find and fix corrupted embeddings.

        Detects:
        - Wrong embedding dimensions (not 768)
        - NaN values
        - Inf values
        - Empty vectors

        Auto-fixes by re-embedding the source file.

        Returns:
            Dictionary with issues_found, issues_fixed, errors, actions_taken
        """
        issues_found = 0
        issues_fixed = 0
        errors = []
        actions = []

        try:
            collection = self._get_chroma_collection()
            if collection.count() == 0:
                daemon_logger.info("No embeddings to check")
                return {
                    "issues_found": 0,
                    "issues_fixed": 0,
                    "errors": [],
                    "actions_taken": [],
                }

            # Get all embeddings to check
            try:
                all_data = collection.get(
                    include=["embeddings", "metadatas", "documents"]
                )
            except Exception as e:
                daemon_logger.warning(f"Could not get embeddings: {e}")
                return {
                    "issues_found": 0,
                    "issues_fixed": 0,
                    "errors": [str(e)],
                    "actions_taken": [],
                }

            corrupted_ids = []
            corrupted_data = []

            if all_data and all_data.get("ids"):
                for i, emb in enumerate(all_data.get("embeddings", [])):
                    if self._is_corrupted_embedding(emb):
                        chunk_id = all_data["ids"][i]
                        metadata = all_data.get("metadatas", [{}])[i]
                        document = all_data.get("documents", [""])[i]
                        corrupted_ids.append(chunk_id)
                        corrupted_data.append(
                            {
                                "chunk_id": chunk_id,
                                "file_path": metadata.get("file_path", ""),
                                "chunk_index": metadata.get("chunk_index", 0),
                                "text": document,
                                "embedding_id": metadata.get("embedding_id", ""),
                            }
                        )
                        issues_found += 1

            daemon_logger.info(f"Found {issues_found} corrupted embeddings")

            # Fix each corrupted embedding by re-embedding
            for data in corrupted_data:
                file_path = data.get("file_path")
                if not file_path:
                    # Can't re-embed without file path, remove from ChromaDB
                    try:
                        collection.delete(ids=[data["chunk_id"]])
                        actions.append(
                            f"Removed orphaned chunk {data['chunk_id']} from ChromaDB"
                        )
                        issues_fixed += 1
                    except Exception as e:
                        errors.append(f"Failed to delete chunk {data['chunk_id']}: {e}")
                    continue

                # Re-embed the file
                try:
                    if os.path.exists(file_path):
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                        # Import here to avoid circular deps
                        from .file_embedder import embed_file

                        result = embed_file(file_path, content)
                        actions.append(f"Re-embedded {file_path}: {result}")
                        issues_fixed += 1
                    else:
                        # File doesn't exist, remove chunk
                        collection.delete(ids=[data["chunk_id"]])
                        actions.append(f"Removed chunk for missing file {file_path}")
                        issues_fixed += 1
                except Exception as e:
                    errors.append(f"Failed to re-embed {file_path}: {e}")
                    daemon_logger.error(f"Failed to re-embed {file_path}: {e}")

        except Exception as e:
            errors.append(f"Error in heal_corrupted_embeddings: {e}")
            daemon_logger.error(f"Error healing corrupted embeddings: {e}")

        result = {
            "issues_found": issues_found,
            "issues_fixed": issues_fixed,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_fixed"] += issues_fixed
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Corrupted embeddings healing complete: {result}")
        return result

    def heal_stale_entries(self) -> dict:
        """Remove entries for files that no longer exist on disk.

        Detects:
        - file_path in registry but file doesn't exist on disk

        Returns:
            Dictionary with issues_found, issues_fixed, errors, actions_taken
        """
        issues_found = 0
        issues_fixed = 0
        errors = []
        actions = []

        try:
            conn = self._get_registry_conn()
            # Use validated table name (whitelist defense)
            table = _validate_table_name(REGISTRY_TABLE)
            cursor = conn.execute(f"SELECT file_path FROM {table}")
            all_files = cursor.fetchall()
            conn.close()

            stale_files = []
            for (file_path,) in all_files:
                if not os.path.exists(file_path):
                    stale_files.append(file_path)
                    issues_found += 1

            daemon_logger.info(f"Found {issues_found} stale registry entries")

            # Remove stale entries
            for file_path in stale_files:
                try:
                    conn = self._get_registry_conn()
                    table = _validate_table_name(REGISTRY_TABLE)
                    conn.execute(
                        f"DELETE FROM {table} WHERE file_path = ?",
                        (file_path,),
                    )
                    conn.commit()
                    conn.close()
                    actions.append(f"Removed stale registry entry: {file_path}")
                    issues_fixed += 1
                except Exception as e:
                    errors.append(f"Failed to remove {file_path}: {e}")
                    daemon_logger.error(
                        f"Failed to remove stale entry {file_path}: {e}"
                    )

        except Exception as e:
            errors.append(f"Error in heal_stale_entries: {e}")
            daemon_logger.error(f"Error healing stale entries: {e}")

        result = {
            "issues_found": issues_found,
            "issues_fixed": issues_fixed,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_fixed"] += issues_fixed
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Stale entries healing complete: {result}")
        return result

    def heal_orphaned_chunks(self) -> dict:
        """Remove chunks without corresponding files in registry.

        Detects:
        - chunks in file_chunks table but no file in file_registry
        - chunks in ChromaDB but no file in registry

        Returns:
            Dictionary with issues_found, issues_fixed, errors, actions_taken
        """
        issues_found = 0
        issues_fixed = 0
        errors = []
        actions = []

        try:
            # Check SQLite chunks vs registry
            sqlite_conn = self._get_sqlite_conn()
            # Use validated table name (whitelist defense)
            sqlite_table = _validate_table_name(SQLITE_TABLE)
            sqlite_cursor = sqlite_conn.execute(
                f"SELECT DISTINCT file_path FROM {sqlite_table}"
            )
            chunked_files = {row[0] for row in sqlite_cursor.fetchall()}

            registry_conn = self._get_registry_conn()
            registry_table = _validate_table_name(REGISTRY_TABLE)
            registry_cursor = registry_conn.execute(
                f"SELECT file_path FROM {registry_table}"
            )
            registered_files = {row[0] for row in registry_cursor.fetchall()}

            sqlite_conn.close()
            registry_conn.close()

            # Find orphaned files in SQLite chunks
            orphaned_files = chunked_files - registered_files
            issues_found += len(orphaned_files)

            daemon_logger.info(
                f"Found {len(orphaned_files)} orphaned chunk files in SQLite"
            )

            # Remove orphaned chunks from SQLite
            for file_path in orphaned_files:
                try:
                    sqlite_conn = self._get_sqlite_conn()
                    # Use validated table name (whitelist defense)
                    sqlite_table = _validate_table_name(SQLITE_TABLE)
                    sqlite_conn.execute(
                        f"DELETE FROM {sqlite_table} WHERE file_path = ?",
                        (file_path,),
                    )
                    sqlite_conn.commit()
                    sqlite_conn.close()
                    actions.append(f"Removed orphaned chunks from SQLite: {file_path}")
                    issues_fixed += 1
                except Exception as e:
                    errors.append(
                        f"Failed to remove orphaned chunks for {file_path}: {e}"
                    )
                    daemon_logger.error(f"Failed to remove orphaned chunks: {e}")

            # Check ChromaDB chunks
            try:
                collection = self._get_chroma_collection()
                if collection.count() > 0:
                    all_data = collection.get(include=["metadatas"])
                    if all_data and all_data.get("ids"):
                        chroma_orphans = []
                        for i, metadata in enumerate(all_data.get("metadatas", [])):
                            file_path = metadata.get("file_path", "")
                            if file_path and file_path not in registered_files:
                                chroma_orphans.append(all_data["ids"][i])

                        if chroma_orphans:
                            issues_found += len(chroma_orphans)
                            daemon_logger.info(
                                f"Found {len(chroma_orphans)} orphaned chunks in ChromaDB"
                            )

                            # Delete orphaned ChromaDB entries
                            collection.delete(ids=chroma_orphans)
                            actions.append(
                                f"Removed {len(chroma_orphans)} orphaned chunks from ChromaDB"
                            )
                            issues_fixed += len(chroma_orphans)
            except Exception as e:
                errors.append(f"Error checking ChromaDB orphans: {e}")
                daemon_logger.error(f"Error healing ChromaDB orphans: {e}")

        except Exception as e:
            errors.append(f"Error in heal_orphaned_chunks: {e}")
            daemon_logger.error(f"Error healing orphaned chunks: {e}")

        result = {
            "issues_found": issues_found,
            "issues_fixed": issues_fixed,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_fixed"] += issues_fixed
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Orphaned chunks healing complete: {result}")
        return result

    def heal_all(self) -> dict:
        """Run all healing operations.

        Returns:
            Dictionary with combined healing report
        """
        daemon_logger.info("Starting full healing cycle")

        # Reset report
        self._report = {
            "issues_found": 0,
            "issues_fixed": 0,
            "errors": [],
            "actions_taken": [],
        }

        # Run all healers
        self.heal_stale_entries()
        self.heal_orphaned_chunks()
        self.heal_corrupted_embeddings()

        daemon_logger.info(
            f"Healing complete: {self._report['issues_found']} issues found, "
            f"{self._report['issues_fixed']} fixed"
        )

        return self._report

    def get_healing_report(self) -> dict:
        """Get detailed healing report.

        Returns:
            Dictionary with full healing report
        """
        return self._report.copy()


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "SelfHealer",
]
