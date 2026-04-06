"""
Shared singleton instances for model router components.

This module ensures that hook.py and the proxy server use the SAME
instances of CircuitBreaker, RateLimiter, VRAMManager, and OllamaManager,
so state (e.g., circuit breaker trips, rate limit counters) is consistent
across all entry points.
"""
import os

from .vram_manager import VRAMManager
from .ollama_manager import OllamaManager
from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter
from .semantic_cache import SemanticCache

from .config import DEFAULT_RATE_LIMITS

vram_manager = VRAMManager(
    max_vram_gb=float(os.getenv("MODEL_ROUTER_MAX_VRAM_GB", "12.0")),
    safety_margin_gb=float(os.getenv("MODEL_ROUTER_VRAM_SAFETY_MARGIN", "1.0")),
)
ollama_manager = OllamaManager()
circuit_breaker = CircuitBreaker(
    failure_threshold=int(os.getenv("MODEL_ROUTER_CB_FAILURE_THRESHOLD", "3")),
    reset_timeout=int(os.getenv("MODEL_ROUTER_CB_RESET_TIMEOUT", "300")),
)
PROVIDER_RATE_LIMITS = {
    "opencode": RateLimiter(
        max_requests=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_MAX", "1")),
        window_seconds=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_WINDOW", "120")),
    ),
    "openrouter": RateLimiter(
        max_requests=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_MAX", "2")),
        window_seconds=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_WINDOW", "60")),
    ),
    "ollama": RateLimiter(
        max_requests=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_OLLAMA_MAX", "30")),
        window_seconds=int(os.getenv("MODEL_ROUTER_RATE_LIMIT_WINDOW", "60")),
    ),
}
SEMANTIC_CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() in ("1", "true", "yes")

semantic_cache = SemanticCache(
    exact_ttl=float(os.getenv("SEMANTIC_CACHE_EXACT_TTL", "60")),
    semantic_ttl=float(os.getenv("SEMANTIC_CACHE_SEMANTIC_TTL", "3600")),
    similarity_threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.85")),
)


# Backwards compatibility alias — points to default provider
rate_limiter = PROVIDER_RATE_LIMITS["opencode"]


def get_rate_limiter(provider: str) -> RateLimiter:
    """Return the rate limiter for a specific provider."""
    if provider not in PROVIDER_RATE_LIMITS:
        import logging
        logging.getLogger(__name__).warning(
            "Unknown provider '%s' — using opencode rate limiter", provider
        )
    return PROVIDER_RATE_LIMITS.get(provider, PROVIDER_RATE_LIMITS["opencode"])
