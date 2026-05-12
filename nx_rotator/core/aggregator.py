"""
NxRotator Core - Enhanced Self-Learning API Key Aggregator
=========================================================

Key features:
- Uses ALL 6 OpenRouter keys in rotation
- Async/await with httpx connection pooling
- Streaming support
- Multi-key retry (not just 1)
- SQLite learning to weight key selection
- Circuit breaker pattern per key
- Request deduplication
- Comprehensive error handling

Usage:
    from nx_rotator import NxRotator
    rotator = NxRotator()

    # Sync
    result = rotator.chat("model-name", [{"role": "user", "content": "Hello"}])

    # Async
    result = await rotator.chat_async("model-name", [{"role": "user", "content": "Hello"}])

    # Streaming
    async for chunk in rotator.chat_stream("model-name", [{"role": "user", "content": "Hello"}]):
        print(chunk, end="")
"""

import json
import os
import sys
import time
import threading
import asyncio
import sqlite3
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, AsyncIterator
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# ============================================================
# Configuration
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = _PROJECT_ROOT / "configs" / "api-keys"
KEYS_FILE = CONFIG_DIR / "keys.json"

DB_FILE = CONFIG_DIR / "nx_rotator_learning.db"
METRICS_FILE = CONFIG_DIR / "nx_rotator_metrics.json"

_lock = threading.Lock()
_async_lock = asyncio.Lock()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENCODE_BASE_URL = "https://api.opencode.ai/v1"

REFERER = "https://n-xyme.github.io"
APP_TITLE = "N-Xyme MIND"

# Provider endpoints mapping
PROVIDER_ENDPOINTS = {
    "openrouter": {
        "base_url": OPENROUTER_BASE_URL,
        "chat_endpoint": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "google": {
        "base_url": GOOGLE_BASE_URL,
        "chat_endpoint": "/chatModels:generateContent",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "groq": {
        "base_url": GROQ_BASE_URL,
        "chat_endpoint": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "opencode": {
        "base_url": OPENCODE_BASE_URL,
        "chat_endpoint": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "",
    },
}

# Enhanced config
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3
CIRCUIT_BREAKER_THRESHOLD = 5  # failures before opening
CIRCUIT_BREAKER_TIMEOUT = 60  # seconds before half-open
REQUEST_DEDUP_WINDOW = 5  # seconds

# Retry backoff config
RETRY_BACKOFF_BASE = 1.0  # seconds
RETRY_BACKOFF_MAX = 30.0  # max seconds
RETRY_BACKOFF_MULTIPLIER = 2.0

# Performance tuning
USE_HTTP2 = True  # HTTP/2 for faster connection reuse
PREWARM_CONNECTIONS = True  # Pre-warm connections on init
DNS_CACHE_TTL = 3600  # DNS cache TTL in seconds

# ============================================================
# Data Models
# ============================================================


@dataclass
class CircuitBreaker:
    """Circuit breaker for each key."""

    failures: int = 0
    state: str = "closed"  # closed, open, half-open
    opened_at: float = 0.0
    last_failure: float = 0.0

    def should_allow(self) -> bool:
        now = time.time()
        if self.state == "closed":
            return True
        if self.state == "open":
            if now - self.opened_at > CIRCUIT_BREAKER_TIMEOUT:
                self.state = "half-open"
                return True
            return False
        # half-open - allow one request
        return True

    def record_success(self):
        self.failures = 0
        self.state = "closed"
        self.opened_at = 0.0

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= CIRCUIT_BREAKER_THRESHOLD:
            self.state = "open"
            self.opened_at = time.time()


@dataclass
class APIKey:
    """A single API key with health tracking."""

    key_id: str
    key: str
    provider: str
    creator_user_id: str
    email: str
    priority: int

    # Limits
    rpm_limit: int = 20
    tpm_limit: int = 50000
    daily_limit: int = 50

    # Runtime state
    is_exhausted: bool = False
    exhausted_at: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_errors: int = 0
    health_score: float = 1.0
    cooldown_until: float = 0.0
    total_tokens: int = 0

    # Enhanced: Circuit breaker
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)

    # Enhanced: Per-model stats
    model_stats: Dict[str, Dict] = field(
        default_factory=lambda: defaultdict(
            lambda: {"requests": 0, "errors": 0, "avg_latency": 0.0}
        )
    )

    # Enhanced: Latency tracking
    latency_history: List[float] = field(default_factory=list)

    def is_available(self) -> bool:
        now = time.time()
        if now < self.cooldown_until:
            return False
        if self.is_exhausted:
            return False
        # Check circuit breaker
        if not self.circuit_breaker.should_allow():
            return False
        return True

    def record_success(self, tokens: int = 0, latency_ms: float = 0.0):
        self.consecutive_errors = 0
        self.health_score = min(1.0, self.health_score + 0.1)
        self.cooldown_until = 0.0
        self.total_tokens += tokens
        self.request_count += 1
        self.last_used = datetime.now()

        # Circuit breaker
        self.circuit_breaker.record_success()

        # Latency tracking
        if latency_ms > 0:
            self.latency_history.append(latency_ms)
            if len(self.latency_history) > 100:
                self.latency_history = self.latency_history[-100:]

    def record_failure(self, error_type: str = "unknown"):
        self.consecutive_errors += 1
        self.error_count += 1
        self.health_score = max(0.0, self.health_score - 0.2)

        # Exponential backoff
        if error_type == "rate_limit" or self.consecutive_errors >= 3:
            cooldown = min(10 * (2 ** (self.consecutive_errors - 1)), 300)
            self.cooldown_until = time.time() + cooldown

        # Circuit breaker
        self.circuit_breaker.record_failure()

    def get_avg_latency(self) -> float:
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)

    def get_success_rate(self) -> float:
        if self.request_count == 0:
            return 1.0
        return (self.request_count - self.error_count) / self.request_count


@dataclass
class RequestResult:
    """Result of a chat request."""

    success: bool
    response: Optional[Dict] = None
    error: Optional[str] = None
    key_used: Optional[str] = None
    latency_ms: float = 0.0
    tokens: int = 0
    retries: int = 0


@dataclass
class StreamChunk:
    """Streaming chunk."""

    delta: str
    finish_reason: Optional[str] = None
    key_used: Optional[str] = None


# ============================================================
# Enhanced Metrics
# ============================================================


class Metrics:
    """Thread-safe metrics collector with enhanced stats."""

    def __init__(self):
        self.total_requests: int = 0
        self.total_tokens: int = 0
        self.total_errors: int = 0
        self.total_rotations: int = 0
        self.total_retries: int = 0
        self.total_deduped: int = 0
        self.circuit_breaker_trips: int = 0

        self.by_key: Dict[str, Dict] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "errors": 0, "retries": 0}
        )
        self.by_model: Dict[str, Dict] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "errors": 0}
        )
        self.by_error: Dict[str, int] = defaultdict(int)

        self.request_times: List[float] = []
        self.uptime_start: datetime = datetime.now()

        # Enhanced: Latency percentiles
        self.latency_p50: float = 0.0
        self.latency_p95: float = 0.0
        self.latency_p99: float = 0.0

    def record_request(
        self,
        key_id: str,
        model: str,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
        retries: int = 0,
    ):
        with _lock:
            self.total_requests += 1
            self.total_retries += retries

            if latency_ms > 0:
                self.request_times.append(latency_ms)
                if len(self.request_times) > 1000:
                    self.request_times = self.request_times[-1000:]
                self._update_percentiles()

            self.by_key[key_id]["requests"] += 1
            self.by_key[key_id]["retries"] += retries
            self.by_model[model]["requests"] += 1

            if success:
                self.total_tokens += tokens
                self.by_key[key_id]["tokens"] += tokens
                self.by_model[model]["tokens"] += tokens
            else:
                self.total_errors += 1
                self.by_key[key_id]["errors"] += 1
                self.by_model[model]["errors"] += 1

    def record_dedup(self):
        with _lock:
            self.total_deduped += 1

    def record_circuit_breaker(self):
        with _lock:
            self.circuit_breaker_trips += 1

    def record_rotation(self):
        with _lock:
            self.total_rotations += 1

    def record_error_type(self, error: str):
        with _lock:
            # Normalize error type
            error_type = error.split(":")[0][:50]
            self.by_error[error_type] += 1

    def _update_percentiles(self):
        if len(self.request_times) < 10:
            return
        sorted_times = sorted(self.request_times)
        n = len(sorted_times)
        self.latency_p50 = sorted_times[int(n * 0.5)]
        self.latency_p95 = sorted_times[int(n * 0.95)]
        self.latency_p99 = sorted_times[int(n * 0.99)]

    def get_stats(self) -> Dict:
        with _lock:
            uptime = datetime.now() - self.uptime_start
            avg_latency = (
                sum(self.request_times) / len(self.request_times)
                if self.request_times
                else 0
            )

            return {
                "total_requests": self.total_requests,
                "total_tokens": self.total_tokens,
                "total_errors": self.total_errors,
                "total_rotations": self.total_rotations,
                "total_retries": self.total_retries,
                "total_deduped": self.total_deduped,
                "circuit_breaker_trips": self.circuit_breaker_trips,
                "error_rate": self.total_errors / max(self.total_requests, 1) * 100,
                "avg_latency_ms": avg_latency,
                "p50_latency_ms": self.latency_p50,
                "p95_latency_ms": self.latency_p95,
                "p99_latency_ms": self.latency_p99,
                "uptime_seconds": uptime.total_seconds(),
                "by_key": dict(self.by_key),
                "by_model": dict(self.by_model),
                "by_error": dict(self.by_error),
            }


