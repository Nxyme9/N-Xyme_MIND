#!/usr/bin/env python3
"""
Health Monitor — Self-monitoring system for memory subsystem.

Monitors:
- SQLite DB integrity
- ChromaDB collection health
- Disk space for all drives
- Process memory usage
- Embedding coverage

Returns health scores (0.0-1.0) and alerts for issues.
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Alert thresholds
DISK_THRESHOLD = 10  # percent
MEMORY_THRESHOLD = 80  # percent
EMBEDDING_COVERAGE_THRESHOLD = 90  # percent

# Drives to check
DRIVES_TO_CHECK = [
    os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
    "/mnt/WIN_LIBRARY",
    "/mnt/NXYME_CORE",
    "/mnt/NXYME_IMAGES",
    "/mnt/backup",
]

# Weights for health score calculation
WEIGHTS = {
    "db_integrity": 0.20,
    "chroma_health": 0.20,
    "disk_space": 0.25,
    "memory_usage": 0.15,
    "embedding_coverage": 0.20,
}


class HealthMonitor:
    """Self-monitoring system for memory subsystem health."""

    def __init__(self, db_path: str, chroma_path: str):
        """Initialize health monitor with paths.

        Args:
            db_path: Path to SQLite registry DB
            chroma_path: Path to ChromaDB storage
        """
        self.db_path: str = db_path
        self.chroma_path: str = chroma_path
        self._last_check: Optional[dict] = None

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _log_check(self, check_name: str, status: str, details: dict) -> None:
        """Log health check to daemon.log."""
        log_entry = (
            f"[{self._get_timestamp()}] HEALTH {check_name}: {status} - {details}"
        )
        logger.info(log_entry)

    def check_db_integrity(self) -> dict:
        """Check SQLite DB integrity.

        Returns:
            dict with status, details, timestamp
        """
        result = {
            "status": "healthy",
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        try:
            # Check if DB file exists
            if not os.path.exists(self.db_path):
                result["status"] = "critical"
                result["details"] = {"error": "Database file not found"}
                self._log_check("db_integrity", "CRITICAL", result["details"])
                return result

            # Check file size
            db_size = os.path.getsize(self.db_path)
            result["details"]["size_bytes"] = db_size
            result["details"]["size_mb"] = round(db_size / (1024 * 1024), 2)

            # Run integrity check
            conn = sqlite3.connect(self.db_path, timeout=30.0)

            # Check tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            result["details"]["tables"] = tables

            if "file_registry" not in tables:
                result["status"] = "warning"
                result["details"]["error"] = "file_registry table missing"
            else:
                # Get row count
                cursor = conn.execute("SELECT COUNT(*) FROM file_registry")
                count = cursor.fetchone()[0]
                result["details"]["registry_count"] = count

                # Run PRAGMA integrity_check
                cursor = conn.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()[0]
                result["details"]["integrity_check"] = integrity

                if integrity != "ok":
                    result["status"] = "critical"
                    result["details"]["integrity_error"] = integrity

            # Check indexes
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            result["details"]["indexes"] = indexes

            conn.close()

        except sqlite3.Error as e:
            result["status"] = "critical"
            result["details"] = {"error": str(e)}
        except Exception as e:
            result["status"] = "warning"
            result["details"] = {"error": str(e)}

        self._log_check("db_integrity", result["status"].upper(), result["details"])
        return result

    def check_chroma_health(self) -> dict:
        """Check ChromaDB collection health.

        Returns:
            dict with status, details, timestamp
        """
        result = {
            "status": "healthy",
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        try:
            # Resolve paths relative to project root
            project_root = Path(__file__).parent.parent.parent
            chroma_full_path = project_root / self.chroma_path

            # Check if directory exists
            if not chroma_full_path.exists():
                result["status"] = "warning"
                result["details"] = {"error": "ChromaDB directory not found"}
                self._log_check("chroma_health", "WARNING", result["details"])
                return result

            # Get directory size
            total_size = 0
            for dirpath, _, filenames in os.walk(chroma_full_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
            result["details"]["size_bytes"] = total_size
            result["details"]["size_mb"] = round(total_size / (1024 * 1024), 2)

            # Try to connect to ChromaDB and check collection
            import chromadb

            client = chromadb.PersistentClient(path=str(chroma_full_path))

            try:
                collection = client.get_or_create_collection("file_embeddings")
                count = collection.count()
                result["details"]["collection_count"] = count

                if count == 0:
                    result["status"] = "warning"
                    result["details"]["warning"] = "No embeddings in collection"
            except Exception as e:
                result["status"] = "warning"
                result["details"]["chroma_error"] = str(e)

        except ImportError:
            result["status"] = "warning"
            result["details"]["error"] = "chromadb not installed"
        except Exception as e:
            result["status"] = "warning"
            result["details"] = {"error": str(e)}

        self._log_check("chroma_health", result["status"].upper(), result["details"])
        return result

    def check_disk_space(self) -> dict:
        """Check available disk space for all drives.

        Returns:
            dict with status, details, timestamp
        """
        result = {
            "status": "healthy",
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        min_free_percent = 100  # Start at 100, will be lowered

        for drive in DRIVES_TO_CHECK:
            try:
                if not os.path.exists(drive):
                    result["details"][drive] = {
                        "status": "missing",
                        "error": "Drive not mounted",
                    }
                    continue

                stat = shutil.disk_usage(drive)
                free_gb = stat.free / (1024**3)
                total_gb = stat.total / (1024**3)
                free_percent = (stat.free / stat.total) * 100

                result["details"][drive] = {
                    "free_bytes": stat.free,
                    "total_bytes": stat.total,
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "free_percent": round(free_percent, 2),
                }

                if free_percent < DISK_THRESHOLD:
                    result["details"][drive]["status"] = "critical"
                    result["status"] = "critical"
                elif free_percent < 20:
                    result["details"][drive]["status"] = "warning"
                    if result["status"] != "critical":
                        result["status"] = "warning"

                min_free_percent = min(min_free_percent, free_percent)

            except Exception as e:
                result["details"][drive] = {
                    "status": "error",
                    "error": str(e),
                }

        result["details"]["min_free_percent"] = round(min_free_percent, 2)

        self._log_check(
            "disk_space",
            result["status"].upper(),
            {"min_free": result["details"]["min_free_percent"]},
        )
        return result

    def check_memory_usage(self) -> dict:
        """Check process memory usage.

        Returns:
            dict with status, details, timestamp
        """
        result = {
            "status": "healthy",
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        try:
            import psutil

            process = psutil.Process(os.getpid())

            mem_info = process.memory_info()
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)

            # Get system memory
            sys_mem = psutil.virtual_memory()
            sys_mem_percent = sys_mem.percent

            result["details"]["process_rss_mb"] = round(rss_mb, 2)
            result["details"]["process_vms_mb"] = round(vms_mb, 2)
            result["details"]["system_percent"] = round(sys_mem_percent, 2)
            result["details"]["system_available_mb"] = round(
                sys_mem.available / (1024 * 1024), 2
            )

            if sys_mem_percent > MEMORY_THRESHOLD:
                result["status"] = "critical"
            elif sys_mem_percent > 70:
                result["status"] = "warning"

        except ImportError:
            # Fallback if psutil not available
            try:
                with open("/proc/meminfo", "r") as f:
                    mem_data = {}
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            mem_data[parts[0].strip()] = parts[1].strip()

                # ParseMemAvailable = MemTotal - MemFree - Buffers -Cached (simplified)
                total_kb = int(mem_data.get("MemTotal:", "0").split()[0])
                available_kb = int(
                    mem_data.get(
                        "MemAvailable:", mem_data.get("MemFree:", "0")
                    ).split()[0]
                )
                free_percent = (available_kb / total_kb) * 100
                used_percent = 100 - free_percent

                result["details"]["system_percent"] = round(used_percent, 2)
                result["details"]["system_available_mb"] = round(available_kb / 1024, 2)

                if used_percent > MEMORY_THRESHOLD:
                    result["status"] = "critical"
                elif used_percent > 70:
                    result["status"] = "warning"

            except Exception as e:
                result["status"] = "warning"
                result["details"]["error"] = f"Could not read memory: {e}"
        except Exception as e:
            result["status"] = "warning"
            result["details"]["error"] = str(e)

        self._log_check("memory_usage", result["status"].upper(), result["details"])
        return result

    def check_embedding_coverage(self) -> dict:
        """Check percentage of files with embeddings.

        Compares registry count vs ChromaDB count.

        Returns:
            dict with status, details, timestamp
        """
        result = {
            "status": "healthy",
            "details": {},
            "timestamp": self._get_timestamp(),
        }

        try:
            # Get registry count
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.execute("SELECT COUNT(*) FROM file_registry")
                registry_count = cursor.fetchone()[0] or 0
                conn.close()
            else:
                registry_count = 0

            result["details"]["registry_count"] = registry_count

            # Get ChromaDB count
            try:
                import chromadb

                project_root = Path(__file__).parent.parent.parent
                chroma_full_path = project_root / self.chroma_path

                if chroma_full_path.exists():
                    client = chromadb.PersistentClient(path=str(chroma_full_path))
                    collection = client.get_or_create_collection("file_embeddings")
                    chroma_count = collection.count()
                else:
                    chroma_count = 0
            except Exception:
                chroma_count = 0

            result["details"]["chroma_count"] = chroma_count

            # Calculate coverage
            if registry_count > 0:
                coverage = (chroma_count / registry_count) * 100
                # Note: chroma_count can be > registry_count due to multiple chunks per file
                # So we cap at 100%
                coverage = min(coverage, 100.0)
                result["details"]["coverage_percent"] = round(coverage, 2)

                if coverage < EMBEDDING_COVERAGE_THRESHOLD:
                    result["status"] = "warning"
            else:
                result["details"]["coverage_percent"] = (
                    100.0 if chroma_count > 0 else 0.0
                )

        except Exception as e:
            result["status"] = "warning"
            result["details"]["error"] = str(e)

        self._log_check(
            "embedding_coverage", result["status"].upper(), result["details"]
        )
        return result

    def check_all(self) -> dict:
        """Run all health checks.

        Returns:
            dict with all check results and overall summary
        """
        checks = {
            "db_integrity": self.check_db_integrity(),
            "chroma_health": self.check_chroma_health(),
            "disk_space": self.check_disk_space(),
            "memory_usage": self.check_memory_usage(),
            "embedding_coverage": self.check_embedding_coverage(),
        }

        self._last_check = {
            "checks": checks,
            "timestamp": self._get_timestamp(),
        }

        return self._last_check

    def get_health_score(self) -> float:
        """Calculate overall health score (0.0-1.0).

        Weighted average of all checks.

        Returns:
            Health score between 0.0 and 1.0
        """
        if self._last_check is None:
            self.check_all()

        score = 0.0

        for check_name, weight in WEIGHTS.items():
            check_result: dict = {}
            if self._last_check and "checks" in self._last_check:
                check_result = self._last_check["checks"].get(check_name, {})
            else:
                # Run individual check
                if check_name == "db_integrity":
                    check_result = self.check_db_integrity()
                elif check_name == "chroma_health":
                    check_result = self.check_chroma_health()
                elif check_name == "disk_space":
                    check_result = self.check_disk_space()
                elif check_name == "memory_usage":
                    check_result = self.check_memory_usage()
                elif check_name == "embedding_coverage":
                    check_result = self.check_embedding_coverage()

            status = check_result.get("status", "healthy")

            if status == "healthy":
                score += weight * 1.0
            elif status == "warning":
                score += weight * 0.5
            elif status == "critical":
                score += weight * 0.0

        return round(score, 3)

    def get_alerts(self) -> list[str]:
        """Return active alerts/warnings.

        Returns:
            List of alert messages
        """
        if self._last_check is None:
            self.check_all()

        alerts: list[str] = []

        checks = self._last_check.get("checks", {}) if self._last_check else {}

        # Check disk space
        disk_check = checks.get("disk_space", {})
        disk_details = disk_check.get("details", {})
        for drive in DRIVES_TO_CHECK:
            if drive in disk_details:
                info = disk_details[drive]
                status = info.get("status", "")
                free_percent = info.get("free_percent", 0)
                if status == "critical" or free_percent < DISK_THRESHOLD:
                    alerts.append(f"LOW DISK on {drive}: {free_percent:.1f}% free")

        # Check memory
        mem_check = checks.get("memory_usage", {})
        mem_percent = mem_check.get("details", {}).get("system_percent", 0)
        if mem_percent > MEMORY_THRESHOLD:
            alerts.append(f"HIGH MEMORY: {mem_percent:.1f}% used")

        # Check embedding coverage
        emb_check = checks.get("embedding_coverage", {})
        coverage = emb_check.get("details", {}).get("coverage_percent", 100)
        if coverage < EMBEDDING_COVERAGE_THRESHOLD:
            alerts.append(f"LOW EMBEDDING COVERAGE: {coverage:.1f}%")

        # Check DB integrity
        db_check = checks.get("db_integrity", {})
        if db_check.get("status") == "critical":
            alerts.append(
                f"DB INTEGRITY CRITICAL: {db_check.get('details', {}).get('error', 'unknown')}"
            )

        return alerts


# Convenience function for CLI usage
def main():
    """Run health monitor and print results."""
    import sys

    # Default paths
    db_path = "context/memory/file_registry.db"
    chroma_path = "context/memory/file_chroma"

    # Allow override via args
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        chroma_path = sys.argv[2]

    monitor = HealthMonitor(db_path, chroma_path)
    result = monitor.check_all()

    print(f"Health Score: {monitor.get_health_score():.3f}")
    print(f"Alerts: {monitor.get_alerts()}")
    print(f"\nDetails:")
    for check_name, check_result in result.get("checks", {}).items():
        print(f"  {check_name}: {check_result.get('status')}")


if __name__ == "__main__":
    main()
