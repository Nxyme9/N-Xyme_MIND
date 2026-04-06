"""VPN backend manager with weighted selection, 429 tracking, and health monitoring."""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter with 429-adaptive quota learning."""

    def __init__(self, name: str, rate_per_minute: float = 80, burst_limit: int = 20):
        self.name = name
        self.rate = rate_per_minute
        self.burst = burst_limit
        self.tokens = float(burst_limit)
        self.last_refill = time.monotonic()
        self.request_count = 0
        self.error_count = 0
        self.last_error_time = 0.0
        self.observed_quota = 0
        self._429_timestamps = []

    def _do_refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * (self.rate / 60.0))
        self.last_refill = now

    def consume(self) -> bool:
        """Return True if a request is allowed under the rate limit."""
        self._do_refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.request_count += 1
            return True
        return False

    def record_429(self):
        """Record a 429 response and learn quota if possible."""
        now = time.monotonic()
        self.error_count += 1
        self.last_error_time = now
        self._429_timestamps.append(now)
        if len(self._429_timestamps) > 100:
            self._429_timestamps = self._429_timestamps[-100:]
        if self.request_count > 0:
            self.observed_quota = max(self.observed_quota, self.request_count)
            self.rate = max(1.0, self.observed_quota * 0.7)
            self.burst = max(1, int(self.rate / 4))

    def should_switch(self) -> bool:
        """True if we're at 80% of observed quota."""
        if self.observed_quota <= 0:
            return False
        return self.request_count >= (self.observed_quota * 0.8)

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "rate": round(self.rate, 1),
            "burst": self.burst,
            "tokens": round(self.tokens, 1),
            "requests": self.request_count,
            "errors": self.error_count,
            "observed_quota": self.observed_quota,
        }


@dataclass
class Backend:
    """Represents a SOCKS5 proxy backend with health tracking."""

    name: str
    socks_host: str
    socks_port: int
    provider: str = "manual"
    country: str = "unknown"
    latency: float = 999.0
    healthy: bool = True
    last_check: float = 0
    request_count: int = 0
    error_count: int = 0
    quota_remaining: float = 100.0
    rate_limited_until: float = 0
    active_connections: int = 0
    max_connections: int = 100
    bucket: TokenBucket = field(default_factory=lambda: TokenBucket("unnamed", 80, 20))
    _consecutive_failures: int = 0

    @property
    def is_rate_limited(self) -> bool:
        return time.monotonic() < self.rate_limited_until

    @property
    def connection_pressure(self) -> float:
        """0.0 = empty, 1.0 = full. Lower is better for load balancing."""
        if self.max_connections <= 0:
            return 1.0
        return min(1.0, self.active_connections / self.max_connections)

    @property
    def available_capacity(self) -> float:
        """0.0 = exhausted, 1.0 = fully available."""
        if not self.healthy or self.is_rate_limited:
            return 0.0
        token_ratio = max(0, self.bucket.tokens / max(1, self.bucket.burst))
        conn_ratio = 1.0 - self.connection_pressure
        latency_score = max(0, 1.0 - (self.latency / 500.0))
        return token_ratio * 0.4 + conn_ratio * 0.4 + latency_score * 0.2

    @property
    def score(self) -> float:
        """Lower is better. Unhealthy/rate-limited get huge scores."""
        if not self.healthy:
            return 999999.0
        if self.is_rate_limited:
            return 999998.0
        return self.latency + (self.error_count * 10)

    def mark_429(self, cooldown: float = 60.0):
        self.error_count += 1
        self.rate_limited_until = time.monotonic() + cooldown
        self.bucket.record_429()


