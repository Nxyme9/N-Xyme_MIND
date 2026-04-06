#!/usr/bin/env python3
"""
Intelligent Router MCP - Self-healing, self-optimizing LLM routing.

Single-module package that provides:
- Model selection based on task complexity
- VPN/SOCKS5 proxy rotation
- Learning from past routing decisions
- MCP protocol interface for OpenCode

Usage:
    python3 -m intelligent_router_mcp  # Start MCP server
    from intelligent_router_mcp import Router  # Use as library
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import threading
import hashlib
import random
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import new intelligence modules
from packages.intelligence.circuit_breaker import get_circuit_breaker_registry
from packages.intelligence.fallback import get_fallback_chain, FallbackChain

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model capability matrix (pre-computed benchmarks)
MODEL_CAPABILITIES = {
    "qwen3.6-plus-free": {
        "reasoning": 0.95,
        "coding": 0.92,
        "creative": 0.88,
        "math": 0.90,
        "analysis": 0.93,
        "summarization": 0.90,
        "context_window": 1000000,
    },
    "qwen3.6-plus": {
        "reasoning": 0.95,
        "coding": 0.92,
        "creative": 0.88,
        "math": 0.90,
        "analysis": 0.93,
        "summarization": 0.90,
        "context_window": 131072,
    },
    "qwen3-coder": {
        "reasoning": 0.85,
        "coding": 0.97,
        "creative": 0.75,
        "math": 0.80,
        "analysis": 0.82,
        "summarization": 0.78,
        "context_window": 131072,
    },
    "deepseek-r1": {
        "reasoning": 0.93,
        "coding": 0.88,
        "creative": 0.82,
        "math": 0.91,
        "analysis": 0.90,
        "summarization": 0.85,
        "context_window": 131072,
    },
    "minimax-m2.5": {
        "reasoning": 0.72,
        "coding": 0.70,
        "creative": 0.78,
        "math": 0.70,
        "analysis": 0.75,
        "summarization": 0.80,
        "context_window": 32768,
    },
    "gemini-2.5-flash": {
        "reasoning": 0.82,
        "coding": 0.78,
        "creative": 0.85,
        "math": 0.80,
        "analysis": 0.85,
        "summarization": 0.88,
        "context_window": 1048576,
    },
}

# Keyword-based category detection
CATEGORY_KEYWORDS = {
    "coding": [
        "code",
        "function",
        "class",
        "def ",
        "async ",
        "implement",
        "debug",
        "fix bug",
        "refactor",
        "api",
        "endpoint",
        "database",
        "sql",
        "test",
        "bug",
        "error",
    ],
    "reasoning": [
        "why",
        "how does",
        "explain",
        "analyze",
        "compare",
        "evaluate",
        "architecture",
        "design",
        "logic",
        "implications",
    ],
    "creative": [
        "write",
        "story",
        "poem",
        "creative",
        "imagine",
        "generate",
        "compose",
        "draft",
        "narrative",
    ],
    "math": [
        "calculate",
        "equation",
        "formula",
        "math",
        "solve",
        "integral",
        "derivative",
        "probability",
    ],
    "summarization": [
        "summarize",
        "summary",
        "brief",
        "tl;dr",
        "key points",
        "overview",
        "condense",
    ],
    "analysis": [
        "analyze",
        "review",
        "critique",
        "evaluate",
        "assess",
        "audit",
        "security",
        "vulnerability",
    ],
}

# Default SOCKS5 proxies
DEFAULT_PROXIES = [
    {"host": "127.0.0.1", "port": 1080, "name": "socks5-1080"},
    {"host": "127.0.0.1", "port": 1081, "name": "socks5-1081"},
    {"host": "127.0.0.1", "port": 1082, "name": "socks5-1082"},
    {"host": "127.0.0.1", "port": 1083, "name": "socks5-1083"},
    {"host": "127.0.0.1", "port": 1084, "name": "socks5-1084"},
    {"host": "127.0.0.1", "port": 1085, "name": "socks5-1085"},
    {"host": "127.0.0.1", "port": 1086, "name": "socks5-1086"},
    {"host": "127.0.0.1", "port": 1087, "name": "socks5-1087"},
]


# ============================================================================
# VPN IP POOL
# ============================================================================


class VPNIP:
    """Represents a single VPN exit IP (SOCKS5 proxy)."""

    def __init__(self, host: str, port: int, name: str = ""):
        self.host = host
        self.port = port
        self.name = name or f"{host}:{port}"
        self.health_score = 1.0
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.avg_latency_ms = 0.0
        self.is_banned = False
        self.ban_until = 0.0

    def is_available(self) -> bool:
        now = time.time()
        if self.is_banned and now < self.ban_until:
            return False
        if now < self.cooldown_until:
            return False
        return True

    def record_success(self, latency_ms: float) -> None:
        self.total_successes += 1
        self.total_requests += 1
        self.consecutive_failures = 0
        alpha = 0.2
        self.avg_latency_ms = alpha * latency_ms + (1 - alpha) * self.avg_latency_ms
        self.health_score = min(1.0, self.health_score + 0.05)

    def record_failure(self) -> None:
        self.total_failures += 1
        self.total_requests += 1
        self.consecutive_failures += 1
        self.health_score = max(0.0, self.health_score - 0.1)
        if self.consecutive_failures >= 3:
            self.cooldown_until = time.time() + 30


class VPNIPPool:
    """Manages VPN IP health and rotation."""

    def __init__(self, proxies: List[Dict] = None):
        self.ips: List[VPNIP] = []
        self._lock = threading.Lock()
        self._index = 0
        for p in proxies or DEFAULT_PROXIES:
            self.ips.append(VPNIP(p["host"], p["port"], p.get("name", "")))

    def get_best_ip(self) -> Optional[VPNIP]:
        """Get next available IP, skipping unhealthy ones."""
        with self._lock:
            available = [ip for ip in self.ips if ip.is_available()]
            if not available:
                return self.ips[self._index % len(self.ips)]
            # Round-robin through available IPs
            ip = available[self._index % len(available)]
            self._index += 1
            return ip

    def get_status(self) -> dict:
        return {
            "total_ips": len(self.ips),
            "available_ips": sum(1 for ip in self.ips if ip.is_available()),
            "ips": [
                {
                    "name": ip.name,
                    "host": ip.host,
                    "port": ip.port,
                    "health_score": ip.health_score,
                    "is_available": ip.is_available(),
                    "is_banned": ip.is_banned,
                    "avg_latency_ms": ip.avg_latency_ms,
                    "consecutive_failures": ip.consecutive_failures,
                }
                for ip in self.ips
            ],
        }


# ============================================================================
# ROUTER BRAIN
# ============================================================================


class RouterBrain:
    """Analyzes requests and selects optimal model using keyword matching."""

    def __init__(self):
        self._cache: Dict[int, dict] = {}
        self._lock = threading.Lock()

    def _detect_categories(self, prompt: str) -> List[str]:
        """Detect categories from prompt keywords."""
        prompt_lower = prompt.lower()
        categories = []
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                categories.append(cat)
        return categories or ["general"]

    def _estimate_complexity(self, prompt: str, categories: List[str]) -> str:
        """Estimate task complexity from prompt length and type."""
        length = len(prompt.split())
        if any(c in categories for c in ["analysis", "reasoning"]):
            return "complex" if length > 100 else "medium"
        if any(c in categories for c in ["coding"]):
            if "implement" in prompt.lower() or "create" in prompt.lower():
                return "medium" if length > 50 else "simple"
        return "simple" if length < 30 else "medium"

    def _score_model(self, model: str, categories: List[str], complexity: str) -> float:
        """Score a model for the given task categories."""
        caps = MODEL_CAPABILITIES.get(model, {})
        if not caps:
            return 0.0

        # Weight based on detected categories
        weights = {
            "coding": 0.3,
            "reasoning": 0.25,
            "creative": 0.15,
            "math": 0.1,
            "analysis": 0.15,
            "summarization": 0.05,
        }

        score = 0.0
        for cat in categories:
            score += caps.get(cat, 0.5) * weights.get(cat, 0.1)

        # Boost for complexity match
        if complexity == "complex" and caps.get("reasoning", 0) > 0.9:
            score *= 1.2
        elif complexity == "simple" and caps.get("coding", 0) > 0.9:
            score *= 1.1

        return min(1.0, score)

    def analyze_request(
        self, prompt: str, system_prompt: str = "", agent_type: str = ""
    ) -> dict:
        """Analyze request and return routing decision with best model."""
        cache_key = hash(f"{prompt[:200]}:{agent_type}")
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key].copy()

        # Detect categories and complexity
        categories = self._detect_categories(prompt)
        complexity = self._estimate_complexity(prompt, categories)

        # Score all models
        model_scores = {}
        for model in MODEL_CAPABILITIES:
            model_scores[model] = self._score_model(model, categories, complexity)

        # Select best model
        best_model = max(model_scores, key=model_scores.get)
        best_score = model_scores[best_model]

        result = {
            "categories": categories,
            "complexity": complexity,
            "required_capabilities": {
                cat: MODEL_CAPABILITIES.get(best_model, {}).get(cat, 0.5)
                for cat in [
                    "reasoning",
                    "coding",
                    "creative",
                    "math",
                    "analysis",
                    "summarization",
                ]
            },
            "best_model": best_model,
            "best_score": round(best_score, 3),
            "model_scores": {k: round(v, 3) for k, v in model_scores.items()},
            "analysis_time_ms": 0.0,
        }

        with self._lock:
            self._cache[cache_key] = result
        return result


# ============================================================================
# LEARNING ENGINE
# ============================================================================


class LearningEngine:
    """Stores routing outcomes, improves routing over time."""

    def __init__(self, db_path: str = "data/intelligent_router/routing_outcomes.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        # Model performance cache (updated on record)
        self._model_performance: Dict[str, dict] = {}
        self._cache_loaded = False

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for better concurrent write handling
        conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout to wait up to 5 seconds instead of failing immediately
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, prompt_hash INTEGER,
            categories TEXT, complexity TEXT, selected_model TEXT, selected_provider TEXT,
            selected_ip TEXT, latency_ms REAL, success INTEGER)""")
        # Enhanced: model performance table
        conn.execute("""CREATE TABLE IF NOT EXISTS model_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT UNIQUE,
            total_requests INTEGER, success_count INTEGER, failure_count INTEGER,
            avg_latency_ms REAL, last_updated REAL)""")
        conn.commit()
        conn.close()

    def _ensure_cache_loaded(self):
        """Lazy load performance cache."""
        if self._cache_loaded:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT model, total_requests, success_count, failure_count, avg_latency_ms FROM model_performance"
        )
        for row in cursor:
            total = row[1] + row[2]
            self._model_performance[row[0]] = {
                "total_requests": row[1] + row[2],
                "success_count": row[1],
                "failure_count": row[2],
                "success_rate": row[1] / total if total > 0 else 0,
                "avg_latency_ms": row[4] or 0,
            }
        conn.close()
        self._cache_loaded = True

    def record_outcome(
        self,
        prompt_hash: int,
        categories: str,
        complexity: str,
        model: str,
        provider: str,
        ip: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.execute(
                "INSERT INTO outcomes VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                (
                    time.time(),
                    prompt_hash,
                    categories,
                    complexity,
                    model,
                    provider,
                    ip,
                    latency_ms,
                    int(success),
                ),
            )

            # Update model performance (upsert)
            if success:
                conn.execute(
                    """INSERT INTO model_performance (model, total_requests, success_count, failure_count, avg_latency_ms, last_updated)
                    VALUES (?, 1, 1, 0, ?, ?) ON CONFLICT(model) DO UPDATE SET
                    total_requests = total_requests + 1,
                    success_count = success_count + 1,
                    avg_latency_ms = (avg_latency_ms * total_requests + ?) / (total_requests + 1),
                    last_updated = ?""",
                    (model, latency_ms, time.time(), latency_ms, time.time()),
                )
            else:
                conn.execute(
                    """INSERT INTO model_performance (model, total_requests, success_count, failure_count, avg_latency_ms, last_updated)
                    VALUES (?, 1, 0, 1, ?, ?) ON CONFLICT(model) DO UPDATE SET
                    total_requests = total_requests + 1,
                    failure_count = failure_count + 1,
                    last_updated = ?""",
                    (model, latency_ms, time.time(), time.time()),
                )

            conn.commit()
        finally:
            conn.close()

        # Invalidate cache on update
        self._cache_loaded = False

    def get_model_performance(self, model: str) -> dict:
        """Get performance stats for a specific model."""
        self._ensure_cache_loaded()
        return self._model_performance.get(
            model,
            {
                "total_requests": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0,
                "avg_latency_ms": 0,
            },
        )

    def get_all_model_performance(self) -> dict:
        """Get performance for all models."""
        self._ensure_cache_loaded()
        return self._model_performance.copy()

    def get_best_model_for(self, categories: str, complexity: str) -> Optional[str]:
        """Get best performing model from past outcomes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """SELECT selected_model, COUNT(*) as cnt, 
            SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_cnt
            FROM outcomes WHERE categories=? AND complexity=? 
            GROUP BY selected_model ORDER BY success_cnt DESC, cnt DESC LIMIT 1""",
            (categories, complexity),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE success=1"
        ).fetchone()[0]
        avg_latency = (
            conn.execute("SELECT AVG(latency_ms) FROM outcomes").fetchone()[0] or 0
        )
        models = conn.execute(
            "SELECT COUNT(DISTINCT selected_model) FROM outcomes"
        ).fetchone()[0]
        conn.close()
        return {
            "total_requests": total,
            "success_rate": success / total if total else 0,
            "avg_latency_ms": round(avg_latency, 1),
            "models_tracked": models,
        }

    def optimize_weights(self) -> dict:
        """Recalculate model weights using capability-based differentiation.

        Produces clear differentiation between models by:
        1. Using model's MAX capability (strongest skill) as base weight
        2. Applying performance multiplier (1.2 for >70% success, 0.7 for <50%)
        3. Applying latency penalty (more aggressive)
        4. Applying sample confidence (needs 100+ samples for full weight)
        5. Normalizing weights to sum to 1.0

        Expected ranges:
        - qwen3-coder (coding=0.97, fast=479ms) → ~0.25-0.30
        - qwen3.6-plus (reasoning=0.95, fast=519ms) → ~0.22-0.27
        - deepseek-r1 (math=0.91, medium=551ms) → ~0.18-0.22
        - gemini-2.5-flash (creative=0.85, medium=632ms) → ~0.15-0.18
        - minimax-m2.5 (coding=0.70, slow=701ms) → ~0.10-0.13
        """
        self._ensure_cache_loaded()

        if not self._model_performance:
            return {"status": "no_data", "weights": {}}

        raw_weights = {}

        for model, perf in self._model_performance.items():
            # 1. Get model's MAX capability (its strongest skill)
            caps = MODEL_CAPABILITIES.get(model, {})
            if caps:
                max_capability = max(
                    caps.get(cat, 0)
                    for cat in [
                        "coding",
                        "reasoning",
                        "creative",
                        "math",
                        "analysis",
                        "summarization",
                    ]
                )
            else:
                max_capability = 0.5

            # 2. Apply performance multiplier
            success_rate = perf.get("success_rate", 0.5)
            total_requests = perf.get("total_requests", 0)
            avg_latency_ms = perf.get("avg_latency_ms", 500)

            if success_rate > 0.7:
                perf_multiplier = 1.2
            elif success_rate < 0.5:
                perf_multiplier = 0.7
            else:
                perf_multiplier = 1.0

            # 3. Apply latency penalty (more aggressive: /500)
            latency_factor = 1 / (1 + avg_latency_ms / 500)

            # 4. Apply sample confidence (needs 100+ samples for full weight)
            confidence = min(1.0, total_requests / 100)

            # 5. Calculate final weight
            weight = max_capability * perf_multiplier * latency_factor * confidence
            raw_weights[model] = weight

        # 6. Normalize weights to sum to 1.0
        total_weight = sum(raw_weights.values())
        if total_weight > 0:
            weights = {k: round(v / total_weight, 4) for k, v in raw_weights.items()}
        else:
            # Fallback: equal weights if no performance data
            num_models = len(raw_weights) if raw_weights else 1
            weights = {k: round(1.0 / num_models, 4) for k in raw_weights}

        return {
            "status": "optimized",
            "weights": weights,
            "raw_weights": {k: round(v, 4) for k, v in raw_weights.items()},
            "models": list(weights.keys()),
            "method": "capability_based_with_performance",
        }


class TrainingSimulator:
    """Generates synthetic training data for the learning engine."""

    def __init__(self, learning: LearningEngine):
        self.learning = learning
        # Sample prompts for different categories
        self._sample_prompts = {
            "coding": [
                "implement a function to sort a list",
                "fix the bug in the API endpoint",
                "write a test for the authentication module",
                "refactor the data processing pipeline",
                "add error handling to the service",
            ],
            "reasoning": [
                "analyze why the system is slow",
                "compare these two approaches",
                "evaluate the security implications",
                "explain the architecture decision",
                "what are the tradeoffs here",
            ],
            "creative": [
                "write a story about AI",
                "compose a poem about coding",
                "generate a creative description",
                "draft an introduction",
                "create a narrative about the future",
            ],
            "analysis": [
                "review the code for security issues",
                "audit the authentication flow",
                "assess the performance bottlenecks",
                "analyze the data patterns",
                "evaluate the test coverage",
            ],
        }

    def generate_training_data(self, num_samples: int = 100) -> dict:
        """Generate synthetic training data that reflects actual model capabilities."""
        import random

        models = list(MODEL_CAPABILITIES.keys())
        results = []

        # Success rate targets per model/category from MODEL_CAPABILITIES * 0.8
        # Formula: base_success = MODEL_CAPABILITIES[model][category] * 0.8 + random.uniform(-0.1, 0.1)
        # Expected results:
        # - qwen3-coder coding: 0.97 * 0.8 = 77.6% (target: 75-85%)
        # - qwen3.6-plus reasoning: 0.95 * 0.8 = 76% (target: 70-80%)
        # - minimax-m2.5 overall: ~59% (target: 55-65%)
        # - gemini-2.5-flash creative: 0.85 * 0.8 = 68% (target: 65-75%)
        # - deepseek-r1 math/reasoning: 0.93 * 0.8 = 74.4% (target: 70-80%)

        for i in range(num_samples):
            category = random.choice(list(self._sample_prompts.keys()))
            prompt = random.choice(self._sample_prompts[category])
            model = random.choice(models)

            # Get capability-based success rate using the formula from task
            caps = MODEL_CAPABILITIES.get(model, {})
            base_capability = caps.get(category, 0.7)

            # Apply the formula: capability * 0.8 + variance
            # This ensures different models have meaningfully different success rates
            base_success = base_capability * 0.8 + random.uniform(-0.1, 0.1)

            # Clamp to realistic bounds
            base_success = max(0.1, min(0.95, base_success))

            success = random.random() < base_success

            # Simulate latency based on model (faster models get lower latency)
            # Higher capability = faster on average
            base_latency = 400 + (1 - base_capability) * 800
            latency = base_latency + random.uniform(-100, 200)

            self.learning.record_outcome(
                prompt_hash=hash(prompt[:50]),
                categories=category,
                complexity=random.choice(["simple", "medium", "complex"]),
                model=model,
                provider="opencode",
                ip=f"127.0.0.1:{random.randint(1080, 1087)}",
                latency_ms=latency,
                success=success,
            )
            results.append(
                {
                    "prompt": prompt,
                    "model": model,
                    "category": category,
                    "success": success,
                    "latency": latency,
                    "success_prob": round(base_success, 3),
                }
            )

        return {
            "samples_generated": num_samples,
            "results": results[-5:],  # Last 5 for display
        }

    def run_training_cycle(self, samples: int = 50) -> dict:
        """Generate data and optimize weights."""
        gen_result = self.generate_training_data(samples)
        opt_result = self.learning.optimize_weights()
        return {
            "generated": gen_result["samples_generated"],
            "optimization": opt_result,
        }


# ============================================================================
# AGENT PREFERENCES
# ============================================================================


class AgentPreferences:
    """Per-agent model preferences."""

    DEFAULT_PREFS = {
        "sisyphus": {"preferred": ["mimo-v2-pro", "minimax-m2.5"], "avoid": []},
        "prometheus": {"preferred": ["mimo-v2-pro", "minimax-m2.5"], "avoid": []},
        "oracle": {"preferred": ["mimo-v2-pro", "minimax-m2.5"], "avoid": []},
        "hephaestus": {"preferred": ["mimo-v2-pro", "minimax-m2.5"], "avoid": []},
        "explore": {"preferred": ["minimax-m2.5", "mimo-v2-pro"], "avoid": []},
        "librarian": {"preferred": ["minimax-m2.5", "mimo-v2-pro"], "avoid": []},
    }

    def __init__(self):
        self._prefs = self.DEFAULT_PREFS.copy()

    def get_preferred_models(self, agent_type: str, session_id: str = "") -> List[str]:
        return self._prefs.get(agent_type, {}).get("preferred", [])

    def get_avoided_models(self, agent_type: str) -> List[str]:
        return self._prefs.get(agent_type, {}).get("avoid", [])


# ============================================================================
# MAIN ROUTER
# ============================================================================


class Router:
    """Self-healing, self-optimizing LLM router."""

    def __init__(self, proxies: List[Dict] = None):
        self.ip_pool = VPNIPPool(proxies)
        self.brain = RouterBrain()
        self.learning = LearningEngine()
        self.prefs = AgentPreferences()
        self._request_count = 0
        # Performance-based model weights (updated on optimization)
        self._model_weights: Dict[str, float] = {}
        self._category_weights: Dict[str, Dict[str, float]] = {}
        # Resilience components
        self._rate_predictor = RateLimitPredictor()
        self._retry_manager = RetryManager()
        self._circuit_breaker = CircuitBreaker()
        self._request_queue = RequestQueue()
        # New: Intelligence module circuit breaker for model health
        self._model_circuit_breaker = get_circuit_breaker_registry(
            "configs/model_router.json"
        )
        self._fallback_chain = get_fallback_chain(
            "default", "configs/model_router.json"
        )
        # Connect rate predictor to token tunnel limits
        self._request_queue.set_dispatch_callback(self._on_dispatch_request)

    def _on_dispatch_request(self, request: dict) -> None:
        """Callback when request is dispatched from queue."""
        # This is called by RequestQueue when a request can proceed
        pass

    def get_resilience_status(self) -> dict:
        """Get combined resilience status from all components."""
        rate_status = self._rate_predictor.get_usage_status()
        circuit_states = self._circuit_breaker.get_all_states()
        queue_depth = self._request_queue.get_queue_depth()
        retry_stats = self._retry_manager.get_stats()

        return {
            "rate_limit": rate_status,
            "circuit_breaker": {
                "total_proxies": len(circuit_states),
                "closed": sum(
                    1 for s in circuit_states.values() if s["state"] == "closed"
                ),
                "open": sum(1 for s in circuit_states.values() if s["state"] == "open"),
                "half_open": sum(
                    1 for s in circuit_states.values() if s["state"] == "half_open"
                ),
                "proxies": circuit_states,
            },
            "request_queue": queue_depth,
            "retry_manager": retry_stats,
        }

    def select_route(
        self,
        prompt: str,
        system_prompt: str = "",
        agent_type: str = "",
        session_id: str = "",
    ) -> dict:
        """Select optimal route for a request."""
        start = time.time()
        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        # 0. Check RateLimitPredictor before routing
        rate_status = self._rate_predictor.get_usage_status()
        if rate_status["warning_level"] in ("critical", "exceeded"):
            # Rate limited - enqueue request instead of failing
            queue_id = self._request_queue.enqueue(
                prompt,
                {
                    "system_prompt": system_prompt,
                    "agent_type": agent_type,
                    "session_id": session_id,
                },
                priority=RequestQueue.PRIORITY_HIGH
                if rate_status["warning_level"] == "critical"
                else RequestQueue.PRIORITY_NORMAL,
            )
            return {
                "model": None,
                "selection_reason": "rate_limited_queued",
                "provider": None,
                "vpn_ip": None,
                "analysis": None,
                "selection_time_ms": round((time.time() - start) * 1000, 1),
                "agent_type": agent_type,
                "session_id": session_id,
                "queue_id": queue_id,
                "rate_warning": rate_status["warning_level"],
            }

        # ============================================================
        # STEP 0: CHECK AGENT CONFIG PREFERENCE (Hybrid Approach)
        # Respect opencode.json router_override.prefer as primary
        # ============================================================
        config_preferred_model = None
        config_fallback_order = []

        # Load config preferences for this agent
        config_path = Path("opencode.json")
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    agent_config = config.get("agent", {}).get(agent_type, {})
                    router_override = agent_config.get("router_override", {})
                    config_preferred_model = router_override.get("prefer")
                    config_fallback_order = router_override.get("fallback_order", [])
            except Exception:
                pass  # Ignore config read errors

        # Check if preferred model is available (circuit breaker OK)
        selected_model = None
        selection_reason = ""

        if config_preferred_model:
            # Map config model name to internal model key
            # Config: "opencode/qwen3.6-plus-free" → Internal: "qwen3.6-plus-free"
            model_key = config_preferred_model.replace("opencode/", "").replace(
                "openrouter/", ""
            )

            if self._model_circuit_breaker.can_execute(model_key):
                selected_model = config_preferred_model  # Keep full name for API call
                selection_reason = "config_prefer"
                print(
                    f"[Router] Using config preference: {config_preferred_model} (key: {model_key})",
                    file=sys.stderr,
                )
            else:
                # Config set but circuit breaker is open - log and fall through to brain
                print(
                    f"[Router] Config preference {config_preferred_model} circuit open, using brain",
                    file=sys.stderr,
                )

        # If preferred model failed or not set, proceed with normal flow
        if not selected_model:
            # 1. Analyze request with router brain
            analysis = self.brain.analyze_request(prompt, system_prompt, agent_type)

            # 2. Select best model from brain analysis
            selected_model = analysis.get("best_model")
            selection_reason = "brain"
        else:
            # Config preference was used - create minimal analysis for other parts
            analysis = {"categories": [], "complexity": "unknown", "model_scores": {}}

        # REMOVED DUPLICATE CODE: Lines 921-923 were overwriting config preference
        # The code below now correctly falls through from config preference path

        ip = None
        for candidate_ip in self.ip_pool.ips:
            proxy_key = f"{candidate_ip.host}:{candidate_ip.port}"
            if candidate_ip.is_available() and self._circuit_breaker.can_execute(
                proxy_key
            ):
                ip = candidate_ip
                break
        if ip is None:
            ip = self.ip_pool.get_best_ip()

        # Initialize these here to avoid "possibly unbound" errors
        preferred = []
        avoided = []

        # 3. Only run brain/learning model selection if NOT using config preference
        # Skip this block if we already selected from config in STEP 0
        if selection_reason != "config_prefer":
            # 3. Select best model: BRAIN FIRST, then learning, then preferences as fallbacks
            selected_model = analysis.get("best_model")
            selection_reason = "brain"

            # Get agent preferences
            preferred = self.prefs.get_preferred_models(agent_type, session_id)
            avoided = self.prefs.get_avoided_models(agent_type)

            # NEW: Check circuit breaker for model selection - skip models with OPEN breakers
            if selected_model and not self._model_circuit_breaker.can_execute(
                selected_model
            ):
                # Model has open circuit breaker - use fallback chain
                fallback_status = self._fallback_chain.get_status()
                available_models = fallback_status.get("available_models", [])
                if available_models:
                    # Use first available model from fallback chain
                    selected_model = available_models[0]
                    selection_reason = "circuit_breaker_fallback"
                else:
                    # All models have open breakers - proceed with default but note the issue
                    selected_model = "minimax-m2.5"
                    selection_reason = "circuit_breaker_all_open"

        # Fallback 1: Learning engine performance-based selection
        if self._model_weights:
            # Use optimized weights if available
            best_weighted_model = None
            best_weight = -1
            for model, base_score in analysis.get("model_scores", {}).items():
                if model in avoided:
                    continue
                weight = self._model_weights.get(model, 0.5)
                adjusted_score = base_score * (
                    0.3 + 0.7 * weight
                )  # Blend brain score with learned weight
                if adjusted_score > best_weight:
                    best_weight = adjusted_score
                    best_weighted_model = model
            if best_weighted_model:
                selected_model = best_weighted_model
                selection_reason = "performance"

        # Fallback 2: Historical best model
        if not selected_model:
            learned_model = self.learning.get_best_model_for(
                ",".join(analysis["categories"]), analysis["complexity"]
            )
            if learned_model and learned_model not in avoided:
                selected_model = learned_model
                selection_reason = "learning"

        # Fallback 3: Agent preferences
        if not selected_model and preferred:
            for model, score in sorted(
                analysis.get("model_scores", {}).items(), key=lambda x: -x[1]
            ):
                if model in preferred and model not in avoided:
                    selected_model = model
                    selection_reason = "preferences"
                    break

        # Final safety
        if not selected_model:
            selected_model = "minimax-m2.5"
            selection_reason = "default"

        self._request_count += 1

        return {
            "model": selected_model,
            "selection_reason": selection_reason,
            "provider": "opencode",
            "vpn_ip": f"{ip.host}:{ip.port}" if ip else None,
            "analysis": analysis,
            "selection_time_ms": round((time.time() - start) * 1000, 1),
            "agent_type": agent_type,
            "session_id": session_id,
        }

    def optimize(self) -> dict:
        """Run optimization to update model weights."""
        result = self.learning.optimize_weights()
        if result.get("weights"):
            self._model_weights = result["weights"]
        return result

    def record_success(
        self,
        route: dict,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0,
    ) -> None:
        """Record successful request."""
        prompt_hash = hash(route.get("session_id", ""))
        self.learning.record_outcome(
            prompt_hash,
            ",".join(route.get("analysis", {}).get("categories", [])),
            route.get("analysis", {}).get("complexity", "unknown"),
            route.get("model", ""),
            route.get("provider", ""),
            route.get("vpn_ip", ""),
            latency_ms,
            True,
        )
        # Update VPN health
        vpn_ip = route.get("vpn_ip", "")
        if vpn_ip:
            for ip in self.ip_pool.ips:
                if f"{ip.host}:{ip.port}" == vpn_ip:
                    ip.record_success(latency_ms)
                    break
        # NEW: Record success in model circuit breaker
        model = route.get("model", "")
        if model:
            self._model_circuit_breaker.record_success(model)

    def record_failure(
        self, route: dict, error_type: str = "", latency_ms: float = 0
    ) -> None:
        """Record failed request."""
        vpn_ip = route.get("vpn_ip", "")
        if vpn_ip:
            for ip in self.ip_pool.ips:
                if f"{ip.host}:{ip.port}" == vpn_ip:
                    ip.record_failure()
                    break
        # NEW: Record failure in model circuit breaker
        model = route.get("model", "")
        if model:
            self._model_circuit_breaker.record_failure(model)

    def get_status(self) -> dict:
        return {
            "total_requests": self._request_count,
            "vpn_ips": self.ip_pool.get_status(),
            "learning": self.learning.get_stats(),
            "agent_preferences": {
                k: v["preferred"] for k, v in self.prefs._prefs.items()
            },
        }


# ============================================================================
# SESSION MANAGER (Per-Session IP Binding)
# ============================================================================


class SessionManager:
    """Binds dedicated VPN IP to each OpenCode session."""

    def __init__(self, ip_pool: VPNIPPool):
        self.ip_pool = ip_pool
        self._sessions: Dict[str, dict] = {}  # session_id -> session data
        self._lock = threading.Lock()

    def create_session(self, session_id: str) -> dict:
        """Create a new session with dedicated IP."""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            # Get dedicated IP for this session
            ip = self.ip_pool.get_best_ip()
            if not ip:
                return {"error": "No available IPs"}

            session = {
                "session_id": session_id,
                "ip_host": ip.host,
                "ip_port": ip.port,
                "ip_name": ip.name,
                "created_at": time.time(),
                "request_count": 0,
                "token_count": 0,
                "last_activity": time.time(),
                "status": "active",
            }
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session info."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_session_status(self, session_id: str) -> dict:
        """Get detailed session status."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found", "session_id": session_id}

        # Get IP health from pool
        ip_health = None
        for ip in self.ip_pool.ips:
            if ip.host == session["ip_host"] and ip.port == session["ip_port"]:
                ip_health = {
                    "health_score": ip.health_score,
                    "is_available": ip.is_available(),
                    "consecutive_failures": ip.consecutive_failures,
                    "avg_latency_ms": ip.avg_latency_ms,
                }
                break

        return {
            "session_id": session_id,
            "ip": f"{session['ip_host']}:{session['ip_port']}",
            "ip_name": session["ip_name"],
            "created_at": session["created_at"],
            "request_count": session["request_count"],
            "token_count": session["token_count"],
            "last_activity": session["last_activity"],
            "status": session["status"],
            "ip_health": ip_health,
        }

    def record_request(self, session_id: str, tokens: int = 0) -> None:
        """Record activity in session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["request_count"] += 1
                self._sessions[session_id]["token_count"] += tokens
                self._sessions[session_id]["last_activity"] = time.time()

    def release_session_ip(self, session_id: str) -> dict:
        """Release session's IP back to pool."""
        with self._lock:
            if session_id not in self._sessions:
                return {"error": "Session not found", "session_id": session_id}

            session = self._sessions[session_id]
            session["status"] = "released"
            session["released_at"] = time.time()

            return {
                "session_id": session_id,
                "released_ip": f"{session['ip_host']}:{session['ip_port']}",
                "released_at": session["released_at"],
            }

    def get_all_sessions(self) -> List[dict]:
        """Get all sessions."""
        with self._lock:
            return list(self._sessions.values())

    def cleanup_inactive(self, max_age_seconds: int = 3600) -> int:
        """Clean up inactive sessions."""
        now = time.time()
        cleaned = 0
        with self._lock:
            to_remove = []
            for sid, sess in self._sessions.items():
                if now - sess.get("last_activity", 0) > max_age_seconds:
                    to_remove.append(sid)
            for sid in to_remove:
                del self._sessions[sid]
                cleaned += 1
        return cleaned


