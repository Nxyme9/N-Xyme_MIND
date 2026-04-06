"""
Model Router Hook — Single entry point for the complete routing pipeline.

Exposes a unified API that classifies tasks, checks resources, and routes
to the optimal model. This is the module that the oh-my-openagent plugin
imports directly.

Pipeline:
    1. Rate limit check
    2. Task classification
    3. Circuit breaker check
    4. VRAM availability (local models)
    5. Model loading via Ollama (local models)
    6. Routing decision

Usage:
    from src.model_router.hook import route_request, get_system_status

    result = route_request("explore", "find all Python files")
    print(result["model"], result["provider"], result["confidence"])

    status = get_system_status()
    print(status)
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
import asyncio
import time
import uuid
from typing import Any, Dict, Optional

# Add project root to path for imports
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.model_router.state import (
    circuit_breaker,
    get_rate_limiter,
    ollama_manager,
    semantic_cache,
    SEMANTIC_CACHE_ENABLED,
    vram_manager,
)
from src.model_router.ollama_manager import OllamaManager
from src.model_router.vram_manager import MODEL_SIZES, VRAMManager

_classifier_module_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_router.py",
)
_spec = importlib.util.spec_from_file_location(
    "_model_router_main", _classifier_module_path
)
_model_router_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_model_router_main)

CLASSIFIER = _model_router_main.CLASSIFIER
ModelProvider = _model_router_main.ModelProvider
ModelRoute = _model_router_main.ModelRoute
TaskComplexity = _model_router_main.TaskComplexity
logger = logging.getLogger(__name__)

try:
    from src.infrastructure.proxy.model_router import AUDIT_LOGGER
except (ImportError, ValueError):
    logging.warning("AUDIT_LOGGER import failed, using fallback logging")
    AUDIT_LOGGER = logging.getLogger("audit.fallback")
    if not AUDIT_LOGGER.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [AUDIT] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        AUDIT_LOGGER.addHandler(handler)
        AUDIT_LOGGER.setLevel(logging.INFO)


def _log(
    level: str,
    msg: str,
    agent_type: str = "",
    model: str = "",
    provider: str = "",
    confidence: float = 0.0,
    **kwargs,
) -> None:
    """Log with structured context for routing decisions."""
    extra = {
        "agent_type": agent_type or "system",
        "model": model or "none",
        "provider": provider or "none",
        "confidence": confidence,
    }
    extra.update(kwargs)
    log_fn = getattr(logger, level, logger.info)
    ctx = ", ".join(f"{k}={v}" for k, v in extra.items() if v)
    log_fn(f"[{ctx}] {msg}")


# ── Model size lookup (extends VRAM manager's known sizes) ─────────────

_KNOWN_MODEL_SIZES: Dict[str, float] = dict(MODEL_SIZES)
_KNOWN_MODEL_SIZES.update(
    {
        "llama3.2:latest": 2.0,
        "minimax-m2.5-free": 0.0,
        "mimo-v2-pro-free": 0.0,
        "qwen3-coder:free": 0.0,
        "deepseek-r1:free": 0.0,
        "sherlock-think-alpha": 0.0,
        "openrouter/vision": 0.0,
    }
)

# ── Shared singleton instances (from state.py) ─────────────────────────

_vram_manager = vram_manager
_ollama_manager = ollama_manager
_circuit_breaker = circuit_breaker
_classifier = CLASSIFIER
# Thread safety lock for routing pipeline.
# threading.Lock is intentional: route_request() is sync and called from
# both sync and async contexts. The lock holds briefly (fallback selection,
# model loading) so event-loop blocking is negligible.
_route_lock = threading.Lock()
# Async-compatible lock for future async entry points.
_route_lock_async = asyncio.Lock()

# TTL cache for Ollama health check (avoids blocking HTTP on every request)
_ollama_health_cache: Dict[str, Any] = {"healthy": True, "last_check": 0.0, "ttl": 30.0}
# ── Public API ─────────────────────────────────────────────────────────


def route_request(agent_type: str, task_content: str = "") -> Dict[str, Any]:
    """Route an agent request through the complete pipeline.

    Steps:
        0. Check Ollama health (graceful degradation)
        1. Check rate limiter — block if exceeded
        2. Classify task using the task classifier
        3. Check circuit breaker for the primary model
        4. If local model, check VRAM availability
        5. If local model, ensure it is loaded via OllamaManager
        6. Return routing decision (with fallback if primary is unavailable)

    Args:
        agent_type: Agent identifier (explore, oracle, hephaestus, etc.)
        task_content: Optional task content for dynamic routing.

    Returns:
        Dict with keys:
            - model: Selected model name
            - provider: Provider string ("ollama", "opencode", "openrouter")
            - confidence: Routing confidence (0.0–1.0)
            - reason: Human-readable explanation
            - fallback_used: Whether fallback was selected
            - rate_limited: Whether the request was rate-limited
            - circuit_broken: Whether the primary model's circuit is open
            - vram_blocked: Whether VRAM prevented local model loading
    """
    request_id = str(uuid.uuid4())

    if AUDIT_LOGGER:
        AUDIT_LOGGER.info(
            "REQUEST_START request_id=%s agent_type=%s",
            request_id, agent_type
        )
    # Step 0 — Ollama health check with TTL cache (avoid blocking HTTP every request)
    now = time.time()
    global _ollama_health_cache
    if now - _ollama_health_cache["last_check"] > _ollama_health_cache["ttl"]:
        try:
            _ollama_health_cache["healthy"] = _ollama_manager.health_check()
            _ollama_health_cache["last_check"] = now
        except Exception:
            _ollama_health_cache["healthy"] = False
            _ollama_health_cache["last_check"] = now
    ollama_healthy = _ollama_health_cache["healthy"]

    # Semantic cache check — before routing pipeline
    if SEMANTIC_CACHE_ENABLED and task_content:
        cached = semantic_cache.get(task_content, agent_type)
        if cached is not None:
            _log("info", "semantic cache hit", agent_type=agent_type)
            result = _empty_result()
            result["request_id"] = request_id
            result["model"] = "cached"
            result["provider"] = "semantic_cache"
            result["confidence"] = 1.0
            result["reason"] = "Response served from semantic cache"
            result["cache_hit"] = True
            result["response"] = cached
            return result

    result = _empty_result()
    result["request_id"] = request_id

    # Step 1 — Rate limit check (per-provider)
    route = _classifier.classify(agent_type, task_content)
    provider_limiter = get_rate_limiter(route.provider.value)
    if not provider_limiter.try_acquire():
        wait = provider_limiter.get_wait_time()
        _log(
            "warning",
            f"rate limit exceeded for {route.provider.value}, retry in {wait:.1f}s",
            agent_type=agent_type,
            provider=route.provider.value,
        )
        if AUDIT_LOGGER:
            AUDIT_LOGGER.warning(
                "RATE_LIMITED request_id=%s agent_type=%s provider=%s",
                request_id, agent_type, route.provider.value
            )
        result.update(
            {
                "model": None,
                "provider": None,
                "confidence": 0.0,
                "reason": f"Rate limit exceeded for {route.provider.value}. Retry in {wait:.1f}s.",
                "rate_limited": True,
            }
        )
        return result

    # Step 2 — Classify task (already done for rate limiting above)

    # Step 3 — Circuit breaker check (primary model)
    primary_model = route.model_name
    if not _circuit_breaker.is_available(primary_model):
        _log(
            "warning",
            "circuit breaker open",
            agent_type=agent_type,
            model=primary_model,
        )
        if AUDIT_LOGGER:
            AUDIT_LOGGER.warning(
                "CIRCUIT_BREAKER_OPEN request_id=%s agent_type=%s model=%s",
                request_id, agent_type, primary_model
            )
        if route.fallback_model and route.fallback_provider:
            with _route_lock:
                return _use_fallback(route, result, "circuit_breaker", request_id=request_id)
        result.update(
            {
                "model": None,
                "provider": None,
                "confidence": 0.0,
                "reason": f"Circuit breaker open for '{primary_model}' and no fallback available.",
            }
        )
        return result

    # Graceful degradation: if Ollama is unhealthy, skip local routes entirely
    if route.is_local and not ollama_healthy:
        _log(
            "warning",
            "Ollama unhealthy, skipping local route",
            agent_type=agent_type,
            model=primary_model,
        )
        if AUDIT_LOGGER:
            AUDIT_LOGGER.warning(
                "OLLAMA_UNHEALTHY request_id=%s agent_type=%s model=%s",
                request_id, agent_type, primary_model
            )
        if route.fallback_model and route.fallback_provider:
            with _route_lock:
                return _use_fallback(route, result, "ollama_unhealthy", request_id=request_id)
        result.update(
            {
                "model": None,
                "provider": None,
                "confidence": 0.0,
                "reason": f"Ollama unhealthy, local route '{primary_model}' unavailable, no fallback.",
            }
        )
        return result

    # Step 4 — VRAM check (local models only)
    if route.is_local:
        model_size = _KNOWN_MODEL_SIZES.get(primary_model, 0.0)
        if model_size > 0 and not _vram_manager.can_load_model(model_size):
            _log(
                "warning",
                f"insufficient VRAM ({model_size} GB)",
                agent_type=agent_type,
                model=primary_model,
            )
            if AUDIT_LOGGER:
                AUDIT_LOGGER.warning(
                    "VRAM_INSUFFICIENT request_id=%s agent_type=%s model=%s size=%sGB",
                    request_id, agent_type, primary_model, model_size
                )
            if route.fallback_model and route.fallback_provider:
                with _route_lock:
                    return _use_fallback(route, result, "vram_exhausted", request_id=request_id)
            result.update(
                {
                    "model": None,
                    "provider": None,
                    "confidence": 0.0,
                    "reason": f"Insufficient VRAM for '{primary_model}' and no fallback.",
                }
            )
            return result

    # Step 5 — Ensure local model is loaded
    if route.is_local:
        with _route_lock:
            if not _ensure_model_loaded(primary_model, route.keep_alive):
                _log(
                    "warning",
                    "failed to load model",
                    agent_type=agent_type,
                    model=primary_model,
                )
                if AUDIT_LOGGER:
                    AUDIT_LOGGER.warning(
                        "MODEL_LOAD_FAILED request_id=%s agent_type=%s model=%s",
                        request_id, agent_type, primary_model
                    )
                if route.fallback_model and route.fallback_provider:
                    return _use_fallback(route, result, "model_load_failed", request_id=request_id)
                result.update(
                    {
                        "model": None,
                        "provider": None,
                        "confidence": 0.0,
                        "reason": f"Failed to load '{primary_model}' and no fallback.",
                    }
                )
                return result

    # Step 6 — Return routing decision
    confidence = _compute_confidence(route, result)
    reason = f"Routed '{agent_type}' to {primary_model} ({route.provider.value})"

    result.update(
        {
            "model": primary_model,
            "provider": route.provider.value,
            "confidence": confidence,
            "reason": reason,
            "complexity": _get_complexity(agent_type),
            "priority": route.priority,
        }
    )
    _log(
        "info",
        reason,
        agent_type=agent_type,
        model=primary_model,
    )
    if AUDIT_LOGGER:
        AUDIT_LOGGER.info(
            "REQUEST_COMPLETE request_id=%s agent_type=%s model=%s provider=%s confidence=%s",
            request_id, agent_type, primary_model, route.provider.value, confidence
        )

    # NOTE: Semantic cache response storage is handled at the proxy level
    # after call_provider() returns the actual LLM response.
    # The hook only has routing metadata, not the actual response.

    return result


def get_system_status() -> Dict[str, Any]:
    """Return a snapshot of the entire routing system status.

    Returns:
        Dict with keys:
            - vram: VRAM usage dict (used_gb, total_gb, free_gb, percent)
            - ollama_health: Boolean — is Ollama reachable
            - circuit_breakers: Dict of model → circuit state
            - rate_limiter: Rate limiter stats
            - loaded_models: List of model names currently in VRAM
    """
    vram = _vram_manager.get_vram_usage()

    ollama_healthy = False
    loaded_models: list[str] = []
    try:
        ollama_healthy = _ollama_manager.health_check()
        if ollama_healthy:
            loaded = _ollama_manager.get_loaded_models()
            loaded_models = [m.name for m in loaded]
    except Exception as exc:
        _log("warning", f"Ollama health check failed: {exc}", agent_type="system")

    cb_states = _circuit_breaker.batch_state(list(_KNOWN_MODEL_SIZES.keys()))
    cb_states = {m: s for m, s in cb_states.items() if s["failures"] > 0 or s["is_open"]}
    from src.model_router.state import PROVIDER_RATE_LIMITS
    rl_stats = {p: l.get_stats() for p, l in PROVIDER_RATE_LIMITS.items()}

    return {
        "vram": vram,
        "ollama_health": ollama_healthy,
        "circuit_breakers": cb_states,
        "rate_limiter": rl_stats,
        "loaded_models": loaded_models,
        "timestamp": time.time(),
    }


def record_success(model: str) -> None:
    """Record a successful API call for the given model.

    Resets the circuit breaker failure counter for the model.
    Call this after a request completes successfully.

    Args:
        model: Model name that succeeded.
    """
    _circuit_breaker.record_success(model)
    _log("debug", "recorded success", model=model)


def record_failure(model: str) -> None:
    """Record a failed API call for the given model.

    Increments the circuit breaker failure counter. Once the threshold
    is reached, the model will be blocked until the backoff period expires.
    Call this after a request fails (timeout, error, etc.).

    Args:
        model: Model name that failed.
    """
    _circuit_breaker.record_failure(model)
    _log("debug", "recorded failure", model=model)


# ── Internal helpers ───────────────────────────────────────────────────


def _empty_result() -> Dict[str, Any]:
    """Return a result dict with default values."""
    return {
        "model": None,
        "provider": None,
        "confidence": 0.0,
        "reason": "",
        "fallback_used": False,
        "rate_limited": False,
        "circuit_broken": False,
        "vram_blocked": False,
    }


def _use_fallback(
    route: ModelRoute, result: Dict[str, Any], reason_key: str, request_id: str = ""
) -> Dict[str, Any]:
    """Select the fallback model and populate the result."""
    fallback_model = route.fallback_model
    fallback_provider = route.fallback_provider

    if not _circuit_breaker.is_available(fallback_model):
        if AUDIT_LOGGER and request_id:
            AUDIT_LOGGER.warning(
                "FALLBACK_UNAVAILABLE request_id=%s model=%s",
                request_id, fallback_model
            )
        result.update(
            {
                "model": None,
                "provider": None,
                "confidence": 0.0,
                "reason": f"Both primary and fallback circuits open.",
            }
        )
        return result

    result.update(
        {
            "model": fallback_model,
            "provider": fallback_provider.value,
            "confidence": 0.5,
            "reason": f"Primary unavailable ({reason_key}), using fallback {fallback_model}",
            "fallback_used": True,
        }
    )
    _log(
        "info",
        "fallback selected",
        model=fallback_model,
        provider=fallback_provider.value,
        confidence=0.5,
    )
    if AUDIT_LOGGER and request_id:
        AUDIT_LOGGER.info(
            "FALLBACK_USED request_id=%s model=%s provider=%s",
            request_id, fallback_model, fallback_provider.value
        )
    return result


def _compute_confidence(route: ModelRoute, result: Dict[str, Any]) -> float:
    """Compute routing confidence based on route priority and fallback usage."""
    base = {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.7}.get(route.priority, 0.5)
    if result.get("fallback_used"):
        base *= 0.6
    return round(base, 2)


def _get_complexity(agent_type: str) -> str:
    """Return the complexity string for an agent type."""
    try:
        route = _classifier.classify(agent_type)
        # Compare the route's complexity attribute directly
        return route.complexity.value if hasattr(route, 'complexity') else "unknown"
    except Exception:
        return "unknown"


def _ensure_model_loaded(model: str, keep_alive: str = "-1") -> bool:
    """Ensure a local model is loaded in Ollama.

    Args:
        model: Model name to load.
        keep_alive: Ollama keep-alive duration.

    Returns:
        True if the model is loaded (or was already loaded).
    """
    try:
        return _ollama_manager.ensure_model_loaded(model)
    except Exception as exc:
        _log("error", f"ensure_model_loaded failed: {exc}", model=model)
        return False


# ── CLI demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("Model Router Hook — Demo")
    print("=" * 60)

    test_cases = [
        ("explore", "find all Python files"),
        ("oracle", "review architecture of the auth module"),
        ("hephaestus", "implement a new REST endpoint with validation"),
        ("sisyphus", "orchestrate the full deployment pipeline"),
        ("multimodal", "analyze the attached screenshot for UI bugs"),
        ("unknown-agent", "some random task"),
    ]

    print("\n── Routing Decisions ──\n")
    for agent, content in test_cases:
        result = route_request(agent, content)
        print(f"Agent: {agent}")
        print(f"  Model:      {result['model']}")
        print(f"  Provider:   {result['provider']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Reason:     {result['reason']}")
        print(f"  Fallback:   {result['fallback_used']}")
        print(f"  Rate Limit: {result['rate_limited']}")
        print(f"  Circuit:    {result['circuit_broken']}")
        print(f"  VRAM Block: {result['vram_blocked']}")
        print()

    print("\n── System Status ──\n")
    status = get_system_status()
    print(
        f"VRAM: {status['vram']['used_gb']:.1f} / {status['vram']['total_gb']:.1f} GB ({status['vram']['percent']:.0f}%)"
    )
    print(f"Ollama: {'ONLINE' if status['ollama_health'] else 'OFFLINE'}")
    print(f"Loaded models: {status['loaded_models'] or '(none)'}")
    print(
        f"Rate limiter: {status['rate_limiter']['available_tokens']:.0f} tokens remaining"
    )
    active_cb = status["circuit_breakers"]
    if active_cb:
        print(f"Circuit breakers with issues: {list(active_cb.keys())}")
    else:
        print("Circuit breakers: all healthy")

    print("\n── Circuit Breaker Test ──\n")
    record_failure("test-model")
    record_failure("test-model")
    record_failure("test-model")
    state = _circuit_breaker.state("test-model")
    print(
        f"test-model after 3 failures: is_open={state['is_open']}, failures={state['failures']}"
    )
    record_success("test-model")
    state = _circuit_breaker.state("test-model")
    print(
        f"test-model after success: is_open={state['is_open']}, failures={state['failures']}"
    )

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)
