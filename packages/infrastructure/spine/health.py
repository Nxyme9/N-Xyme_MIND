#!/usr/bin/env python3
"""SpineHealthProbe - 3-layer health monitoring for Golden Spine Ollama service."""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("spine.health")

# Default Ollama settings
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_INTERVAL = 30.0
DEFAULT_MODEL = "qwen2.5-coder:7b"


@dataclass
class HealthResult:
    """Result of a health check."""

    layer: str  # "process", "model", "responsive"
    healthy: bool
    latency_ms: float = 0.0
    message: str = ""
    details: Optional[Dict] = None


@dataclass
class FullHealthReport:
    """Full health report from all 3 layers."""

    process: HealthResult = field(default_factory=lambda: HealthResult("process", False))
    model: HealthResult = field(default_factory=lambda: HealthResult("model", False))
    responsive: HealthResult = field(default_factory=lambda: HealthResult("responsive", False))
    overall_healthy: bool = False
    timestamp: float = field(default_factory=time.time)


class SpineHealthProbe:
    """3-layer health probe for Ollama service.

    Layers:
    1. process - Check if Ollama HTTP server is running (GET /api/version)
    2. model   - Check if model is loaded (GET /api/tags)
    3. responsive - Check if model responds to prompts (POST /api/generate)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        interval: float = DEFAULT_INTERVAL,
        model: str = DEFAULT_MODEL,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.interval = interval
        self.model = model
        self.timeout = timeout
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_report: Optional[FullHealthReport] = None

    def check_process(self) -> HealthResult:
        """Layer 1: Check if Ollama process is running via HTTP GET /api/version."""
        start = time.time()
        try:
            resp = requests.get(f"{self.base_url}/api/version", timeout=self.timeout)
            latency_ms = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                return HealthResult(
                    layer="process",
                    healthy=True,
                    latency_ms=latency_ms,
                    message=f"Ollama running (version: {data.get('version', 'unknown')})",
                    details=data,
                )
            else:
                return HealthResult(
                    layer="process",
                    healthy=False,
                    latency_ms=latency_ms,
                    message=f"Unexpected status: {resp.status_code}",
                )
        except requests.exceptions.ConnectionError:
            return HealthResult(
                layer="process",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Cannot connect to Ollama - process not running",
            )
        except requests.exceptions.Timeout:
            return HealthResult(
                layer="process",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Connection timeout",
            )
        except Exception as e:
            return HealthResult(
                layer="process",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=f"Error: {str(e)[:100]}",
            )

    def check_model(self) -> HealthResult:
        """Layer 2: Check if model is available via HTTP GET /api/tags."""
        start = time.time()
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            latency_ms = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                models: List[Dict] = data.get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]

                if any(self.model.split(":")[0] in name for name in model_names):
                    return HealthResult(
                        layer="model",
                        healthy=True,
                        latency_ms=latency_ms,
                        message=f"Model '{self.model}' is available",
                        details={"available_models": model_names},
                    )
                else:
                    return HealthResult(
                        layer="model",
                        healthy=False,
                        latency_ms=latency_ms,
                        message=f"Model '{self.model}' not found in available models",
                        details={"available_models": model_names},
                    )
            else:
                return HealthResult(
                    layer="model",
                    healthy=False,
                    latency_ms=latency_ms,
                    message=f"Unexpected status: {resp.status_code}",
                )
        except requests.exceptions.ConnectionError:
            return HealthResult(
                layer="model",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Cannot connect to Ollama",
            )
        except requests.exceptions.Timeout:
            return HealthResult(
                layer="model",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Connection timeout",
            )
        except Exception as e:
            return HealthResult(
                layer="model",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=f"Error: {str(e)[:100]}",
            )

    def check_responsive(self) -> HealthResult:
        """Layer 3: Check if model responds to a test prompt via POST /api/generate."""
        start = time.time()
        try:
            payload = {
                "model": self.model,
                "prompt": "ping",
                "stream": False,
            }
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            latency_ms = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "").strip()
                return HealthResult(
                    layer="responsive",
                    healthy=True,
                    latency_ms=latency_ms,
                    message="Model responds to prompts",
                    details={"response_preview": response_text[:100]},
                )
            else:
                return HealthResult(
                    layer="responsive",
                    healthy=False,
                    latency_ms=latency_ms,
                    message=f"Unexpected status: {resp.status_code}",
                )
        except requests.exceptions.ConnectionError:
            return HealthResult(
                layer="responsive",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Cannot connect to Ollama",
            )
        except requests.exceptions.Timeout:
            return HealthResult(
                layer="responsive",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message="Generation timeout",
            )
        except Exception as e:
            return HealthResult(
                layer="responsive",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                message=f"Error: {str(e)[:100]}",
            )

    def is_healthy(self) -> FullHealthReport:
        """Run all 3 health check layers and return combined report."""
        process_result = self.check_process()
        model_result = self.check_model() if process_result.healthy else HealthResult(
            layer="model", healthy=False, message="Skipped - process not healthy"
        )
        responsive_result = self.check_responsive() if model_result.healthy else HealthResult(
            layer="responsive", healthy=False, message="Skipped - model not healthy"
        )

        report = FullHealthReport(
            process=process_result,
            model=model_result,
            responsive=responsive_result,
            overall_healthy=process_result.healthy and model_result.healthy and responsive_result.healthy,
            timestamp=time.time(),
        )

        with self._lock:
            self._last_report = report

        return report

    def start_monitoring(self) -> None:
        """Start background health monitoring thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            logger.info(f"Started health monitoring (interval={self.interval}s)")

    def stop_monitoring(self) -> None:
        """Stop background health monitoring thread."""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Stopped health monitoring")

    def get_status(self) -> Optional[FullHealthReport]:
        """Get last health report (thread-safe)."""
        with self._lock:
            return self._last_report

    def _monitor_loop(self) -> None:
        """Background loop that checks health at configured interval."""
        while True:
            with self._lock:
                if not self._running:
                    break

            self.is_healthy()

            # Sleep in small increments to allow quick shutdown
            for _ in range(int(self.interval)):
                with self._lock:
                    if not self._running:
                        break
                time.sleep(1)


# Module-level singleton instance
_default_probe: Optional[SpineHealthProbe] = None
_default_lock = threading.Lock()


def get_probe(
    base_url: str = DEFAULT_OLLAMA_URL,
    interval: float = DEFAULT_INTERVAL,
    model: str = DEFAULT_MODEL,
) -> SpineHealthProbe:
    """Get or create the default health probe singleton."""
    global _default_probe
    with _default_lock:
        if _default_probe is None:
            _default_probe = SpineHealthProbe(
                base_url=base_url,
                interval=interval,
                model=model,
            )
        return _default_probe


def is_healthy() -> FullHealthReport:
    """Quick check if Spine is healthy (uses singleton probe)."""
    return get_probe().is_healthy()


if __name__ == "__main__":
    # Quick test
    import sys

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    probe = SpineHealthProbe()

    print("=== Single Health Check ===")
    report = probe.is_healthy()
    print(f"Process: {report.process}")
    print(f"Model: {report.model}")
    print(f"Responsive: {report.responsive}")
    print(f"Overall: {'HEALTHY' if report.overall_healthy else 'UNHEALTHY'}")

    print("\n=== Starting Background Monitoring ===")
    probe.start_monitoring()
    time.sleep(3)

    status = probe.get_status()
    if status:
        print(f"Background check - Overall: {'HEALTHY' if status.overall_healthy else 'UNHEALTHY'}")

    probe.stop_monitoring()
    print("Done")