# ============================================================================
# TOKEN TUNNEL (Per-Session Throughput)
# ============================================================================


class TokenTunnel:
    """Per-session throughput channel with rate limiting."""

    def __init__(self, rpm_limit: int = 60000, tpm_limit: int = 1000000):
        self.rpm_limit = rpm_limit  # Requests per minute
        self.tpm_limit = tpm_limit  # Tokens per minute
        self._session_tunnels: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def _get_or_create_tunnel(self, session_id: str) -> dict:
        """Get or create tunnel for session."""
        with self._lock:
            if session_id not in self._session_tunnels:
                self._session_tunnels[session_id] = {
                    "rpm_used": 0,
                    "tpm_used": 0,
                    "window_start": time.time(),
                    "total_requests": 0,
                    "total_tokens": 0,
                }
            return self._session_tunnels[session_id]

    def _reset_window_if_needed(self, tunnel: dict) -> None:
        """Reset minute window if expired."""
        now = time.time()
        if now - tunnel["window_start"] >= 60:
            tunnel["rpm_used"] = 0
            tunnel["tpm_used"] = 0
            tunnel["window_start"] = now

    def can_proceed(self, session_id: str, tokens_needed: int = 0) -> dict:
        """Check if request can proceed under rate limits."""
        tunnel = self._get_or_create_tunnel(session_id)
        self._reset_window_if_needed(tunnel)

        rpm_available = self.rpm_limit - tunnel["rpm_used"]
        tpm_available = self.tpm_limit - tunnel["tpm_used"]

        can_rpm = tunnel["rpm_used"] < self.rpm_limit
        can_tpm = tunnel["tpm_used"] + tokens_needed <= self.tpm_limit

        return {
            "session_id": session_id,
            "can_proceed": can_rpm and can_tpm,
            "rpm_remaining": rpm_available,
            "tpm_remaining": tpm_available,
            "rpm_used": tunnel["rpm_used"],
            "tpm_used": tunnel["tpm_used"],
        }

    def record_request(self, session_id: str, tokens: int = 0) -> None:
        """Record request throughput."""
        tunnel = self._get_or_create_tunnel(session_id)
        self._reset_window_if_needed(tunnel)
        tunnel["rpm_used"] += 1
        tunnel["tpm_used"] += tokens
        tunnel["total_requests"] += 1
        tunnel["total_tokens"] += tokens

    def get_tunnel_status(self, session_id: str) -> dict:
        """Get tunnel status for session."""
        tunnel = self._get_or_create_tunnel(session_id)
        self._reset_window_if_needed(tunnel)
        return {
            "session_id": session_id,
            "rpm_limit": self.rpm_limit,
            "tpm_limit": self.tpm_limit,
            "rpm_used": tunnel["rpm_used"],
            "tpm_used": tunnel["tpm_used"],
            "rpm_remaining": self.rpm_limit - tunnel["rpm_used"],
            "tpm_remaining": self.tpm_limit - tunnel["tpm_used"],
            "total_requests": tunnel["total_requests"],
            "total_tokens": tunnel["total_tokens"],
        }


