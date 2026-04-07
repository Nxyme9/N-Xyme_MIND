#!/usr/bin/env python3
"""GoldenSpine - Core orchestrator for AI model serving with resilience pipeline.

Ties together health monitoring, fallback chain, and run tracking into a unified interface.
Thread-safe with lazy imports to avoid circular dependencies.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("golden_spine")


# =============================================================================
# Lazy Import Functions - Avoid Circular Dependencies
# =============================================================================


def _get_spine_config() -> type:
    """Lazy import SpineConfig."""
    from packages.infrastructure.spine.config import SpineConfig

    return SpineConfig


def _get_health_probe() -> type:
    """Lazy import SpineHealthProbe."""
    from packages.infrastructure.spine.health import SpineHealthProbe

    return SpineHealthProbe


def _get_health_result() -> type:
    """Lazy import HealthResult."""
    from packages.infrastructure.spine.health import HealthResult

    return HealthResult


def _get_full_health_report() -> type:
    """Lazy import FullHealthReport."""
    from packages.infrastructure.spine.health import FullHealthReport

    return FullHealthReport


def _get_spine_fallback() -> type:
    """Lazy import SpineFallback."""
    from packages.infrastructure.spine.fallback import SpineFallback

    return SpineFallback


def _get_run_tracker() -> type:
    """Lazy import RunTracker."""
    from packages.infrastructure.spine.run_tracker import RunTracker

    return RunTracker


def _get_run_record() -> type:
    """Lazy import RunRecord."""
    from packages.infrastructure.spine.run_tracker import RunRecord

    return RunRecord


def _get_local_llm() -> type:
    """Lazy import LocalLLM."""
    from packages.local_llm.ollama_client import LocalLLM

    return LocalLLM


# =============================================================================
# GoldenSpine - Core Orchestrator
# =============================================================================


class GoldenSpine:
    """Core orchestrator for AI model serving with resilience pipeline.

    Integrates:
    - HealthProbe: 3-layer health monitoring (process, model, responsive)
    - FallbackChain: Automatic failover to secondary models with circuit breaker
    - RunTracker: SQLite-based run tracking for debugging and analytics

    Thread-safe with lazy imports to avoid circular dependencies.
    """

    def __init__(self, config: Optional[SpineConfig] = None):
        """Initialize GoldenSpine with configuration.

        Args:
            config: SpineConfig instance. Creates default if not provided.
        """
        # Import SpineConfig lazily
        SpineConfig = _get_spine_config()
        self._config = config or SpineConfig()

        # Thread safety
        self._lock = threading.Lock()

        # Initialize components (lazily imported)
        self._health_probe: Optional[SpineHealthProbe] = None
        self._fallback: Optional[SpineFallback] = None
        self._run_tracker: Optional[RunTracker] = None

        # State tracking
        self._running = False
        self._run_count = 0
        self._last_error: Optional[str] = None

        logger.info(f"GoldenSpine initialized with config: {self._config.to_dict()}")

    def start(self) -> None:
        """Start health monitoring thread.

        Spawns background thread for periodic health checks.
        Thread-safe - idempotent (multiple calls are harmless).
        """
        with self._lock:
            if self._running:
                logger.warning("GoldenSpine already running")
                return

            # Initialize health probe lazily
            if self._health_probe is None:
                SpineHealthProbe = _get_health_probe()
                self._health_probe = SpineHealthProbe(
                    base_url=f"http://{self._config.bind_host}:{self._config.port}",
                    model=self._config.model_path,
                )

            # Start monitoring
            self._health_probe.start_monitoring()
            self._running = True
            logger.info("GoldenSpine started - health monitoring active")

    def stop(self) -> None:
        """Stop health monitoring and perform graceful shutdown.

        Stops background health monitoring thread and flushes pending run records.
        Thread-safe - idempotent.
        """
        with self._lock:
            if not self._running:
                logger.warning("GoldenSpine not running")
                return

            # Stop health probe
            if self._health_probe is not None:
                self._health_probe.stop_monitoring()

            # Flush run tracker
            if self._run_tracker is not None:
                self._run_tracker.flush()

            self._running = False
            logger.info("GoldenSpine stopped - graceful shutdown complete")

    def probe(self) -> FullHealthReport:
        """Run health check across all 3 layers.

        Returns:
            FullHealthReport with process, model, and responsive layer results.
        """
        with self._lock:
            if self._health_probe is None:
                SpineHealthProbe = _get_health_probe()
                self._health_probe = SpineHealthProbe(
                    base_url=f"http://{self._config.bind_host}:{self._config.port}",
                    model=self._config.model_path,
                )

        return self._health_probe.is_healthy()

    def run(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> RunRecord:
        """Execute inference with full resilience pipeline.

        Pipeline:
        1. Check health (via health probe)
        2. Try primary model (via fallback chain)
        3. Fallback on failure (via fallback chain with circuit breaker)
        4. Record run (via run tracker)
        5. Return result

        Args:
            prompt: The prompt to send to the model
            model: Optional model override (uses config.model_path if not set)
            **kwargs: Additional parameters passed to the model

        Returns:
            RunRecord with execution details (model, latency, success, etc.)
        """
        # Generate run ID
        run_id = f"spine-{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        # Determine model to use
        model_to_use = model or self._config.model_path

        # Initialize components lazily
        with self._lock:
            if self._fallback is None:
                SpineFallback = _get_spine_fallback()
                self._fallback = SpineFallback(
                    primary_model=self._config.model_path,
                    fallback_models=self._config.fallback_models,
                )

            if self._run_tracker is None:
                RunTracker = _get_spine_tracker()
                self._run_tracker = RunTracker()

        # Execute with fallback chain
        fallback_result = self._fallback.execute(
            prompt=prompt,
            model=model_to_use,
            config=kwargs,
        )

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Determine if fallback was used
        fallback_used = (
            fallback_result.model_used != self._config.model_path
            if fallback_result.success
            else False
        )

        # Create run record
        RunRecord = _get_run_record()
        record = RunRecord(
            run_id=run_id,
            model=fallback_result.model_used or model_to_use,
            prompt=prompt,
            response="" if not fallback_result.success else "Success",
            latency_ms=latency_ms,
            success=fallback_result.success,
            error=fallback_result.error,
            fallback_used=fallback_used,
        )

        # Record the run
        self._run_tracker.record_run(record)

        # Update state
        with self._lock:
            self._run_count += 1
            if not fallback_result.success:
                self._last_error = fallback_result.error

        logger.info(
            f"Run {run_id}: model={record.model}, success={record.success}, "
            f"latency={latency_ms:.0f}ms, fallback_used={fallback_used}"
        )

        return record

    def status(self) -> Dict[str, Any]:
        """Get current status of GoldenSpine.

        Returns:
            Dictionary with:
            - running: Whether health monitoring is active
            - run_count: Total number of runs executed
            - last_error: Last error message (if any)
            - health: Current health report (if probe available)
            - fallback_status: Status of fallback chain with circuit states
            - run_stats: Run tracker statistics
        """
        with self._lock:
            status: Dict[str, Any] = {
                "running": self._running,
                "run_count": self._run_count,
                "last_error": self._last_error,
                "config": self._config.to_dict(),
            }

            # Add health info if available
            if self._health_probe is not None:
                health_report = self._health_probe.get_status()
                if health_report:
                    status["health"] = {
                        "overall_healthy": health_report.overall_healthy,
                        "process": {
                            "healthy": health_report.process.healthy,
                            "message": health_report.process.message,
                        },
                        "model": {
                            "healthy": health_report.model.healthy,
                            "message": health_report.model.message,
                        },
                        "responsive": {
                            "healthy": health_report.responsive.healthy,
                            "message": health_report.responsive.message,
                        },
                    }

            # Add fallback status if available
            if self._fallback is not None:
                status["fallback_status"] = self._fallback.get_status()

            # Add run stats if available
            if self._run_tracker is not None:
                try:
                    status["run_stats"] = self._run_tracker.get_stats()
                except Exception as e:
                    logger.warning(f"Failed to get run stats: {e}")

            return status

    def config(self, **kwargs: Any) -> None:
        """Update configuration.

        Args:
            **kwargs: Configuration keys to update (e.g., model_path='llama3.2:1b')
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                    logger.info(f"Config updated: {key}={value}")
                else:
                    logger.warning(f"Unknown config key: {key}")

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------

    def __enter__(self) -> "GoldenSpine":
        """Context manager entry - starts health monitoring."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - stops health monitoring."""
        self.stop()


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


