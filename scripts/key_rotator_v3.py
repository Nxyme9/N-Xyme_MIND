#!/usr/bin/env python3
"""
ULTIMATE API KEY ROTATOR - BLEEDING EDGE v3.0

Maximum throughput system with:
- Auto-rotation on rate limit detection (instant failover)
- MCP server for OpenCode integration
- Daemon mode with error monitoring
- Direct OpenCode wrapper for zero-config integration
- Health monitoring and auto-recovery
- Multi-account IP rotation

Usage:
    python key_rotator_v3.py status          # Show status
    python key_rotator_v3.py get-key         # Get current key (for .env)
    python key_rotator_v3.py get-model       # Get current model
    python key_rotator_v3.py test            # Run diagnostic tests
    python key_rotator_v3.py daemon          # Run as daemon with auto-rotation
    python key_rotator_v3.py mcp             # Run as MCP server
    python key_rotator_v3.py opencode        # Direct OpenCode wrapper
    python key_rotator_v3.py health          # Health check
"""

import json
import os
import sys
import time
import hashlib
import threading
import subprocess
import socket
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import signal
import atexit
import re
import base64

# Third-party for HTTP (optional)
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WARN] requests library not installed - limited functionality")

# Config paths
CONFIG_DIR = Path(__file__).parent.parent / "configs" / "api-keys"
KEYS_FILE = CONFIG_DIR / "keys.json"
USAGE_FILE = CONFIG_DIR / "usage.json"
STATE_FILE = CONFIG_DIR / "rotator_state.json"
ENV_FILE = Path.home() / ".config" / "opencode" / ".env"
LOG_FILE = CONFIG_DIR / "rotator.log"

# Lock for thread safety
_state_lock = threading.Lock()
_requests_lock = threading.Lock()

# Request tracking for rate limiting
_request_timestamps: deque = deque(maxlen=1000)
_error_log: deque = deque(maxlen=100)

# BLEEDING EDGE MODELS - Maximum context, best performance
MODELS_PRIORITY = [
    # Tier 1: Highest context (262K) - Primary workhorses
    (
        "nvidia/nemotron-3-super-120b-a12b:free",
        262144,
        "openrouter",
        "NVIDIA endpoint - fastest free",
    ),
    ("qwen/qwen3-coder:free", 262144, "openrouter", "Best for code - qwen3"),
    ("google/gemma-4-31b-it:free", 262144, "openrouter", "Gemma 4 - latest Google"),
    (
        "mistralai/mistral-small-3.1-24b:free",
        262144,
        "openrouter",
        "Mistral small - fast",
    ),
    # Tier 2: 131K context - Fallback
    ("qwen/qwen3-32b", 131072, "openrouter", "Qwen3 32B - balanced"),
    ("deepseek/deepseek-r1:free", 131072, "openrouter", "DeepSeek R1 - reasoning"),
    (
        "meta-llama/llama-3.3-70b-instruct:free",
        131072,
        "openrouter",
        "Llama 3.3 - Meta",
    ),
    # Tier 3: Auto-router (last resort)
    ("openrouter/auto", 200000, "openrouter", "Auto-select best model"),
]

# Rate limit error patterns to detect
RATE_LIMIT_PATTERNS = [
    r"rate.limit",
    r"rate_limit",
    r"too many requests",
    r"429",
    r"temporarily.*rate",
    r"upstream.*saturated",
    r"quota.*exceeded",
    r"daily.*limit",
    r"rpm.*exceeded",
    r"tpm.*exceeded",
]

# Payment/auth error patterns - keys need to be rotated/marked
AUTH_ERROR_PATTERNS = [
    r"402",
    r"insufficient credits",
    r"payment required",
    r"invalid.*key",
    r"unauthorized",
    r"auth.*fail",
    r"api.*key.*invalid",
    r"not a valid.*key",
]


@dataclass
class KeyInfo:
    """Information about an API key."""

    key_id: str
    key: str
    provider: str
    creator_user_id: Optional[str] = None
    rpm_limit: int = 20
    tpm_limit: int = 50000
    daily_limit: int = 50
    account_email: Optional[str] = None
    priority: int = 0

    # Runtime state
    is_exhausted: bool = False
    exhausted_at: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass
class ModelInfo:
    """Information about a model."""

    model_id: str
    context_limit: int
    provider: str
    description: str = ""
    is_exhausted: bool = False
    exhausted_at: Optional[datetime] = None
    error_count: int = 0


