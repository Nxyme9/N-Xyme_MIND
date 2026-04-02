#!/usr/bin/env python3
"""opencode-vpn rotator: HTTP CONNECT proxy with SOCKS5 backends,
429 detection, token bucket rate limiting, provider fallback,
health checking, and ANSI dashboard."""

import asyncio
import socket
import struct
import json
import time
import sys
import os
import signal
import random
import hashlib
import argparse
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger("rotator")

# ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
CLEAR_SCREEN = "\033[2J"
MOVE_HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
BOX_H = "─"
BOX_V = "│"
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"
BOX_T = "┬"
BOX_B = "┴"
BOX_L = "├"
BOX_R = "┤"
BOX_C = "┼"


class TokenBucket:
    """Token bucket rate limiter with 429-adaptive quota learning."""

    def __init__(self, name: str, rate_per_minute: float = 80,
                 burst_limit: int = 20):
        self.name = name
        self.rate = rate_per_minute
        self.burst = burst_limit
        self.tokens = float(burst_limit)
        self.last_refill = time.monotonic()
        self.request_count = 0
        self.error_count = 0
        self.last_error_time = 0.0
        self.observed_quota = 0  # Learned from 429 responses
        self._429_timestamps: deque = deque(maxlen=100)

    def _do_refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.burst,
            self.tokens + elapsed * (self.rate / 60.0)
        )
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
        if self.request_count > 0:
            self.observed_quota = max(self.observed_quota,
                                      self.request_count)
            # Reduce rate to 70% of observed quota
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
    active_connections: int = 0  # For weighted load balancing
    max_connections: int = 100   # Max concurrent connections
    bucket: TokenBucket = field(
        default_factory=lambda: TokenBucket("unnamed", 80, 20))

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
        # Factor in: tokens remaining, connection pressure, latency
        token_ratio = max(0, self.bucket.tokens / max(1, self.bucket.burst))
        conn_ratio = 1.0 - self.connection_pressure
        latency_score = max(0, 1.0 - (self.latency / 500.0))  # 500ms = 0 score
        return (token_ratio * 0.4 + conn_ratio * 0.4 + latency_score * 0.2)

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

    def __repr__(self):
        status = "OK" if self.healthy else "DOWN"
        if self.is_rate_limited:
            status = "429"
        return f"Backend({self.name} {self.socks_host}:{self.socks_port} [{status}] {self.latency:.0f}ms)"


class ProviderFallback:
    """Manages provider chain: OpenRouter → Groq → Cerebras → DeepSeek → Ollama."""

    PROVIDERS = [
        {"name": "openrouter",
         "base_url": "https://openrouter.ai/api/v1",
         "api_key_env": "OPENROUTER_API_KEY"},
        {"name": "groq",
         "base_url": "https://api.groq.com/openai/v1",
         "api_key_env": "GROQ_API_KEY"},
        {"name": "cerebras",
         "base_url": "https://api.cerebras.ai/v1",
         "api_key_env": "CEREBRAS_API_KEY"},
        {"name": "deepseek",
         "base_url": "https://api.deepseek.com/v1",
         "api_key_env": "DEEPSEEK_API_KEY"},
        {"name": "ollama",
         "base_url": "http://localhost:11434/v1",
         "api_key_env": None},
    ]

    def get_available_providers(self) -> List[dict]:
        """Return list of providers that have API keys configured."""
        available = []
        for p in self.PROVIDERS:
            if p["api_key_env"] is None:
                available.append(p)
                continue
            key = os.environ.get(p["api_key_env"], "")
            if key:
                available.append(p)
        return available

    def get_provider_url(self, name: str) -> Optional[str]:
        for p in self.PROVIDERS:
            if p["name"] == name:
                return p["base_url"]
        return None

    def get_api_key(self, name: str) -> Optional[str]:
        for p in self.PROVIDERS:
            if p["name"] == name:
                if p["api_key_env"] is None:
                    return None
                return os.environ.get(p["api_key_env"])
        return None


class StealthMode:
    """Adds random delays to requests to avoid burst detection."""

    def __init__(self, enabled: bool = False, min_delay: float = 0.5,
                 max_delay: float = 2.0):
        self.enabled = enabled
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_history: deque = deque(maxlen=50)

    async def maybe_delay(self, bucket: Optional[TokenBucket] = None):
        if not self.enabled:
            return
        delay = random.uniform(self.min_delay, self.max_delay)
        if bucket and bucket.should_switch():
            delay *= 2.0
        self.request_history.append(time.monotonic())
        if len(self.request_history) >= 3:
            recent = list(self.request_history)[-3:]
            gaps = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
            if all(g < 0.1 for g in gaps):
                delay = max(delay, self.max_delay)
        await asyncio.sleep(delay)


