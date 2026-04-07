#!/usr/bin/env python3
"""PatternAnalyzer — Detects run patterns for orchestration health.

Scans runs for:
- INTEGRITY_FAIL: Runs with failed integrity checks
- BLOCKS: Runs blocked by critic
- EVIDENCE_GAPS: Runs with missing evidence
- LOOPING: Repetitive run patterns

Thread-safe with SQLite storage at ~/.cache/n-xyme-mind/patterns.db
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/patterns.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file, returning None on failure."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# Pattern dataclasses
@dataclass
class FailurePattern:
    """Represents an integrity failure pattern."""

    pattern_id: str = "P001"
    type: str = "INTEGRITY_FAIL"
    severity: str = "HIGH"
    description: str = ""
    supporting_run_ids: List[str] = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.9


@dataclass
class BlockPattern:
    """Represents a blocked run pattern."""

    pattern_id: str = "P002"
    type: str = "BLOCKS"
    severity: str = "MED"
    description: str = ""
    supporting_run_ids: List[str] = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.7


@dataclass
class GapPattern:
    """Represents an evidence gap pattern."""

    pattern_id: str = "P003"
    type: str = "EVIDENCE_GAPS"
    severity: str = "MED"
    description: str = ""
    supporting_run_ids: List[str] = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.7


@dataclass
class LoopPattern:
    """Represents a looping/repetitive pattern."""

    pattern_id: str = "P004"
    type: str = "LOOPING"
    severity: str = "LOW"
    description: str = ""
    supporting_run_ids: List[str] = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.6


@dataclass
class AnalysisResult:
    """Result of pattern analysis."""

    failures: List[FailurePattern] = field(default_factory=list)
    blocks: List[BlockPattern] = field(default_factory=list)
    gaps: List[GapPattern] = field(default_factory=list)
    loops: List[LoopPattern] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class PatternAnalyzer:
    """SQLite-backed pattern analyzer for run health detection.

    Thread-safe with locking for concurrent access.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize PatternAnalyzer.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/n-xyme-mind/patterns.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                severity TEXT,
                confidence REAL,
                details TEXT,
                UNIQUE(run_id, pattern_type)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_run_id ON patterns(run_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_detected ON patterns(detected_at)"
        )
        conn.commit()
        conn.close()

    def _save_pattern(
        self,
        run_id: str,
        pattern_type: str,
        severity: str,
        confidence: float,
        details: Dict[str, Any],
    ) -> None:
        """Save a detected pattern to the database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO patterns 
                       (run_id, pattern_type, detected_at, severity, confidence, details)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        pattern_type,
                        _now_iso(),
                        severity,
                        confidence,
                        json.dumps(details, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def detect_integrity_failures(
        self, runs: List[Dict[str, Any]]
    ) -> List[FailurePattern]:
        """Detect runs with failed integrity checks.

        Args:
            runs: List of run dictionaries with run_id and optional paths

        Returns:
            List of FailurePattern objects
        """
        failures: List[FailurePattern] = []
        supporting_runs: List[str] = []

        for run in runs:
            run_id = run.get("run_id", "")
            run_path = run.get("path")

            if run_path:
                integrity = _load_json(Path(run_path) / "_meta" / "integrity.json")
                if integrity and str(integrity.get("status", "")).upper() == "FAIL":
                    supporting_runs.append(run_id)
                    self._save_pattern(
                        run_id=run_id,
                        pattern_type="INTEGRITY_FAIL",
                        severity="HIGH",
                        confidence=0.9,
                        details={
                            "status": integrity.get("status"),
                            "errors": integrity.get("errors", []),
                        },
                    )

        if supporting_runs:
            failures.append(
                FailurePattern(
                    pattern_id="P001",
                    type="INTEGRITY_FAIL",
                    severity="HIGH",
                    description="One or more runs failed integrity checks (missing/extra files or hash issues).",
                    supporting_run_ids=supporting_runs,
                    recommended_action="Run nxm_doctor and inspect 06_runs/<RUN_ID>/_meta/integrity.json to understand missing files.",
                    confidence=0.9,
                )
            )

        return failures

    def detect_blocks(self, runs: List[Dict[str, Any]]) -> List[BlockPattern]:
        """Detect runs blocked by the critic.

        Args:
            runs: List of run dictionaries with run_id and optional paths

        Returns:
            List of BlockPattern objects
        """
        blocks: List[BlockPattern] = []
        supporting_runs: List[str] = []

        for run in runs:
            run_id = run.get("run_id", "")
            run_path = run.get("path")

            if run_path:
                verdict = _load_json(Path(run_path) / "verdict.json")
                if verdict and str(verdict.get("verdict", "")).upper() == "BLOCK":
                    supporting_runs.append(run_id)
                    self._save_pattern(
                        run_id=run_id,
                        pattern_type="BLOCKS",
                        severity="MED",
                        confidence=0.7,
                        details={
                            "reason": verdict.get("reason", ""),
                            "verdict": "BLOCK",
                        },
                    )

        if len(supporting_runs) >= 2:
            blocks.append(
                BlockPattern(
                    pattern_id="P002",
                    type="BLOCKS",
                    severity="MED",
                    description="Multiple runs were BLOCKed by the critic in the scanned window.",
                    supporting_run_ids=supporting_runs,
                    recommended_action="Inspect verdict reasons and provide missing evidence or adjust scope. Consider recording a decision if policy needs clarity.",
                    confidence=0.7,
                )
            )

        return blocks

    def detect_evidence_gaps(self, runs: List[Dict[str, Any]]) -> List[GapPattern]:
        """Detect runs with evidence gaps.

        Args:
            runs: List of run dictionaries with run_id and optional paths

        Returns:
            List of GapPattern objects
        """
        gaps: List[GapPattern] = []
        evidence_gap_runs: List[str] = []

        for run in runs:
            run_id = run.get("run_id", "")
            run_path = run.get("path")

            if run_path:
                evidence = _load_json(Path(run_path) / "evidence_map.json")
                if evidence:
                    claims = evidence.get("claims", []) or []
                    unsupported_fact_count = 0
                    for c in claims:
                        ctype = str(c.get("type", "")).upper()
                        support = str(c.get("support", "")).upper()
                        risk = str(c.get("risk", "")).upper()
                        if ctype == "FACT" and support == "UNSUPPORTED":
                            unsupported_fact_count += 1
                        if (
                            ctype == "FACT"
                            and support == "UNSUPPORTED"
                            and risk == "HIGH"
                        ):
                            if run_id not in evidence_gap_runs:
                                evidence_gap_runs.append(run_id)
                    if unsupported_fact_count >= 3 and run_id not in evidence_gap_runs:
                        evidence_gap_runs.append(run_id)
                else:
                    # Fallback: check index_patch.json for audit tags
                    idx = _load_json(Path(run_path) / "index_patch.json")
                    if idx:
                        tags = idx.get("tags", []) or []
                        if any(str(tag).lower() == "audit" for tag in tags):
                            evidence_gap_runs.append(run_id)

                # Save each detected gap
                if run_id in evidence_gap_runs:
                    self._save_pattern(
                        run_id=run_id,
                        pattern_type="EVIDENCE_GAPS",
                        severity="MED",
                        confidence=0.7,
                        details={"run_id": run_id},
                    )

        if evidence_gap_runs:
            gaps.append(
                GapPattern(
                    pattern_id="P003",
                    type="EVIDENCE_GAPS",
                    severity="MED",
                    description="Evidence gaps detected (missing evidence_map or multiple unsupported facts).",
                    supporting_run_ids=sorted(set(evidence_gap_runs)),
                    recommended_action="Ensure evidence refs (EVT:/SNAP:/DOC:/PASTE:) accompany FACT claims and keep Evidence Cortex enabled for audits/high-risk runs.",
                    confidence=0.7,
                )
            )

        return gaps

    def detect_looping(self, runs: List[Dict[str, Any]]) -> List[LoopPattern]:
        """Detect repetitive/looping run patterns.

        Detects runs with similar prompts or repeated task patterns.

        Args:
            runs: List of run dictionaries with run_id and optional paths

        Returns:
            List of LoopPattern objects
        """
        loops: List[LoopPattern] = []

        # Build prompt hash to run_id mapping
        prompt_hashes: Dict[str, List[str]] = {}

        for run in runs:
            run_id = run.get("run_id", "")
            prompt = run.get("prompt", "")

            if prompt:
                # Simple hash: first 50 chars of prompt (use string key)
                prompt_hash = str(hash(prompt[:50]))
                if prompt_hash not in prompt_hashes:
                    prompt_hashes[prompt_hash] = []
                prompt_hashes[prompt_hash].append(run_id)

        # Find runs with same prompt (3+ = potential loop)
        looping_runs: List[str] = []
        for prompt_hash, run_ids in prompt_hashes.items():
            if len(run_ids) >= 3:
                looping_runs.extend(run_ids)

        if looping_runs:
            loops.append(
                LoopPattern(
                    pattern_id="P004",
                    type="LOOPING",
                    severity="LOW",
                    description="Repetitive runs detected with similar prompts.",
                    supporting_run_ids=sorted(set(looping_runs)),
                    recommended_action="Analyze the repeating task. Consider adding a reflexion checkpoint or escalating to break the loop.",
                    confidence=0.6,
                )
            )
            # Save patterns
            for run_id in looping_runs:
                self._save_pattern(
                    run_id=run_id,
                    pattern_type="LOOPING",
                    severity="LOW",
                    confidence=0.6,
                    details={"run_id": run_id},
                )

        return loops

    def analyze_runs(
        self,
        runs: List[Dict[str, Any]],
        patterns: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """Analyze runs for all or specified pattern types.

        Args:
            runs: List of run dictionaries with run_id, path, and optional prompt
            patterns: Optional list of pattern types to detect.
                     Options: INTEGRITY_FAIL, BLOCKS, EVIDENCE_GAPS, LOOPING.
                     If None, detects all patterns.

        Returns:
            AnalysisResult with detected patterns
        """
        if patterns is None:
            patterns = ["INTEGRITY_FAIL", "BLOCKS", "EVIDENCE_GAPS", "LOOPING"]

        failures = []
        blocks = []
        gaps = []
        loops = []

        with self._lock:
            if "INTEGRITY_FAIL" in patterns:
                failures = self.detect_integrity_failures(runs)
            if "BLOCKS" in patterns:
                blocks = self.detect_blocks(runs)
            if "EVIDENCE_GAPS" in patterns:
                gaps = self.detect_evidence_gaps(runs)
            if "LOOPING" in patterns:
                loops = self.detect_looping(runs)

        total_issues = len(failures) + len(blocks) + len(gaps) + len(loops)

        summary = {
            "total_runs_scanned": len(runs),
            "patterns_detected": total_issues,
            "integrity_failures": len(failures),
            "blocks": len(blocks),
            "evidence_gaps": len(gaps),
            "looping": len(loops),
            "timestamp": _now_iso(),
        }

        return AnalysisResult(
            failures=failures,
            blocks=blocks,
            gaps=gaps,
            loops=loops,
            summary=summary,
        )

    def get_patterns_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all patterns for a specific run.

        Args:
            run_id: The run ID to query

        Returns:
            List of pattern dictionaries
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                """SELECT pattern_type, detected_at, severity, confidence, details
                   FROM patterns WHERE run_id = ? ORDER BY detected_at DESC""",
                (run_id,),
            ).fetchall()
            conn.close()

            return [
                {
                    "pattern_type": row[0],
                    "detected_at": row[1],
                    "severity": row[2],
                    "confidence": row[3],
                    "details": json.loads(row[4]) if row[4] else {},
                }
                for row in rows
            ]

    def get_recent_patterns(
        self,
        limit: int = 100,
        pattern_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent patterns.

        Args:
            limit: Maximum number of patterns to return
            pattern_type: Optional filter by pattern type

        Returns:
            List of pattern dictionaries
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT run_id, pattern_type, detected_at, severity, confidence, details FROM patterns"
            params: List[Any] = []

            if pattern_type:
                query += " WHERE pattern_type = ?"
                params.append(pattern_type)

            query += " ORDER BY detected_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            conn.close()

            return [
                {
                    "run_id": row[0],
                    "pattern_type": row[1],
                    "detected_at": row[2],
                    "severity": row[3],
                    "confidence": row[4],
                    "details": json.loads(row[5]) if row[5] else {},
                }
                for row in rows
            ]

    def clear_patterns(self, older_than_days: Optional[int] = None) -> int:
        """Clear patterns from database.

        Args:
            older_than_days: If specified, only clear patterns older than N days

        Returns:
            Number of patterns cleared
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            if older_than_days:
                from datetime import timedelta

                cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                cursor = conn.execute(
                    "DELETE FROM patterns WHERE detected_at < ?",
                    (cutoff.isoformat(),),
                )
            else:
                cursor = conn.execute("DELETE FROM patterns")
            conn.commit()
            count = cursor.rowcount
            conn.close()
            return count


# Global singleton
_analyzer: Optional[PatternAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_analyzer() -> PatternAnalyzer:
    """Get or create the global PatternAnalyzer instance."""
    global _analyzer
    with _analyzer_lock:
        if _analyzer is None:
            _analyzer = PatternAnalyzer()
        return _analyzer


def analyze_runs(
    runs: List[Dict[str, Any]],
    patterns: Optional[List[str]] = None,
) -> AnalysisResult:
    """Convenience function to analyze runs."""
    return get_analyzer().analyze_runs(runs, patterns)


def get_patterns_for_run(run_id: str) -> List[Dict[str, Any]]:
    """Convenience function to get patterns for a run."""
    return get_analyzer().get_patterns_for_run(run_id)


def get_recent_patterns(
    limit: int = 100,
    pattern_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convenience function to get recent patterns."""
    return get_analyzer().get_recent_patterns(limit, pattern_type)
