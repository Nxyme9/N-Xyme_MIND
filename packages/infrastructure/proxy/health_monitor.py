"""Provider Health Monitor — HTTP checks for all providers."""

import asyncio
import time
import threading
from typing import Dict, Optional


class ProviderHealth:
    def __init__(self, name: str, health_url: str, interval: float = 30.0):
        self.name = name
        self.health_url = health_url
        self.interval = interval
        self.is_healthy = True
        self.last_check = 0.0
        self.latency_ms = 0.0
        self.consecutive_failures = 0
        self.last_error = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "is_healthy": self.is_healthy,
            "latency_ms": round(self.latency_ms, 1),
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "last_check": round(time.time() - self.last_check, 1) if self.last_check else -1,
        }


class HealthMonitor:
    def __init__(self):
        self._providers: Dict[str, ProviderHealth] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_provider(self, name: str, health_url: str, interval: float = 30.0) -> None:
        with self._lock:
            self._providers[name] = ProviderHealth(name, health_url, interval)

    def get_status(self, name: str = "") -> dict:
        with self._lock:
            if name:
                return self._providers.get(name, {}).to_dict()
            return {n: p.to_dict() for n, p in self._providers.items()}

    def is_provider_healthy(self, name: str) -> bool:
        with self._lock:
            return self._providers.get(name, ProviderHealth("", "")).is_healthy

    def get_healthy_providers(self) -> list:
        with self._lock:
            return [n for n, p in self._providers.items() if p.is_healthy]

    def start_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self) -> None:
        """Background loop that checks provider health."""
        import urllib.request
        import urllib.error
        while self._running:
            for name, provider in list(self._providers.items()):
                if time.time() - provider.last_check < provider.interval:
                    continue
                start = time.time()
                try:
                    req = urllib.request.Request(provider.health_url, method='HEAD')
                    urllib.request.urlopen(req, timeout=5)
                    provider.is_healthy = True
                    provider.latency_ms = (time.time() - start) * 1000
                    provider.consecutive_failures = 0
                    provider.last_error = ""
                except Exception as e:
                    provider.is_healthy = False
                    provider.consecutive_failures += 1
                    provider.last_error = str(e)[:100]
                provider.last_check = time.time()
            time.sleep(5)


# Global instance with default providers
health_monitor = HealthMonitor()
health_monitor.add_provider("opencode", "https://opencode.ai/health", interval=60.0)
health_monitor.add_provider("openrouter", "https://openrouter.ai/api/v1/models", interval=30.0)
health_monitor.add_provider("google", "https://generativelanguage.googleapis.com/v1beta/models", interval=30.0)