class HealthChecker:
    """Periodic health checks for SOCKS5 backends."""

    def __init__(self, backends: List[Backend], interval: float = 300):
        self.backends = backends
        self.interval = interval
        self._running = False

    async def check_one(self, backend: Backend) -> bool:
        """Check a single backend by connecting through SOCKS5."""
        try:
            start = time.monotonic()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(backend.socks_host,
                                        backend.socks_port),
                timeout=5.0
            )
            # SOCKS5 greeting: version 5, 1 auth method (no auth)
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=5.0)
            if resp != b"\x05\x00":
                raise ConnectionError("SOCKS5 auth rejected")
            # CONNECT to httpbin.org:80
            host = b"httpbin.org"
            req = b"\x05\x01\x00\x03" + bytes([len(host)]) + host + b"\x00\x50"
            writer.write(req)
            await writer.drain()
            reply = await asyncio.wait_for(reader.readexactly(10), timeout=5.0)
            if reply[1] != 0:
                raise ConnectionError(f"SOCKS5 connect failed: {reply[1]}")
            elapsed = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            backend.latency = elapsed
            backend.healthy = True
            backend.last_check = time.monotonic()
            return True
        except Exception as exc:
            logger.debug("Health check failed for %s: %s", backend.name, exc)
            backend.healthy = False
            backend.latency = 9999.0
            backend.last_check = time.monotonic()
            return False

    async def check_all(self):
        """Check all backends concurrently."""
        tasks = [self.check_one(b) for b in self.backends]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_forever(self):
        """Run periodic health checks."""
        self._running = True
        while self._running:
            await self.check_all()
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False


class Dashboard:
    """ANSI terminal dashboard showing backend status and proxy stats."""

    def __init__(self, backends: List[Backend], proxy_stats: dict):
        self.backends = backends
        self.stats = proxy_stats

    def _bar(self, value: float, width: int = 10) -> str:
        """Render a colored percentage bar."""
        filled = int(value / 100 * width)
        empty = width - filled
        if value >= 70:
            color = GREEN
        elif value >= 30:
            color = YELLOW
        else:
            color = RED
        return f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET}"

    def render(self) -> str:
        """Render the full dashboard as a string."""
        lines = []
        w = 75
        def hline(left, mid, right):
            return left + mid.join([BOX_H * 14, BOX_H * 9,
                                    BOX_H * 10, BOX_H * 9,
                                    BOX_H * 7, BOX_H * 8]) + right

        lines.append(f"{BOX_TL}{BOX_H * w}{BOX_TR}")
        title = " opencode-vpn Dashboard "
        lines.append(f"{BOX_V}{BOLD}{CYAN}{title:^{w}}{RESET}{BOX_V}")
        lines.append(hline(BOX_L, BOX_C, BOX_R))

        hdr = (f"  {BOLD}{'Backend':<14}{BOX_V}{'Status':<9}"
               f"{BOX_V}{'Quota':<10}{BOX_V}{'Latency':<9}"
               f"{BOX_V}{'Conns':<7}{BOX_V}{'Capcty':<8}{RESET}")
        lines.append(f"{BOX_V}{hdr}{BOX_V}")
        lines.append(hline(BOX_L, BOX_C, BOX_R))

        healthy_count = 0
        limited_count = 0
        total_conns = 0
        for b in self.backends:
            if b.healthy:
                healthy_count += 1
            if b.is_rate_limited:
                limited_count += 1
            total_conns += b.active_connections

            if not b.healthy:
                status = f"{RED}✗ DOWN{RESET} "
            elif b.is_rate_limited:
                status = f"{YELLOW}✗ 429 {RESET} "
            else:
                status = f"{GREEN}✓ OK  {RESET} "

            quota_pct = b.quota_remaining
            lat_str = f"{b.latency:.0f}ms"
            bar = self._bar(quota_pct)
            conns = f"{b.active_connections}"
            cap = f"{b.available_capacity*100:.0f}%"
            row = (f"  {b.name:<14}{BOX_V}{status}{BOX_V}"
                   f"{bar} {BOX_V} {lat_str:<8}"
                   f"{BOX_V} {conns:<6}{BOX_V} {cap:<7}")
            lines.append(f"{BOX_V}{row}{BOX_V}")

        lines.append(hline(BOX_L, BOX_C, BOX_R))

        total = len(self.backends)
        reqs = self.stats.get("total_requests", 0)
        errs = self.stats.get("total_429s", 0)
        switches = self.stats.get("total_switches", 0)

        summary1 = (f"  Total: {total} | {GREEN}Healthy: {healthy_count}"
                    f"{RESET} | {YELLOW}Rate-limited: {limited_count}{RESET}")
        lines.append(f"{BOX_V}{summary1:<{w}}{BOX_V}")
        summary2 = (f"  Requests: {reqs:,} | 429s: {errs} | "
                    f"Switches: {switches} | Conns: {total_conns}")
        lines.append(f"{BOX_V}{summary2:<{w}}{BOX_V}")
        lines.append(f"{BOX_BL}{BOX_H * w}{BOX_BR}")
        return "\n".join(lines)

    async def run_live(self, refresh: float = 2.0):
        """Refresh dashboard every N seconds."""
        sys.stdout.write(HIDE_CURSOR)
        try:
            while True:
                sys.stdout.write(CLEAR_SCREEN + MOVE_HOME)
                sys.stdout.write(self.render() + "\n")
                sys.stdout.flush()
                await asyncio.sleep(refresh)
        finally:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.flush()


