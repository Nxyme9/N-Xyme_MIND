#!/usr/bin/env python3
"""
OpenCode Auto-Rotation Middleware

This script wraps OpenCode and automatically handles rate limits by:
1. Intercepts API errors from OpenCode
2. Detects rate limit errors
3. Rotates to next key/model automatically
4. Retries the request

Usage:
    # Replace opencode command in your shell
    alias opencode='python /path/to/scripts/opencode_wrapper.py'

    # Or run directly
    python scripts/opencode_wrapper.py [opencode-args]
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the rotator
from key_rotator_v3 import UltimateKeyRotator


class OpenCodeWrapper:
    """Wrapper that adds auto-rotation to OpenCode."""

    def __init__(self):
        self.rotator = UltimateKeyRotator()
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def setup_environment(self):
        """Set up environment with current key/model."""
        key = self.rotator.get_current_key("openrouter")
        model = self.rotator.get_current_model()

        if key:
            os.environ["OPENROUTER_API_KEY"] = key.key
            print(f"[WRAPPER] Using key: {key.key_id}")

        if model:
            os.environ["OPENROUTER_MODEL"] = model.model_id
            print(f"[WRAPPER] Using model: {model.model_id}")

        # Also update .env for persistence
        self.rotator.update_env_file(key.key, model.model_id if model else None)

    def run_with_rotation(self, args: list) -> int:
        """
        Run opencode with automatic rotation on rate limits.
        """
        # Get current key/model
        key = self.rotator.get_current_key("openrouter")
        model = self.rotator.get_current_model()

        if not key or not model:
            print("[ERROR] No keys or models available")
            return 1

        # Set environment
        os.environ["OPENROUTER_API_KEY"] = key.key
        os.environ["OPENROUTER_MODEL"] = model.model_id

        # Build command - use opencode from PATH
        cmd = ["opencode"] + args[1:]  # Skip script name

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                # Record request
                self.rotator.record_request()

                # Run opencode
                result = subprocess.run(cmd, env=os.environ.copy(), text=True)

                # Check exit code
                if result.returncode == 0:
                    # Success - sync state
                    self.rotator._save_state()
                    return 0

                # Check for rate limit in output
                output = result.stdout + result.stderr

                if self._is_rate_limit(output):
                    print(f"[WRAPPER] Rate limit detected, rotating...")

                    # Mark current key/model as exhausted
                    self.rotator.mark_key_exhausted("openrouter")
                    self.rotator.mark_model_exhausted()

                    # Get new key/model
                    key = self.rotator.get_next_key("openrouter")
                    model = self.rotator.get_next_model()

                    if key and model:
                        os.environ["OPENROUTER_API_KEY"] = key.key
                        os.environ["OPENROUTER_MODEL"] = model.model_id
                        self.rotator.update_env_file(key.key, model.model_id)

                        print(
                            f"[WRAPPER] Retrying with key={key.key_id}, model={model.model_id}"
                        )
                        retry_count += 1
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        print("[ERROR] No more keys/models available")
                        return 1
                else:
                    # Other error - just return
                    print(result.stderr)
                    return result.returncode

            except Exception as e:
                error_str = str(e)
                last_error = error_str

                # Check if it's a rate limit error
                if self._is_rate_limit(error_str):
                    print(f"[WRAPPER] Rate limit in exception, rotating...")
                    self.rotator.mark_key_exhausted("openrouter")
                    self.rotator.mark_model_exhausted()

                    key = self.rotator.get_next_key("openrouter")
                    model = self.rotator.get_next_model()

                    if key and model:
                        os.environ["OPENROUTER_API_KEY"] = key.key
                        os.environ["OPENROUTER_MODEL"] = model.model_id
                        retry_count += 1
                        time.sleep(self.retry_delay)
                        continue

                print(f"[ERROR] {error_str}")
                return 1

        print(f"[ERROR] Max retries ({self.max_retries}) exceeded")
        if last_error:
            print(f"Last error: {last_error}")
        return 1

    def _is_rate_limit(self, text: str) -> bool:
        """Check if text contains rate limit error."""
        text_lower = text.lower()
        patterns = [
            "rate limit",
            "429",
            "too many requests",
            "temporarily",
            "quota",
            "daily limit",
            "rpm limit",
            "upstream saturated",
        ]
        return any(p in text_lower for p in patterns)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: opencode_wrapper.py [opencode-args]")
        print('Example: opencode_wrapper.py chat "Hello"')
        sys.exit(1)

    wrapper = OpenCodeWrapper()

    # Setup environment
    wrapper.setup_environment()

    # Run with rotation
    exit_code = wrapper.run_with_rotation(sys.argv)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
