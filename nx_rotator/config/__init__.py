"""
NxRotator Configuration
=======================

Default configuration for the NxRotator system.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class KeyConfig:
    """Configuration for a single API key."""

    key_id: str
    priority: int = 0
    rpm_limit: int = 20
    tpm_limit: int = 50000
    daily_limit: int = 50
    enabled: bool = True


@dataclass
class RotatorConfig:
    """Main configuration for NxRotator."""

    # OpenRouter settings
    base_url: str = "https://openrouter.ai/api/v1"
    referer: str = "https://n-xyme.github.io"
    app_title: str = "N-Xyme MIND"

    # Connection settings
    timeout: int = 60
    max_retries: int = 1

    # Health settings
    health_check_interval: int = 30
    cooldown_base: int = 10
    max_cooldown: int = 300
    max_consecutive_errors: int = 3

    # Metrics settings
    metrics_window: int = 1000

    @classmethod
    def from_file(cls, path: Path) -> "RotatorConfig":
        """Load config from JSON file."""
        import json

        if not path.exists():
            return cls()

        with open(path) as f:
            data = json.load(f)

        return cls(
            base_url=data.get("base_url", cls.base_url),
            referer=data.get("referer", cls.referer),
            app_title=data.get("app_title", cls.app_title),
            timeout=data.get("timeout", cls.timeout),
            max_retries=data.get("max_retries", cls.max_retries),
            health_check_interval=data.get(
                "health_check_interval", cls.health_check_interval
            ),
            cooldown_base=data.get("cooldown_base", cls.cooldown_base),
            max_cooldown=data.get("max_cooldown", cls.max_cooldown),
            max_consecutive_errors=data.get(
                "max_consecutive_errors", cls.max_consecutive_errors
            ),
            metrics_window=data.get("metrics_window", cls.metrics_window),
        )


# Default config
DEFAULT_CONFIG = RotatorConfig()


# Model configurations
MODELS = {
    "nemotron-3-super": {
        "name": "NVIDIA Nemotron 3 Super 120B",
        "context": 262144,
        "output": 8192,
        "recommended": True,
    },
    "qwen3-coder": {
        "name": "Qwen 3 Coder",
        "context": 262144,
        "output": 8192,
        "recommended": True,
    },
    "gemma-4": {
        "name": "Google Gemma 4 31B",
        "context": 262144,
        "output": 8192,
    },
    "deepseek-r1": {
        "name": "DeepSeek R1",
        "context": 131072,
        "output": 8192,
    },
    "mistral-small": {
        "name": "Mistral Small 3.1",
        "context": 262144,
        "output": 8192,
    },
}


def get_model_info(model_name: str) -> Optional[Dict]:
    """Get model info by name (partial match)."""
    for key, info in MODELS.items():
        if key in model_name.lower():
            return info
    return None
