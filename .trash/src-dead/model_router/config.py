"""
Central configuration for model router.

All model sizes, providers, and routing defaults are defined here as the single
source of truth. Other modules import from this config.
"""

from enum import Enum
from typing import Dict

# Known model sizes in GB (approximate VRAM footprint)
MODEL_SIZES: Dict[str, float] = {
    "llama3.2:3b": 2.0,
    "llama3.2:1b": 0.7,
    "qwen2.5-coder:7b": 4.5,
    "qwen2.5-coder:14b": 9.0,
    "qwen3:8b": 5.2,
    "deepseek-r1:14b": 9.0,
    "llava:7b": 4.5,
}

DEFAULT_MODEL_SIZE_GB = 4.0

# Provider configurations
PROVIDERS = {
    "opencode": {
        "base_url": "https://opencode.ai/api/chat",
        "models": ["opencode/mimo-v2-pro-free", "opencode/minimax-m2.5-free"],
        "requires_key": True,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models": [
            "openrouter/*",
            "qwen/qwen3-coder:free",
            "deepseek/deepseek-r1:free",
        ],
        "requires_key": True,
    },
    "ollama": {
        "base_url": "http://localhost:11434/api/chat",
        "models": ["qwen2.5-coder:7b", "qwen3:8b", "llama3.2:3b"],
        "requires_key": False,
    },
}

# Default rate limits per provider
DEFAULT_RATE_LIMITS = {
    "opencode": {
        "max_requests": 8,
        "window_seconds": 60,
    },
    "openrouter": {
        "max_requests": 8,
        "window_seconds": 60,
    },
    "ollama": {
        "max_requests": 30,
        "window_seconds": 60,
    },
}


class RoutingStrategy(Enum):
    """Routing strategy for model selection."""

    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE = "performance"
    FALLBACK = "fallback"