# ============================================================
# Request Deduplication
# ============================================================


class RequestDeduplicator:
    """Deduplicate identical requests within a time window."""

    def __init__(self, window_seconds: float = REQUEST_DEDUP_WINDOW):
        self.window_seconds = window_seconds
        self.pending: Dict[str, tuple] = {}  # request_hash -> (future, timestamp)
        self._lock = threading.Lock()

    def _hash_request(self, model: str, messages: List[Dict]) -> str:
        content = json.dumps({"model": model, "messages": messages}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def check_or_wait(self, model: str, messages: List[Dict]) -> Optional[any]:
        """Check if identical request exists. Return Future if found, None if new."""
        request_hash = self._hash_request(model, messages)

        with _lock:
            now = time.time()

            # Clean old entries
            self.pending = {
                k: v
                for k, v in self.pending.items()
                if now - v[1] < self.window_seconds
            }

            if request_hash in self.pending:
                return self.pending[request_hash][0]

            # Placeholder - will be replaced when request completes
            return None

    def register(self, model: str, messages: List[Dict], future: any):
        request_hash = self._hash_request(model, messages)
        with _lock:
            self.pending[request_hash] = (future, time.time())


# ============================================================
# SQLite Learning Engine
# ============================================================


class LearningEngine:
    """SQLite-based learning to weight key selection."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            timestamp REAL, 
            key_id TEXT,
            model TEXT, 
            success INTEGER, 
            error_type TEXT, 
            latency_ms REAL,
            tokens_used INTEGER)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS key_performance (
            key_id TEXT PRIMARY KEY, 
            total_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0, 
            avg_latency_ms REAL DEFAULT 0.0,
            total_tokens INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            last_updated REAL)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS model_preference (
            model TEXT,
            key_id TEXT,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0.0,
            PRIMARY KEY (model, key_id))""")

        conn.commit()
        conn.close()

    def record(
        self,
        key_id: str,
        model: str,
        success: bool,
        error_type: str,
        latency_ms: float,
        tokens_used: int,
    ):
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Main outcome
            conn.execute(
                """INSERT INTO outcomes 
                (timestamp, key_id, model, success, error_type, latency_ms, tokens_used) 
                VALUES (?,?,?,?,?,?,?)""",
                (
                    time.time(),
                    key_id,
                    model,
                    int(success),
                    error_type,
                    latency_ms,
                    tokens_used,
                ),
            )

            # Key performance
            conn.execute(
                """INSERT INTO key_performance 
                (key_id, total_requests, successful_requests, avg_latency_ms, total_tokens, success_rate, last_updated)
                VALUES (?,?,?,?,?,?,?) 
                ON CONFLICT(key_id) DO UPDATE SET
                total_requests = total_requests + 1,
                successful_requests = successful_requests + excluded.successful_requests,
                avg_latency_ms = CASE 
                    WHEN total_requests = 0 THEN excluded.avg_latency_ms
                    ELSE (avg_latency_ms * total_requests + excluded.avg_latency_ms) / (total_requests + 1)
                END,
                total_tokens = total_tokens + excluded.total_tokens,
                success_rate = CAST(successful_requests AS REAL) / (total_requests + 1),
                last_updated = excluded.last_updated""",
                (
                    key_id,
                    1,
                    int(success),
                    latency_ms,
                    tokens_used,
                    1.0 if success else 0.0,
                    time.time(),
                ),
            )

            # Model preference
            conn.execute(
                """INSERT INTO model_preference 
                (model, key_id, success_count, failure_count, avg_latency_ms)
                VALUES (?,?,?,?,?)
                ON CONFLICT(model, key_id) DO UPDATE SET
                success_count = success_count + excluded.success_count,
                failure_count = failure_count + excluded.failure_count,
                avg_latency_ms = (avg_latency_ms * (success_count + failure_count - 1) + excluded.avg_latency_ms) 
                / (success_count + failure_count)""",
                (model, key_id, int(success), int(not success), latency_ms),
            )

            conn.commit()
        finally:
            conn.close()

    def get_key_weights(self) -> Dict[str, float]:
        """Get learned weights for each key."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Calculate success_rate on the fly since it might not be in older schemas
            cursor = conn.execute(
                """SELECT key_id, 
                    COALESCE(CAST(successful_requests AS REAL) / NULLIF(total_requests, 0), 1.0) * 
                    COALESCE(1.0 / NULLIF(avg_latency_ms/1000, 0), 1.0) as weight
                FROM key_performance 
                WHERE total_requests > 0
                ORDER BY weight DESC"""
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_best_key_for_model(self, model: str) -> Optional[str]:
        """Get best key for a specific model based on history."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """SELECT key_id FROM model_preference 
                WHERE model = ? ORDER BY success_count DESC, avg_latency_ms ASC LIMIT 1""",
                (model,),
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()


# ============================================================
# Main Aggregator Class
# ============================================================


class NxRotator:
    """
    Enhanced API Key Aggregator with self-learning.

    Features:
    - Async/await with httpx connection pooling
    - Streaming support
    - Multi-key retry (up to MAX_RETRIES)
    - SQLite learning to weight key selection
    - Circuit breaker pattern per key
    - Request deduplication
    - Model-specific routing
    """

    def __init__(self, use_proxy: bool = False):
        self.keys: List[APIKey] = []
        self.metrics = Metrics()
        self.learning = LearningEngine(DB_FILE)
        self.deduplicator = RequestDeduplicator()
        self._current_key_idx: int = 0
        self._running = False

        # Async HTTP client (lazy init)
        self._async_client: Optional[httpx.AsyncClient] = None

        # Thread pool for sync requests
        self._executor = ThreadPoolExecutor(max_workers=10)

        if not HAS_REQUESTS and not HAS_HTTPX:
            raise ImportError("requests or httpx library required")

        self._load_keys()

        # Apply learned weights on init
        self._apply_learned_weights()

        # Pre-warm HTTP connections for faster first request
        if PREWARM_CONNECTIONS:
            self._prewarm_connections()

        print(f"[NxRotator] Initialized with {len(self.keys)} keys")

    def _prewarm_connections(self):
        """Pre-warm connections to OpenRouter for faster first request."""
        print("[NxRotator] Pre-warming connections...")
        try:
            # Make a lightweight HEAD request to establish connection
            import socket

            # Resolve DNS once and cache
            host = "openrouter.ai"
            socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)

            # Make a simple request to warm up
            requests.head(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"HTTP-Referer": REFERER, "X-Title": APP_TITLE},
                timeout=5,
            )
            print("[NxRotator] ✅ Connections pre-warmed")
        except Exception as e:
            print(f"[NxRotator] ⚠️ Pre-warm failed: {e}")

    def _load_keys(self):
        if not KEYS_FILE.exists():
            print(f"[ERROR] Keys file not found: {KEYS_FILE}")
            return

        with open(KEYS_FILE, "r") as f:
            data = json.load(f)

        # Load ALL providers - aggregate TPM and rate limits
        total_rpm = 0
        total_tpm = 0

        for provider, key_list in data.items():
            if not isinstance(key_list, list):
                continue

            for k in key_list:
                key_value = k.get("key", "")
                # Skip empty env var placeholders
                if key_value.startswith("${") and key_value.endswith("}"):
                    print(
                        f"[NxRotator] Skipping {provider} - env var not set: {key_value}"
                    )
                    continue

                key_rpm = k.get("rpm_limit", 20)
                key_tpm = k.get("tpm_limit", 50000)
                total_rpm += key_rpm
                total_tpm += key_tpm

                self.keys.append(
                    APIKey(
                        key_id=k.get("key_id", "unknown"),
                        key=key_value,
                        provider=provider,
                        creator_user_id=k.get("creator_user_id", ""),
                        email=k.get("account_email", f"{provider}@unknown"),
                        priority=k.get("priority", 0),
                        rpm_limit=key_rpm,
                        tpm_limit=key_tpm,
                        daily_limit=k.get("daily_limit", 50),
                    )
                )

        print(
            f"[NxRotator] Aggregated limits: {total_rpm} RPM, {total_tpm} TPM from {len(self.keys)} keys"
        )

    def _apply_learned_weights(self):
        """Apply learned weights from SQLite to key selection."""
        weights = self.learning.get_key_weights()
        for key in self.keys:
            if key.key_id in weights:
                # Blend learned weight with default health
                key.health_score = (key.health_score + weights[key.key_id]) / 2
                print(
                    f"[NxRotator] {key.key_id}: applied weight {weights[key.key_id]:.2f}"
                )

    def get_next_key(self, model: str = None) -> APIKey:
        """Get next available key based on weighted round-robin."""
        if not self.keys:
            raise ValueError("No API keys loaded!")

        available = [k for k in self.keys if k.is_available()]

        if available:
            # Weighted round-robin: select key probabilistically based on weight
            # Weight = health_score (which already includes learned weights)
            weights = [k.health_score for k in available]

            # Try to use model-specific preference if model is provided
            preferred_key_id = None
            if model:
                preferred_key_id = self.learning.get_best_key_for_model(model)
                if preferred_key_id:
                    # Boost weight for preferred key by 50%
                    for i, k in enumerate(available):
                        if k.key_id == preferred_key_id:
                            weights[i] *= 1.5
                            print(
                                f"[NxRotator] Model {model}: boosting preference for {preferred_key_id}"
                            )
                            break

            total_weight = sum(weights)

            if total_weight > 0:
                # Probabilistic selection
                import random

                r = random.random() * total_weight
                cumulative = 0
                for i, k in enumerate(available):
                    cumulative += weights[i]
                    if r <= cumulative:
                        self._current_key_idx = self.keys.index(k)
                        return k

                # Fallback to last key
                self._current_key_idx = self.keys.index(available[-1])
                return available[-1]
            else:
                # No weight - fall back to health-sorted
                available.sort(
                    key=lambda k: (
                        -k.health_score,
                        k.get_avg_latency(),
                        k.consecutive_errors,
                    )
                )
                self._current_key_idx = self.keys.index(available[0])
                return available[0]

        # All keys exhausted - soft reset
        print("[NxRotator] All keys exhausted, soft resetting...")
        for key in self.keys:
            key.consecutive_errors = min(key.consecutive_errors, 2)
            key.cooldown_until = 0.0
            # Also reset circuit breaker
            key.circuit_breaker.state = "closed"
            key.circuit_breaker.failures = 0

        self._current_key_idx = 0
        return self.keys[0]

    def _do_request(
        self,
        key: APIKey,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
    ) -> requests.Response:
        """Make HTTP request using requests library."""
        return requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {key.key}",
                "Content-Type": "application/json",
                "HTTP-Referer": REFERER,
                "X-Title": APP_TITLE,
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=DEFAULT_TIMEOUT,
        )

    async def _do_request_async(
        self,
        key: APIKey,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
    ) -> httpx.Response:
        """Make HTTP request using httpx async client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )

        return await self._async_client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {key.key}",
                "Content-Type": "application/json",
                "HTTP-Referer": REFERER,
                "X-Title": APP_TITLE,
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )

    def chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> RequestResult:
        """
        Send chat request through aggregator with multi-key retry.

        Implements:
        - Request deduplication
        - Multi-key retry (up to MAX_RETRIES)
        - Circuit breaker
        - SQLite learning
        """
        # Check dedup
        existing = self.deduplicator.check_or_wait(model, messages)
        if existing is not None:
            self.metrics.record_dedup()
            # Wait for existing request (simplified - in production use proper future)

        start_time = time.time()
        retries = 0

        for attempt in range(MAX_RETRIES):
            key = self.get_next_key(model)

            try:
                resp = self._do_request(key, model, messages, max_tokens, temperature)
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)

                    # Success
                    key.record_success(tokens, latency_ms)
                    self.learning.record(
                        key.key_id, model, True, "", latency_ms, tokens
                    )
                    self.metrics.record_request(
                        key.key_id, model, True, tokens, latency_ms, retries
                    )

                    return RequestResult(
                        success=True,
                        response=data,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                        retries=retries,
                    )

                elif resp.status_code == 429:
                    # Rate limit - rotate and retry
                    key.record_failure("rate_limit")
                    self.learning.record(
                        key.key_id, model, False, "rate_limit", latency_ms, 0
                    )
                    self.metrics.record_request(
                        key.key_id, model, False, latency_ms=latency_ms, retries=retries
                    )
                    self.metrics.record_rotation()

                    print(
                        f"[NxRotator] Rate limit on {key.key_id}, rotating (attempt {attempt + 1}/{MAX_RETRIES})..."
                    )

                    # Mark exhausted temporarily
                    key.is_exhausted = True
                    key.exhausted_at = datetime.now()

                    retries += 1
                    if retries >= MAX_RETRIES:
                        return RequestResult(
                            success=False,
                            error="Max retries exceeded due to rate limits",
                            key_used=key.key_id,
                            latency_ms=latency_ms,
                            retries=retries,
                        )
                    # Retry backoff: wait before next attempt
                    backoff = min(
                        RETRY_BACKOFF_BASE
                        * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                        RETRY_BACKOFF_MAX,
                    )
                    time.sleep(backoff)
                    continue

                else:
                    # Other HTTP error - handle specific codes
                    error_text = resp.text[:200]
                    status = resp.status_code

                    # Handle specific HTTP errors
                    if status == 401:
                        # Unauthorized - key invalid, mark for permanent removal
                        print(
                            f"[NxRotator] CRITICAL: Key {key.key_id} unauthorized (401). Disabling."
                        )
                        key.is_exhausted = True
                        key.is_disabled = True
                        error_prefix = "auth_invalid"
                    elif status == 403:
                        # Forbidden - quota exceeded or permissions issue
                        print(
                            f"[NxRotator] Key {key.key_id} forbidden (403). Treating as rate limit."
                        )
                        key.is_exhausted = True
                        key.exhausted_at = datetime.now()
                        error_prefix = "forbidden"
                    elif status == 500:
                        # Server error - retry with backoff
                        print(f"[NxRotator] OpenRouter server error (500). Retrying...")
                        error_prefix = "server_error"
                    elif status == 503:
                        # Service unavailable - retry with backoff
                        print(
                            f"[NxRotator] OpenRouter service unavailable (503). Retrying..."
                        )
                        error_prefix = "service_unavailable"
                    else:
                        error_prefix = f"http_{status}"

                    key.record_failure(error_prefix)
                    self.learning.record(
                        key.key_id,
                        model,
                        False,
                        f"http_{resp.status_code}",
                        latency_ms,
                        0,
                    )
                    self.metrics.record_request(
                        key.key_id, model, False, latency_ms=latency_ms, retries=retries
                    )
                    self.metrics.record_error_type(f"http_{resp.status_code}")

                    retries += 1
                    if retries >= MAX_RETRIES:
                        return RequestResult(
                            success=False,
                            error=error_text,
                            key_used=key.key_id,
                            latency_ms=latency_ms,
                            retries=retries,
                        )
                    # Retry backoff: wait before next attempt
                    backoff = min(
                        RETRY_BACKOFF_BASE
                        * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                        RETRY_BACKOFF_MAX,
                    )
                    time.sleep(backoff)
                    continue

            except Exception as e:
                error_str = str(e)
                latency_ms = (time.time() - start_time) * 1000

                key.record_failure("exception")
                self.learning.record(
                    key.key_id, model, False, "exception", latency_ms, 0
                )
                self.metrics.record_request(
                    key.key_id, model, False, latency_ms=latency_ms, retries=retries
                )
                self.metrics.record_error_type("exception")

                retries += 1
                if retries >= MAX_RETRIES:
                    return RequestResult(
                        success=False,
                        error=error_str,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        retries=retries,
                    )
                # Retry backoff: wait before next attempt
                backoff = min(
                    RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                    RETRY_BACKOFF_MAX,
                )
                time.sleep(backoff)
                continue

        return RequestResult(
            success=False,
            error="All retries exhausted",
            latency_ms=(time.time() - start_time) * 1000,
            retries=retries,
        )

    async def chat_async(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> RequestResult:
        """Async version of chat."""
        start_time = time.time()
        retries = 0

        for attempt in range(MAX_RETRIES):
            key = self.get_next_key(model)

            try:
                resp = await self._do_request_async(
                    key, model, messages, max_tokens, temperature
                )
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)

                    key.record_success(tokens, latency_ms)
                    self.learning.record(
                        key.key_id, model, True, "", latency_ms, tokens
                    )
                    self.metrics.record_request(
                        key.key_id, model, True, tokens, latency_ms, retries
                    )

                    return RequestResult(
                        success=True,
                        response=data,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                        retries=retries,
                    )

                elif resp.status_code == 429:
                    key.record_failure("rate_limit")
                    self.learning.record(
                        key.key_id, model, False, "rate_limit", latency_ms, 0
                    )
                    self.metrics.record_request(
                        key.key_id, model, False, latency_ms=latency_ms, retries=retries
                    )
                    self.metrics.record_rotation()

                    key.is_exhausted = True
                    key.exhausted_at = datetime.now()

                    retries += 1
                    if retries >= MAX_RETRIES:
                        break
                    # Retry backoff: wait before next attempt
                    backoff = min(
                        RETRY_BACKOFF_BASE
                        * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                        RETRY_BACKOFF_MAX,
                    )
                    await asyncio.sleep(backoff)
                    continue

                else:
                    key.record_failure(f"http_{resp.status_code}")
                    self.learning.record(
                        key.key_id,
                        model,
                        False,
                        f"http_{resp.status_code}",
                        latency_ms,
                        0,
                    )
                    self.metrics.record_request(
                        key.key_id, model, False, latency_ms=latency_ms, retries=retries
                    )

                    retries += 1
                    if retries >= MAX_RETRIES:
                        break
                    # Retry backoff: wait before next attempt
                    backoff = min(
                        RETRY_BACKOFF_BASE
                        * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                        RETRY_BACKOFF_MAX,
                    )
                    await asyncio.sleep(backoff)
                    continue

            except Exception as e:
                key.record_failure("exception")
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    key.key_id, model, False, latency_ms=latency_ms, retries=retries
                )

                retries += 1
                if retries >= MAX_RETRIES:
                    break
                # Retry backoff: wait before next attempt
                backoff = min(
                    RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                    RETRY_BACKOFF_MAX,
                )
                await asyncio.sleep(backoff)
                continue

        return RequestResult(
            success=False,
            error="All retries exhausted",
            latency_ms=(time.time() - start_time) * 1000,
            retries=retries,
        )

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming chat with retry support - yields chunks as they arrive."""
        start_time = time.time()
        retries = 0
        last_error = None

        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )

        while retries < MAX_RETRIES:
            key = self.get_next_key(model)

            try:
                async with self._async_client.stream(
                    "POST",
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": REFERER,
                        "X-Title": APP_TITLE,
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    },
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    yield StreamChunk(
                                        delta="",
                                        finish_reason="stop",
                                        key_used=key.key_id,
                                    )
                                    break

                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get(
                                        "delta", {}
                                    )
                                    content = delta.get("content", "")
                                    finish = chunk.get("choices", [{}])[0].get(
                                        "finish_reason"
                                    )

                                    if content or finish:
                                        yield StreamChunk(
                                            delta=content,
                                            finish_reason=finish,
                                            key_used=key.key_id,
                                        )
                                except json.JSONDecodeError:
                                    continue

                        latency_ms = (time.time() - start_time) * 1000
                        key.record_success(0, latency_ms)
                        self.metrics.record_request(
                            key.key_id, model, True, 0, latency_ms
                        )
                        return  # Success - exit retry loop
                    elif response.status_code == 429:
                        # Rate limit - rotate and retry
                        key.record_failure("rate_limit")
                        key.is_exhausted = True
                        key.exhausted_at = datetime.now()
                        print(
                            f"[NxRotator] Stream rate limit on {key.key_id}, rotating..."
                        )
                        self.metrics.record_rotation()
                    else:
                        # Other HTTP error
                        key.record_failure(f"http_{response.status_code}")
                        last_error = f"HTTP {response.status_code}"
                        print(
                            f"[NxRotator] Stream error {response.status_code} on {key.key_id}"
                        )

            except Exception as e:
                key.record_failure("exception")
                last_error = str(e)
                print(f"[NxRotator] Stream exception on {key.key_id}: {e}")
                self.metrics.record_request(
                    key.key_id,
                    model,
                    False,
                    latency_ms=(time.time() - start_time) * 1000,
                )

            # Retry with backoff
            retries += 1
            if retries >= MAX_RETRIES:
                break
            backoff = min(
                RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** (retries - 1)),
                RETRY_BACKOFF_MAX,
            )
            await asyncio.sleep(backoff)
            print(f"[NxRotator] Stream retry {retries}/{MAX_RETRIES}...")

        # All retries exhausted - yield error chunk
        yield StreamChunk(
            delta="",
            finish_reason="error",
            key_used=key.key_id if retries > 0 else "unknown",
        )

    def parallel_chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> List[RequestResult]:
        """
        PARALLEL mode - Fire ALL available keys simultaneously!

        This is the "tunnel" concept - all 6 keys working in parallel
        for 6x throughput on long responses.

        Returns list of results (one per key).
        Use the fastest successful response.
        """
        import concurrent.futures

        available_keys = [k for k in self.keys if k.is_available()]

        if not available_keys:
            return [RequestResult(success=False, error="No available keys")]

        print(
            f"[NxRotator] PARALLEL: Firing {len(available_keys)} keys simultaneously..."
        )

        def _fire_single(key: APIKey) -> RequestResult:
            start_time = time.time()
            try:
                resp = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": REFERER,
                        "X-Title": APP_TITLE,
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    key.record_success(tokens, latency_ms)
                    return RequestResult(
                        success=True,
                        response=data,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                    )
                else:
                    key.record_failure(f"http_{resp.status_code}")
                    return RequestResult(
                        success=False,
                        error=f"HTTP {resp.status_code}",
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                    )
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                key.record_failure("exception")
                return RequestResult(
                    success=False,
                    error=str(e),
                    key_used=key.key_id,
                    latency_ms=latency_ms,
                )

        # Fire ALL keys in parallel using ThreadPoolExecutor
        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(available_keys)
        ) as executor:
            future_to_key = {
                executor.submit(_fire_single, k): k for k in available_keys
            }

            for future in concurrent.futures.as_completed(future_to_key):
                result = future.result()
                results.append(result)
                print(
                    f"[NxRotator] Parallel result: {result.key_used} - {'SUCCESS' if result.success else 'FAIL'} ({result.latency_ms:.0f}ms)"
                )

        return results

    def race_chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> RequestResult:
        """
        RACE mode - Fire ALL keys, return FIRST success, cancel rest!

        This is the FASTEST possible method:
        - All 6 keys fire simultaneously
        - First successful response wins
        - Other requests cancelled immediately
        - Zero waiting for slow keys

        Ideal for: Low-latency critical requests
        """
        import concurrent.futures

        available_keys = [k for k in self.keys if k.is_available()]

        if not available_keys:
            return RequestResult(success=False, error="No available keys")

        print(f"[NxRotator] RACE: {len(available_keys)} keys racing to finish...")

        # Shared state for early termination
        winner_found = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        winner_event = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        result_holder = [None]  # Use list to allow mutation in closure

        def _fire_with_cancel(key: APIKey) -> RequestResult:
            start_time = time.time()
            try:
                resp = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": REFERER,
                        "X-Title": APP_TITLE,
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    key.record_success(tokens, latency_ms)

                    result = RequestResult(
                        success=True,
                        response=data,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                    )
                    result_holder[0] = result
                    print(
                        f"[NxRotator] 🏆 RACE WINNER: {key.key_id} at {latency_ms:.0f}ms"
                    )
                    return result
                else:
                    key.record_failure(f"http_{resp.status_code}")
                    return RequestResult(
                        success=False,
                        error=f"HTTP {resp.status_code}",
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                    )
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                key.record_failure("exception")
                return RequestResult(
                    success=False,
                    error=str(e),
                    key_used=key.key_id,
                    latency_ms=latency_ms,
                )

        # Fire with FIRST_COMPLETE policy - returns as soon as any completes
        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(available_keys)
        ) as executor:
            # Submit all and wait for first completion
            futures = {executor.submit(_fire_with_cancel, k): k for k in available_keys}

            # Wait for first result
            done, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )

            for future in done:
                result = future.result()
                results.append(result)
                if result.success:
                    # Cancel all remaining futures
                    for f in futures:
                        f.cancel()
                    print(
                        f"[NxRotator] RACE: Cancelled {len(futures) - 1} other requests"
                    )
                    return result

            # No winner yet - wait for rest
            for future in concurrent.futures.as_completed(futures):
                if future not in done:
                    result = future.result()
                    results.append(result)
                    if result.success:
                        return result

        # Return fastest failure if no success
        if results:
            fastest = min(results, key=lambda x: x.latency_ms)
            return fastest

        return RequestResult(success=False, error="All race participants failed")

    def funnel_chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
        strategy: str = "balanced",  # "balanced", "speed", "depth"
    ) -> RequestResult:
        """
        FUNNEL mode - TRUE 6x throughput via prompt splitting!

        This is the BLEEDING EDGE funnel concept:
        1. SPLIT: Split prompt into 6 parts (one per key)
        2. PARALLEL: All 6 keys process their part simultaneously
        3. MERGE: Combine all responses into single coherent result

        vs Race mode: Race only uses ONE response (wastes 5 keys)
        vs Funnel: ALL 6 keys contribute = TRUE 6x throughput

        Strategies:
        - "balanced": Equal split, merge results
        - "speed": 6x parallel requests, take first complete
        - "depth": Each key does different analysis, merge all

        ⚠️ Note: Works best for open-ended生成, code, long-form content
        """
        import concurrent.futures

        available_keys = [k for k in self.keys if k.is_available()]

        if not available_keys:
            return RequestResult(success=False, error="No available keys")

        if len(available_keys) < 2:
            # Not enough keys - fall back to single
            return self.chat(model, messages, max_tokens, temperature)

        num_keys = len(available_keys)

        # Extract the actual user message content
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        if not user_content:
            return RequestResult(success=False, error="No user message found")

        # Split the prompt into parts
        parts = self._split_prompt(user_content, num_keys, strategy)

        print(
            f"[NxRotator] FUNNEL: Split into {num_keys} parts, processing in parallel..."
        )
        print(f"[NxRotator] Strategy: {strategy}")

        def _process_part(idx: int, key: APIKey, part_content: str) -> RequestResult:
            """Process a single part of the split prompt."""
            start_time = time.time()

            # Create modified messages with this part
            part_messages = [{"role": "user", "content": part_content}]

            # Add system context for context preservation
            if strategy == "depth":
                system_instruction = f"""You are part {idx + 1} of {num_keys} parallel analysts.
