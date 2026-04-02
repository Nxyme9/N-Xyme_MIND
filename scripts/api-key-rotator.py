#!/usr/bin/env python3
"""
API Key Rotator - The REAL solution for rate limits.

When free tokens run out, rotate to a different API key.
This works because rate limits are per-key, not per-IP.

Usage:
    python scripts/api-key-rotator.py              # Show status
    python scripts/api-key-rotator.py --test        # Test rotation
    python scripts/api-key-rotator.py --rotate      # Force rotate
"""

import json
import os
import time
import requests
from pathlib import Path
from datetime import datetime

# Config paths
CONFIG_DIR = Path(__file__).parent.parent / "configs" / "api-keys"
KEYS_FILE = CONFIG_DIR / "keys.json"
USAGE_FILE = CONFIG_DIR / "usage.json"


class APIKeyRotator:
    """Rotate between multiple API keys when rate limits are hit."""

    def __init__(self):
        self.keys = self.load_keys()
        self.usage = self.load_usage()
        self.current_index = 0

    def load_keys(self):
        """Load API keys from config."""
        if KEYS_FILE.exists():
            with open(KEYS_FILE, "r") as f:
                return json.load(f)
        return {"opencode": [], "openrouter": [], "groq": []}

    def load_usage(self):
        """Load usage stats."""
        if USAGE_FILE.exists():
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_usage(self):
        """Save usage stats."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USAGE_FILE, "w") as f:
            json.dump(self.usage, f, indent=2)

    def get_provider_status(self, provider):
        """Check if provider has available keys."""
        keys = self.keys.get(provider, [])
        if not keys:
            return {"available": False, "reason": "No keys configured"}

        for key_info in keys:
            key = key_info.get("key")
            usage = self.usage.get(key, {"count": 0, "reset_at": None})

            # Check if reset time passed
            if usage.get("reset_at"):
                reset_time = datetime.fromisoformat(usage["reset_at"])
                if datetime.now() > reset_time:
                    usage["count"] = 0
                    usage["reset_at"] = None

            # Check if under limit
            limit = key_info.get("daily_limit", 200)
            if usage["count"] < limit:
                return {
                    "available": True,
                    "key": key,
                    "used": usage["count"],
                    "limit": limit,
                    "remaining": limit - usage["count"],
                }

        return {"available": False, "reason": "All keys exhausted"}

    def get_next_key(self, provider):
        """Get next available API key for provider."""
        keys = self.keys.get(provider, [])

        for i, key_info in enumerate(keys):
            key = key_info.get("key")
            usage = self.usage.get(key, {"count": 0, "reset_at": None})

            # Check if reset time passed
            if usage.get("reset_at"):
                reset_time = datetime.fromisoformat(usage["reset_at"])
                if datetime.now() > reset_time:
                    usage["count"] = 0
                    usage["reset_at"] = None

            # Check if under limit
            limit = key_info.get("daily_limit", 200)
            if usage["count"] < limit:
                self.current_index = i
                return key

        return None

    def record_usage(self, key):
        """Record API usage for a key."""
        if key not in self.usage:
            self.usage[key] = {"count": 0, "reset_at": None}

        self.usage[key]["count"] += 1

        # Set reset time if not set (24 hours from now)
        if not self.usage[key].get("reset_at"):
            reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            reset_time = reset_time.replace(day=reset_time.day + 1)
            self.usage[key]["reset_at"] = reset_time.isoformat()

        self.save_usage()

    def mark_exhausted(self, key):
        """Mark a key as exhausted (hit rate limit)."""
        if key not in self.usage:
            self.usage[key] = {"count": 0, "reset_at": None}

        # Set reset time to tomorrow
        reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        reset_time = reset_time.replace(day=reset_time.day + 1)
        self.usage[key]["reset_at"] = reset_time.isoformat()

        self.save_usage()

    def rotate(self, provider):
        """Rotate to next available key."""
        print(f"\n[ROTATE] Rotating {provider} API key...")

        new_key = self.get_next_key(provider)

        if new_key:
            print(f"[ROTATE] Switched to new key: {new_key[:20]}...")
            return new_key
        else:
            print(f"[ROTATE] ERROR: No available keys for {provider}!")
            print(f"[ROTATE] All keys exhausted. Need to:")
            print(f"  1. Wait for reset (24h)")
            print(f"  2. Add more keys")
            print(f"  3. Switch provider")
            return None

    def show_status(self):
        """Show status of all providers and keys."""
        print("=" * 60)
        print("API KEY ROTATOR STATUS")
        print("=" * 60)

        for provider in ["opencode", "openrouter", "groq"]:
            print(f"\n{provider.upper()}:")
            status = self.get_provider_status(provider)

            if status["available"]:
                print(f"  [OK] Available")
                print(f"  Key: {status['key'][:20]}...")
                print(f"  Used: {status['used']}/{status['limit']}")
                print(f"  Remaining: {status['remaining']}")
            else:
                print(f"  [EXHAUSTED] {status['reason']}")

            # Show all keys
            keys = self.keys.get(provider, [])
            if keys:
                print(f"  Total keys: {len(keys)}")
                for i, key_info in enumerate(keys):
                    key = key_info.get("key")
                    usage = self.usage.get(key, {"count": 0})
                    limit = key_info.get("daily_limit", 200)
                    print(f"    Key {i + 1}: {usage['count']}/{limit} used")

    def test_rotation(self):
        """Test the rotation system."""
        print("\n" + "=" * 60)
        print("API KEY ROTATION TEST")
        print("=" * 60)

        for provider in ["opencode", "openrouter", "groq"]:
            print(f"\n[TEST] Testing {provider}...")

            # Get current key
            current_key = self.get_next_key(provider)
            if current_key:
                print(f"  Current key: {current_key[:20]}...")

            # Simulate exhaustion
            print(f"  Simulating rate limit hit...")
            if current_key:
                self.mark_exhausted(current_key)

            # Rotate to next key
            new_key = self.rotate(provider)

            if new_key:
                print(f"  [SUCCESS] Rotated to: {new_key[:20]}...")
            else:
                print(f"  [FAIL] No more keys available")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)


def setup_example_keys():
    """Create example keys file if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not KEYS_FILE.exists():
        example_keys = {
            "opencode": [
                {"key": "YOUR_OPENCODE_KEY_1", "daily_limit": 200},
                {"key": "YOUR_OPENCODE_KEY_2", "daily_limit": 200},
                {"key": "YOUR_OPENCODE_KEY_3", "daily_limit": 200},
            ],
            "openrouter": [
                {"key": "YOUR_OPENROUTER_KEY_1", "daily_limit": 50},
                {"key": "YOUR_OPENROUTER_KEY_2", "daily_limit": 50},
            ],
            "groq": [
                {"key": "YOUR_GROQ_KEY_1", "daily_limit": 14400},
                {"key": "YOUR_GROQ_KEY_2", "daily_limit": 14400},
            ],
        }

        with open(KEYS_FILE, "w") as f:
            json.dump(example_keys, f, indent=2)

        print(f"[SETUP] Created example keys file: {KEYS_FILE}")
        print(f"[SETUP] Edit this file to add your real API keys")


def main():
    import sys

    # Setup example keys if needed
    setup_example_keys()

    # Create rotator
    rotator = APIKeyRotator()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            rotator.show_status()
        elif arg == "--test":
            rotator.test_rotation()
        elif arg == "--rotate":
            provider = sys.argv[2] if len(sys.argv) > 2 else "opencode"
            rotator.rotate(provider)
        else:
            print(f"Unknown option: {arg}")
            print("Usage: api-key-rotator.py [--status|--test|--rotate [provider]]")
    else:
        rotator.show_status()


if __name__ == "__main__":
    main()
