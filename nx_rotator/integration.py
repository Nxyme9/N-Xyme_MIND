"""
NxRotator Integration Layer
===========================

Integrates NxRotator into the infrastructure proxy layer.
Provides ON/OFF toggle for multi-key rotation.

Usage:
    # Enable in opencode.json:
    "nx_rotator": {
        "enabled": true,
        "fallback_to_single": true
    }

    # Then import:
    from nx_rotator_integration import get_rotator_client
    client = get_rotator_client()
    result = client.chat("model", messages)
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional

# Import the core rotator
from nx_rotator.core.aggregator import NxRotator, RequestResult

# ============================================================
# Configuration
# ============================================================

# Try to load from configs/api-keys/nx_rotator.json (not opencode.json - causes schema validation errors)
_CONFIG_PATH = Path("configs/api-keys/nx_rotator.json")
_NX_ROTATOR_CONFIG: Dict = {}


def _load_config():
    """Load nx_rotator config from configs/api-keys/nx_rotator.json."""
    global _NX_ROTATOR_CONFIG
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            config = json.load(f)
        _NX_ROTATOR_CONFIG = config
    return _NX_ROTATOR_CONFIG


def is_enabled() -> bool:
    """Check if nx_rotator is enabled."""
    config = _load_config()
    return config.get("enabled", False)


def get_fallback_mode() -> bool:
    """Check if should fallback to single key on failure."""
    config = _load_config()
    return config.get("fallback_to_single", True)


# ============================================================
# Singleton Instance
# ============================================================

_rotator_instance: Optional[NxRotator] = None


def get_rotator() -> Optional[NxRotator]:
    """Get singleton rotator instance (lazy init)."""
    global _rotator_instance
    if not is_enabled():
        return None
    if _rotator_instance is None:
        _rotator_instance = NxRotator()
        print(f"[NxRotator] Enabled - using {len(_rotator_instance.keys)} keys")
    return _rotator_instance


# ============================================================
# Client Wrapper (implements same interface as old proxy)
# ============================================================


class RotatorClient:
    """
    Drop-in replacement for OpenRouter API calls.

    Provides same interface as the old single-key approach,
    but with multi-key rotation when enabled.
    """

    def __init__(self):
        self._rotator = get_rotator()
        self._fallback = get_fallback_mode()
        self._single_key = os.getenv("OPENROUTER_API_KEY", "")

    def chat(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
        **kwargs,
    ) -> RequestResult:
        """
        Send chat request.

        If nx_rotator enabled: uses multi-key rotation
        Otherwise: uses single key from env var
        """
        # Use nx_rotator if enabled
        if self._rotator:
            return self._rotator.chat(model, messages, max_tokens, temperature)

        # Fallback to single key
        if not self._single_key:
            return RequestResult(
                success=False, error="No OPENROUTER_API_KEY set and nx_rotator disabled"
            )

        # Make single-key request (old approach)
        import requests

        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._single_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://n-xyme.github.io",
                    "X-Title": "N-Xyme MIND",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60,
            )

            if resp.status_code == 200:
                return RequestResult(
                    success=True,
                    response=resp.json(),
                    key_used="single-key",
                    latency_ms=0,
                )
            else:
                return RequestResult(
                    success=False,
                    error=resp.text[:200],
                    key_used="single-key",
                )
        except Exception as e:
            return RequestResult(
                success=False,
                error=str(e),
                key_used="single-key",
            )

    def get_stats(self) -> Dict:
        """Get rotator stats."""
        if self._rotator:
            return self._rotator.get_all_stats()
        return {"enabled": False}


# ============================================================
# Factory Function
# ============================================================

_client_instance: Optional[RotatorClient] = None


def get_rotator_client() -> RotatorClient:
    """Get singleton client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = RotatorClient()
    return _client_instance


# ============================================================
# Convenience
# ============================================================


def chat(model: str, messages: List[Dict], **kwargs) -> RequestResult:
    """Quick chat function."""
    return get_rotator_client().chat(model, messages, **kwargs)


def toggle(enabled: bool = None) -> bool:
    """
    Toggle nx_rotator on/off.

    Args:
        enabled: True to enable, False to disable, None to toggle

    Returns:
        Current enabled state
    """
    global _rotator_instance, _client_instance

    if enabled is None:
        enabled = not is_enabled()

    # Update config directly (no nested nx_rotator key)
    config = {"enabled": enabled, "fallback_to_single": True}

    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # Reset instances
    _rotator_instance = None
    _client_instance = None

    print(f"[NxRotator] {'Enabled' if enabled else 'Disabled'}")
    return enabled


def status() -> Dict:
    """Get current status."""
    config = _load_config()
    client = get_rotator_client()

    return {
        "enabled": is_enabled(),
        "config": config,
        "stats": client.get_stats(),
    }