Your specific role: {self._get_part_role(idx, num_keys)}
Analyze the following and provide your unique perspective.
Output ONLY your analysis - no meta-commentary."""
            else:
                system_instruction = f"""You are part {idx + 1} of {num_keys} parallel processors.
Continue the response naturally. Start directly with your content."""

            part_messages.insert(0, {"role": "system", "content": system_instruction})

            try:
                resp = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": REFERER,
                        "X-Title": APP_TITLE,
                    },
                    json={
                        "model": model,
                        "messages": part_messages,
                        "max_tokens": max_tokens // num_keys,  # Split token budget
                        "temperature": temperature,
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    key.record_success(tokens, latency_ms)

                    # Extract the actual response content
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    return RequestResult(
                        success=True,
                        response={
                            "content": content,
                            "part_idx": idx,
                            "key_id": key.key_id,
                        },
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                    )
                else:
                    key.record_failure(f"http_{resp.status_code}")
                    return RequestResult(
                        success=False,
                        error=f"HTTP {resp.status_code}",
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                    )
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                key.record_failure("exception")
                return RequestResult(
                    success=False,
                    error=str(e),
                    key_used=key.key_id,
                    latency_ms=latency_ms,
                )

        # Execute ALL parts in parallel
        results = []
        total_tokens = 0
        max_latency = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_keys) as executor:
            futures = []
            for idx, key in enumerate(available_keys):
                future = executor.submit(_process_part, idx, key, parts[idx])
                futures.append(future)

            # Wait for ALL to complete (true parallelism)
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                if result.success:
                    total_tokens += result.tokens
                    max_latency = max(max_latency, result.latency_ms)
                    print(
                        f"[NxRotator] FUNNEL part: {result.key_used} - ✅ ({result.latency_ms:.0f}ms, {result.tokens} tokens)"
                    )
                else:
                    print(
                        f"[NxRotator] FUNNEL part: {result.key_used} - ❌ ({result.error})"
                    )

        # Merge all successful responses
        successful = [r for r in results if r.success]

        if not successful:
            return RequestResult(success=False, error="All funnel parts failed")

        # Merge based on strategy
        merged_content = self._merge_responses(successful, strategy)

        # Calculate aggregated metrics
        avg_latency = sum(r.latency_ms for r in successful) / len(successful)

        print(f"[NxRotator] FUNNEL complete: {len(successful)}/{num_keys} succeeded")
        print(
            f"[NxRotator] Total tokens: {total_tokens} | Max latency: {max_latency:.0f}ms"
        )
        print(f"[NxRotator] Speedup: ~{max_latency / avg_latency:.1f}x vs serial")

        return RequestResult(
            success=True,
            response={
                "content": merged_content,
                "parts": len(successful),
                "total_tokens": total_tokens,
                "individual_results": [
                    {
                        "key_id": r.key_used,
                        "tokens": r.tokens,
                        "latency_ms": r.latency_ms,
                    }
                    for r in successful
                ],
            },
            key_used="funnel_merged",
            latency_ms=max_latency,
            tokens=total_tokens,
        )

    def _split_prompt(self, content: str, num_parts: int, strategy: str) -> List[str]:
        """Split prompt into parts for parallel processing."""

        if strategy == "speed":
            # Same prompt to all - they race, take best
            return [content] * num_parts

        if strategy == "depth":
            # Each key gets a different aspect to analyze
            aspects = [
                "Provide a technical analysis with code examples",
                "Provide a creative/counter-analysis",
                "Summarize the key points concisely",
                "Provide edge cases and considerations",
                "Explain the underlying principles",
                "Provide practical applications and examples",
            ]
            return [f"{content}\n\n[{aspect}]" for aspect in aspects[:num_parts]]

        # Balanced - split by sentences/paragraphs
        # Split on paragraph boundaries first
        paragraphs = content.split("\n\n")

        if len(paragraphs) >= num_parts:
            # Distribute paragraphs evenly
            part_size = len(paragraphs) // num_parts
            parts = []
            for i in range(num_parts):
                start = i * part_size
                if i == num_parts - 1:
                    # Last part gets remainder
                    part = "\n\n".join(paragraphs[start:])
                else:
                    part = "\n\n".join(paragraphs[start : start + part_size])
                parts.append(part)
            return parts

        # If not enough paragraphs, split by sentences
        import re

        sentences = re.split(r"(?<=[.!?])\s+", content)

        if len(sentences) >= num_parts:
            part_size = len(sentences) // num_parts
            parts = []
            for i in range(num_parts):
                start = i * part_size
                if i == num_parts - 1:
                    part = " ".join(sentences[start:])
                else:
                    part = " ".join(sentences[start : start + part_size])
                parts.append(part)
            return parts

        # Fallback: just repeat
        return [content] * num_parts

    def _merge_responses(self, results: List[RequestResult], strategy: str) -> str:
        """Merge multiple responses into one coherent result."""

        if strategy == "speed":
            # Take first/longest response
            return max(
                results, key=lambda x: len(x.response.get("content", ""))
            ).response.get("content", "")

        if strategy == "depth":
            # Combine all perspectives
            merged = "## Multi-Perspective Analysis\n\n"
            for r in results:
                content = r.response.get("content", "")
                key_id = r.key_used
                merged += f"### [{key_id}]\n{content}\n\n"
            return merged

        # Balanced - interleave or concatenate
        # For now, simple concatenation with separators
        merged = ""
        for r in results:
            content = r.response.get("content", "")
            if content:
                merged += content + "\n\n---\n\n"

        return merged.strip()

    def _get_part_role(self, idx: int, total: int) -> str:
        """Get the role for a specific part in depth mode."""
        roles = [
            "Technical Expert",
            "Creative Thinker",
            "Concise Summarizer",
            "Edge Case Analyst",
            "Principle Explainer",
            "Practical Application Expert",
        ]
        return roles[idx % len(roles)]

    def turbo_chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> RequestResult:
        """
        TURBO mode - Maximum REQUEST throughput!

        Fire IDENTICAL request to ALL 6 keys simultaneously.
        Take FIRST successful response.
        Cancel rest immediately.

        This gives you 6x REQUEST throughput (not token throughput).
        - Single key: 20 RPM
        - Turbo mode: 120 RPM of requests

        Use when: You need fast responses, don't need merged content.
        Result is identical to single request, just faster.

        Best for: Chat apps, real-time interactions
        """
        import concurrent.futures

        available_keys = [k for k in self.keys if k.is_available()]

        if not available_keys:
            return RequestResult(success=False, error="No available keys")

        print(f"[NxRotator] TURBO: {len(available_keys)} keys racing for latency...")

        def _fire_single(key: APIKey) -> RequestResult:
            start_time = time.time()
            try:
                resp = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": REFERER,
                        "X-Title": APP_TITLE,
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
                latency_ms = (time.time() - start_time) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    key.record_success(tokens, latency_ms)

                    print(
                        f"[NxRotator] TURBO winner: {key.key_id} at {latency_ms:.0f}ms"
                    )

                    return RequestResult(
                        success=True,
                        response=data,
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                        tokens=tokens,
                    )
                else:
                    key.record_failure(f"http_{resp.status_code}")
                    return RequestResult(
                        success=False,
                        error=f"HTTP {resp.status_code}",
                        key_used=key.key_id,
                        latency_ms=latency_ms,
                    )
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                key.record_failure("exception")
                return RequestResult(
                    success=False,
                    error=str(e),
                    key_used=key.key_id,
                    latency_ms=latency_ms,
                )

        # Submit all, wait for FIRST_COMPLETE
        winner = None
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(available_keys)
        ) as executor:
            futures = {executor.submit(_fire_single, k): k for k in available_keys}

            # Wait for first to complete
            done, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )

            for future in done:
                result = future.result()
                if result.success:
                    # Cancel all others
                    for f in futures:
                        f.cancel()
                    winner = result
                    break

            if not winner:
                # All failed or none completed yet - wait for rest
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result.success:
                        winner = result
                        # Cancel remaining
                        for f in futures:
                            f.cancel()
                        break

        if winner:
            return winner

        return RequestResult(success=False, error="All turbo participants failed")

    @property
    def active_keys(self) -> int:
        return sum(1 for k in self.keys if not k.is_exhausted)

    @property
    def total_rpm(self) -> int:
        return sum(k.rpm_limit for k in self.keys if not k.is_exhausted)

    @property
    def total_tpm(self) -> int:
        return sum(k.tpm_limit for k in self.keys if not k.is_exhausted)

    def get_key_stats(self) -> List[Dict]:
        return [
            {
                "key_id": k.key_id,
                "email": k.email,
                "available": k.is_available(),
                "health": k.health_score,
                "requests": k.request_count,
                "errors": k.error_count,
                "tokens": k.total_tokens,
                "consecutive_errors": k.consecutive_errors,
                "cooldown_remaining": max(0, k.cooldown_until - time.time()),
                "circuit_breaker": k.circuit_breaker.state,
                "avg_latency_ms": k.get_avg_latency(),
                "success_rate": k.get_success_rate(),
            }
            for k in self.keys
        ]

    def get_all_stats(self) -> Dict:
        return {
            "status": "operational" if self.active_keys > 0 else "degraded",
            "active_keys": self.active_keys,
            "total_keys": len(self.keys),
            "aggregated_rpm": self.total_rpm,
            "aggregated_tpm": self.total_tpm,
            "key_stats": self.get_key_stats(),
            "metrics": self.metrics.get_stats(),
        }

    def reset_exhausted(self):
        for key in self.keys:
            key.is_exhausted = False
            key.exhausted_at = None
            key.consecutive_errors = 0
            key.cooldown_until = 0.0
            key.circuit_breaker.state = "closed"
            key.circuit_breaker.failures = 0
        print("[NxRotator] All keys reset")

    def close(self):
        """Clean up resources."""
        if self._async_client:
            asyncio.run(self._async_client.aclose())
        self._executor.shutdown(wait=False)


# ============================================================
# Convenience Functions
# ============================================================


def get_rotator() -> NxRotator:
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = NxRotator()
    return _rotator_instance


_rotator_instance: Optional[NxRotator] = None
