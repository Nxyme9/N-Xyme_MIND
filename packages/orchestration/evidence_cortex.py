#!/usr/bin/env python3
"""EvidenceCortex — SQLite-based evidence tracking for claims.

Records claims with token references for verification purposes.
Thread-safe with locking for concurrent access.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/evidence.db"


class EvidenceType(Enum):
    """Evidence type prefixes for token references."""

    EVT_ = "EVT_"  # Event tokens
    SNAP_ = "SNAP_"  # Snapshot tokens
    DOC_ = "DOC_"  # Document tokens
    PASTE_ = "PASTE_"  # Paste tokens


# Supported token prefixes (derived from EvidenceType values)
SUPPORTED_TOKENS = [e.value for e in EvidenceType]


@dataclass
class EvidenceRecord:
    """Record of a single piece of evidence."""

    id: str
    claim: str
    evidence_type: str
    support: str  # "SUPPORTED" or "UNSUPPORTED"
    risk: str  # Risk level (e.g., "LOW", "MEDIUM", "HIGH")
    token_refs: List[str]
    timestamp: str


class EvidenceCortex:
    """SQLite-based evidence tracker with thread-safe operations."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize EvidenceCortex.

        Args:
            db_path: Path to SQLite database.
                     Defaults to ~/.cache/n-xyme-mind/evidence.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                claim TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                support TEXT NOT NULL,
                risk TEXT NOT NULL DEFAULT 'LOW',
                token_refs TEXT NOT NULL DEFAULT '[]',
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_timestamp ON evidence(timestamp)"
        )
        conn.commit()
        conn.close()

    def record_evidence(
        self,
        claim: str,
        evidence_type: str,
        support: str,
        risk: str = "LOW",
        token_refs: Optional[List[str]] = None,
    ) -> EvidenceRecord:
        """Record a piece of evidence for a claim.

        Args:
            claim: The claim text to record
            evidence_type: Type of evidence (from EvidenceType enum values)
            support: Support level ("SUPPORTED" or "UNSUPPORTED")
            risk: Risk level (default "LOW")
            token_refs: List of token references (default empty list)

        Returns:
            EvidenceRecord with generated id and timestamp
        """
        if token_refs is None:
            token_refs = []

        record = EvidenceRecord(
            id=uuid.uuid4().hex,
            claim=claim,
            evidence_type=evidence_type,
            support=support,
            risk=risk,
            token_refs=token_refs,
            timestamp=datetime.now().isoformat(),
        )

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    """INSERT INTO evidence 
                       (id, claim, evidence_type, support, risk, token_refs, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.id,
                        record.claim,
                        record.evidence_type,
                        record.support,
                        record.risk,
                        str(record.token_refs),
                        record.timestamp,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return record

    def get_evidence(
        self,
        claim: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvidenceRecord]:
        """Retrieve evidence records with optional filters.

        Args:
            claim: Optional claim text filter (partial match)
            type: Optional evidence type filter
            limit: Maximum number of records to return (default 100)

        Returns:
            List of EvidenceRecord objects, most recent first
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)

            query = "SELECT * FROM evidence WHERE 1=1"
            params: List[Any] = []

            if claim:
                query += " AND claim LIKE ?"
                params.append(f"%{claim}%")
            if type:
                query += " AND evidence_type = ?"
                params.append(type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            conn.close()

            return [
                EvidenceRecord(
                    id=row[0],
                    claim=row[1],
                    evidence_type=row[2],
                    support=row[3],
                    risk=row[4],
                    token_refs=eval(row[5]),  # Parse JSON-like list
                    timestamp=row[6],
                )
                for row in rows
            ]

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all evidence records.

        Returns:
            Dictionary with aggregate stats
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)

            # Overall stats
            overall = conn.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN support = 'SUPPORTED' THEN 1 ELSE 0 END) as supported,
                    SUM(CASE WHEN support = 'UNSUPPORTED' THEN 1 ELSE 0 END) as unsupported
                   FROM evidence"""
            ).fetchone()

            # By evidence type
            by_type = conn.execute(
                """SELECT evidence_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN support = 'SUPPORTED' THEN 1 ELSE 0 END) as supported
                   FROM evidence GROUP BY evidence_type"""
            ).fetchall()

            # By risk level
            by_risk = conn.execute(
                """SELECT risk,
                        COUNT(*) as total
                   FROM evidence GROUP BY risk"""
            ).fetchall()

            conn.close()

            return {
                "total_records": overall[0] if overall else 0,
                "supported_count": overall[1] if overall else 0,
                "unsupported_count": overall[2] if overall else 0,
                "support_rate": (
                    overall[1] / overall[0] if overall and overall[0] > 0 else 0
                ),
                "by_type": {
                    row[0]: {
                        "total": row[1],
                        "supported": row[2],
                    }
                    for row in by_type
                },
                "by_risk": {row[0]: row[1] for row in by_risk},
            }

    def close(self) -> None:
        """Close the database connection."""
        # SQLite connections are closed after each operation
        # This method exists for API consistency
        pass

    def __enter__(self) -> "EvidenceCortex":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Global singleton
_cortex: Optional[EvidenceCortex] = None
_cortex_lock = threading.Lock()


def get_cortex() -> EvidenceCortex:
    """Get or create the global EvidenceCortex instance."""
    global _cortex
    with _cortex_lock:
        if _cortex is None:
            _cortex = EvidenceCortex()
        return _cortex


def record_evidence(
    claim: str,
    evidence_type: str,
    support: str,
    risk: str = "LOW",
    token_refs: Optional[List[str]] = None,
) -> EvidenceRecord:
    """Convenience function to record evidence."""
    return get_cortex().record_evidence(
        claim=claim,
        evidence_type=evidence_type,
        support=support,
        risk=risk,
        token_refs=token_refs,
    )


def get_evidence(
    claim: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
) -> List[EvidenceRecord]:
    """Convenience function to get evidence records."""
    return get_cortex().get_evidence(
        claim=claim,
        type=type,
        limit=limit,
    )


def get_stats() -> dict[str, Any]:
    """Convenience function to get evidence statistics."""
    return get_cortex().get_stats()
