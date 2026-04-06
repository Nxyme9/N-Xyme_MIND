#!/usr/bin/env python3
"""Memory Daemon — Main continuous daemon loop for self-aware memory system.

Integrates:
- file_watcher: Real-time file monitoring
- scan_scheduler: Periodic full scans
- health_monitor: System health checks
- priority_engine: Task prioritization

Runs continuously as a background daemon with graceful signal handling.
"""

import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Ensure src/memory is in path
sys.path.insert(0, str(PROJECT_ROOT))


def _resolve_watch_drives() -> list[str]:
    """Resolve watch drives, only including paths that actually exist."""
    candidates = [
        os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
        "/mnt/WIN_LIBRARY",
        "/mnt/NXYME_CORE",
    ]
    return [d for d in candidates if d and os.path.isdir(d)]


# Default configuration with proper types
DEFAULT_CONFIG: dict[str, Any] = {
    "log_level": "INFO",
    "log_file": "context/memory/daemon.log",
    "status_file": "context/memory/daemon-status.json",
    "pid_file": "context/memory/daemon.pid",
    "health_check_interval_seconds": 30,
    "scan_interval_hours": 24,
    "watch_drives": _resolve_watch_drives(),
}

logger: logging.Logger = logging.getLogger(__name__)


class HealthMonitor:
    """Simple health monitor that checks system components."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._status: dict[str, Any] = {
            "healthy": True,
            "components": {},
            "last_check": None,
            "errors": [],
        }

    def check(self) -> dict[str, Any]:
        """Run health check on all components."""
        errors: list[str] = []
        components: dict[str, Any] = {}

        # Check file watcher
        try:
            from .file_watcher import is_watcher_running

            watcher_ok = is_watcher_running()
            components["file_watcher"] = {"running": watcher_ok, "healthy": watcher_ok}
            if not watcher_ok:
                errors.append("File watcher not running")
        except Exception as e:
            components["file_watcher"] = {
                "running": False,
                "healthy": False,
                "error": str(e),
            }
            errors.append(f"File watcher error: {e}")

        # Check scan scheduler
        try:
            from .scan_scheduler import get_scan_status

            scan_status = get_scan_status()
            scheduler_ok = scan_status.get("is_running", False)
            components["scan_scheduler"] = {
                "running": scheduler_ok,
                "healthy": scheduler_ok,
                "last_scan": scan_status.get("last_scan"),
                "next_scan": scan_status.get("next_scan"),
            }
            if not scheduler_ok:
                errors.append("Scan scheduler not running")
        except Exception as e:
            components["scan_scheduler"] = {
                "running": False,
                "healthy": False,
                "error": str(e),
            }
            errors.append(f"Scan scheduler error: {e}")

        # Check drive health
        try:
            from .config import health_check_drives

            drive_results = health_check_drives()
            all_healthy = all(r.get("healthy", False) for r in drive_results.values())
            components["drives"] = {"healthy": all_healthy, "drives": drive_results}
            if not all_healthy:
                errors.append("Some drives not healthy")
        except Exception as e:
            components["drives"] = {"healthy": False, "error": str(e)}
            errors.append(f"Drive health check error: {e}")

        # Check vector index (simplified - just check module exists)
        try:
            from . import vector_index

            components["vector_index"] = {"healthy": True}
        except Exception as e:
            components["vector_index"] = {"healthy": False, "error": str(e)}
            errors.append(f"Vector index error: {e}")

        self._status = {
            "healthy": len(errors) == 0,
            "components": components,
            "last_check": datetime.now().isoformat(),
            "errors": errors[-10:],  # Keep last 10 errors
        }

        return self._status

    @property
    def status(self) -> dict[str, Any]:
        """Get current health status."""
        return self._status


# Note: Real PriorityEngine is at src/memory/priority_engine.py
# This daemon uses the real one via _priority_engine attribute


class MemoryDaemon:
    """Main daemon class for continuous memory system operation."""

    # Memory monitoring constants
    MAX_MEMORY_MB: int = 1024  # 1GB limit before graceful restart
    MEMORY_CHECK_INTERVAL: int = 30  # Check every 30 seconds

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize daemon with configuration.

        Args:
            config: Configuration dictionary (uses defaults if not provided)
        """
        # Merge config with defaults, ensuring proper types
        self.config = DEFAULT_CONFIG.copy()
        if config:
            for key, value in config.items():
                self.config[key] = value

        self._running = False
        self._health_monitor: Optional[HealthMonitor] = None
        self._priority_engine = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._learning_thread: Optional[threading.Thread] = None
        self._memory_monitor_thread: Optional[threading.Thread] = None
        self._memory_stop_event = threading.Event()
        self._learning_stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._status: dict[str, Any] = {
            "started": False,
            "running": False,
            "stopped": False,
            "components": {},
            "started_at": None,
            "stopped_at": None,
            "errors": [],
            "memory_mb": 0,
        }

        # Setup logging
        self._setup_logging()

        # Register signal handlers
        self._setup_signal_handlers()

        logger.info("MemoryDaemon initialized")

    def _setup_logging(self) -> None:
        """Setup logging to file and console."""
        log_file = PROJECT_ROOT / str(
            self.config.get("log_file", "context/memory/daemon.log")
        )
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        log_level_str = str(self.config.get("log_level", "INFO"))
        log_level = getattr(logging, log_level_str, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout),
            ],
        )

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, initiating graceful shutdown...")
        self.stop()

    def _write_pid(self) -> None:
        """Write PID file."""
        pid_file = PROJECT_ROOT / str(
            self.config.get("pid_file", "context/memory/daemon.pid")
        )
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))

    def _remove_pid(self) -> None:
        """Remove PID file."""
        pid_file = PROJECT_ROOT / str(
            self.config.get("pid_file", "context/memory/daemon.pid")
        )
        if pid_file.exists():
            pid_file.unlink()

    def _write_status(self) -> None:
        """Write daemon status to file."""
        status_file = PROJECT_ROOT / str(
            self.config.get("status_file", "context/memory/daemon-status.json")
        )
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Get component status
        components: dict[str, Any] = {}
        if self._health_monitor:
            components["health"] = self._health_monitor.status

        # Get scan status if available
        try:
            from .scan_scheduler import get_scan_status

            components["scan_scheduler"] = get_scan_status()
        except Exception as e:
            logger.debug(f"Could not get scan status: {e}")

        # Get watcher status
        try:
            from .file_watcher import is_watcher_running

            components["file_watcher"] = {"running": is_watcher_running()}
        except Exception as e:
            logger.debug(f"Could not get watcher status: {e}")

        status: dict[str, Any] = {
            "daemon": {
                "running": self._running,
                "pid": os.getpid(),
                "started_at": self._status.get("started_at"),
            },
            "components": components,
            "last_update": datetime.now().isoformat(),
        }

        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)

    def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                if self._health_monitor:
                    self._health_monitor.check()
                self._write_status()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            # Sleep until next check
            interval = int(self.config.get("health_check_interval_seconds", 30))
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)

    def _learning_cycle_loop(self) -> None:
        """Background learning cycle loop."""
        import logging
        from . import learning_config
        from .priority_engine import PriorityEngine
        from .knowledge_graph import KnowledgeGraph
        from .enhancements import archive_old_memories

        logger.info("Learning cycle loop started")

        while not self._learning_stop_event.is_set():
            try:
                # Get learning config
                config = learning_config.get_config()
                cycle_minutes: int = int(config.get("learning_cycle_minutes", 120))
                enabled = config.get("enabled", False)

                if not enabled:
                    logger.debug("Learning disabled, sleeping...")
                    time.sleep(60)
                    continue

                logger.info("Starting learning cycle...")

                # 0. Track budget for this cycle
                try:
                    from src.intelligence.budget_tracker import get_budget_tracker

                    tracker = get_budget_tracker()
                    tracker.record_continuation("learning_cycle")
                    status = tracker.get_status("learning_cycle")
                    if status.get("nudge_message"):
                        logger.warning(f"Budget nudge: {status['nudge_message']}")
                except Exception as e:
                    logger.debug(f"Budget tracking skipped: {e}")
                # 1. Adapt priority weights
                try:
                    if self._priority_engine:
                        self._priority_engine._adapt_weights()
                        logger.info("Priority weights adapted")
                except Exception as e:
                    logger.error(f"Error adapting priority weights: {e}")

                # 2. Check knowledge graph for merges
                try:
                    kg = KnowledgeGraph()
                    merges = kg.suggest_merges(  # type: ignore[attr-defined]
                        threshold=config.get("consolidation_threshold", 0.95)
                    )
                    if merges:
                        logger.info(f"Found {len(merges)} entity merge suggestions")
                    else:
                        logger.debug("No entity merges suggested")
                except Exception as e:
                    logger.error(f"Error checking knowledge graph merges: {e}")

                # 3. Archive old memories if enabled
                try:
                    if config.get("forget_enabled", False):
                        days = config.get("feedback_ttl_days", 90)
                        archived = archive_old_memories(
                            db_path=config.get("db_path"),
                            days=days,
                            min_importance=config.get("min_confidence", 0.8),
                        )
                        logger.info(f"Archived {archived} old memories")
                except Exception as e:
                    logger.error(f"Error archiving old memories: {e}")
                # 4. Run self-healing check
                try:
                    from src.memory.self_healer import SelfHealer
                    from src.health.health_schema import (
                        HealthScore,
                        MetricType,
                        SystemHealth,
                    )
                    from src.health.health_composite import CompositeHealthScorer
                    from src.health.auto_recovery import AutoRecovery

                    # Run self-healer
                    db_path = str(PROJECT_ROOT / "context/memory/file_registry.db")
                    chroma_path = str(PROJECT_ROOT / "context/memory/file_chroma")
                    healer = SelfHealer(db_path, chroma_path)
                    report = healer.heal_all()
                    if report.get("issues_found", 0) > 0:
                        logger.info(f"Self-healer: {report}")

                    scorer = CompositeHealthScorer()
                    recovery = AutoRecovery()
                    recovery.register_default_handlers()

                    # Helper function to measure Ollama response time
                    def measure_ollama_health() -> tuple[float, float]:
                        """Measure Ollama response time and error rate."""
                        import urllib.request
                        import json

                        start = time.time()
                        try:
                            req = urllib.request.Request(
                                "http://localhost:11434/api/tags"
                            )
                            with urllib.request.urlopen(req, timeout=5) as resp:
                                data = json.loads(resp.read().decode())
                                elapsed_ms = (time.time() - start) * 1000
                                # Normalize: <500ms = 100, >5000ms = 0
                                response_score = max(0, 100 - (elapsed_ms - 500) / 50)
                                return response_score, 0.0  # No error
                        except Exception:
                            return 0.0, 100.0  # Max error rate

                    # Helper function to measure Memory DB health
                    def measure_memory_db_health() -> tuple[float, float]:
                        """Measure Memory DB accessibility and size."""
                        import sqlite3

                        db_path = PROJECT_ROOT / "context/memory/memory.db"
                        try:
                            if db_path.exists():
                                conn = sqlite3.connect(str(db_path), timeout=2)
                                cursor = conn.cursor()
                                cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                                count = cursor.fetchone()[0]
                                conn.close()
                                # More tables = healthier (normalized 0-100)
                                return min(100.0, count * 10), 0.0
                            return 0.0, 100.0  # DB doesn't exist = error
                        except Exception:
                            return 0.0, 100.0

                    # Helper function to measure Knowledge Graph health
                    def measure_knowledge_graph_health() -> tuple[float, float]:
                        """Measure Knowledge Graph entity/relation count."""
                        try:
                            kg = KnowledgeGraph()
                            stats = kg.get_stats()
                            entities = stats.get("entities", 0)
                            relations = stats.get("relationships", 0)
                            # Normalize: more entities = healthier
                            total = entities + relations
                            score = min(100.0, total / 10)  # 100 entities = 100 score
                            return score, 0.0
                        except Exception:
                            return 0.0, 100.0

                    # Helper function to measure MCP Server health
                    def measure_mcp_server_health() -> tuple[float, float]:
                        """Measure MCP Server process responsiveness."""
                        try:
                            import psutil

                            # Check if mcp_server process is running
                            for proc in psutil.process_iter(["name", "cmdline"]):
                                try:
                                    cmdline = proc.info.get("cmdline", [])
                                    if cmdline and "mcp_server" in " ".join(cmdline):
                                        # Process found - check if responsive
                                        return (
                                            80.0,
                                            0.0,
                                        )  # Process exists = reasonably healthy
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                            return 20.0, 80.0  # No process found
                        except Exception:
                            return 0.0, 100.0  # Cannot determine health

                    # Measure real metrics for each component
                    ollama_response, ollama_error = measure_ollama_health()
                    memory_response, memory_error = measure_memory_db_health()
                    kg_response, kg_error = measure_knowledge_graph_health()
                    mcp_response, mcp_error = measure_mcp_server_health()

                    # Record real metrics
                    scorer.record_metric(
                        "ollama", MetricType.RESPONSE_TIME, ollama_response
                    )
                    scorer.record_metric("ollama", MetricType.ERROR_RATE, ollama_error)
                    scorer.record_metric(
                        "memory_db", MetricType.RESPONSE_TIME, memory_response
                    )
                    scorer.record_metric(
                        "memory_db", MetricType.ERROR_RATE, memory_error
                    )
                    scorer.record_metric(
                        "memory_db", MetricType.RESOURCE, memory_response
                    )
                    scorer.record_metric(
                        "knowledge_graph", MetricType.RESPONSE_TIME, kg_response
                    )
                    scorer.record_metric(
                        "knowledge_graph", MetricType.ERROR_RATE, kg_error
                    )
                    scorer.record_metric(
                        "knowledge_graph", MetricType.RESOURCE, kg_response
                    )
                    scorer.record_metric("mcp_server", MetricType.QUALITY, mcp_response)
                    scorer.record_metric("mcp_server", MetricType.ERROR_RATE, mcp_error)
                    system_health = scorer.calculate_system_health()
                    recovery_results = recovery.check_and_recover(system_health)
                    if recovery_results:
                        for comp, state in recovery_results.items():
                            logger.info(
                                f"Recovery for '{comp}': {state.attempts} attempts, recovered={state.recovered}"
                            )
                except Exception as e:
                    logger.error(f"Error in self-healing check: {e}")

                # 5. Run sleep cycle (JOURNAL → CONSOLIDATE → RECALL)
                try:
                    from .core.sleep_cycle import SleepCycle

                    db_path = str(
                        Path(__file__).parent.parent.parent
                        / "context/memory/sleep_cycle.db"
                    )
                    sc = SleepCycle(db_path=db_path)
                    result = sc.run_cycle()
                    logger.info(
                        f"Sleep cycle completed: {len(result.phases_completed)} phases"
                    )
                    if result.stats:
                        for phase, stats in result.stats.items():
                            logger.info(f"  {phase}: {stats}")

                    # Re-index sleep cycle results back to memory router
                    try:
                        from src.memory.router import get_router

                        router = get_router()
                        if hasattr(router, "reindex"):
                            router.reindex(  # type: ignore[attr-defined]
                                result.consolidated_memories  # type: ignore[attr-defined]
                                if hasattr(result, "consolidated_memories")
                                else []
                            )
                            logger.info("Sleep cycle results re-indexed")
                    except Exception as e:
                        logger.debug(f"Sleep re-index skipped: {e}")
                except Exception as e:
                    logger.error(f"Error running sleep cycle: {e}")
                logger.info("Learning cycle completed")

            except Exception as e:
                logger.error(f"Learning cycle error: {e}")

            # Sleep until next cycle (check stop event every minute)
            for _ in range(cycle_minutes):
                if self._learning_stop_event.is_set():
                    break
                time.sleep(1)

        logger.info("Learning cycle loop stopped")

    def _get_memory_mb(self) -> float:
        """Get current process RSS in MB."""
        try:
            with open(f"/proc/{os.getpid()}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024  # kB → MB
        except Exception:
            return 0.0
        return 0.0

    def _memory_monitor_loop(self) -> None:
        """Monitor memory usage and trigger graceful restart if exceeded."""
        logger.info(
            f"Memory monitor started (limit: {self.MAX_MEMORY_MB}MB, "
            f"check interval: {self.MEMORY_CHECK_INTERVAL}s)"
        )
        while not self._memory_stop_event.is_set():
            try:
                rss_mb = self._get_memory_mb()
                self._status["memory_mb"] = round(rss_mb, 1)

                if rss_mb > self.MAX_MEMORY_MB:
                    logger.warning(
                        f"Memory limit exceeded: {rss_mb:.0f}MB > {self.MAX_MEMORY_MB}MB. "
                        f"Triggering graceful restart..."
                    )
                    self.stop()
                    # Re-exec the daemon process
                    import sys

                    os.execv(sys.executable, [sys.executable] + sys.argv)
                    return  # Never reached after execv

                self._memory_stop_event.wait(self.MEMORY_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Memory monitor error: {e}")
                self._memory_stop_event.wait(self.MEMORY_CHECK_INTERVAL)

        logger.info("Memory monitor stopped")

    def start(self) -> bool:
        """Start the daemon.

        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            logger.warning("Daemon already running")
            return False

        try:
            logger.info("Starting MemoryDaemon...")

            # Write PID file
            self._write_pid()

            # Initialize components
            self._health_monitor = HealthMonitor(self.config)
            # Use the real PriorityEngine from priority_engine module
            try:
                from .priority_engine import PriorityEngine as RealPriorityEngine

                db_path = self.config.get("db_path", "context/memory/file_registry.db")
                self._priority_engine = RealPriorityEngine(db_path)
                logger.info("Real PriorityEngine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize PriorityEngine: {e}")

            # Start file watcher
            try:
                from .file_watcher import start_watcher

                drives: list[str] = self.config.get(
                    "watch_drives", DEFAULT_CONFIG["watch_drives"]
                )
                if start_watcher(drives=drives):
                    logger.info("File watcher started")
                else:
                    logger.warning("Failed to start file watcher")
            except Exception as e:
                logger.error(f"File watcher error: {e}")

            # Start scan scheduler
            try:
                from .scan_scheduler import start_scheduler

                interval: int = int(self.config.get("scan_interval_hours", 24))
                if start_scheduler(interval_hours=interval):
                    logger.info(f"Scan scheduler started (interval: {interval}h)")
                else:
                    logger.warning("Failed to start scan scheduler")
            except Exception as e:
                logger.error(f"Scan scheduler error: {e}")

            # Start health check thread
            self._health_check_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True,
            )
            self._health_check_thread.start()
            self._threads.append(self._health_check_thread)

            # Start memory monitor thread
            self._memory_stop_event.clear()
            self._memory_monitor_thread = threading.Thread(
                target=self._memory_monitor_loop,
                daemon=True,
            )
            self._memory_monitor_thread.start()
            self._threads.append(self._memory_monitor_thread)
            logger.info("Memory monitor started")

            # Start learning cycle thread if enabled
            try:
                from . import learning_config

                if learning_config.get_config("enabled"):
                    self._learning_stop_event.clear()
                    self._learning_thread = threading.Thread(
                        target=self._learning_cycle_loop,
                        daemon=True,
                    )
                    self._learning_thread.start()
                    self._threads.append(self._learning_thread)
                    logger.info("Learning cycle thread started")
            except Exception as e:
                logger.error(f"Error starting learning thread: {e}")

            # Mark as running
            self._running = True
            self._status["started"] = True
            self._status["running"] = True
            self._status["started_at"] = datetime.now().isoformat()

            logger.info("MemoryDaemon started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            self._status["errors"].append(str(e))
            return False

    def stop(self) -> bool:
        """Stop the daemon gracefully.

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._running:
            logger.warning("Daemon not running")
            return False

        try:
            logger.info("Stopping MemoryDaemon...")

            # Stop running flag
            self._running = False
            self._status["running"] = False

            # Stop file watcher
            try:
                from .file_watcher import stop_watcher

                stop_watcher()
                logger.info("File watcher stopped")
            except Exception as e:
                logger.error(f"Error stopping file watcher: {e}")

            # Stop scan scheduler
            try:
                from .scan_scheduler import stop_scheduler

                stop_scheduler()
                logger.info("Scan scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping scan scheduler: {e}")

            # Signal memory monitor to stop
            if hasattr(self, "_memory_stop_event"):
                self._memory_stop_event.set()

            # Signal learning thread to stop
            if hasattr(self, "_learning_stop_event"):
                self._learning_stop_event.set()
            # Wait for threads to finish
            for thread in self._threads:
                if thread.is_alive():
                    thread.join(timeout=5)

            # Clean up
            self._remove_pid()
            self._status["stopped"] = True
            self._status["stopped_at"] = datetime.now().isoformat()

            # Write final status
            self._write_status()

            logger.info("MemoryDaemon stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False

    def restart(self) -> bool:
        """Restart the daemon (stop then start).

        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting MemoryDaemon...")

        self.stop()
        time.sleep(1)
        return self.start()

    def status(self) -> dict[str, Any]:
        """Get current daemon status.

        Returns:
            Dictionary with current status
        """
        status: dict[str, Any] = {
            "running": self._running,
            "started": bool(self._status.get("started", False)),
            "stopped": bool(self._status.get("stopped", False)),
            "started_at": self._status.get("started_at"),
            "stopped_at": self._status.get("stopped_at"),
            "components": {},
            "errors": self._status.get("errors", []),
        }

        # Get component status
        if self._health_monitor:
            status["components"]["health_monitor"] = self._health_monitor.status

        try:
            from .file_watcher import is_watcher_running

            status["components"]["file_watcher"] = {"running": is_watcher_running()}
        except Exception:
            pass

        try:
            from .scan_scheduler import get_scan_status

            status["components"]["scan_scheduler"] = get_scan_status()
        except Exception:
            pass

        return status

    def run(self) -> None:
        """Main event loop - blocks until stopped."""
        logger.info("MemoryDaemon entering main loop...")

        # Start the daemon
        if not self.start():
            logger.error("Failed to start daemon, exiting...")
            sys.exit(1)

        # Block until stopped
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()

        logger.info("MemoryDaemon main loop ended")


def main() -> None:
    """Main entry point for running as a module."""
    daemon = MemoryDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
