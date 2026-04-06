#!/usr/bin/env python3
"""
Auto-Recovery — Automatic recovery from failures detected by integrity_checker.

Provides:
- recover_failed_embeddings(): Re-embed files that failed embedding
- rebuild_corrupted_indexes(): Rebuild corrupted ChromaDB indexes
- recover_missing_chunks(): Recover chunks missing from ChromaDB
- recover_all(): Run all recovery operations
- get_recovery_report(): Return detailed recovery report

Detection: Files in registry but no embeddings in ChromaDB
Recovery: Re-embed using file_embedder.py embed_file()
Index rebuild: Drop and recreate ChromaDB collection, re-embed all
Logs all actions to daemon.log
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

import chromadb

from .embeddings import get_engine

# Constants
COLLECTION_NAME = "file_embeddings"
SQLITE_TABLE = "file_chunks"
REGISTRY_TABLE = "file_registry"

# Configure logging to daemon.log
daemon_logger = logging.getLogger("auto_recovery")
daemon_logger.setLevel(logging.INFO)
handler = logging.FileHandler("daemon.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
daemon_logger.addHandler(handler)


class AutoRecovery:
    """Automatic recovery from embedding and index failures."""

    def __init__(self, db_path: str, chroma_path: str):
        """Initialize AutoRecovery with paths.

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

        self._chroma_client: Optional[chromadb.PersistentClient] = None  # type: ignore[assignment]
        self._chroma_collection: Optional[chromadb.Collection] = None  # type: ignore[assignment]

        # Recovery report accumulation
        self._report = {
            "issues_found": 0,
            "issues_recovered": 0,
            "errors": [],
            "actions_taken": [],
        }

    def _get_chroma_collection(self) -> "chromadb.Collection":
        """Get or initialize ChromaDB collection."""
        if self._chroma_collection is not None:
            return self._chroma_collection

        self._chroma_client = chromadb.PersistentClient(path=str(self._chroma_path))  # type: ignore[assignment]
        self._chroma_collection = self._chroma_client.get_or_create_collection(  # type: ignore[union-attr]
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return self._chroma_collection  # type: ignore[return-value]

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        """Get SQLite connection for chunks."""
        conn = sqlite3.connect(str(self._sqlite_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _get_registry_conn(self) -> sqlite3.Connection:
        """Get registry SQLite connection."""
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _get_embedded_files(self) -> set[str]:
        """Get set of files that have embeddings in ChromaDB."""
        embedded_files = set()
        try:
            collection = self._get_chroma_collection()
            if collection.count() > 0:
                all_data = collection.get(include=["metadatas"])
                metadatas = all_data.get("metadatas")
                if metadatas:
                    for metadata in metadatas:
                        if metadata and isinstance(metadata, dict):
                            fp = metadata.get("file_path")
                            if isinstance(fp, str) and fp:
                                embedded_files.add(fp)
        except Exception as e:
            daemon_logger.warning(f"Could not get embedded files from ChromaDB: {e}")
        return embedded_files

    def recover_failed_embeddings(self) -> dict:
        """Re-embed files that failed embedding.

        Detects:
        - Files in registry but no embeddings in ChromaDB

        Recovery:
        - Re-embed using file_embedder.embed_file()

        Returns:
            Dictionary with issues_found, issues_recovered, errors, actions_taken
        """
        issues_found = 0
        issues_recovered = 0
        errors = []
        actions = []

        try:
            # Get all files in registry
            conn = self._get_registry_conn()
            cursor = conn.execute(f"SELECT file_path FROM {REGISTRY_TABLE}")
            registered_files = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not registered_files:
                daemon_logger.info("No files in registry to check")
                return {
                    "issues_found": 0,
                    "issues_recovered": 0,
                    "errors": [],
                    "actions_taken": [],
                }

            # Get files with embeddings
            embedded_files = self._get_embedded_files()

            # Find files without embeddings
            registered_set = set(registered_files)
            files_without_embeddings = registered_set - embedded_files
            issues_found = len(files_without_embeddings)

            daemon_logger.info(f"Found {issues_found} files without embeddings")

            # Re-embed each missing file
            for file_path in files_without_embeddings:
                try:
                    if not os.path.exists(file_path):
                        # File doesn't exist - log warning but don't add to errors
                        actions.append(f"Skipped missing file: {file_path}")
                        issues_recovered += 1
                        continue

                    # Read file content
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not content.strip():
                        actions.append(f"Skipped empty file: {file_path}")
                        issues_recovered += 1
                        continue

                    # Import here to avoid circular deps
                    from .drive_embedder import embed_file_content as embed_file  # type: ignore[import]

                    result = embed_file(file_path, content)  # type: ignore[call-arg]
                    actions.append(
                        f"Re-embedded {file_path}: {result.get('embedded', 0)} chunks"
                    )
                    issues_recovered += 1

                except Exception as e:
                    errors.append(f"Failed to re-embed {file_path}: {e}")
                    daemon_logger.error(f"Failed to re-embed {file_path}: {e}")

        except Exception as e:
            errors.append(f"Error in recover_failed_embeddings: {e}")
            daemon_logger.error(f"Error recovering failed embeddings: {e}")

        result = {
            "issues_found": issues_found,
            "issues_recovered": issues_recovered,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_recovered"] += issues_recovered
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Failed embeddings recovery complete: {result}")
        return result

    def rebuild_corrupted_indexes(self) -> dict:
        """Rebuild corrupted ChromaDB indexes.

        Detects:
        - Collection count mismatch
        - Unreadable data
        - Index corruption

        Recovery:
        - Drop and recreate collection
        - Re-embed all files from registry

        Returns:
            Dictionary with issues_found, issues_recovered, errors, actions_taken
        """
        issues_found = 0
        issues_recovered = 0
        errors = []
        actions = []

        try:
            # Check ChromaDB integrity
            chroma_path = self._chroma_path
            if not chroma_path.exists():
                daemon_logger.warning(f"ChromaDB path does not exist: {chroma_path}")
                return {
                    "issues_found": 0,
                    "issues_recovered": 0,
                    "errors": ["ChromaDB path does not exist"],
                    "actions_taken": [],
                }

            # Try to access the collection
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(name=COLLECTION_NAME)
                count = collection.count()

                # Try to peek - if this fails, collection is corrupted
                try:
                    sample = collection.peek(limit=min(10, count))
                    if sample is None or len(sample.get("ids", [])) == 0:
                        issues_found = 1
                        daemon_logger.warning(
                            "ChromaDB collection is empty or unreadable"
                        )
                except Exception as e:
                    issues_found = 1
                    errors.append(f"Collection peek failed: {e}")
                    daemon_logger.warning(f"Collection peek failed: {e}")

            except Exception as e:
                # Collection doesn't exist or is corrupted
                issues_found = 1
                errors.append(f"Collection access failed: {e}")
                daemon_logger.warning(f"Collection access failed: {e}")

            if issues_found > 0:
                # Rebuild the index
                try:
                    # Delete the entire ChromaDB directory
                    import shutil

                    if chroma_path.exists():
                        shutil.rmtree(chroma_path)
                        actions.append(
                            f"Removed corrupted ChromaDB directory: {chroma_path}"
                        )

                    # Recreate directory
                    chroma_path.mkdir(parents=True, exist_ok=True)
                    actions.append(f"Recreated ChromaDB directory: {chroma_path}")

                    # Re-embed all files from registry
                    conn = self._get_registry_conn()
                    cursor = conn.execute(f"SELECT file_path FROM {REGISTRY_TABLE}")
                    registered_files = [row[0] for row in cursor.fetchall()]
                    conn.close()

                    from .drive_embedder import embed_file_content as embed_file  # type: ignore[import]

                    reembedded_count = 0
                    for file_path in registered_files:
                        try:
                            if os.path.exists(file_path):
                                with open(
                                    file_path, "r", encoding="utf-8", errors="ignore"
                                ) as f:
                                    content = f.read()
                                if content.strip():
                                    embed_file(file_path, content)  # type: ignore[call-arg]
                                    reembedded_count += 1
                        except Exception as e:
                            errors.append(f"Failed to re-embed {file_path}: {e}")
                            daemon_logger.error(f"Failed to re-embed {file_path}: {e}")

                    actions.append(f"Re-embedded {reembedded_count} files")
                    issues_recovered = 1

                except Exception as e:
                    errors.append(f"Failed to rebuild index: {e}")
                    daemon_logger.error(f"Failed to rebuild index: {e}")

        except Exception as e:
            errors.append(f"Error in rebuild_corrupted_indexes: {e}")
            daemon_logger.error(f"Error rebuilding corrupted indexes: {e}")

        result = {
            "issues_found": issues_found,
            "issues_recovered": issues_recovered,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_recovered"] += issues_recovered
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Index rebuild complete: {result}")
        return result

    def recover_missing_chunks(self) -> dict:
        """Recover chunks missing from ChromaDB.

        Detects:
        - Files in SQLite chunks but no corresponding embeddings in ChromaDB

        Recovery:
        - Re-embed files with missing chunks

        Returns:
            Dictionary with issues_found, issues_recovered, errors, actions_taken
        """
        issues_found = 0
        issues_recovered = 0
        errors = []
        actions = []

        try:
            # Get files from SQLite chunks
            sqlite_conn = self._get_sqlite_conn()
            cursor = sqlite_conn.execute(
                f"SELECT DISTINCT file_path FROM {SQLITE_TABLE}"
            )
            chunked_files = {row[0] for row in cursor.fetchall()}
            sqlite_conn.close()

            if not chunked_files:
                daemon_logger.info("No files in SQLite chunks to check")
                return {
                    "issues_found": 0,
                    "issues_recovered": 0,
                    "errors": [],
                    "actions_taken": [],
                }

            # Get files with embeddings
            embedded_files = self._get_embedded_files()

            # Find files in SQLite but not in ChromaDB
            files_with_missing_chunks = chunked_files - embedded_files
            issues_found = len(files_with_missing_chunks)

            daemon_logger.info(f"Found {issues_found} files with missing chunks")

            # Re-embed each file with missing chunks
            for file_path in files_with_missing_chunks:
                try:
                    if not os.path.exists(file_path):
                        actions.append(f"Skipped missing file: {file_path}")
                        issues_recovered += 1
                        continue

                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not content.strip():
                        actions.append(f"Skipped empty file: {file_path}")
                        issues_recovered += 1
                        continue

                    from .drive_embedder import embed_file_content as embed_file  # type: ignore[import]

                    result = embed_file(file_path, content)  # type: ignore[call-arg]
                    actions.append(
                        f"Recovered chunks for {file_path}: {result.get('embedded', 0)} chunks"
                    )
                    issues_recovered += 1

                except Exception as e:
                    errors.append(f"Failed to recover chunks for {file_path}: {e}")
                    daemon_logger.error(
                        f"Failed to recover chunks for {file_path}: {e}"
                    )

        except Exception as e:
            errors.append(f"Error in recover_missing_chunks: {e}")
            daemon_logger.error(f"Error recovering missing chunks: {e}")

        result = {
            "issues_found": issues_found,
            "issues_recovered": issues_recovered,
            "errors": errors,
            "actions_taken": actions,
        }

        self._report["issues_found"] += issues_found
        self._report["issues_recovered"] += issues_recovered
        self._report["errors"].extend(errors)
        self._report["actions_taken"].extend(actions)

        daemon_logger.info(f"Missing chunks recovery complete: {result}")
        return result

    def recover_all(self) -> dict:
        """Run all recovery operations.

        Returns:
            Dictionary with combined recovery report
        """
        daemon_logger.info("Starting full recovery cycle")

        # Reset report
        self._report = {
            "issues_found": 0,
            "issues_recovered": 0,
            "errors": [],
            "actions_taken": [],
        }

        # Run all recovery operations
        self.recover_failed_embeddings()
        self.recover_missing_chunks()
        self.rebuild_corrupted_indexes()

        daemon_logger.info(
            f"Recovery complete: {self._report['issues_found']} issues found, "
            f"{self._report['issues_recovered']} recovered"
        )

        return self._report

    def get_recovery_report(self) -> dict:
        """Get detailed recovery report.

        Returns:
            Dictionary with full recovery report
        """
        return self._report.copy()


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = ["AutoRecovery"]
