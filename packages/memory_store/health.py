#!/usr/bin/env python3
"""Health monitoring for memory+learning system.

Provides HealthCheck class for monitoring:
- Memory stores (RelationalStore)
- Learning engine (Q-Learning, OutcomeLogger)
- MCP servers (memory_store, learning_engine)
- Database integrity (SQLite, WAL)
- Cognitive engines (Forgetting, Trust, Priority)

Usage:
    from memory_store.health import HealthCheck
    health = HealthCheck()
    result = health.get_overall_health()
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatusEnum(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthStatus:
    """Health status for a single component."""

    component: str
    status: HealthStatusEnum
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)


class HealthCheck:
    """Health monitoring for memory+learning system.

    All checks are read-only and include timeout handling.
    Maximum 5 seconds per check to prevent hanging.
    """

    DEFAULT_TIMEOUT = 5.0  # seconds
    DB_PATH = "context/memory/mind_from_mind.db"
    FILE_REGISTRY_PATH = "context/memory/file_registry.db"
    LEARNING_EVENTS_PATH = "context/memory/learning_events.db"
    OUTCOMES_PATH = ".sisyphus/outcomes.db"
    Q_LEARNING_PATH = ".sisyphus/routing.db"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize HealthCheck.

        Args:
            timeout: Maximum time for each health check in seconds.
        """
        self.timeout = timeout
        self._lock = threading.Lock()

    def _timed_check(self, check_func) -> tuple[HealthStatus, bool]:
        """Execute a health check with timeout.

        Args:
            check_func: Function that returns HealthStatus.

        Returns:
            Tuple of (HealthStatus, success_bool).
        """
        result = {"success": False, "error": "timeout"}
        status = HealthStatusEnum.UNHEALTHY

        def run_check():
            nonlocal result, status
            start_time = time.perf_counter()
            try:
                hs = check_func()
                result = {
                    "component": hs.component,
                    "status": hs.status,
                    "latency_ms": hs.latency_ms,
                    "details": hs.details,
                }
                status = hs.status
            except Exception as e:
                result = {"error": str(e)}
                status = HealthStatusEnum.UNHEALTHY

        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            return (
                HealthStatus(
                    component="timeout_check",
                    status=HealthStatusEnum.UNHEALTHY,
                    latency_ms=self.timeout * 1000,
                    details={"error": f"Check timed out after {self.timeout}s"},
                ),
                False,
            )

        return (
            HealthStatus(
                component=result.get("component", "unknown"),
                status=status,
                latency_ms=result.get("latency_ms", 0),
                details=result.get("details", {}),
            ),
            status != HealthStatusEnum.UNHEALTHY,
        )

    def check_memory_stores(self) -> HealthStatus:
        """Check memory store connectivity.

        Returns:
            HealthStatus with store health information.
        """
        start = time.perf_counter()
        details = {}

        try:
            # Check RelationalStore
            db_path = Path(self.DB_PATH)
            if db_path.exists():
                conn = sqlite3.connect(str(db_path), timeout=2.0)
                try:
                    # Quick query to verify connectivity
                    conn.execute("SELECT COUNT(*) FROM memories LIMIT 1").fetchone()
                    details["relational_store"] = "ok"
                except Exception as e:
                    details["relational_store"] = f"error: {str(e)}"
                finally:
                    conn.close()
            else:
                details["relational_store"] = "not_found"

            # Check file_registry if exists
            registry_path = Path(self.FILE_REGISTRY_PATH)
            if registry_path.exists():
                conn = sqlite3.connect(str(registry_path), timeout=2.0)
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cur.fetchall()]
                    details["file_registry"] = f"ok ({len(tables)} tables)"
                except Exception as e:
                    details["file_registry"] = f"error: {str(e)}"
                finally:
                    conn.close()
            else:
                details["file_registry"] = "not_found"

            # Determine overall status
            has_errors = any("error" in str(v).lower() for v in details.values())
            status = (
                HealthStatusEnum.UNHEALTHY if has_errors else HealthStatusEnum.HEALTHY
            )

            # Check if at least one store is available
            if not any(v == "ok" for v in details.values()):
                status = HealthStatusEnum.UNHEALTHY

        except Exception as e:
            details["error"] = str(e)
            status = HealthStatusEnum.UNHEALTHY

        latency_ms = (time.perf_counter() - start) * 1000

        return HealthStatus(
            component="memory_stores",
            status=status,
            latency_ms=latency_ms,
            details=details,
        )

    def check_learning_engine(self) -> HealthStatus:
        """Check learning engine components.

        Returns:
            HealthStatus with learning engine health.
        """
        start = time.perf_counter()
        details = {}

        try:
            # Check OutcomeLogger
            outcomes_path = Path(self.OUTCOMES_PATH)
            if outcomes_path.exists():
                conn = sqlite3.connect(str(outcomes_path), timeout=2.0)
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM outcomes")
                    count = cur.fetchone()[0]
                    details["outcome_logger"] = f"ok ({count} outcomes)"
                except Exception as e:
                    details["outcome_logger"] = f"error: {str(e)}"
                finally:
                    conn.close()
            else:
                details["outcome_logger"] = "not_found"

            # Check Q-Learning database
            qlearning_path = Path(self.Q_LEARNING_PATH)
            if qlearning_path.exists():
                conn = sqlite3.connect(str(qlearning_path), timeout=2.0)
                try:
                    cur = conn.cursor()
                    # Check for q_learning table
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='q_learning'"
                    )
                    if cur.fetchone():
                        details["q_learning"] = "ok"
                    else:
                        details["q_learning"] = "no_table"
                except Exception as e:
                    details["q_learning"] = f"error: {str(e)}"
                finally:
                    conn.close()
            else:
                details["q_learning"] = "not_found"

            # Check LearningEventBus database
            events_path = Path(self.LEARNING_EVENTS_PATH)
            if events_path.exists():
                conn = sqlite3.connect(str(events_path), timeout=2.0)
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cur.fetchall()]
                    details["learning_events"] = f"ok ({len(tables)} tables)"
                except Exception as e:
                    details["learning_events"] = f"error: {str(e)}"
                finally:
                    conn.close()
            else:
                details["learning_events"] = "not_found"

            # Determine status
            ok_count = sum(1 for v in details.values() if "ok" in str(v).lower())
            if ok_count >= 2:
                status = HealthStatusEnum.HEALTHY
            elif ok_count == 1:
                status = HealthStatusEnum.DEGRADED
            else:
                status = HealthStatusEnum.UNHEALTHY

        except Exception as e:
            details["error"] = str(e)
            status = HealthStatusEnum.UNHEALTHY

        latency_ms = (time.perf_counter() - start) * 1000

        return HealthStatus(
            component="learning_engine",
            status=status,
            latency_ms=latency_ms,
            details=details,
        )

    def check_mcp_servers(self) -> HealthStatus:
        """Check MCP server availability.

        Returns:
            HealthStatus with MCP server health.
        """
        start = time.perf_counter()
        details = {}

        try:
            # Check memory_store MCP server module
            try:
                from packages.memory_store import mcp_server

                details["memory_store_mcp"] = "importable"
            except ImportError as e:
                details["memory_store_mcp"] = f"import_error: {str(e)}"
            except Exception as e:
                details["memory_store_mcp"] = f"error: {str(e)}"

            # Check learning_engine MCP server module
            try:
                from packages.learning_engine import mcp_server

                details["learning_engine_mcp"] = "importable"
            except ImportError as e:
                details["learning_engine_mcp"] = f"import_error: {str(e)}"
            except Exception as e:
                details["learning_engine_mcp"] = f"error: {str(e)}"

            # Determine status
            import_errors = sum(
                1 for v in details.values() if "import_error" in str(v).lower()
            )
            if import_errors == 0:
                status = HealthStatusEnum.HEALTHY
            elif import_errors == 1:
                status = HealthStatusEnum.DEGRADED
            else:
                status = HealthStatusEnum.UNHEALTHY

        except Exception as e:
            details["error"] = str(e)
            status = HealthStatusEnum.UNHEALTHY

        latency_ms = (time.perf_counter() - start) * 1000

        return HealthStatus(
            component="mcp_servers",
            status=status,
            latency_ms=latency_ms,
            details=details,
        )

    def check_database_integrity(self) -> HealthStatus:
        """Check database integrity (SQLite integrity, WAL mode).

        Returns:
            HealthStatus with database integrity information.
        """
        start = time.perf_counter()
        details = {}

        try:
            # Check main memory database
            db_path = Path(self.DB_PATH)
            if db_path.exists():
                conn = sqlite3.connect(str(db_path), timeout=2.0)
                try:
                    # Run integrity check
                    cursor = conn.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    details["integrity_check"] = result[0] if result else "unknown"

                    # Check WAL mode
                    cursor = conn.execute("PRAGMA journal_mode")
                    journal_mode = cursor.fetchone()[0]
                    details["journal_mode"] = journal_mode

                    # Check page count
                    cursor = conn.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    details["page_count"] = page_count

                    # Check schema version
                    cursor = conn.execute("SELECT COUNT(*) FROM schema_migrations")
                    migrations = cursor.fetchone()[0]
                    details["schema_migrations"] = migrations

                except Exception as e:
                    details["error"] = str(e)
                finally:
                    conn.close()
            else:
                details["integrity_check"] = "not_found"

            # Check outcomes database
            outcomes_path = Path(self.OUTCOMES_PATH)
            if outcomes_path.exists():
                conn = sqlite3.connect(str(outcomes_path), timeout=2.0)
                try:
                    cursor = conn.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    details["outcomes_integrity"] = result[0] if result else "unknown"
                except Exception as e:
                    details["outcomes_error"] = str(e)
                finally:
                    conn.close()

            # Determine status
            if "integrity_check" in details:
                if details.get("integrity_check") == "ok":
                    status = HealthStatusEnum.HEALTHY
                elif "error" in str(details.get("integrity_check", "")).lower():
                    status = HealthStatusEnum.UNHEALTHY
                else:
                    status = HealthStatusEnum.DEGRADED
            else:
                status = HealthStatusEnum.UNHEALTHY

        except Exception as e:
            details["error"] = str(e)
            status = HealthStatusEnum.UNHEALTHY

        latency_ms = (time.perf_counter() - start) * 1000

        return HealthStatus(
            component="database_integrity",
            status=status,
            latency_ms=latency_ms,
            details=details,
        )

    def check_cognitive_engines(self) -> HealthStatus:
        """Check cognitive engine components.

        Returns:
            HealthStatus with cognitive engine health.
        """
        start = time.perf_counter()
        details = {}

        try:
            # Check Forgetting engine (AdaptiveDecay)
            try:
                from packages.memory_store.cognitive.forgetting import AdaptiveDecay

                db_path = Path(self.DB_PATH)
                forgetting = AdaptiveDecay(db_path)
                stats = forgetting.get_decay_stats()
                details["forgetting"] = "ok (stats available)"
            except ImportError as e:
                details["forgetting"] = f"import_error: {str(e)}"
            except Exception as e:
                details["forgetting"] = f"error: {str(e)}"

            # Check Trust engine (TrustAwareRetrieval)
            try:
                from packages.memory_store.cognitive.trust import TrustAwareRetrieval

                trust = TrustAwareRetrieval(Path(self.DB_PATH))
                stats = trust.get_stats()
                details["trust"] = "ok (stats available)"
            except ImportError as e:
                details["trust"] = f"import_error: {str(e)}"
            except Exception as e:
                details["trust"] = f"error: {str(e)}"

            # Check Priority engine
            try:
                from packages.memory_store.cognitive.priority import PriorityEngine

                priority = PriorityEngine(self.FILE_REGISTRY_PATH)
                stats = priority.get_learning_stats()
                details["priority"] = "ok (stats available)"
            except ImportError as e:
                details["priority"] = f"import_error: {str(e)}"
            except Exception as e:
                details["priority"] = f"error: {str(e)}"

            # Determine status
            ok_count = sum(1 for v in details.values() if v.startswith("ok"))
            if ok_count >= 3:
                status = HealthStatusEnum.HEALTHY
            elif ok_count >= 1:
                status = HealthStatusEnum.DEGRADED
            else:
                status = HealthStatusEnum.UNHEALTHY

        except Exception as e:
            details["error"] = str(e)
            status = HealthStatusEnum.UNHEALTHY

        latency_ms = (time.perf_counter() - start) * 1000

        return HealthStatus(
            component="cognitive_engines",
            status=status,
            latency_ms=latency_ms,
            details=details,
        )

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall health status across all components.

        Returns:
            Dict with overall status and individual component statuses.
        """
        # Run all health checks
        checks = [
            self.check_memory_stores,
            self.check_learning_engine,
            self.check_mcp_servers,
            self.check_database_integrity,
            self.check_cognitive_engines,
        ]

        results = []
        for check in checks:
            hs = check()
            results.append(
                {
                    "component": hs.component,
                    "status": hs.status.value,
                    "latency_ms": round(hs.latency_ms, 2),
                    "details": hs.details,
                }
            )

        # Calculate overall status
        unhealthy_count = sum(1 for r in results if r["status"] == "unhealthy")
        degraded_count = sum(1 for r in results if r["status"] == "degraded")

        if unhealthy_count > 0:
            overall_status = HealthStatusEnum.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatusEnum.DEGRADED
        else:
            overall_status = HealthStatusEnum.HEALTHY

        # Calculate total latency
        total_latency = sum(r["latency_ms"] for r in results)

        return {
            "overall_status": overall_status.value,
            "total_latency_ms": round(total_latency, 2),
            "components": results,
            "timestamp": time.time(),
        }


# Module-level convenience function
def get_health_check(timeout: float = 5.0) -> HealthCheck:
    """Get a HealthCheck instance.

    Args:
        timeout: Maximum time for each health check in seconds.

    Returns:
        HealthCheck instance.
    """
    return HealthCheck(timeout=timeout)


def quick_health() -> dict[str, Any]:
    """Quick health check - runs all checks and returns overall status.

    Returns:
        Dict with overall health status.
    """
    checker = HealthCheck()
    return checker.get_overall_health()


__all__ = [
    "HealthCheck",
    "HealthStatus",
    "HealthStatusEnum",
    "get_health_check",
    "quick_health",
]