# ============================================================================
# TRAINING LOOP SYSTEM
# ============================================================================


class TriggerPolicy:
    """Decides when to run training cycle."""

    def __init__(
        self,
        trigger_on_count: int = 50,
        trigger_on_time_seconds: int = 3600,
        min_samples_for_training: int = 30,
    ):
        self.trigger_on_count = trigger_on_count
        self.trigger_on_time_seconds = trigger_on_time_seconds
        self.min_samples_for_training = min_samples_for_training
        self._last_trigger_time = time.time()
        self._request_count_since_last = 0

    def should_trigger(self, total_outcomes: int) -> bool:
        now = time.time()
        if self._request_count_since_last >= self.trigger_on_count:
            return True
        if now - self._last_trigger_time >= self.trigger_on_time_seconds:
            return True
        if total_outcomes >= self.min_samples_for_training:
            return True
        return False

    def record_trigger(self) -> None:
        self._last_trigger_time = time.time()
        self._request_count_since_last = 0

    def record_request(self) -> None:
        self._request_count_since_last += 1


class DataCollector:
    """Collects real routing outcomes for training."""

    def __init__(self, learning_engine: LearningEngine):
        self.learning = learning_engine
        self._pending_outcomes: List[dict] = []
        self._lock = threading.Lock()

    def collect_outcome(
        self,
        prompt: str,
        categories: List[str],
        complexity: str,
        selected_model: str,
        vpn_ip: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        with self._lock:
            self._pending_outcomes.append(
                {
                    "timestamp": time.time(),
                    "prompt_hash": hash(prompt[:100]),
                    "categories": ",".join(categories),
                    "complexity": complexity,
                    "model": selected_model,
                    "ip": vpn_ip,
                    "latency_ms": latency_ms,
                    "success": success,
                }
            )

    def flush_to_learning(self) -> int:
        with self._lock:
            count = len(self._pending_outcomes)
            for outcome in self._pending_outcomes:
                self.learning.record_outcome(
                    prompt_hash=outcome["prompt_hash"],
                    categories=outcome["categories"],
                    complexity=outcome["complexity"],
                    model=outcome["model"],
                    provider="opencode",
                    ip=outcome["ip"],
                    latency_ms=outcome["latency_ms"],
                    success=outcome["success"],
                )
            self._pending_outcomes.clear()
            return count

    def get_pending_count(self) -> int:
        with self._lock:
            return len(self._pending_outcomes)


class WeightOptimizer:
    """Optimizes routing weights based on outcomes."""

    def __init__(self, learning_engine: LearningEngine):
        self.learning = learning_engine

    def compute_weights(self) -> Dict[str, float]:
        result = self.learning.optimize_weights()
        return result.get("weights", {})

    def compute_category_weights(self) -> Dict[str, Dict[str, float]]:
        conn = sqlite3.connect(self.learning.db_path)
        weights_by_category = {}
        for category in [
            "coding",
            "reasoning",
            "creative",
            "analysis",
            "math",
            "summarization",
        ]:
            cursor = conn.execute(
                """SELECT selected_model, COUNT(*) as cnt,
                SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_cnt,
                AVG(latency_ms) as avg_latency
                FROM outcomes WHERE categories LIKE ?
                GROUP BY selected_model""",
                (f"%{category}%",),
            )
            category_weights = {}
            total_weight = 0.0
            for row in cursor:
                model, cnt, success_cnt, avg_latency = row
                if cnt < 3:
                    continue
                success_rate = success_cnt / cnt if cnt > 0 else 0
                latency_factor = 1 / (1 + (avg_latency or 0) / 1000)
                weight = success_rate * latency_factor
                category_weights[model] = weight
                total_weight += weight
            if total_weight > 0:
                category_weights = {
                    k: round(v / total_weight, 3) for k, v in category_weights.items()
                }
            weights_by_category[category] = category_weights
        conn.close()
        return weights_by_category


class ShadowEvaluator:
    """Tests new weights in shadow mode before committing."""

    def __init__(self, router: Router, shadow_ratio: float = 0.1):
        self.router = router
        self.shadow_ratio = shadow_ratio
        self._shadow_count = 0
        self._new_weights_history: List[dict] = []
        self._current_weights_history: List[dict] = []

    def should_use_new_weights(self) -> bool:
        import random

        self._shadow_count += 1
        return self._shadow_count % 10 == 0

    def record_shadow_outcome(
        self,
        used_new_weights: bool,
        model_selected: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        outcome = {
            "timestamp": time.time(),
            "model": model_selected,
            "success": success,
            "latency_ms": latency_ms,
        }
        if used_new_weights:
            self._new_weights_history.append(outcome)
            if len(self._new_weights_history) > 50:
                self._new_weights_history = self._new_weights_history[-50:]
        else:
            self._current_weights_history.append(outcome)
            if len(self._current_weights_history) > 50:
                self._current_weights_history = self._current_weights_history[-50:]

    def evaluate_new_weights(self) -> dict:
        if not self._new_weights_history:
            return {"status": "insufficient_data"}
        new_success = sum(1 for o in self._new_weights_history if o["success"]) / len(
            self._new_weights_history
        )
        new_latency = sum(o["latency_ms"] for o in self._new_weights_history) / len(
            self._new_weights_history
        )
        if self._current_weights_history:
            current_success = sum(
                1 for o in self._current_weights_history if o["success"]
            ) / len(self._current_weights_history)
            current_latency = sum(
                o["latency_ms"] for o in self._current_weights_history
            ) / len(self._current_weights_history)
        else:
            stats = self.router.learning.get_stats()
            current_success = stats.get("success_rate", 0.5)
            current_latency = stats.get("avg_latency_ms", 500)
        return {
            "status": "compared",
            "new_weights": {
                "success_rate": round(new_success, 3),
                "avg_latency_ms": round(new_latency, 1),
                "sample_size": len(self._new_weights_history),
            },
            "current_weights": {
                "success_rate": round(current_success, 3),
                "avg_latency_ms": round(current_latency, 1),
                "sample_size": len(self._current_weights_history),
            },
            "improvement": {
                "success_delta": round(new_success - current_success, 3),
                "latency_delta": round(new_latency - current_latency, 1),
            },
        }

    def is_safe_to_commit(self, min_improvement: float = 0.02) -> bool:
        eval_result = self.evaluate_new_weights()
        if eval_result["status"] == "insufficient_data":
            return False
        improvement = eval_result.get("improvement", {})
        success_delta = improvement.get("success_delta", 0)
        return success_delta >= min_improvement


class MetricsDashboard:
    """Exposes training loop metrics."""

    def __init__(
        self,
        trigger_policy: TriggerPolicy,
        data_collector: DataCollector,
        weight_optimizer: WeightOptimizer,
        shadow_evaluator: ShadowEvaluator,
    ):
        self.trigger = trigger_policy
        self.collector = data_collector
        self.optimizer = weight_optimizer
        self.shadow = shadow_evaluator
        self._training_cycles = 0
        self._last_training_time = 0.0

    def get_metrics(self) -> dict:
        learning_stats = self.optimizer.learning.get_stats()
        model_perf = self.optimizer.learning.get_all_model_performance()
        shadow_eval = self.shadow.evaluate_new_weights()
        current_weights = self.optimizer.compute_weights()
        return {
            "training": {
                "total_cycles": self._training_cycles,
                "last_training_time": self._last_training_time,
                "requests_since_last": self.trigger._request_count_since_last,
                "next_trigger_at": max(
                    0,
                    self.trigger.trigger_on_count
                    - self.trigger._request_count_since_last,
                ),
            },
            "data_collection": {
                "pending_outcomes": self.collector.get_pending_count(),
                "total_outcomes": learning_stats.get("total_requests", 0),
            },
            "current_weights": current_weights,
            "model_performance": model_perf,
            "shadow_evaluation": shadow_eval,
            "overall_success_rate": learning_stats.get("success_rate", 0),
            "avg_latency_ms": learning_stats.get("avg_latency_ms", 0),
        }


class TrainingLoop:
    """Main training loop that orchestrates all components."""

    def __init__(
        self,
        router: Router,
        trigger_on_count: int = 50,
        trigger_on_time_seconds: int = 3600,
    ):
        self.router = router
        self.trigger = TriggerPolicy(
            trigger_on_count=trigger_on_count,
            trigger_on_time_seconds=trigger_on_time_seconds,
        )
        self.collector = DataCollector(router.learning)
        self.optimizer = WeightOptimizer(router.learning)
        self.shadow = ShadowEvaluator(router)
        self.dashboard = MetricsDashboard(
            self.trigger, self.collector, self.optimizer, self.shadow
        )
        self._is_running = True
        self._lock = threading.Lock()
        self._last_weights: Dict[str, float] = {}

    def on_request_completed(
        self,
        prompt: str,
        categories: List[str],
        complexity: str,
        selected_model: str,
        vpn_ip: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Call this after each routing decision completes."""
        self.collector.collect_outcome(
            prompt, categories, complexity, selected_model, vpn_ip, latency_ms, success
        )
        self.trigger.record_request()
        # Check if should trigger training
        total_outcomes = self.router.learning.get_stats().get("total_requests", 0)
        if self.trigger.should_trigger(total_outcomes):
            self.run_training_cycle()

    def run_training_cycle(self) -> dict:
        """Run a complete training cycle."""
        with self._lock:
            start_time = time.time()
            # Step 1: Flush pending outcomes to learning engine
            flushed = self.collector.flush_to_learning()
            # Step 2: Compute new weights
            new_weights = self.optimizer.compute_weights()
            category_weights = self.optimizer.compute_category_weights()
            # Step 3: Shadow evaluation
            shadow_eval = self.shadow.evaluate_new_weights()
            is_safe = self.shadow.is_safe_to_commit()
            # Step 4: Decide whether to commit
            should_commit = is_safe and len(new_weights) > 0
            if should_commit:
                self._last_weights = self.router._model_weights.copy()
                self.router._model_weights = new_weights
                self.router._category_weights = category_weights
                commit_status = "committed"
            else:
                commit_status = "rejected"
            self.trigger.record_trigger()
            self.dashboard._training_cycles += 1
            self.dashboard._last_training_time = start_time
            return {
                "status": commit_status,
                "flushed_outcomes": flushed,
                "new_weights": new_weights,
                "category_weights": category_weights,
                "shadow_evaluation": shadow_eval,
                "duration_ms": round((time.time() - start_time) * 1000, 1),
            }

    def get_metrics(self) -> dict:
        """Get dashboard metrics."""
        return self.dashboard.get_metrics()

    def force_training(self) -> dict:
        """Manually trigger training."""
        return self.run_training_cycle()

    def stop(self) -> None:
        """Stop the training loop."""
        self._is_running = False

    def start(self) -> None:
        """Restart the training loop."""
        self._is_running = True


# ============================================================================
# RATE LIMIT PREDICTOR (Sliding Window Rate Limit Anticipation)
# ============================================================================


class RateLimitPredictor:
    """Sliding window rate limit anticipation with warning levels."""

    def __init__(self, token_tunnel: "TokenTunnel" = None):
        self._token_tunnel = token_tunnel
        self._lock = threading.Lock()
        # Sliding window: track requests in 60-second windows
        self._window_seconds = 60
        self._request_timestamps: List[float] = []
        self._token_timestamps: List[tuple] = []  # (timestamp, tokens)
        # Default limits (can be overridden by TokenTunnel)
        self._rpm_limit = 60000
        self._tpm_limit = 1000000

    def set_limits(self, rpm_limit: int, tpm_limit: int) -> None:
        """Set RPM/TPM limits."""
        with self._lock:
            self._rpm_limit = rpm_limit
            self._tpm_limit = tpm_limit

    def set_token_tunnel(self, token_tunnel: "TokenTunnel") -> None:
        """Set TokenTunnel reference for limit synchronization."""
        self._token_tunnel = token_tunnel
        if token_tunnel:
            self.set_limits(token_tunnel.rpm_limit, token_tunnel.tpm_limit)

    def _cleanup_old_timestamps(self, now: float) -> None:
        """Remove timestamps outside the sliding window."""
        cutoff = now - self._window_seconds
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]
        self._token_timestamps = [
            (ts, tokens) for ts, tokens in self._token_timestamps if ts > cutoff
        ]

    def record_request(self, tokens: int = 0) -> None:
        """Record a request for rate tracking."""
        now = time.time()
        with self._lock:
            self._cleanup_old_timestamps(now)
            self._request_timestamps.append(now)
            if tokens > 0:
                self._token_timestamps.append((now, tokens))

    def get_usage_status(self) -> dict:
        """Get current RPM/TPM usage status."""
        now = time.time()
        with self._lock:
            self._cleanup_old_timestamps(now)
            rpm_used = len(self._request_timestamps)
            tpm_used = sum(tokens for _, tokens in self._token_timestamps)

            rpm_pct = (rpm_used / self._rpm_limit) * 100 if self._rpm_limit > 0 else 0
            tpm_pct = (tpm_used / self._tpm_limit) * 100 if self._tpm_limit > 0 else 0

            return {
                "rpm_used": rpm_used,
                "rpm_limit": self._rpm_limit,
                "rpm_remaining": max(0, self._rpm_limit - rpm_used),
                "rpm_percent": round(rpm_pct, 1),
                "tpm_used": tpm_used,
                "tpm_limit": self._tpm_limit,
                "tpm_remaining": max(0, self._tpm_limit - tpm_used),
                "tpm_percent": round(tpm_pct, 1),
                "warning_level": self._get_warning_level(max(rpm_pct, tpm_pct)),
            }

    def _get_warning_level(self, percent: float) -> str:
        """Determine warning level based on usage percentage."""
        if percent > 95:
            return "exceeded"
        elif percent > 80:
            return "critical"
        elif percent > 60:
            return "warning"
        return "safe"

    def predict_time_to_limit(self) -> float:
        """Predict seconds until RPM limit is reached (-1 if safe)."""
        now = time.time()
        with self._lock:
            self._cleanup_old_timestamps(now)
            if not self._request_timestamps:
                return -1

            # Calculate current request rate
            window_duration = (
                now - min(self._request_timestamps)
                if self._request_timestamps
                else self._window_seconds
            )
            if window_duration <= 0:
                return -1

            requests_per_second = len(self._request_timestamps) / window_duration
            if requests_per_second <= 0:
                return -1

            remaining_requests = self._rpm_limit - len(self._request_timestamps)
            if remaining_requests <= 0:
                return 0

            return remaining_requests / requests_per_second

    def get_warning_level(self) -> str:
        """Get current warning level (safe, warning, critical, exceeded)."""
        status = self.get_usage_status()
        return status["warning_level"]


# ============================================================================
# RETRY MANAGER (Exponential Backoff with Jitter)
# ============================================================================


class RetryManager:
    """Exponential backoff retry handler with jitter."""

    # Retriable HTTP status codes
    RETRIABLE_STATUS = {429, 503, 504}
    # Retriable exception types
    RETRIABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._lock = threading.Lock()
        # Retry statistics
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff + jitter."""
        # Exponential backoff: min(base_delay * 2^attempt, max_delay)
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        # Add jitter: delay *= 1 + random.uniform(0, 0.5)
        jitter = 1 + random.uniform(0, 0.5)
        return delay * jitter

    def is_retriable(self, error: Exception) -> bool:
        """Check if error is retriable."""
        # Check HTTP status codes
        if hasattr(error, "status_code"):
            return error.status_code in self.RETRIABLE_STATUS
        if hasattr(error, "code"):
            return error.code in self.RETRIABLE_STATUS
        # Check exception types
        if isinstance(error, self.RETRIABLE_EXCEPTIONS):
            return True
        # Check for specific non-retriable errors
        error_str = str(error).lower()
        non_retriable = [
            "401",
            "unauthorized",
            "403",
            "forbidden",
            "404",
            "not found",
            "valueerror",
        ]
        if any(ng in error_str for ng in non_retriable):
            return False
        return True

    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    with self._lock:
                        self.successful_retries += 1
                return result
            except Exception as e:
                last_exception = e
                if not self.is_retriable(e):
                    with self._lock:
                        self.failed_retries += 1
                    raise
                if attempt < self.max_retries:
                    delay = self.get_retry_delay(attempt)
                    time.sleep(delay)
                    with self._lock:
                        self.total_retries += 1
                else:
                    with self._lock:
                        self.failed_retries += 1
        raise last_exception

    def get_stats(self) -> dict:
        """Get retry statistics."""
        with self._lock:
            total = self.total_retries + self.successful_retries + self.failed_retries
            return {
                "total_retries": self.total_retries,
                "successful_retries": self.successful_retries,
                "failed_retries": self.failed_retries,
                "retry_rate": round(total / max(1, self.total_retries), 3)
                if self.total_retries > 0
                else 0,
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
            }


# ============================================================================
# CIRCUIT BREAKER (Proxy Health State Machine)
# ============================================================================


class CircuitBreaker:
    """Circuit breaker for proxy health state management."""

    # States
    CLOSED = "closed"  # Healthy, requests allowed
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._lock = threading.Lock()
        # State per proxy: proxy_key -> {"state": str, "failures": int, "last_failure": float, "opened_at": float}
        self._proxy_states: Dict[str, dict] = {}

    def _get_proxy_state(self, proxy_key: str) -> dict:
        """Get or create state for proxy."""
        if proxy_key not in self._proxy_states:
            self._proxy_states[proxy_key] = {
                "state": self.CLOSED,
                "failures": 0,
                "last_failure": 0.0,
                "opened_at": 0.0,
            }
        return self._proxy_states[proxy_key]

    def can_execute(self, proxy_key: str) -> bool:
        """Check if request can execute for this proxy."""
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            if state["state"] == self.CLOSED:
                return True
            if state["state"] == self.OPEN:
                # Check if reset timeout expired
                now = time.time()
                if now - state["opened_at"] >= self.reset_timeout:
                    state["state"] = self.HALF_OPEN
                    return True
                return False
            # HALF_OPEN allows one request
            return True

    def record_success(self, proxy_key: str) -> None:
        """Record successful request for proxy."""
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            if state["state"] == self.HALF_OPEN:
                # Success in half-open -> closed
                state["state"] = self.CLOSED
                state["failures"] = 0
            elif state["state"] == self.CLOSED:
                # Reset failures on success
                state["failures"] = 0

    def record_failure(self, proxy_key: str) -> None:
        """Record failed request for proxy."""
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            state["failures"] += 1
            state["last_failure"] = time.time()

            if state["state"] == self.HALF_OPEN:
                # Failure in half-open -> open again
                state["state"] = self.OPEN
                state["opened_at"] = time.time()
            elif state["state"] == self.CLOSED:
                # Check threshold
                if state["failures"] >= self.failure_threshold:
                    state["state"] = self.OPEN
                    state["opened_at"] = time.time()

    def get_state(self, proxy_key: str) -> str:
        """Get state for proxy."""
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            # Auto-transition OPEN -> HALF_OPEN if timeout expired
            if state["state"] == self.OPEN:
                now = time.time()
                if now - state["opened_at"] >= self.reset_timeout:
                    return self.HALF_OPEN
            return state["state"]

    def get_all_states(self) -> dict:
        """Get states for all proxies."""
        with self._lock:
            result = {}
            for proxy_key in self._proxy_states:
                result[proxy_key] = {
                    "state": self.get_state(proxy_key),
                    "failures": self._proxy_states[proxy_key]["failures"],
                    "last_failure": self._proxy_states[proxy_key]["last_failure"],
                }
            return result


# ============================================================================
# REQUEST QUEUE (Priority Queue with Auto-Dispatch)
# ============================================================================


class RequestQueue:
    """Priority queue for holding requests during cooldown periods."""

    # Priority levels
    PRIORITY_NORMAL = 0
    PRIORITY_HIGH = 1
    PRIORITY_CRITICAL = 2

    def __init__(self, max_wait: int = 300, check_interval: float = 5.0):
        self.max_wait = max_wait
        self.check_interval = check_interval
        self._lock = threading.Lock()
        # Priority queue: List of (priority, created_at, id, prompt, params)
        self._queue: List[tuple] = []
        self._dead_letters: Dict[str, dict] = {}  # id -> request data
        self._next_id = 0
        self._dispatcher_running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        # Callback for dispatch (set by Router)
        self._dispatch_callback = None

    def set_dispatch_callback(self, callback) -> None:
        """Set callback for auto-dispatch."""
        self._dispatch_callback = callback

    def enqueue(
        self,
        prompt: str,
        params: dict,
        priority: int = PRIORITY_NORMAL,
    ) -> str:
        """Add request to queue. Returns request ID."""
        now = time.time()
        request_id = f"req_{self._next_id}"
        self._next_id += 1

        with self._lock:
            request = {
                "id": request_id,
                "prompt": prompt,
                "params": params,
                "priority": priority,
                "created_at": now,
                "max_wait": self.max_wait,
                "status": "pending",
            }
            # Insert sorted by priority (higher first), then by time
            inserted = False
            for i, (p, ct, _, _, _) in enumerate(self._queue):
                if priority > p or (priority == p and now < ct):
                    self._queue.insert(i, (priority, now, request_id, prompt, params))
                    inserted = True
                    break
            if not inserted:
                self._queue.append((priority, now, request_id, prompt, params))

            # Start dispatcher if not running
            if not self._dispatcher_running:
                self._start_dispatcher()

        return request_id

    def dequeue(self) -> Optional[dict]:
        """Remove and return highest priority pending request."""
        now = time.time()
        with self._lock:
            if not self._queue:
                return None
            # Check oldest request for expiration
            while self._queue:
                priority, created_at, req_id, prompt, params = self._queue[0]
                if now - created_at > self.max_wait:
                    # Move to dead letters
                    _, _, req_id, prompt, params = self._queue.pop(0)
                    self._dead_letters[req_id] = {
                        "id": req_id,
                        "prompt": prompt,
                        "params": params,
                        "created_at": created_at,
                        "expired_at": now,
                        "reason": "max_wait_exceeded",
                    }
                else:
                    break

            if not self._queue:
                return None

            priority, created_at, req_id, prompt, params = self._queue.pop(0)
            return {
                "id": req_id,
                "prompt": prompt,
                "params": params,
                "priority": priority,
                "created_at": created_at,
            }

    def get_queue_depth(self) -> dict:
        """Get queue depth by priority."""
        with self._lock:
            return {
                "total": len(self._queue),
                "critical": sum(
                    1 for p, _, _, _, _ in self._queue if p == self.PRIORITY_CRITICAL
                ),
                "high": sum(
                    1 for p, _, _, _, _ in self._queue if p == self.PRIORITY_HIGH
                ),
                "normal": sum(
                    1 for p, _, _, _, _ in self._queue if p == self.PRIORITY_NORMAL
                ),
            }

    def get_dead_letters(self) -> List[dict]:
        """Get expired requests."""
        with self._lock:
            return list(self._dead_letters.values())

    def requeue_dead_letter(self, request_id: str) -> bool:
        """Re-queue a dead letter."""
        with self._lock:
            if request_id not in self._dead_letters:
                return False
            dl = self._dead_letters.pop(request_id)
            self.enqueue(
                dl["prompt"], dl["params"], dl.get("priority", self.PRIORITY_NORMAL)
            )
            return True

    def _start_dispatcher(self) -> None:
        """Start background dispatcher thread."""
        self._dispatcher_running = True
        self._dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop, daemon=True
        )
        self._dispatcher_thread.start()

    def _dispatcher_loop(self) -> None:
        """Background dispatcher that checks if requests can proceed."""
        while self._dispatcher_running:
            time.sleep(self.check_interval)
            # Try to dispatch one request
            request = self.dequeue()
            if request and self._dispatch_callback:
                try:
                    self._dispatch_callback(request)
                except Exception:
                    pass  # Callback errors handled by caller
            # Stop if queue empty
            with self._lock:
                if not self._queue and self._dispatcher_running:
                    self._dispatcher_running = False


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_router: Optional[Router] = None
_session_manager: Optional[SessionManager] = None
_token_tunnel: Optional[TokenTunnel] = None
_training_loop: Optional[TrainingLoop] = None


def get_router() -> Router:
    global _router
    if _router is None:
        _router = Router()
    return _router


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(get_router().ip_pool)
    return _session_manager


def get_token_tunnel() -> TokenTunnel:
    global _token_tunnel
    if _token_tunnel is None:
        _token_tunnel = TokenTunnel()
    return _token_tunnel


def get_training_loop() -> TrainingLoop:
    global _training_loop
    if _training_loop is None:
        _training_loop = TrainingLoop(get_router())
    return _training_loop


_rate_predictor: Optional[RateLimitPredictor] = None
_retry_manager: Optional[RetryManager] = None
_circuit_breaker: Optional[CircuitBreaker] = None
_request_queue: Optional[RequestQueue] = None


def get_rate_predictor() -> RateLimitPredictor:
    global _rate_predictor
    if _rate_predictor is None:
        _rate_predictor = RateLimitPredictor()
    return _rate_predictor


def get_retry_manager() -> RetryManager:
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


def get_circuit_breaker() -> CircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker


def get_request_queue() -> RequestQueue:
    global _request_queue
    if _request_queue is None:
        _request_queue = RequestQueue()
    return _request_queue


# ============================================================================
# MCP SERVER
# ============================================================================


def handle_mcp_request(method: str, params: dict) -> dict:
    """Handle MCP request."""
    router = get_router()

    # Standard MCP methods
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": "intelligent-router-mcp", "version": "1.0.0"},
        }
    elif method == "tools/list":
        return {
            "tools": [
                {"name": "route_task", "description": "Route a task to optimal model"},
                {"name": "record_success", "description": "Record successful routing"},
                {"name": "record_failure", "description": "Record failed routing"},
                {
                    "name": "get_router_status",
                    "description": "Get router health status",
                },
                {
                    "name": "get_available_models",
                    "description": "List available models",
                },
                {"name": "get_routing_history", "description": "Get routing history"},
                {
                    "name": "create_session",
                    "description": "Create session with dedicated IP",
                },
                {"name": "get_session_status", "description": "Get session status"},
                {"name": "release_session_ip", "description": "Release session IP"},
                {"name": "get_tunnel_status", "description": "Get token tunnel status"},
                {"name": "check_tunnel", "description": "Check if request can proceed"},
                {"name": "start_training_loop", "description": "Start training loop"},
                {"name": "stop_training_loop", "description": "Stop training loop"},
                {"name": "get_training_metrics", "description": "Get training metrics"},
                {"name": "force_training", "description": "Force training cycle"},
                {"name": "optimize_router", "description": "Optimize router weights"},
                {
                    "name": "get_model_performance",
                    "description": "Get model performance stats",
                },
                {"name": "run_training", "description": "Run training simulation"},
                {"name": "get_weights", "description": "Get current model weights"},
                {
                    "name": "get_rate_prediction",
                    "description": "Get rate limit prediction",
                },
                {
                    "name": "get_circuit_states",
                    "description": "Get circuit breaker states",
                },
                {"name": "enqueue_request", "description": "Enqueue request for later"},
                {"name": "get_queue_status", "description": "Get request queue status"},
                {
                    "name": "get_resilience_status",
                    "description": "Get resilience status",
                },
                {"name": "get_retry_stats", "description": "Get retry statistics"},
            ]
        }

    if method == "tools/route_task":
        return router.select_route(
            params.get("prompt", ""),
            params.get("system_prompt", ""),
            params.get("agent_type", ""),
        )
    elif method == "tools/record_success":
        router.record_success(
            params.get("route", {}),
            params.get("input_tokens", 0),
            params.get("output_tokens", 0),
            params.get("latency_ms", 0),
        )
        return {"status": "success"}
    elif method == "tools/record_failure":
        router.record_failure(
            params.get("route", {}),
            params.get("error_type", ""),
            params.get("latency_ms", 0),
        )
        return {"status": "recorded"}
    elif method == "tools/get_router_status":
        return router.get_status()
    elif method == "tools/get_available_models":
        return [{"model": name, **caps} for name, caps in MODEL_CAPABILITIES.items()]
    elif method == "tools/get_routing_history":
        # Quick SQLite query for history
        conn = sqlite3.connect(get_router().learning.db_path)
        cursor = conn.execute(
            """SELECT timestamp, categories, complexity, selected_model, 
            selected_ip, latency_ms, success FROM outcomes ORDER BY timestamp DESC LIMIT ?""",
            (params.get("limit", 10),),
        )
        results = [
            {
                "timestamp": r[0],
                "categories": r[1],
                "complexity": r[2],
                "model": r[3],
                "provider": "opencode",  # Default provider
                "vpn_ip": r[4],
                "latency_ms": r[5],
                "success": bool(r[6]),
            }
            for r in cursor.fetchall()
        ]
        conn.close()
        return results
    # Session management tools
    elif method == "tools/create_session":
        session_id = params.get("session_id", str(uuid.uuid4())[:8])
        return get_session_manager().create_session(session_id)
    elif method == "tools/get_session_status":
        return get_session_manager().get_session_status(params.get("session_id", ""))
    elif method == "tools/release_session_ip":
        return get_session_manager().release_session_ip(params.get("session_id", ""))
    elif method == "tools/get_tunnel_status":
        return get_token_tunnel().get_tunnel_status(params.get("session_id", ""))
    elif method == "tools/check_tunnel":
        return get_token_tunnel().can_proceed(
            params.get("session_id", ""),
            params.get("tokens_needed", 0),
        )
    # Training/optimization tools
    elif method == "tools/optimize_router":
        return get_router().optimize()
    elif method == "tools/get_model_performance":
        return router.learning.get_all_model_performance()
    elif method == "tools/run_training":
        simulator = TrainingSimulator(router.learning)
        return simulator.run_training_cycle(params.get("samples", 50))
    elif method == "tools/get_weights":
        return {
            "weights": router._model_weights,
            "status": "active" if router._model_weights else "not_trained",
        }
    # Training loop control
    elif method == "tools/start_training_loop":
        get_training_loop().start()
        return {"status": "started"}
    elif method == "tools/stop_training_loop":
        get_training_loop().stop()
        return {"status": "stopped"}
    elif method == "tools/get_training_metrics":
        return get_training_loop().get_metrics()
    elif method == "tools/force_training":
        return get_training_loop().force_training()
    # Resilience/MCP tools
    elif method == "tools/get_rate_prediction":
        return get_rate_predictor().get_usage_status()
    elif method == "tools/get_circuit_states":
        return get_circuit_breaker().get_all_states()
    elif method == "tools/enqueue_request":
        priority = params.get("priority", 0)
        if isinstance(priority, str):
            priority_map = {"normal": 0, "high": 1, "critical": 2}
            priority = priority_map.get(priority.lower(), 0)
        return {
            "request_id": get_request_queue().enqueue(
                params.get("prompt", ""),
                params.get("params", {}),
                priority,
            )
        }
    elif method == "tools/get_queue_status":
        q = get_request_queue()
        depth = q.get_queue_depth()
        dead_letters = q.get_dead_letters()
        return {
            "depth": depth,
            "dead_letters_count": len(dead_letters),
            "dead_letters": dead_letters,
        }
    elif method == "tools/get_resilience_status":
        return router.get_resilience_status()
    elif method == "tools/get_retry_stats":
        return get_retry_manager().get_stats()
    # NEW: Intelligence module integration tools
    elif method == "tools/execute_with_fallback":
        # Execute with fallback chain - tries models in order until one succeeds
        prompt = params.get("prompt", "")
        task_callable_str = params.get("task_callable", "")

        def dummy_task_callable(model: str):
            """Dummy task that simulates execution."""
            # This will be replaced by actual callable in production
            raise NotImplementedError("Use tools/get_model_health for status check")

        result = router._fallback_chain.execute(dummy_task_callable)
        return {
            "model": result.model,
            "success": result.success,
            "attempts": result.attempts,
            "errors": result.errors,
            "latency_ms": result.latency_ms,
            "fallback_path": result.fallback_path,
        }
    elif method == "tools/get_circuit_breaker_status":
        # Return all model circuit breaker states from intelligence module
        return router._model_circuit_breaker.get_all_states()
    elif method == "tools/get_model_health":
        # Return health report from .sisyphus/model_health.json
        health_file = Path(".sisyphus/model_health.json")
        if health_file.exists():
            try:
                with open(health_file) as f:
                    return json.load(f)
            except Exception as e:
                return {"error": f"Failed to load health file: {e}"}
        else:
            return {
                "status": "no_data",
                "message": "No health data available. Run health checks first.",
                "file": str(health_file),
            }
    else:
        return {"error": f"Unknown method: {method}"}


def main():
    """MCP server main loop."""
    print("=== Intelligent Router MCP ===", file=sys.stderr)
    print(f"Python: {sys.version}", file=sys.stderr)

    # Test on startup
    result = get_router().select_route("test", agent_type="test")
    print(
        f"Test OK: model={result['model']}, reason={result['selection_reason']}",
        file=sys.stderr,
    )

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            response = handle_mcp_request(
                request.get("method", ""), request.get("params", {})
            )

            print(
                json.dumps({"id": request.get("id", 1), "result": response}), flush=True
            )

        except Exception as e:
            print(json.dumps({"id": 1, "error": {"message": str(e)}}), flush=True)


if __name__ == "__main__":
    main()
