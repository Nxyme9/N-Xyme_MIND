#!/usr/bin/env python3
"""
OpenCode Integration Module

Import this in your code to get automatic key rotation:
    from scripts.opencode_integration import get_openrouter_config

    config = get_openrouter_config()
    # config = {"api_key": "...", "model": "..."}
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from key_rotator_v3 import UltimateKeyRotator

# Singleton rotator instance
_rotator: Optional[UltimateKeyRotator] = None


def get_rotator() -> UltimateKeyRotator:
    """Get or create rotator instance."""
    global _rotator
    if _rotator is None:
        _rotator = UltimateKeyRotator()
    return _rotator


def get_openrouter_config() -> Dict[str, str]:
    """
    Get current OpenRouter configuration (API key + model).
    Use this for direct API calls.
    """
    rotator = get_rotator()
    key = rotator.get_current_key("openrouter")
    model = rotator.get_current_model()

    return {
        "api_key": key.key if key else "",
        "model": model.model_id if model else "openrouter/auto",
        "key_id": key.key_id if key else "",
        "context_limit": model.context_limit if model else 0,
    }


def rotate_on_error(error_message: str) -> bool:
    """
    Check if error is rate limit and rotate if needed.
    Returns True if rotation occurred.
    """
    rotator = get_rotator()
    return rotator.check_error_and_rotate(error_message)


def rotate() -> None:
    """Force rotation to next key/model."""
    rotator = get_rotator()
    rotator.rotate("openrouter")
    rotator.rotate_model()
    key = rotator.get_current_key("openrouter")
    model = rotator.get_current_model()
    if key:
        rotator.update_env_file(key.key, model.model_id if model else None)


def health_check() -> Dict:
    """Get health status."""
    rotator = get_rotator()
    return rotator.health_check()


def sync_env() -> None:
    """Sync current key to .env file."""
    rotator = get_rotator()
    key = rotator.get_current_key("openrouter")
    model = rotator.get_current_model()
    if key:
        rotator.update_env_file(key.key, model.model_id if model else None)


# For direct CLI usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenCode Integration")
    parser.add_argument("action", choices=["config", "rotate", "health", "sync"])
    args = parser.parse_args()

    if args.action == "config":
        config = get_openrouter_config()
        print(f"API Key: {config['api_key'][:30]}...")
        print(f"Model: {config['model']}")
        print(f"Key ID: {config['key_id']}")
        print(f"Context: {config['context_limit']:,}")

    elif args.action == "rotate":
        rotate()
        config = get_openrouter_config()
        print(f"Rotated to: {config['key_id']} / {config['model']}")

    elif args.action == "health":
        health = health_check()
        print(health)

    elif args.action == "sync":
        sync_env()
        print("Synced to .env")
