#!/usr/bin/env python3
"""Integrity Checker — Periodic integrity checks for memory data stores.

This module runs periodic integrity checks on all data stores:
- SQLite registry integrity
- ChromaDB collection integrity
- File existence validation
- Embedding consistency checks

Reports issues without fixing them (that's self_healer's job).
Stores integrity reports in `context/memory/integrity-reports/`.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

REPORTS_DIR = "context/memory/integrity-reports"
COLLECTION_NAME = "file_embeddings"


class IntegrityChecker:
    """Periodic integrity checker for memory data stores."""

    def __init__(self, db_path: str, chroma_path: str):
        """Initialize integrity checker with paths."""
        self.db_path = db_path
        self.chroma_path = chroma_path
        self._ensure_reports_dir()

    def _ensure_reports_dir(self) -> None:
        """Ensure reports directory exists."""
        project_root = Path(__file__).parent.parent.parent
        reports_dir = project_root / REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        project_root = Path(__file__).parent.parent.parent
        db_full_path = project_root / self.db_path
        conn = sqlite3.connect(str(db_full_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _get_chroma_path(self) -> Path:
        """Get full ChromaDB path."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / self.chroma_path

    def check_sqlite_integrity(self) -> dict[str, Any]:
        """Check SQLite database integrity."""
        ts = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {
            "check": "sqlite_integrity",
            "status": "warning",
            "details": {},
            "timestamp": ts,
        }

        try:
            project_root = Path(__file__).parent.parent.parent
            db_full_path = project_root / self.db_path

            if not db_full_path.exists():
                result["status"] = "fail"
                result["details"]["error"] = f"Database file not found: {db_full_path}"
                return result

            conn = sqlite3.connect(str(db_full_path), timeout=30.0)
            cursor = conn.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            table_counts: dict[str, Any] = {}
            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_counts[table] = count
                except Exception as e:
                    table_counts[table] = f"error: {e}"
            conn.close()
            result["details"]["integrity_check"] = (
                integrity_result[0] if integrity_result else "unknown"
            )
            result["details"]["tables"] = tables
            result["details"]["table_counts"] = table_counts
            if integrity_result and integrity_result[0] == "ok":
                result["status"] = "pass"
            logger.info(f"SQLite integrity check: {result['status']}")
        except Exception as e:
            result["status"] = "fail"
            result["details"]["error"] = str(e)
            logger.error(f"SQLite integrity check failed: {e}")

        return result

    def check_chroma_integrity(self) -> dict[str, Any]:
        """Check ChromaDB collection integrity."""
        ts = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {
            "check": "chroma_integrity",
            "status": "warning",
            "details": {},
            "timestamp": ts,
        }

        try:
            chroma_path = self._get_chroma_path()
            if not chroma_path.exists():
                result["status"] = "fail"
                result["details"]["error"] = (
                    f"ChromaDB directory not found: {chroma_path}"
                )
                return result

            import chromadb

            client = chromadb.PersistentClient(path=str(chroma_path))
            try:
                collection = client.get_collection(name=COLLECTION_NAME)
            except Exception:
                collection = client.create_collection(
                    name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
                )

            count = collection.count()
            try:
                sample = collection.peek(limit=min(10, count))
                readable = sample is not None
                sample_count = len(sample.get("ids", [])) if sample else 0
            except Exception as e:
                readable = False
                sample_count = 0
                result["details"]["read_error"] = str(e)

            result["details"]["collection_name"] = COLLECTION_NAME
            result["details"]["total_embeddings"] = count
            result["details"]["sample_readable"] = readable
            result["details"]["sample_count"] = sample_count

            if count > 0 and readable:
                result["status"] = "pass"
            elif count == 0 and readable:
                result["status"] = "warning"
                result["details"]["note"] = "Collection is empty but readable"

            logger.info(f"ChromaDB integrity check: {result['status']}")
        except ImportError:
            result["status"] = "fail"
            result["details"]["error"] = "chromadb not installed"
            logger.error("ChromaDB not installed")
        except Exception as e:
            result["status"] = "fail"
            result["details"]["error"] = str(e)
            logger.error(f"ChromaDB integrity check failed: {e}")

        return result

    def check_file_existence(
        self, drives: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Check if registered files still exist on disk."""
        ts = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {
            "check": "file_existence",
            "status": "warning",
            "details": {},
            "timestamp": ts,
        }

        try:
            conn = self._get_db_connection()
            if drives:
                placeholders = ",".join(["?"] * len(drives))
                cursor = conn.execute(
                    f"SELECT file_path, drive FROM file_registry WHERE drive IN ({placeholders})",
                    drives,
                )
            else:
                cursor = conn.execute("SELECT file_path, drive FROM file_registry")
            files = cursor.fetchall()
            conn.close()

            if not files:
                result["status"] = "pass"
                result["details"]["note"] = "No files registered"
                return result

            missing_files: list[dict[str, str]] = []
            existing_count = 0
            for file_path, drive in files:
                if os.path.exists(file_path):
                    existing_count += 1
                else:
                    missing_files.append({"path": file_path, "drive": drive})

            result["details"]["total_registered"] = len(files)
            result["details"]["existing"] = existing_count
            result["details"]["missing"] = len(missing_files)
            result["details"]["missing_files"] = missing_files

            if len(missing_files) == 0:
                result["status"] = "pass"
            elif len(missing_files) < len(files) * 0.1:
                result["status"] = "warning"
            else:
                result["status"] = "fail"

            logger.info(
                f"File existence check: {result['status']} ({len(missing_files)}/{len(files)} missing)"
            )
        except Exception as e:
            result["status"] = "fail"
            result["details"]["error"] = str(e)
            logger.error(f"File existence check failed: {e}")

        return result

    def check_embedding_consistency(self) -> dict[str, Any]:
        """Check if all registry entries have corresponding embeddings."""
        ts = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {
            "check": "embedding_consistency",
            "status": "warning",
            "details": {},
            "timestamp": ts,
        }

        try:
            conn = self._get_db_connection()
            cursor = conn.execute("SELECT file_path FROM file_registry")
            registered_files = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not registered_files:
                result["status"] = "pass"
                result["details"]["note"] = "No files in registry"
                return result

            chroma_path = self._get_chroma_path()
            import chromadb

            client = chromadb.PersistentClient(path=str(chroma_path))
            try:
                collection = client.get_collection(name=COLLECTION_NAME)
            except Exception:
                collection = client.create_collection(
                    name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
                )

            all_embeddings = collection.get()
            embedded_files: set[str] = set()

            metadatas = all_embeddings.get("metadatas")
            if metadatas:
                for metadata in metadatas:
                    if metadata and isinstance(metadata, dict):
                        fp = metadata.get("file_path")
                        if isinstance(fp, str):
                            embedded_files.add(fp)

            registered_set = set(registered_files)
            files_with_embeddings = registered_set & embedded_files
            files_without_embeddings = registered_set - embedded_files

            result["details"]["total_registered"] = len(registered_set)
            result["details"]["with_embeddings"] = len(files_with_embeddings)
            result["details"]["without_embeddings"] = len(files_without_embeddings)
            result["details"]["files_without_embeddings"] = list(
                files_without_embeddings
            )[:100]

            if len(files_without_embeddings) == 0:
                result["status"] = "pass"
            elif len(files_without_embeddings) < len(registered_set) * 0.1:
                result["status"] = "warning"
            else:
                result["status"] = "fail"

            logger.info(
                f"Embedding consistency check: {result['status']} ({len(files_without_embeddings)}/{len(registered_set)} without embeddings)"
            )
        except Exception as e:
            result["status"] = "fail"
            result["details"]["error"] = str(e)
            logger.error(f"Embedding consistency check failed: {e}")

        return result

    def check_integrity(self) -> dict[str, Any]:
        """Run all integrity checks."""
        ts = datetime.now(timezone.utc).isoformat()
        report: dict[str, Any] = {
            "timestamp": ts,
            "db_path": self.db_path,
            "chroma_path": self.chroma_path,
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
        }

        checks = [
            self.check_sqlite_integrity(),
            self.check_chroma_integrity(),
            self.check_file_existence(),
            self.check_embedding_consistency(),
        ]

        for check in checks:
            report["checks"].append(check)
            status = check.get("status", "warning")
            if status == "pass":
                report["summary"]["passed"] += 1
            elif status == "fail":
                report["summary"]["failed"] += 1
            else:
                report["summary"]["warnings"] += 1

        report["summary"]["total"] = len(checks)
        logger.info(
            f"Integrity check complete: "
            f"{report['summary']['passed']} passed, "
            f"{report['summary']['warnings']} warnings, "
            f"{report['summary']['failed']} failed"
        )
        return report

    def save_report(self, report: dict[str, Any]) -> str:
        """Save integrity report to disk."""
        project_root = Path(__file__).parent.parent.parent
        reports_dir = project_root / REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = report.get("timestamp", datetime.now(timezone.utc).isoformat())
        safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
        filename = f"integrity-report-{safe_timestamp}.json"
        filepath = reports_dir / filename
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved integrity report to {filepath}")
        return str(filepath)

    def get_last_report(self) -> Optional[dict[str, Any]]:
        """Get the last integrity report."""
        project_root = Path(__file__).parent.parent.parent
        reports_dir = project_root / REPORTS_DIR
        if not reports_dir.exists():
            return None
        report_files = sorted(reports_dir.glob("integrity-report-*.json"))
        if not report_files:
            return None
        last_report_path = report_files[-1]
        try:
            with open(last_report_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read last report: {e}")
            return None


__all__ = ["IntegrityChecker"]