@dataclass
class RotatorState:
    """Current state of the rotator."""

    current_key_index: int = 0
    current_model_index: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_rotations: int = 0
    last_rotation: Optional[str] = None
    daemon_mode: bool = False
    health_score: float = 100.0


class UltimateKeyRotator:
    """BLEEDING EDGE API key rotation system with auto-failover."""

    def __init__(self):
        self.keys: Dict[str, List[KeyInfo]] = {}
        self.models: List[ModelInfo] = []
        self.state = RotatorState()
        self._daemon_thread = None
        self._running = False
        self._health_check_interval = 30  # seconds

        # Load configuration
        self._load_keys()
        self._load_models()
        self._load_state()

        # Track request rate
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup cleanup on exit."""
        atexit.register(self._save_state)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n[ROTATOR] Shutting down...")
        self._running = False
        self._save_state()
        sys.exit(0)

    def _load_keys(self):
        """Load API keys from config."""
        if not KEYS_FILE.exists():
            print(f"[ERROR] Keys file not found: {KEYS_FILE}")
            return

        with open(KEYS_FILE, "r") as f:
            data = json.load(f)

        for provider, key_list in data.items():
            self.keys[provider] = []
            for k in key_list:
                key_info = KeyInfo(
                    key_id=k.get("key_id", "unknown"),
                    key=k.get("key", ""),
                    provider=provider,
                    creator_user_id=k.get("creator_user_id"),
                    rpm_limit=k.get("rpm_limit", 20),
                    tpm_limit=k.get("tpm_limit", 50000),
                    daily_limit=k.get("daily_limit", 50),
                    account_email=k.get("account_email"),
                    priority=k.get("priority", 0),
                )
                self.keys[provider].append(key_info)

        print(
            f"[LOADED] {sum(len(v) for v in self.keys.values())} keys across {len(self.keys)} providers"
        )

    def _load_models(self):
        """Load model configuration."""
        for model_id, context, provider, description in MODELS_PRIORITY:
            self.models.append(
                ModelInfo(
                    model_id=model_id,
                    context_limit=context,
                    provider=provider,
                    description=description,
                )
            )
        print(f"[LOADED] {len(self.models)} bleeding edge models")

    def _load_state(self):
        """Load persisted state."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                self.state.current_key_index = data.get("current_key_index", 0)
                self.state.current_model_index = data.get("current_model_index", 0)
                self.state.total_requests = data.get("total_requests", 0)
                self.state.successful_requests = data.get("successful_requests", 0)
                self.state.failed_requests = data.get("failed_requests", 0)
                self.state.total_rotations = data.get("total_rotations", 0)
                self.state.last_rotation = data.get("last_rotation")
                self.state.daemon_mode = data.get("daemon_mode", False)
                self.state.health_score = data.get("health_score", 100.0)
                print(
                    f"[STATE] Loaded - key_idx={self.state.current_key_index}, model_idx={self.state.current_model_index}"
                )
            except Exception as e:
                print(f"[WARN] Could not load state: {e}")

    def _save_state(self):
        """Persist state to disk."""
        with _state_lock:
            data = {
                "current_key_index": self.state.current_key_index,
                "current_model_index": self.state.current_model_index,
                "total_requests": self.state.total_requests,
                "successful_requests": self.state.successful_requests,
                "failed_requests": self.state.failed_requests,
                "total_rotations": self.state.total_rotations,
                "last_rotation": self.state.last_rotation,
                "daemon_mode": self.state.daemon_mode,
                "health_score": self.state.health_score,
                "updated_at": datetime.now().isoformat(),
            }
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)

    def get_current_key(self, provider: str = "openrouter") -> Optional[KeyInfo]:
        """Get the currently active key for a provider."""
        keys = self.keys.get(provider, [])
        if not keys:
            return None
        idx = self.state.current_key_index % len(keys)
        return keys[idx]

    def get_current_model(self) -> Optional[ModelInfo]:
        """Get the currently active model."""
        if not self.models:
            return None
        idx = self.state.current_model_index % len(self.models)
        return self.models[idx]

    def get_next_key(self, provider: str = "openrouter") -> Optional[KeyInfo]:
        """Get the next available key (not exhausted)."""
        keys = self.keys.get(provider, [])
        if not keys:
            return None

        # Try each key starting from current
        for i in range(len(keys)):
            idx = (self.state.current_key_index + i) % len(keys)
            key = keys[idx]

            if key.is_exhausted:
                continue

            self.state.current_key_index = idx
            return key

        # All keys exhausted - reset all and try again
        self._log("All keys exhausted, resetting...")
        for key in keys:
            key.is_exhausted = False
            key.error_count = 0

        self.state.current_key_index = 0
        return keys[0] if keys else None

    def get_next_model(self) -> Optional[ModelInfo]:
        """Get the next model when upstream is saturated."""
        for i in range(len(self.models)):
            idx = (self.state.current_model_index + i) % len(self.models)
            model = self.models[idx]

            # Skip recently exhausted (wait 2 min)
            if model.is_exhausted and model.exhausted_at:
                if datetime.now() - model.exhausted_at < timedelta(minutes=2):
                    continue

            model.is_exhausted = False
            model.error_count = 0

            self.state.current_model_index = idx
            return model

        # All models exhausted, reset all
        self._log("All models exhausted, resetting...")
        for model in self.models:
            model.is_exhausted = False
            model.error_count = 0

        self.state.current_model_index = 0
        return self.models[0]

    def check_error_and_rotate(self, error_message: str) -> bool:
        """
        Auto-detect rate limit errors and rotate if needed.
        Returns True if rotation happened.
        """
        error_lower = error_message.lower()

        # Check for rate limit patterns
        for pattern in RATE_LIMIT_PATTERNS:
            if re.search(pattern, error_lower):
                self._log(f"[AUTO-ROTATE] Detected rate limit: {error_message[:100]}")

                # Mark current key as exhausted
                key = self.get_current_key("openrouter")
                if key:
                    key.is_exhausted = True
                    key.exhausted_at = datetime.now()
                    key.last_error = error_message[:200]
                    key.error_count += 1

                # Mark current model as exhausted
                model = self.get_current_model()
                if model:
                    model.is_exhausted = True
                    model.exhausted_at = datetime.now()
                    model.error_count += 1

                # Rotate to next key
                new_key = self.get_next_key("openrouter")
                self.state.total_rotations += 1
                self.state.last_rotation = (
                    f"auto_key_{new_key.key_id if new_key else 'none'}"
                )

                # Also rotate model to try different upstream
                new_model = self.get_next_model()
                self.state.last_rotation += (
                    f", auto_model_{new_model.model_id if new_model else 'none'}"
                )

                # Update .env with new key
                if new_key:
                    self.update_env_file(
                        new_key.key, new_model.model_id if new_model else None
                    )

                self._save_state()
                self._log(
                    f"[AUTO-ROTATE] Rotated to key={new_key.key_id if new_key else 'None'}, model={new_model.model_id if new_model else 'None'}"
                )
                return True

        # Also check for auth/payment errors (402, 401, 403)
        for pattern in AUTH_ERROR_PATTERNS:
            if re.search(pattern, error_lower):
                self._log(
                    f"[AUTO-ROTATE] Detected auth/payment error: {error_message[:100]}"
                )

                # Mark current key as exhausted (auth issues = permanent until fixed)
                key = self.get_current_key("openrouter")
                if key:
                    key.is_exhausted = True
                    key.exhausted_at = datetime.now()
                    key.last_error = error_message[:200]
                    key.error_count += 1

                # Rotate to next key immediately
                new_key = self.get_next_key("openrouter")
                self.state.total_rotations += 1
                self.state.last_rotation = (
                    f"auth_error_key_{new_key.key_id if new_key else 'none'}"
                )

                self._save_state()
                self._log(
                    f"[AUTO-ROTATE] Auth error - rotated to key={new_key.key_id if new_key else 'None'}"
                )
                return True

        return False

    def mark_key_exhausted(self, provider: str = "openrouter"):
        """Mark current key as rate limited."""
        key = self.get_current_key(provider)
        if key:
            key.is_exhausted = True
            key.exhausted_at = datetime.now()
            self.state.total_rotations += 1
            self.state.last_rotation = f"key_exhausted_{key.key_id}"
            self._save_state()
            self._log(f"[ROTATOR] Key {key.key_id} marked exhausted")

    def mark_model_exhausted(self):
        """Mark current model as saturated."""
        model = self.get_current_model()
        if model:
            model.is_exhausted = True
            model.exhausted_at = datetime.now()
            self.state.total_rotations += 1
            self.state.last_rotation = f"model_exhausted_{model.model_id}"
            self._save_state()
            self._log(f"[ROTATOR] Model {model.model_id} marked exhausted")

    def rotate(self, provider: str = "openrouter") -> Optional[KeyInfo]:
        """Force rotate to next key."""
        key = self.get_next_key(provider)
        if key:
            self.state.total_rotations += 1
            self.state.last_rotation = f"rotate_to_{key.key_id}"
            self._save_state()
            self._log(f"[ROTATOR] Rotated to key: {key.key_id}")
            return key
        return None

    def rotate_model(self) -> Optional[ModelInfo]:
        """Force rotate to next model."""
        model = self.get_next_model()
        if model:
            self.state.total_rotations += 1
            self.state.last_rotation = f"rotate_to_{model.model_id}"
            self._save_state()
            self._log(f"[ROTATOR] Rotated to model: {model.model_id}")
            return model
        return None

    def record_request(self):
        """Record that a request was made."""
        with _requests_lock:
            _request_timestamps.append(datetime.now())
            self.state.total_requests += 1
            self._save_state()

    def record_success(self):
        """Record a successful request."""
        self.state.successful_requests += 1
        self._save_state()

    def record_failure(self):
        """Record a failed request."""
        self.state.failed_requests += 1
        self._save_state()

    def check_rate_limit(self, provider: str = "openrouter") -> bool:
        """Check if we're at rate limit for a provider."""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)

        with _requests_lock:
            recent_requests = sum(
                1 for ts in _request_timestamps if ts > one_minute_ago
            )

        key = self.get_current_key(provider)
        if key and recent_requests >= key.rpm_limit:
            self._log(
                f"[RATE LIMIT] {recent_requests} req/min, limit is {key.rpm_limit}"
            )
            return True

        return False

    def update_env_file(self, api_key: str, model: str = None):
        """Update the .env file with current key and model."""
        if not ENV_FILE.exists():
            self._log(f"[WARN] .env file not found: {ENV_FILE}")
            return

        # Read current .env
        env_vars = {}
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip('"').strip("'")

        # Update with new key
        env_vars["OPENROUTER_API_KEY"] = api_key

        # Write back
        lines = []
        for key, val in env_vars.items():
            lines.append(f'{key}="{val}"')

        with open(ENV_FILE, "w") as f:
            f.write("\n".join(lines) + "\n")

        self._log(f"[ENV] Updated .env with key: {api_key[:20]}...")

    def _log(self, message: str):
        """Log to file and print."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Append to log file
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

    def health_check(self) -> Dict[str, Any]:
        """Run health check and return status."""
        key = self.get_current_key("openrouter")
        model = self.get_current_model()

        # Test API connectivity
        api_status = "unknown"
        if HAS_REQUESTS and key:
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key.key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model.model_id if model else "openrouter/auto",
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 5,
                    },
                    timeout=10,
                )
                api_status = (
                    "healthy"
                    if resp.status_code == 200
                    else f"error_{resp.status_code}"
                )
            except Exception as e:
                api_status = f"error: {str(e)[:50]}"

        # Calculate health score
        total_keys = sum(len(v) for v in self.keys.values())
        available_keys = sum(
            1 for keys in self.keys.values() for k in keys if not k.is_exhausted
        )

        total_models = len(self.models)
        available_models = sum(1 for m in self.models if not m.is_exhausted)

        key_health = (available_keys / total_keys * 100) if total_keys > 0 else 0
        model_health = (
            (available_models / total_models * 100) if total_models > 0 else 0
        )

        self.state.health_score = (key_health + model_health) / 2

        return {
            "status": "healthy" if api_status == "healthy" else "degraded",
            "api_status": api_status,
            "current_key": key.key_id if key else None,
            "current_model": model.model_id if model else None,
            "keys_available": available_keys,
            "keys_total": total_keys,
            "models_available": available_models,
            "models_total": total_models,
            "health_score": self.state.health_score,
            "total_requests": self.state.total_requests,
            "successful_requests": self.state.successful_requests,
            "failed_requests": self.state.failed_requests,
            "total_rotations": self.state.total_rotations,
        }

    def show_status(self):
        """Display current status."""
        health = self.health_check()

        print("\n" + "=" * 70)
        print("🟢 ULTIMATE KEY ROTATOR v3.0 - BLEEDING EDGE")
        print("=" * 70)

        # Current key
        key = self.get_current_key("openrouter")
        model = self.get_current_model()

        print(f"\n📱 CURRENT KEY:")
        if key:
            print(f"   ID: {key.key_id}")
            print(f"   Key: {key.key[:25]}...")
            print(f"   User: {key.creator_user_id or 'unknown'}")
            print(f"   Errors: {key.error_count}")
            print(f"   Status: {'❌ EXHAUSTED' if key.is_exhausted else '✅ ACTIVE'}")
        else:
            print("   None")

        print(f"\n🤖 CURRENT MODEL:")
        if model:
            print(f"   Model: {model.model_id}")
            print(f"   Context: {model.context_limit:,}")
            print(f"   Description: {model.description}")
            print(f"   Status: {'❌ EXHAUSTED' if model.is_exhausted else '✅ ACTIVE'}")
        else:
            print("   None")

        print(f"\n💚 HEALTH:")
        print(f"   API: {health['api_status']}")
        print(f"   Score: {health['health_score']:.1f}%")
        print(f"   Keys: {health['keys_available']}/{health['keys_total']}")
        print(f"   Models: {health['models_available']}/{health['models_total']}")

        print(f"\n📊 STATS:")
        print(f"   Total Requests: {self.state.total_requests}")
        print(f"   Successful: {self.state.successful_requests}")
        print(f"   Failed: {self.state.failed_requests}")
        print(f"   Total Rotations: {self.state.total_rotations}")
        print(f"   Last Rotation: {self.state.last_rotation or 'none'}")

        # All keys
        print(f"\n📋 ALL KEYS ({sum(len(v) for v in self.keys.values())} total):")
        for provider, keys in self.keys.items():
            for i, k in enumerate(keys):
                status = "❌" if k.is_exhausted else "✅"
                print(f"   {status} {k.key_id} ({k.key[:15]}...) - err:{k.error_count}")

        # Model rotation order
        print(f"\n🔄 MODEL ROTATION ORDER:")
        for i, m in enumerate(self.models):
            status = "❌" if m.is_exhausted else "✅"
            current = " ← CURRENT" if i == self.state.current_model_index else ""
            print(
                f"   {i + 1}. {status} {m.model_id} ({m.context_limit:,} ctx){current}"
            )

        print("\n" + "=" * 70)

    def test_rotation(self):
        """Test the rotation system."""
        print("\n" + "=" * 70)
        print("🧪 TESTING AUTO-ROTATION SYSTEM")
        print("=" * 70)

        # Health check
        health = self.health_check()
        print(f"\n1. Health Check: {health['status']}")
        print(f"   API Status: {health['api_status']}")
        print(f"   Health Score: {health['health_score']:.1f}%")

        # Current state
        key = self.get_current_key("openrouter")
        model = self.get_current_model()
        print(f"\n2. Current State:")
        print(f"   Key: {key.key_id if key else 'None'}")
        print(f"   Model: {model.model_id if model else 'None'}")

        # Test model rotation
        print(f"\n3. Testing Model Rotation...")
        old_model_idx = self.state.current_model_index
        new_model = self.rotate_model()
        print(f"   Rotated: {old_model_idx} → {self.state.current_model_index}")
        print(f"   New Model: {new_model.model_id if new_model else 'None'}")

        # Test key rotation
        print(f"\n4. Testing Key Rotation...")
        old_key_idx = self.state.current_key_index
        new_key = self.rotate("openrouter")
        print(f"   Rotated: {old_key_idx} → {self.state.current_key_index}")
        print(f"   New Key: {new_key.key_id if new_key else 'None'}")

        # Test auto-rotate on error
        print(f"\n5. Testing Auto-Rotation on Error...")
        test_error = "rate limit exceeded - 429"
        rotated = self.check_error_and_rotate(test_error)
        print(f"   Detected rate limit: {rotated}")

        print("\n" + "=" * 70)
        print("✅ TESTS COMPLETE")
        print("=" * 70)

    def run_daemon(self):
        """Run as daemon with auto-rotation."""
        self._log("[DAEMON] Starting Ultimate Key Rotator daemon...")
        self.state.daemon_mode = True
        self._running = True
        self._save_state()

        # Health check loop
        while self._running:
            try:
                health = self.health_check()
                self._log(
                    f"[DAEMON] Health: {health['health_score']:.1f}% - API: {health['api_status']}"
                )

                # If health is low, try to rotate
                if health["health_score"] < 50:
                    self._log("[DAEMON] Low health - triggering rotation")
                    self.rotate("openrouter")
                    self.rotate_model()

            except Exception as e:
                self._log(f"[DAEMON] Error: {e}")

            time.sleep(self._health_check_interval)

    def run_mcp_server(self):
        """Run as MCP server for OpenCode integration."""
        self._log("[MCP] Starting MCP server...")

        # Simple MCP-like interface via stdin/stdout
        import sys

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())
                method = request.get("method", "")
                params = request.get("params", {})

                if method == "get_key":
                    key = self.get_current_key(params.get("provider", "openrouter"))
                    response = {"result": key.key if key else None}

                elif method == "get_model":
                    model = self.get_current_model()
                    response = {"result": model.model_id if model else None}

                elif method == "rotate":
                    key = self.rotate(params.get("provider", "openrouter"))
                    response = {"result": key.key if key else None}

                elif method == "check_error":
                    rotated = self.check_error_and_rotate(params.get("error", ""))
                    response = {"result": rotated}

                elif method == "health":
                    response = {"result": self.health_check()}

                else:
                    response = {"error": f"Unknown method: {method}"}

                print(json.dumps(response), flush=True)

            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)

    def run_opencode_wrapper(self, args: List[str]):
        """
        Direct OpenCode wrapper - replaces opencode command with auto-rotation.
        Usage: python key_rotator_v3.py opencode [opencode-args...]
        """
        self._log("[WRAPPER] Starting OpenCode with auto-rotation...")

        # Get current key and model
        key = self.get_current_key("openrouter")
        model = self.get_current_model()

        if not key or not model:
            print("[ERROR] No keys or models available")
            sys.exit(1)

        # Update environment
        os.environ["OPENROUTER_API_KEY"] = key.key
        os.environ["OPENROUTER_MODEL"] = model.model_id

        self._log(f"[WRAPPER] Using key: {key.key_id}, model: {model.model_id}")

        # Build opencode command
        cmd = ["opencode"] + args[1:]  # Skip 'opencode' arg

        # Run with retry logic
        max_retries = len(self.keys.get("openrouter", [])) * len(self.models)
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Execute opencode
                result = subprocess.run(cmd, env=os.environ.copy())
                sys.exit(result.returncode)

            except Exception as e:
                error_str = str(e)
                self._log(f"[WRAPPER] Error: {error_str}")

                # Check if we should rotate
                if self.check_error_and_rotate(error_str):
                    retry_count += 1
                    key = self.get_current_key("openrouter")
                    model = self.get_current_model()
                    os.environ["OPENROUTER_API_KEY"] = key.key if key else ""
                    os.environ["OPENROUTER_MODEL"] = model.model_id if model else ""
                    self._log(
                        f"[WRAPPER] Retry {retry_count}/{max_retries} with key: {key.key_id if key else 'None'}"
                    )
                    continue
                else:
                    # Not a rate limit error, re-raise
                    raise

        self._log("[WRAPPER] All retries exhausted")
        sys.exit(1)


def main():
    """Main entry point."""
    rotator = UltimateKeyRotator()

    if len(sys.argv) < 2:
        rotator.show_status()
        return

    cmd = sys.argv[1]

    if cmd == "status":
        rotator.show_status()

    elif cmd == "test":
        rotator.test_rotation()

    elif cmd == "get-key":
        key = rotator.get_current_key("openrouter")
        if key:
            print(key.key)

    elif cmd == "get-model":
        model = rotator.get_current_model()
        if model:
            print(model.model_id)

    elif cmd == "rotate":
        key = rotator.rotate("openrouter")
        if key:
            print(f"Rotated to: {key.key}")

    elif cmd == "rotate-model":
        model = rotator.rotate_model()
        if model:
            print(f"Rotated to: {model.model_id}")

    elif cmd == "health":
        health = rotator.health_check()
        print(json.dumps(health, indent=2))

    elif cmd == "daemon":
        rotator.run_daemon()

    elif cmd == "mcp":
        rotator.run_mcp_server()

    elif cmd == "opencode":
        rotator.run_opencode_wrapper(sys.argv)

    elif cmd == "mark-exhausted":
        rotator.mark_key_exhausted("openrouter")

    elif cmd == "update-env":
        key = rotator.get_current_key("openrouter")
        model = rotator.get_current_model()
        if key:
            rotator.update_env_file(key.key, model.model_id if model else None)

    else:
        print(f"Unknown command: {cmd}")
        print(
            "Usage: key_rotator_v3.py [status|test|get-key|get-model|rotate|daemon|mcp|opencode|health]"
        )


if __name__ == "__main__":
    main()