def _get_spine_tracker() -> type:
    """Lazy import RunTracker (internal helper)."""
    from packages.infrastructure.spine.run_tracker import RunTracker

    return RunTracker


# Global singleton instance
_spine_instance: Optional[GoldenSpine] = None
_spine_lock = threading.Lock()


def get_spine(config: Optional[SpineConfig] = None) -> GoldenSpine:
    """Get or create the global GoldenSpine instance.

    Args:
        config: Optional SpineConfig. Uses default if not provided.

    Returns:
        GoldenSpine singleton instance
    """
    global _spine_instance

    SpineConfig = _get_spine_config()

    with _spine_lock:
        if _spine_instance is None:
            _spine_instance = GoldenSpine(config=config or SpineConfig())
            logger.info("Created global GoldenSpine instance")

        return _spine_instance


def reset_spine() -> None:
    """Reset the global GoldenSpine instance."""
    global _spine_instance

    with _spine_lock:
        if _spine_instance is not None:
            _spine_instance.stop()
            _spine_instance = None
            logger.info("Reset global GoldenSpine instance")


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== GoldenSpine Test ===\n")

    # Create instance
    spine = GoldenSpine()
    print(f"Created: {spine._config.model_path}")

    # Start monitoring
    print("\n--- Starting Health Monitoring ---")
    spine.start()

    # Wait a moment for health check
    time.sleep(2)

    # Get status
    print("\n--- Status ---")
    status = spine.status()
    print(f"Running: {status['running']}")
    print(f"Run count: {status['run_count']}")
    if "health" in status:
        h = status["health"]
        print(f"Health: {h.get('overall_healthy', 'unknown')}")

    # Test probe
    print("\n--- Health Probe ---")
    report = spine.probe()
    print(f"Overall healthy: {report.overall_healthy}")
    print(f"Process: {report.process.message}")
    print(f"Model: {report.model.message}")

    # Test run (if healthy)
    if report.overall_healthy:
        print("\n--- Test Run ---")
        result = spine.run("Hello, are you working?")
        print(f"Model: {result.model}")
        print(f"Success: {result.success}")
        print(f"Latency: {result.latency_ms:.0f}ms")
    else:
        print("\n--- Skipping Run (not healthy) ---")

    # Final status
    print("\n--- Final Status ---")
    final_status = spine.status()
    print(f"Run count: {final_status['run_count']}")

    # Stop
    print("\n--- Stopping ---")
    spine.stop()
    print("Done")

    sys.exit(0)