class RotatingProxy:
    """HTTP CONNECT proxy that routes through rotating SOCKS5 backends."""

    BUFFER_SIZE = 65536

    def __init__(self, host: str, port: int, backends: List[Backend]):
        self.host = host
        self.port = port
        self.backends = backends
        self.current_index = 0
        self.stats: dict = {
            "total_requests": 0,
            "total_429s": 0,
            "total_switches": 0,
            "start_time": time.time(),
        }
        self._server: Optional[asyncio.AbstractServer] = None
        self.stealth = StealthMode()
        self._rr_index = 0  # Round-robin fallback index

    def select_backend(self) -> Optional[Backend]:
        """Weighted selection for parallel agent load balancing.

        Uses available_capacity (token ratio * 0.4 + conn ratio * 0.4 + latency * 0.2)
        to score each backend, then does weighted random selection. This ensures:
        - Backends with more tokens get proportionally more traffic
        - Backends with fewer active connections get more traffic
        - Faster backends get a small bonus
        - Unhealthy/rate-limited backends are excluded
        """
        # Filter to healthy + not rate-limited
        candidates = [b for b in self.backends
                      if b.healthy and not b.is_rate_limited]
        if not candidates:
            # Fallback: healthy only (even if rate-limited)
            candidates = [b for b in self.backends if b.healthy]
        if not candidates:
            # Last resort: anyone alive
            candidates = self.backends
        if not candidates:
            return None

        # Single candidate = just return it
        if len(candidates) == 1:
            return candidates[0]

        # Weighted random selection based on available capacity
        capacities = [b.available_capacity for b in candidates]
        total = sum(capacities)

        if total <= 0:
            # All exhausted — round-robin fallback
            self._rr_index = (self._rr_index + 1) % len(candidates)
            return candidates[self._rr_index]

        # Weighted random pick
        r = random.random() * total
        cumulative = 0.0
        for i, cap in enumerate(capacities):
            cumulative += cap
            if r <= cumulative:
                return candidates[i]

        return candidates[-1]

    def mark_backend_unhealthy(self, backend: Backend):
        backend.healthy = False
        logger.warning("Marked %s unhealthy", backend.name)
        self.stats["total_switches"] += 1

    async def _socks5_connect(self, reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter,
                              target_host: str, target_port: int):
        """Perform SOCKS5 CONNECT handshake."""
        # Greeting: version 5, 1 method (no auth)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        resp = await asyncio.wait_for(reader.readexactly(2), timeout=10.0)
        if resp[0] != 0x05 or resp[1] != 0x00:
            raise ConnectionError(
                f"SOCKS5 greeting rejected: {resp.hex()}")
        # CONNECT request
        host_bytes = target_host.encode("ascii")
        port_bytes = struct.pack("!H", target_port)
        req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + port_bytes
        writer.write(req)
        await writer.drain()
        # Read reply header
        header = await asyncio.wait_for(reader.readexactly(4), timeout=10.0)
        if header[1] != 0x00:
            raise ConnectionError(
                f"SOCKS5 connect failed: rep={header[1]}")
        # Skip bound address
        atyp = header[3]
        if atyp == 0x01:
            await asyncio.wait_for(reader.readexactly(6), timeout=10.0)
        elif atyp == 0x03:
            length = (await asyncio.wait_for(
                reader.readexactly(1), timeout=10.0))[0]
            await asyncio.wait_for(
                reader.readexactly(length + 2), timeout=10.0)
        elif atyp == 0x04:
            await asyncio.wait_for(reader.readexactly(18), timeout=10.0)

    async def _relay(self, r1: asyncio.StreamReader,
                     r2: asyncio.StreamReader,
                     w1: asyncio.StreamWriter,
                     w2: asyncio.StreamWriter,
                     watch_429: bool = False,
                     backend: Optional[Backend] = None):
        """Bidirectional relay with optional 429 detection on r1→w1 path."""
        async def forward(src, dst, detect=False):
            try:
                while True:
                    data = await src.read(self.BUFFER_SIZE)
                    if not data:
                        break
                    if detect and watch_429 and backend:
                        text = data[:512].decode("ascii", errors="replace")
                        if "429" in text:
                            backend.mark_429()
                            self.stats["total_429s"] += 1
                            logger.warning("429 detected on %s",
                                           backend.name)
                    dst.write(data)
                    await dst.drain()
            except (asyncio.CancelledError, ConnectionError, OSError):
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        t1 = asyncio.create_task(forward(r1, w2, detect=False))
        t2 = asyncio.create_task(forward(r2, w1, detect=True))
        await asyncio.gather(t1, t2, return_exceptions=True)

    async def handle_connect(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter):
        """Handle a single HTTP CONNECT request."""
        backend: Optional[Backend] = None
        try:
            # Read the CONNECT request line by line
            request_line = await asyncio.wait_for(
                reader.readline(), timeout=15.0)
            if not request_line:
                writer.close()
                return
            # Parse: CONNECT host:port HTTP/1.1
            parts = request_line.decode("ascii", errors="replace").strip().split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                writer.close()
                return
            target = parts[1]
            if ":" in target:
                host, port_str = target.rsplit(":", 1)
                port = int(port_str)
            else:
                host = target
                port = 443
            # Drain remaining request headers
            while True:
                line = await asyncio.wait_for(
                    reader.readline(), timeout=10.0)
                if line in (b"\r\n", b"\n", b""):
                    break

            self.stats["total_requests"] += 1
            await self.stealth.maybe_delay()

            # Select and connect through backend
            backend = self.select_backend()
            if not backend:
                writer.write(b"HTTP/1.1 503 No Backend Available\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            # Track active connections for weighted load balancing
            backend.active_connections += 1

            if not backend.bucket.consume():
                # Rate limited by local bucket
                backend.mark_429()
                self.stats["total_429s"] += 1
                writer.write(b"HTTP/1.1 429 Too Many Requests\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            try:
                s_reader, s_writer = await asyncio.wait_for(
                    asyncio.open_connection(backend.socks_host,
                                            backend.socks_port),
                    timeout=10.0
                )
                await self._socks5_connect(s_reader, s_writer, host, port)
            except Exception as exc:
                logger.error("Backend %s failed: %s", backend.name, exc)
                backend.error_count += 1
                self.mark_backend_unhealthy(backend)
                # Try fallback
                backend = self.select_backend()
                if not backend:
                    writer.write(
                        b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await writer.drain()
                    writer.close()
                    return
                try:
                    s_reader, s_writer = await asyncio.wait_for(
                        asyncio.open_connection(backend.socks_host,
                                                backend.socks_port),
                        timeout=10.0
                    )
                    await self._socks5_connect(
                        s_reader, s_writer, host, port)
                except Exception:
                    writer.write(
                        b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await writer.drain()
                    writer.close()
                    return

            # Send 200 Connection Established to client
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            backend.request_count += 1

            # Relay data with 429 watching
            await self._relay(
                reader, s_reader, writer, s_writer,
                watch_429=True, backend=backend
            )

        except (asyncio.CancelledError, ConnectionError, OSError,
                asyncio.TimeoutError) as exc:
            logger.debug("Connection handler error: %s", exc)
        finally:
            # Release connection tracking
            if backend is not None:
                backend.active_connections = max(0, backend.active_connections - 1)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        """Start the proxy TCP server."""
        self._server = await asyncio.start_server(
            self.handle_connect, self.host, self.port)
        logger.info("Proxy listening on %s:%d", self.host, self.port)

    async def stop(self):
        """Gracefully stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Proxy stopped")


def load_backends(config_file: Optional[str] = None) -> List[Backend]:
    """Load backends from config files or environment."""
    backends = []
    config_paths = []
    if config_file:
        config_paths.append(Path(config_file))
    config_paths.extend([
        Path.home() / ".config/opencode-vpn/state/servers.json",
        Path.home() / ".config/opencode-vpn/oracle-vms.json",
    ])
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
        servers = data if isinstance(data, list) else data.get("servers", [])
        for srv in servers:
            key = f"{srv.get('socks_host')}:{srv.get('socks_port')}"
            if key in seen:
                continue
            seen.add(key)
            name = srv.get("name", key)
            b = Backend(
                name=name,
                socks_host=srv.get("socks_host", "127.0.0.1"),
                socks_port=srv.get("socks_port", 1080),
                provider=srv.get("provider", "manual"),
                country=srv.get("country", "unknown"),
                bucket=TokenBucket(name, 80, 20),
            )
            backends.append(b)
    # Fallback: single local SOCKS5
    if not backends:
        env_host = os.environ.get("ROTATOR_SOCKS_HOST", "127.0.0.1")
        env_port = int(os.environ.get("ROTATOR_SOCKS_PORT", "1080"))
        backends.append(Backend(
            name="local",
            socks_host=env_host,
            socks_port=env_port,
            bucket=TokenBucket("local", 80, 20),
        ))
        logger.info("No config found, using default local backend %s:%d",
                     env_host, env_port)
    return backends


def print_stats_json(proxy: RotatingProxy, backends: List[Backend]):
    """Print machine-readable JSON stats."""
    uptime = time.time() - proxy.stats["start_time"]
    output = {
        "uptime_seconds": round(uptime, 1),
        "total_requests": proxy.stats["total_requests"],
        "total_429s": proxy.stats["total_429s"],
        "total_switches": proxy.stats["total_switches"],
        "backends": [],
    }
    for b in backends:
        output["backends"].append({
            "name": b.name,
            "host": b.socks_host,
            "port": b.socks_port,
            "healthy": b.healthy,
            "rate_limited": b.is_rate_limited,
            "latency_ms": round(b.latency, 1),
            "requests": b.request_count,
            "errors": b.error_count,
            "bucket": b.bucket.get_stats(),
        })
    print(json.dumps(output, indent=2))


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


async def main():
    parser = argparse.ArgumentParser(
        description="opencode-vpn rotator: rotating SOCKS5 proxy")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Listen address (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8888,
                        help="Listen port (default: 8888)")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--dashboard", "-d", action="store_true",
                        help="Show live ANSI dashboard")
    parser.add_argument("--health", action="store_true",
                        help="Run initial health check on startup")
    parser.add_argument("--health-interval", type=float, default=300,
                        help="Health check interval in seconds (default: 300)")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in daemon mode (no dashboard, log to stderr)")
    parser.add_argument("--stats", action="store_true",
                        help="Print stats as JSON and exit")
    parser.add_argument("--stealth", action="store_true",
                        help="Enable stealth mode with random delays")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Load backends
    backends = load_backends(args.config)
    if not backends:
        logger.error("No backends configured. Set ROTATOR_SOCKS_HOST/PORT "
                      "or create ~/.config/opencode-vpn/state/servers.json")
        sys.exit(1)

    logger.info("Loaded %d backend(s): %s", len(backends),
                ", ".join(b.name for b in backends))

    # Create proxy
    proxy = RotatingProxy(args.host, args.port, backends)
    proxy.stealth.enabled = args.stealth

    # Setup signal handlers
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    # Start proxy
    await proxy.start()

    # Start health checker
    checker = HealthChecker(backends, interval=args.health_interval)
    if args.health:
        logger.info("Running initial health check...")
        await checker.check_all()
        healthy = sum(1 for b in backends if b.healthy)
        logger.info("Health check done: %d/%d healthy",
                     healthy, len(backends))

    health_task = asyncio.create_task(checker.run_forever())

    # Stats mode: print and exit
    if args.stats:
        await asyncio.sleep(0.5)
        print_stats_json(proxy, backends)
        health_task.cancel()
        await proxy.stop()
        return

    # Dashboard or idle
    dashboard = Dashboard(backends, proxy.stats)
    if args.dashboard:
        dash_task = asyncio.create_task(dashboard.run_live(refresh=2.0))
    else:
        dash_task = None
        logger.info("Rotator running on %s:%d (ctrl-c to stop)",
                     args.host, args.port)

    # Wait for shutdown
    await shutdown_event.wait()
    logger.info("Shutting down...")
    checker.stop()
    health_task.cancel()
    if dash_task:
        dash_task.cancel()
    await proxy.stop()
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()
    print_stats_json(proxy, backends)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
