#!/usr/bin/env python3
"""
Tiered Model Fallback Script

Implements priority-based model fallback with circuit breaker pattern.
Supports OpenAI-compatible API format for all model providers.
"""

import os
import sys
import importlib.util
import json
import time
import random
import argparse
import logging
from typing import Optional
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MODEL_CONFIG = {
    "openrouter/deepseek/deepseek-r1": {
        "name": "DeepSeek R1",
        "tier": "Premium",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "timeout": 60,
    },
    "openrouter/qwen/qwen3-coder": {
        "name": "Qwen3 Coder",
        "tier": "Premium",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "timeout": 60,
    },
    "google/gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "tier": "Google",
        "api_key_env": "GOOGLE_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "timeout": 60,
    },
    os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free"): {
        "name": "Qwen3.6 Plus",
        "tier": "Zen",
        "api_key_env": "OPENCODE_API_KEY",
        "base_url": "https://api.opencode.ai/v1",
        "timeout": 60,
    },
    os.getenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free"): {
        "name": "MiniMax M2.5",
        "tier": "Zen",
        "api_key_env": "OPENCODE_API_KEY",
        "base_url": "https://api.opencode.ai/v1",
        "timeout": 60,
    },
    os.getenv("GGUF_MODEL", "qwen2.5-coder-7b-q4_k_m"): {
        "name": "Qwen2.5 Coder 7B (GGUF)",
        "tier": "Local",
        "api_key_env": "GGUF_API_KEY",
        "base_url": "http://localhost:8080/v1",
        "timeout": 60,
    },
    os.getenv("OLLAMA_MODEL", "ollama/llama3.2:3b"): {
        "name": "Llama 3.2 3B (Ollama - FALLBACK)",
        "tier": "Local",
        "api_key_env": "OLLAMA_API_KEY",
        "base_url": "http://localhost:11434/v1",
        "timeout": 60,
        "is_fallback": True,
    },
}

PRIORITY_MODELS = list(MODEL_CONFIG.keys())