class VPNManager:
    """Manages VPN backends for automatic rotation on rate limits."""

    def __init__(
        self, config_path: Optional[str] = None, health_interval: float = 300.0
    ):
        self.config_path = config_path
        self.health_interval = health_interval
        self.backends: list[Backend] = []
        self._lock = asyncio.Lock()
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
        self._total_requests = 0
        self._total_429s = 0
        self._total_backends_removed = 0

    async def initialize(self) -> None:
        """Load backends from config, start health checker."""
        self._load_backends()
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())

    async def shutdown(self) -> None:
        """Stop health checker."""
        self._running = False
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    def _load_backends(self) -> None:
        """Load backends from config file."""
        config_paths = []
        if self.config_path:
            config_paths.append(Path(self.config_path))
        env_config = os.environ.get("VPN_BACKENDS_CONFIG")
        if env_config:
            config_paths.append(Path(env_config))
        config_paths.append(Path.home() / ".config/opencode-vpn/state/servers.json")

        seen = set()
        for path in config_paths:
            if not path.exists():
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cannot load %s: %s", path, exc)
                continue

            servers = (
                data
                if isinstance(data, list)
                else data.get("backends", data.get("servers", []))
            )
            for srv in servers:
                key = f"{srv.get('socks_host')}:{srv.get('socks_port')}"
                if key in seen:
                    continue
                seen.add(key)
                name = srv.get("name", key)
                bucket = TokenBucket(name, 80, 20)
                backend = Backend(
                    name=name,
                    socks_host=srv.get("socks_host", "127.0.0.1"),
                    socks_port=srv.get("socks_port", 1080),
                    provider=srv.get("provider", "manual"),
                    country=srv.get("country", "unknown"),
                    bucket=bucket,
                )
                self.backends.append(backend)

        if not self.backends:
            env_host = os.environ.get("ROTATOR_SOCKS_HOST", "127.0.0.1")
            env_port = int(os.environ.get("ROTATOR_SOCKS_PORT", "1080"))
            self.backends.append(
                Backend(
                    name="local",
                    socks_host=env_host,
                    socks_port=env_port,
                    bucket=TokenBucket("local", 80, 20),
                )
            )
            logger.info(
                "No config found, using default local backend %s:%d", env_host, env_port
            )

        logger.info(
            "Loaded %d backend(s): %s",
            len(self.backends),
            ", ".join(b.name for b in self.backends),
        )

    def select_backend(self) -> Optional[Backend]:
        """Weighted selection for parallel agent load balancing."""
        candidates = [b for b in self.backends if b.healthy and not b.is_rate_limited]
        if not candidates:
            candidates = [b for b in self.backends if b.healthy]
        if not candidates:
            candidates = self.backends
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        capacities = [b.available_capacity for b in candidates]
        total = sum(capacities)

        if total <= 0:
            idx = random.randint(0, len(candidates) - 1)
            return candidates[idx]

        r = random.random() * total
        cumulative = 0.0
        for i, cap in enumerate(capacities):
            cumulative += cap
            if r <= cumulative:
                return candidates[i]

        return candidates[-1]

    async def mark_backend_429(self, backend: Backend, cooldown: float = 60.0) -> None:
        """Mark a backend as rate-limited."""
        async with self._lock:
            backend.mark_429(cooldown)
            self._total_429s += 1

    async def mark_backend_unhealthy(self, backend: Backend) -> None:
        """Mark a backend as unhealthy."""
        async with self._lock:
            backend.healthy = False
            logger.warning("Marked %s unhealthy", backend.name)

    def get_backend_stats(self) -> list[dict]:
        """Get stats for all backends."""
        result = []
        for b in self.backends:
            stats = {
                "name": b.name,
                "host": b.socks_host,
                "port": b.socks_port,
                "healthy": b.healthy,
                "rate_limited": b.is_rate_limited,
                "latency_ms": round(b.latency, 1),
                "requests": b.request_count,
                "errors": b.error_count,
                "active_connections": b.active_connections,
                "available_capacity": round(b.available_capacity, 3),
                "bucket": b.bucket.get_stats(),
            }
            result.append(stats)
        return result

    def get_summary(self) -> dict:
        """Get summary of all backends."""
        healthy = sum(1 for b in self.backends if b.healthy)
        rate_limited = sum(1 for b in self.backends if b.is_rate_limited)
        total_requests = sum(b.request_count for b in self.backends)
        total_429s = sum(b.error_count for b in self.backends)
        return {
            "total": len(self.backends),
            "healthy": healthy,
            "rate_limited": rate_limited,
            "total_requests": total_requests,
            "total_429s": total_429s,
            "backends_removed": self._total_backends_removed,
        }

    async def _health_check_loop(self) -> None:
        """Run periodic health checks on all backends concurrently."""
        while self._running:
            # Check all backends concurrently
            tasks = [self._check_one_backend(b) for b in self.backends]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stale backend cleanup: remove backends with 3+ consecutive failures
            stale_backends = [
                b for b in self.backends
                if getattr(b, '_consecutive_failures', 0) >= 3
            ]
            for backend in stale_backends:
                logger.warning(f"Removing stale backend {backend.name} ",
                               f"({backend._consecutive_failures} consecutive failures)")
                self.backends.remove(backend)
                self._total_backends_removed += 1
            
            await asyncio.sleep(self.health_interval)

    async def _check_one_backend(self, backend: Backend) -> bool:
        """Check a single backend by connecting through SOCKS5."""
        try:
            start = time.monotonic()
            # Step 1: Connect to SOCKS5 proxy
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(backend.socks_host, backend.socks_port),
                timeout=5.0,
            )
            # Step 2: Send SOCKS5 greeting
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=5.0)
            if resp != b"\x05\x00":
                raise ConnectionError("SOCKS5 auth rejected")
            # Step 3: Try to CONNECT to a simple IPv4 host (1.1.1.1:80)
            # Using IP address avoids DNS resolution issues through SOCKS5
            req = b"\x05\x01\x00\x01" + bytes([1, 1, 1, 1]) + b"\x00\x50"
            writer.write(req)
            await writer.drain()
            reply = await asyncio.wait_for(reader.readexactly(10), timeout=5.0)
            if reply[1] != 0:
                raise ConnectionError(f"SOCKS5 connect failed: {reply[1]}")
            elapsed = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            async with self._lock:
                backend.latency = elapsed
                backend.healthy = True
                backend.last_check = time.monotonic()
                backend._consecutive_failures = 0
            return True
        except Exception as exc:
            logger.debug("Health check failed for %s: %s", backend.name, exc)
            async with self._lock:
                backend.healthy = False
                backend.latency = 9999.0
                backend.last_check = time.monotonic()
                backend._consecutive_failures = getattr(backend, '_consecutive_failures', 0) + 1
            return False