class CircuitBreaker:
    """Circuit breaker pattern implementation for model fallback."""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: int = 300,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        state_file: str = ".cache/circuit-breaker.json",
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.state_file = state_file
        self.failures = {}
        self.last_failure_time = {}
        self._load_state()

    def get_delay(self, failure_count: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = min(self.base_delay * (2**failure_count), self.max_delay)
        if self.jitter:
            delay *= 1 + random.uniform(0, 0.5)
        return delay

    def record_failure(self, model: str) -> None:
        """Record a failure for a model."""
        self.failures[model] = self.failures.get(model, 0) + 1
        self.last_failure_time[model] = time.time()
        logger.warning(
            f"Circuit breaker: {model} now has {self.failures[model]} consecutive failures"
        )
        self._save_state()

    def record_success(self, model: str) -> None:
        """Record a success and reset failure counter."""
        if model in self.failures:
            logger.info(
                f"Circuit breaker: {model} succeeded, resetting failure counter"
            )
        self.failures[model] = 0
        self._save_state()

    def is_available(self, model: str) -> bool:
        """Check if a model is available (not in circuit open state)."""
        if model not in self.failures:
            return True

        if self.failures[model] >= self.failure_threshold:
            elapsed = time.time() - self.last_failure_time.get(model, 0)
            delay = self.get_delay(self.failures[model])
            if elapsed >= delay:
                logger.info(
                    f"Circuit breaker: {model} backoff period expired (delay={delay:.1f}s), allowing retry"
                )
                self.failures[model] = 0
                return True
            remaining = int(delay - elapsed)
            logger.warning(
                f"Circuit breaker: {model} is open, skipping for {remaining}s more (backoff delay={delay:.1f}s)"
            )
            return False
        return True

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        cache_dir = os.path.dirname(self.state_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _save_state(self) -> None:
        """Save circuit breaker state to JSON file."""
        self._ensure_cache_dir()
        state = {
            "failures": self.failures,
            "last_failure_time": self.last_failure_time,
        }
        tmp_file = self.state_file + ".tmp"
        try:
            with open(tmp_file, "w") as f:
                json.dump(state, f)
            os.replace(tmp_file, self.state_file)
        except Exception as e:
            logger.warning(f"Failed to save circuit breaker state: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

    def _load_state(self) -> None:
        """Load circuit breaker state from JSON file."""
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
            self.failures = state.get("failures", {})
            self.last_failure_time = state.get("last_failure_time", {})
            logger.info(f"Loaded circuit breaker state from {self.state_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted circuit breaker state file: {e}, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker state: {e}")


class RateLimiter:
    """Token bucket rate limiter with thread-safe blocking acquire."""

    def __init__(self, max_requests: int = 8, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._tokens = float(max_requests)
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * (self.max_requests / self.window_seconds)
        self._tokens = min(self.max_requests, self._tokens + tokens_to_add)
        self._last_refill = now

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait_time = (1.0 - self._tokens) / (
                    self.max_requests / self.window_seconds
                )
            time.sleep(min(wait_time, 1.0))

    def try_acquire(self) -> bool:
        """Non-blocking attempt to acquire a token."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def get_stats(self) -> dict:
        with self._lock:
            self._refill()
            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "available_tokens": self._tokens,
            }


class ModelFallback:
    """Main class for handling model fallback logic."""

    def __init__(self, model_config: Optional[dict] = None):
        self.model_config = model_config or MODEL_CONFIG
        self.circuit_breaker = CircuitBreaker()
        self.local_router = self._load_local_router().LocalRouter()
        self.rate_limiter = RateLimiter()
        self.model_config = model_config or MODEL_CONFIG
        self.circuit_breaker = CircuitBreaker()
        self.local_router = self._load_local_router().LocalRouter()

    def get_api_key(self, model: str) -> Optional[str]:
        """Get API key from environment for the model."""
        config = self.model_config[model]
        api_key_env = config.get("api_key_env")
        if api_key_env:
            return os.environ.get(api_key_env)

        if config["tier"] == "Local":
            return "ollama"
        return None

    def _validate_api_key(self, model: str) -> bool:
        """Validate that API key exists before attempting request."""
        config = self.model_config[model]
        api_key_env = config.get("api_key_env")

        if config["tier"] == "Local":
            return True

        if not api_key_env:
            logger.warning(f"No API key configured for model: {model}")
            return False

        api_key = os.environ.get(api_key_env)
        if not api_key:
            logger.warning(f"API key missing for {model} (env: {api_key_env})")
            return False

        return True

    def build_headers(self, model: str, api_key: str) -> dict:
        """Build headers for API request."""
        headers = {"Content-Type": "application/json"}

        if model.startswith("ollama/"):
            pass
        elif model.startswith("google/"):
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    def build_payload(self, model: str, prompt: str) -> dict:
        """Build request payload for the model."""
        if model.startswith("ollama/"):
            model_name = model.split("/")[-1]
            return {"model": model_name, "prompt": prompt, "stream": False}
        elif model.startswith("google/"):
            return {"contents": [{"parts": [{"text": prompt}]}]}
        else:
            model_name = model.split("/")[-1] if "/" in model else model
            return {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
            }

    def determine_error_type(self, error: Exception) -> str:
        """Determine the type of error for proper handling."""
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif (
            "rate limit" in error_str
            or "429" in error_str
            or "too many requests" in error_str
        ):
            return "rate_limit"
        elif "401" in error_str or "unauthorized" in error_str:
            return "auth_error"
        elif "403" in error_str or "forbidden" in error_str:
            return "forbidden"
        elif (
            "500" in error_str
            or "502" in error_str
            or "503" in error_str
            or "internal server" in error_str
        ):
            return "server_error"
        elif "connection" in error_str or "refused" in error_str:
            return "connection_error"
        else:
            return "api_error"

    def call_model(self, model: str, prompt: str) -> dict:
        """Make API call to a specific model using OpenAI-compatible format."""
        import requests

        config = self.model_config[model]
        api_key = self.get_api_key(model)

        url = f"{config['base_url']}/chat/completions"
        headers = self.build_headers(model, api_key or "dummy")
        payload = self.build_payload(model, prompt)

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=config["timeout"]
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return {
                        "success": True,
                        "response": result["choices"][0]["message"]["content"],
                        "model": model,
                    }
                return {"success": False, "error": "No response content"}
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        retry_seconds = int(retry_after)
                    except ValueError:
                        retry_seconds = 1
                    logger.warning(
                        f"Rate limited, sleeping {retry_seconds}s (Retry-After header)"
                    )
                    time.sleep(retry_seconds)
                raise Exception("Rate limit exceeded (429)")
            elif response.status_code == 401:
                raise Exception("Unauthorized (401)")
            elif response.status_code == 403:
                raise Exception("Forbidden (403)")
            elif response.status_code >= 500:
                raise Exception(f"Server error ({response.status_code})")
            else:
                raise Exception(f"API error: {response.status_code}")

        except requests.Timeout:
            raise Exception("Request timeout")
        except requests.ConnectionError as e:
            raise Exception(f"Connection error: {str(e)}")

    def _load_local_router(self):
        """Load local-router module (hyphenated filename requires special handling)."""
        module_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "local-router.py"
        )
        spec = importlib.util.spec_from_file_location("local_router", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _try_local_first(self, prompt: str) -> Optional[dict]:
        """Try local model first for simple/medium tasks."""
        if not self.local_router.is_local_available():
            logger.info("Local GGUF not available, skipping local-first routing")
            return None

        complexity = self.local_router.classify(prompt)
        if complexity not in ("simple", "medium"):
            logger.info(
                f"Task classified as '{complexity}', skipping local-first routing"
            )
            return None

        logger.info(f"Task classified as '{complexity}', trying local GGUF model first")
        local_models = self.local_router.get_local_models()
        for local_model in local_models:
            model_key = f"gguf/{local_model}"
            if model_key not in self.model_config:
                self.model_config[model_key] = {
                    "name": f"{local_model} (GGUF)",
                    "tier": "Local",
                    "api_key_env": None,
                    "base_url": "http://localhost:8080/v1",
                    "timeout": 60,
                }

            try:
                self.rate_limiter.acquire()
                result = self.call_model(model_key, prompt)
                if result.get("success"):
                    self.circuit_breaker.record_success(model_key)
                    logger.info(f"Success with local model: {local_model}")
                    return {
                        "success": True,
                        "response": result["response"],
                        "model": model_key,
                        "tier": "Local",
                    }
            except Exception as e:
                error_type = self.determine_error_type(e)
                logger.warning(
                    f"Local model {local_model} failed ({error_type}): {str(e)}"
                )
                self.circuit_breaker.record_failure(model_key)

        logger.warning("All local models failed, proceeding with cloud fallback chain")
        return None

    def call_with_fallback(
        self, prompt: str, model_list: Optional[list] = None
    ) -> dict:
        """
        Call models in priority order with fallback logic.

        Args:
            prompt: The prompt to send to the model
            model_list: Optional custom list of models (defaults to model_config keys)

        Returns:
            dict with 'success', 'response', 'model', or 'error' keys
        """
        if model_list is None:
            model_list = list(self.model_config.keys())

        local_result = self._try_local_first(prompt)
        if local_result and local_result.get("success"):
            return local_result

        errors = []

        for model in model_list:
            if model not in self.model_config:
                logger.warning(f"Unknown model: {model}, skipping")
                continue

            if not self.circuit_breaker.is_available(model):
                continue

            if not self._validate_api_key(model):
                logger.info(f"Skipping model {model} due to missing API key")
                continue

            config = self.model_config[model]
            logger.info(f"Trying model: {model} ({config['name']} - {config['tier']})")

            try:
                self.rate_limiter.acquire()
                result = self.call_model(model, prompt)

                if result.get("success"):
                    self.circuit_breaker.record_success(model)
                    logger.info(f"Success with model: {model}")
                    return {
                        "success": True,
                        "response": result["response"],
                        "model": model,
                        "tier": config["tier"],
                    }

            except Exception as e:
                error_type = self.determine_error_type(e)
                logger.warning(f"Model {model} failed ({error_type}): {str(e)}")

                self.circuit_breaker.record_failure(model)
                errors.append({"model": model, "error": str(e), "type": error_type})

                delay = 5.0 if error_type == "rate_limit" else 1.0
                logger.info(f"Sleeping {delay}s before next fallback attempt")
                time.sleep(delay)

                continue

        error_msg = f"All models failed. Errors: {json.dumps(errors)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "failed_models": [e["model"] for e in errors],
        }


def run_test_fallback():
    """Simulate fallback scenarios for testing."""
    fallback = ModelFallback()

    test_cases = [
        {
            "name": "Test 1: All models fail (simulated)",
            "prompt": "Hello, this is a test prompt.",
            "simulate_failure": True,
            "models_to_test": PRIORITY_MODELS[:3],
        },
        {
            "name": "Test 2: Partial failure (simulated)",
            "prompt": "What is 2+2?",
            "simulate_failure": True,
            "models_to_test": PRIORITY_MODELS[:2],
        },
        {
            "name": "Test 3: Full fallback chain (simulated)",
            "prompt": "Tell me a joke.",
            "simulate_failure": True,
            "models_to_test": PRIORITY_MODELS,
        },
    ]

    print("\n" + "=" * 60)
    print("MODEL FALLBACK TEST MODE")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}")
        print("-" * 40)

        if test.get("simulate_failure"):
            print("Simulating failures for all models...")
            result = {
                "success": False,
                "error": f"[SIMULATED] All {len(test['models_to_test'])} models failed in test mode",
                "failed_models": test["models_to_test"],
            }

        print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
        if result.get("success"):
            print(f"Response from {result.get('model')} ({result.get('tier')})")
            print(f"Response: {result.get('response', '')[:100]}...")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("Circuit Breaker State:")
    print("-" * 40)
    for model in PRIORITY_MODELS:
        failures = fallback.circuit_breaker.failures.get(model, 0)
        print(f"  {model}: {failures} failures")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Tiered Model Fallback Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --prompt "Hello world"
  %(prog)s --test-fallback
  %(prog)s --model-list opencode/qwen3.6-plus-free opencode/minimax-m2.5-free --prompt "Test"
        """,
    )

    parser.add_argument("--prompt", type=str, help="Prompt to send to the model")

    parser.add_argument(
        "--model-list",
        type=str,
        nargs="+",
        help="Custom list of models to try (in priority order)",
    )

    parser.add_argument(
        "--test-fallback",
        action="store_true",
        help="Run in test mode to simulate fallback scenarios",
    )

    args = parser.parse_args()

    if args.test_fallback:
        run_test_fallback()
    elif args.prompt:
        fallback = ModelFallback()
        result = fallback.call_with_fallback(args.prompt, args.model_list)

        if result.get("success"):
            print(f"\nSuccess! Model: {result.get('model')} ({result.get('tier')})")
            print(f"Response: {result.get('response')}")
        else:
            print(f"\nFailed: {result.get('error')}")
            print(f"Failed models: {result.get('failed_models', [])}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
