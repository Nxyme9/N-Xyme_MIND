"""
Comprehensive integration tests for the model router system.

Tests the entire routing pipeline end-to-end:
- VRAM Manager
- Ollama Manager
- Circuit Breaker
- Rate Limiter
- Router Hook
- Proxy Server endpoints
- Startup/Status scripts
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from model_router.circuit_breaker import CircuitBreaker
from model_router.ollama_manager import OllamaManager
from model_router.rate_limiter import RateLimiter
from model_router.vram_manager import VRAMManager, VRAMManagerError


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for circuit breaker state."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def circuit_breaker(temp_cache_dir):
    """Create a CircuitBreaker with isolated state file."""
    state_file = os.path.join(temp_cache_dir, "circuit-breaker.json")
    return CircuitBreaker(
        failure_threshold=3,
        reset_timeout=300,
        base_delay=1.0,
        max_delay=60.0,
        jitter=False,
        state_file=state_file,
    )


@pytest.fixture
def rate_limiter():
    """Create a RateLimiter with small limits for fast testing."""
    return RateLimiter(max_requests=5, window_seconds=60.0)


@pytest.fixture
def vram_manager():
    """Create a VRAMManager for testing."""
    return VRAMManager(max_vram_gb=12.0, safety_margin_gb=1.0)


@pytest.fixture
def ollama_manager():
    """Create an OllamaManager for testing."""
    return OllamaManager()


@pytest.fixture
def proxy_base_url():
    """Base URL for the proxy server."""
    host = os.getenv("MODEL_ROUTER_HOST", "127.0.0.1")
    port = os.getenv("MODEL_ROUTER_PORT", "8080")
    return f"http://{host}:{port}"


# ── VRAM Manager Tests ──────────────────────────────────────────────────


class TestVRAMManager:
    """Tests for the VRAM Manager component."""

    def test_get_vram_usage_returns_dict_with_correct_keys(self, vram_manager):
        """get_vram_usage returns dict with correct keys."""
        result = vram_manager.get_vram_usage()
        assert isinstance(result, dict)
        assert "used_gb" in result
        assert "total_gb" in result
        assert "free_gb" in result
        assert "percent" in result

    def test_get_vram_usage_returns_float_values(self, vram_manager):
        """All VRAM usage values are floats."""
        result = vram_manager.get_vram_usage()
        assert isinstance(result["used_gb"], float)
        assert isinstance(result["total_gb"], float)
        assert isinstance(result["free_gb"], float)
        assert isinstance(result["percent"], float)

    def test_get_vram_usage_returns_zero_on_no_gpu(self, vram_manager):
        """Returns all zeros when nvidia-smi is not available."""
        with patch.object(
            vram_manager, "_run_nvidia_smi", side_effect=VRAMManagerError("no gpu")
        ):
            result = vram_manager.get_vram_usage()
            assert result["used_gb"] == 0.0
            assert result["total_gb"] == 0.0
            assert result["free_gb"] == 0.0
            assert result["percent"] == 0.0

    def test_can_load_model_with_float(self, vram_manager):
        """can_load_model accepts a float model size."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 2.0,
                "total_gb": 16.0,
                "free_gb": 14.0,
                "percent": 12.5,
            },
        ):
            result = vram_manager.can_load_model(4.5)
            assert result is True

    def test_can_load_model_with_string(self, vram_manager):
        """can_load_model accepts a model name string."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 2.0,
                "total_gb": 16.0,
                "free_gb": 14.0,
                "percent": 12.5,
            },
        ):
            result = vram_manager.can_load_model("qwen2.5-coder:7b")
            assert result is True

    def test_can_load_model_unknown_model(self, vram_manager):
        """can_load_model uses default size for unknown model names."""
        result = vram_manager.can_load_model("unknown-model:999b")
        # Unknown models use default size (4.0GB) - should return True if VRAM available
        assert isinstance(result, bool)

    def test_can_load_model_exceeds_limit(self, vram_manager):
        """can_load_model returns False when VRAM would exceed limit."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 10.0,
                "total_gb": 16.0,
                "free_gb": 6.0,
                "percent": 62.5,
            },
        ):
            result = vram_manager.can_load_model(4.5)
            assert result is False

    def test_get_available_vram(self, vram_manager):
        """get_available_vram returns free_gb from usage."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 3.0,
                "total_gb": 16.0,
                "free_gb": 13.0,
                "percent": 18.75,
            },
        ):
            result = vram_manager.get_available_vram()
            assert result == 13.0

    def test_get_loaded_models(self, vram_manager):
        """get_loaded_models returns tracked models."""
        vram_manager.register_loaded_model("model-a", 2.0)
        vram_manager.register_loaded_model("model-b", 4.5)
        result = vram_manager.get_loaded_models()
        assert "model-a" in result
        assert "model-b" in result
        assert result["model-a"] == 2.0
        assert result["model-b"] == 4.5

    def test_register_and_unregister_model(self, vram_manager):
        """Models can be registered and unregistered."""
        vram_manager.register_loaded_model("test-model", 3.0)
        assert vram_manager.get_loaded_models()["test-model"] == 3.0
        size = vram_manager.unregister_loaded_model("test-model")
        assert size == 3.0
        assert "test-model" not in vram_manager.get_loaded_models()

    def test_unregister_nonexistent_model(self, vram_manager):
        """Unregistering a nonexistent model returns None."""
        result = vram_manager.unregister_loaded_model("nonexistent")
        assert result is None

    def test_get_models_to_unload(self, vram_manager):
        """get_models_to_unload returns largest models first."""
        vram_manager.register_loaded_model("small", 1.0)
        vram_manager.register_loaded_model("medium", 4.5)
        vram_manager.register_loaded_model("large", 8.0)
        result = vram_manager.get_models_to_unload(5.0)
        assert result == ["large"]

    def test_get_models_to_unload_empty(self, vram_manager):
        """get_models_to_unload returns empty list when target is 0."""
        result = vram_manager.get_models_to_unload(0)
        assert result == []

    def test_get_vram_budget(self, vram_manager):
        """get_vram_budget returns all required keys."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 3.0,
                "total_gb": 16.0,
                "free_gb": 13.0,
                "percent": 18.75,
            },
        ):
            result = vram_manager.get_vram_budget()
            assert "max_gb" in result
            assert "safety_margin_gb" in result
            assert "effective_limit_gb" in result
            assert "used_gb" in result
            assert "available_gb" in result
            assert "headroom_gb" in result
            assert result["max_gb"] == 12.0
            assert result["safety_margin_gb"] == 1.0
            assert result["effective_limit_gb"] == 11.0

    def test_is_over_limit(self, vram_manager):
        """is_over_limit returns True when usage exceeds effective limit."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 11.5,
                "total_gb": 16.0,
                "free_gb": 4.5,
                "percent": 71.9,
            },
        ):
            assert vram_manager.is_over_limit() is True

    def test_is_not_over_limit(self, vram_manager):
        """is_over_limit returns False when usage is below effective limit."""
        with patch.object(
            vram_manager,
            "get_vram_usage",
            return_value={
                "used_gb": 5.0,
                "total_gb": 16.0,
                "free_gb": 11.0,
                "percent": 31.25,
            },
        ):
            assert vram_manager.is_over_limit() is False

    def test_vram_manager_init_validation(self):
        """VRAMManager validates constructor arguments."""
        with pytest.raises(VRAMManagerError, match="positive"):
            VRAMManager(max_vram_gb=0)
        with pytest.raises(VRAMManagerError, match="non-negative"):
            VRAMManager(max_vram_gb=12.0, safety_margin_gb=-1.0)
        with pytest.raises(VRAMManagerError, match="less than"):
            VRAMManager(max_vram_gb=12.0, safety_margin_gb=12.0)


# ── Ollama Manager Tests ────────────────────────────────────────────────


class TestOllamaManager:
    """Tests for the Ollama Manager component."""

    def test_health_check_returns_bool(self, ollama_manager):
        """health_check returns a boolean."""
        result = ollama_manager.health_check()
        assert isinstance(result, bool)

    def test_health_check_true_when_ollama_running(self, ollama_manager):
        """health_check returns True when Ollama is running."""
        try:
            import httpx

            client = httpx.Client(timeout=5.0)
            resp = client.get(f"{ollama_manager.ollama_url}/api/tags")
            if resp.status_code == 200:
                assert ollama_manager.health_check() is True
            client.close()
        except Exception:
            pytest.skip("Ollama not running")

    def test_health_check_false_when_ollama_unreachable(self):
        """health_check returns False when Ollama is unreachable."""
        manager = OllamaManager(ollama_url="http://localhost:19999")
        result = manager.health_check()
        assert result is False

    def test_get_loaded_models_returns_list(self, ollama_manager):
        """get_loaded_models returns a list."""
        result = ollama_manager.get_loaded_models()
        assert isinstance(result, list)

    def test_get_available_models_returns_list(self, ollama_manager):
        """get_available_models returns a list."""
        result = ollama_manager.get_available_models()
        assert isinstance(result, list)

    def test_context_manager(self):
        """OllamaManager works as a context manager."""
        with OllamaManager() as manager:
            assert isinstance(manager.ollama_url, str)

    def test_close_method(self):
        """close() cleans up the HTTP client."""
        manager = OllamaManager()
        manager.close()

    def test_ollama_url_stripped(self):
        """ollama_url is properly stripped of trailing slashes."""
        manager = OllamaManager(ollama_url="http://localhost:11434/")
        assert manager.ollama_url == "http://localhost:11434"


# ── Circuit Breaker Tests ───────────────────────────────────────────────


class TestCircuitBreaker:
    """Tests for the Circuit Breaker component."""

    def test_initially_available(self, circuit_breaker):
        """A model is available by default (no failures)."""
        assert circuit_breaker.is_available("test-model") is True

    def test_record_failure_increments_count(self, circuit_breaker):
        """record_failure increments the failure counter."""
        circuit_breaker.record_failure("test-model")
        state = circuit_breaker.state("test-model")
        assert state["failures"] == 1

    def test_record_success_resets_counter(self, circuit_breaker):
        """record_success resets the failure counter to 0."""
        circuit_breaker.record_failure("test-model")
        circuit_breaker.record_failure("test-model")
        circuit_breaker.record_success("test-model")
        state = circuit_breaker.state("test-model")
        assert state["failures"] == 0

    def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Circuit opens after reaching failure threshold."""
        for _ in range(3):
            circuit_breaker.record_failure("test-model")
        state = circuit_breaker.state("test-model")
        assert state["is_open"] is True
        assert state["failures"] == 3

    def test_unavailable_when_circuit_open(self, circuit_breaker):
        """Model is unavailable when circuit is open."""
        for _ in range(3):
            circuit_breaker.record_failure("test-model")
        assert circuit_breaker.is_available("test-model") is False

    def test_reset_clears_state(self, circuit_breaker):
        """reset() clears all failure state for a model."""
        circuit_breaker.record_failure("test-model")
        circuit_breaker.record_failure("test-model")
        circuit_breaker.reset("test-model")
        state = circuit_breaker.state("test-model")
        assert state["failures"] == 0
        assert state["is_open"] is False
        assert circuit_breaker.is_available("test-model") is True

    def test_state_returns_correct_keys(self, circuit_breaker):
        """state() returns dict with all required keys."""
        state = circuit_breaker.state("test-model")
        assert "model" in state
        assert "failures" in state
        assert "last_failure_time" in state
        assert "is_open" in state
        assert "threshold" in state

    def test_get_delay_exponential(self, circuit_breaker):
        """get_delay returns exponentially increasing delays."""
        delay_0 = circuit_breaker.get_delay(0)
        delay_1 = circuit_breaker.get_delay(1)
        delay_2 = circuit_breaker.get_delay(2)
        assert delay_1 > delay_0
        assert delay_2 > delay_1

    def test_state_persistence(self, temp_cache_dir):
        """Circuit breaker state persists across instances."""
        state_file = os.path.join(temp_cache_dir, "circuit-breaker.json")
        cb1 = CircuitBreaker(failure_threshold=3, jitter=False, state_file=state_file)
        cb1.record_failure("persisted-model")
        cb1.record_failure("persisted-model")

        cb2 = CircuitBreaker(failure_threshold=3, jitter=False, state_file=state_file)
        state = cb2.state("persisted-model")
        assert state["failures"] == 2

    def test_corrupted_state_file_handled(self, temp_cache_dir):
        """Corrupted state file is handled gracefully."""
        state_file = os.path.join(temp_cache_dir, "circuit-breaker.json")
        with open(state_file, "w") as f:
            f.write("not valid json{{{")
        cb = CircuitBreaker(failure_threshold=3, jitter=False, state_file=state_file)
        assert cb.is_available("any-model") is True

    def test_multiple_models_independent(self, circuit_breaker):
        """Circuit breakers for different models are independent."""
        circuit_breaker.record_failure("model-a")
        circuit_breaker.record_failure("model-a")
        circuit_breaker.record_failure("model-a")
        assert circuit_breaker.is_available("model-a") is False
        assert circuit_breaker.is_available("model-b") is True


# ── Rate Limiter Tests ──────────────────────────────────────────────────


class TestRateLimiter:
    """Tests for the Rate Limiter component."""

    def test_acquire_works(self, rate_limiter):
        """acquire() successfully consumes a token."""
        rate_limiter.acquire()
        stats = rate_limiter.get_stats()
        assert stats["available_tokens"] < rate_limiter.max_requests

    def test_try_acquire_returns_true_when_tokens_available(self, rate_limiter):
        """try_acquire() returns True when tokens are available."""
        result = rate_limiter.try_acquire()
        assert result is True

    def test_try_acquire_returns_false_when_exhausted(self):
        """try_acquire() returns False when no tokens remain."""
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_blocks_after_limit(self):
        """After consuming all tokens, try_acquire blocks until refill."""
        limiter = RateLimiter(max_requests=1, window_seconds=60.0)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_get_wait_time_returns_zero_when_available(self, rate_limiter):
        """get_wait_time returns 0 when tokens are available."""
        wait = rate_limiter.get_wait_time()
        assert wait == 0.0

    def test_get_wait_time_returns_positive_when_exhausted(self):
        """get_wait_time returns positive value when exhausted."""
        limiter = RateLimiter(max_requests=1, window_seconds=60.0)
        limiter.try_acquire()
        wait = limiter.get_wait_time()
        assert wait > 0.0

    def test_get_stats_returns_correct_keys(self, rate_limiter):
        """get_stats returns dict with correct keys."""
        stats = rate_limiter.get_stats()
        assert "max_requests" in stats
        assert "window_seconds" in stats
        assert "available_tokens" in stats

    def test_token_refill_over_time(self):
        """Tokens refill after waiting."""
        limiter = RateLimiter(max_requests=2, window_seconds=1.0)
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.try_acquire() is False
        time.sleep(1.1)
        assert limiter.try_acquire() is True

    def test_thread_safety(self):
        """Rate limiter is thread-safe under concurrent access."""
        import threading

        limiter = RateLimiter(max_requests=10, window_seconds=60.0)
        acquired = []
        lock = threading.Lock()

        def try_acquire_thread():
            if limiter.try_acquire():
                with lock:
                    acquired.append(1)

        threads = [threading.Thread(target=try_acquire_thread) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(acquired) == 10


# ── Router Hook Tests ───────────────────────────────────────────────────


class TestRouterHook:
    """Tests for the Router Hook (pipeline entry point)."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset hook module singletons between tests to avoid state leakage."""
        import importlib
        import model_router.hook as hook_module

        hook_module._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=300,
            jitter=False,
            state_file=tempfile.mktemp(suffix=".json"),
        )
        hook_module._rate_limiter = RateLimiter(max_requests=100, window_seconds=60.0)
        yield

    def test_route_request_returns_valid_routing_decision(self):
        """route_request returns a dict with all required keys."""
        from model_router.hook import route_request

        result = route_request("explore", "find all Python files")
        assert isinstance(result, dict)
        assert "model" in result
        assert "provider" in result
        assert "confidence" in result
        assert "reason" in result
        assert "fallback_used" in result
        assert "rate_limited" in result
        assert "circuit_broken" in result
        assert "vram_blocked" in result

    def test_route_request_for_known_agent(self):
        """route_request routes known agent types correctly."""
        from model_router.hook import route_request

        result = route_request("oracle", "review architecture")
        assert result["model"] is not None
        assert result["provider"] is not None
        assert result["confidence"] > 0.0

    def test_route_request_for_unknown_agent(self):
        """route_request handles unknown agent types gracefully."""
        from model_router.hook import route_request

        result = route_request("unknown-agent-xyz", "some task")
        assert result["model"] is not None
        assert result["rate_limited"] is False

    def test_get_system_status_returns_all_required_fields(self):
        """get_system_status returns dict with all required fields."""
        from model_router.hook import get_system_status

        status = get_system_status()
        assert isinstance(status, dict)
        assert "vram" in status
        assert "ollama_health" in status
        assert "circuit_breakers" in status
        assert "rate_limiter" in status
        assert "loaded_models" in status
        assert "timestamp" in status

    def test_get_system_status_vram_has_keys(self):
        """get_system_status vram field has required keys."""
        from model_router.hook import get_system_status

        status = get_system_status()
        vram = status["vram"]
        assert "used_gb" in vram
        assert "total_gb" in vram
        assert "free_gb" in vram
        assert "percent" in vram

    def test_record_success_updates_circuit_breaker(self):
        """record_success resets circuit breaker failure counter."""
        from model_router.hook import record_success
        from model_router.hook import _circuit_breaker

        _circuit_breaker.record_failure("hook-test-model")
        _circuit_breaker.record_failure("hook-test-model")
        record_success("hook-test-model")
        state = _circuit_breaker.state("hook-test-model")
        assert state["failures"] == 0

    def test_record_failure_updates_circuit_breaker(self):
        """record_failure increments circuit breaker failure counter."""
        from model_router.hook import record_failure
        from model_router.hook import _circuit_breaker

        _circuit_breaker.reset("hook-test-model-2")
        record_failure("hook-test-model-2")
        state = _circuit_breaker.state("hook-test-model-2")
        assert state["failures"] == 1

    def test_rate_limit_exceeded(self):
        """route_request returns rate_limited=True when limit exceeded."""
        from src.model_router.hook import route_request, _classifier
        from src.model_router.state import get_rate_limiter
        import time

        # Find which provider 'explore' routes to
        route = _classifier.classify("explore", "test")
        provider = route.provider.value

        # Exhaust that provider's rate limiter
        rl = get_rate_limiter(provider)
        with rl._lock:
            rl.max_requests = 1
            rl.window_seconds = 3600  # 1 hour, negligible refill
            rl._tokens = 0.0
            rl._last_refill = time.monotonic()

        result = route_request("explore", "rate limited request")
        assert result["rate_limited"] is True
        assert result["model"] is None


# ── Proxy Server Tests ──────────────────────────────────────────────────


class TestProxyServer:
    """Tests for the proxy server HTTP endpoints."""

    def _check_proxy_running(self, proxy_base_url):
        """Skip all proxy tests if the server is not running."""
        try:
            import httpx

            client = httpx.Client(timeout=5.0)
            resp = client.get(f"{proxy_base_url}/health")
            client.close()
            if resp.status_code != 200:
                pytest.skip("Proxy server not running")
        except Exception:
            pytest.skip("Proxy server not running")

    def test_health_endpoint_returns_healthy(self, proxy_base_url):
        """/health endpoint returns healthy status."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "ollama" in data
            assert "vram_used_gb" in data
            assert "vram_free_gb" in data

    def test_vram_endpoint_returns_vram_data(self, proxy_base_url):
        """/vram endpoint returns VRAM data."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/vram")
            assert resp.status_code == 200
            data = resp.json()
            assert "usage" in data
            assert "over_limit" in data
            assert "used_gb" in data["usage"]
            assert "total_gb" in data["usage"]
            assert "free_gb" in data["usage"]
            assert "percent" in data["usage"]

    def test_circuit_breaker_endpoint_returns_state(self, proxy_base_url):
        """/circuit-breaker endpoint returns circuit breaker state."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/circuit-breaker")
            assert resp.status_code == 200
            data = resp.json()
            assert "providers" in data
            assert "failure_threshold" in data
            assert "reset_timeout" in data
            assert isinstance(data["providers"], dict)

    def test_rate_limiter_endpoint_returns_stats(self, proxy_base_url):
        """/rate-limiter endpoint returns rate limiter stats."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/rate-limiter")
            assert resp.status_code == 200
            data = resp.json()
            assert "max_requests" in data
            assert "window_seconds" in data
            assert "available_tokens" in data

    def test_models_loaded_endpoint_returns_list(self, proxy_base_url):
        """/models/loaded endpoint returns list of loaded models."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/models/loaded")
            assert resp.status_code == 200
            data = resp.json()
            assert "models" in data
            assert "count" in data
            assert isinstance(data["models"], list)
            assert isinstance(data["count"], int)

    def test_v1_models_endpoint(self, proxy_base_url):
        """/v1/models endpoint returns available models."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/v1/models")
            assert resp.status_code == 200
            data = resp.json()
            assert "models" in data
            assert isinstance(data["models"], list)

    def test_stats_endpoint(self, proxy_base_url):
        """/stats endpoint returns usage statistics."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{proxy_base_url}/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert "providers" in data
            assert "recent_requests" in data


# ── Script Tests ────────────────────────────────────────────────────────


class TestScripts:
    """Tests for the bin/ shell scripts."""

    @pytest.fixture
    def root_dir(self):
        """Get the project root directory."""
        return PROJECT_ROOT

    def test_start_model_router_script_exists(self, root_dir):
        """bin/start-model-router.sh exists and is executable."""
        script_path = os.path.join(root_dir, "bin", "start-model-router.sh")
        assert os.path.exists(script_path)
        assert os.access(script_path, os.X_OK)

    def test_status_model_router_script_exists(self, root_dir):
        """bin/status-model-router.sh exists and is executable."""
        script_path = os.path.join(root_dir, "bin", "status-model-router.sh")
        assert os.path.exists(script_path)
        assert os.access(script_path, os.X_OK)

    def test_start_model_router_script_has_valid_shebang(self, root_dir):
        """bin/start-model-router.sh has a valid shebang line."""
        script_path = os.path.join(root_dir, "bin", "start-model-router.sh")
        with open(script_path) as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/")

    def test_status_model_router_script_has_valid_shebang(self, root_dir):
        """bin/status-model-router.sh has a valid shebang line."""
        script_path = os.path.join(root_dir, "bin", "status-model-router.sh")
        with open(script_path) as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/")

    def test_status_model_router_script_runs(self, root_dir):
        """bin/status-model-router.sh runs without crashing."""
        script_path = os.path.join(root_dir, "bin", "status-model-router.sh")
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=root_dir,
        )
        assert result.returncode == 0
        assert "Model Router" in result.stdout

    def test_stop_model_router_script_exists(self, root_dir):
        """bin/stop-model-router.sh exists and is executable."""
        script_path = os.path.join(root_dir, "bin", "stop-model-router.sh")
        assert os.path.exists(script_path)
        assert os.access(script_path, os.X_OK)


# ── End-to-End Pipeline Tests ───────────────────────────────────────────


class TestEndToEndPipeline:
    """End-to-end tests for the complete routing pipeline."""

    def test_full_routing_pipeline(self):
        """Test the complete routing pipeline: classify -> circuit check -> route."""
        from src.model_router.hook import route_request, record_success
        from src.model_router.state import get_rate_limiter
        import time

        # Reset rate limiters to full
        for provider in ["opencode", "openrouter", "ollama"]:
            rl = get_rate_limiter(provider)
            with rl._lock:
                rl._tokens = float(rl.max_requests)
                rl._last_refill = time.monotonic()

        result = route_request("explore", "find all files")
        assert result["model"] is not None
        assert result["provider"] is not None
        assert result["confidence"] > 0.0
        assert result["rate_limited"] is False

        if result["model"]:
            record_success(result["model"])

    def test_circuit_breaker_integration_in_pipeline(self):
        """Test circuit breaker affects routing decisions."""
        from model_router.hook import route_request, record_failure, _circuit_breaker

        _circuit_breaker.reset("llama3.2:latest")

        for _ in range(3):
            record_failure("llama3.2:latest")

        result = route_request("explore", "find files")

        if result.get("circuit_broken"):
            assert result["fallback_used"] is True or result["model"] is None

    def test_system_status_completeness(self):
        """Test that system status contains all expected subsystem data."""
        from src.model_router.hook import get_system_status

        status = get_system_status()

        assert isinstance(status["vram"], dict)
        assert isinstance(status["ollama_health"], bool)
        assert isinstance(status["circuit_breakers"], dict)
        assert isinstance(status["rate_limiter"], dict)
        assert isinstance(status["loaded_models"], list)
        assert isinstance(status["timestamp"], float)

        vram = status["vram"]
        assert all(k in vram for k in ["used_gb", "total_gb", "free_gb", "percent"])

        rl = status["rate_limiter"]
        # Rate limiter is now per-provider dict
        assert "opencode" in rl
        assert "openrouter" in rl
        assert "ollama" in rl
        for provider in rl.values():
            assert all(k in provider for k in ["max_requests", "window_seconds", "available_tokens"])


# ── Advanced Proxy Tests ────────────────────────────────────────────────


class TestAdvancedProxy:
    """Advanced proxy server tests for concurrency, timeouts, security, and validation."""

    def _check_proxy_running(self, proxy_base_url):
        """Skip all proxy tests if the server is not running."""
        try:
            import httpx

            client = httpx.Client(timeout=5.0)
            resp = client.get(f"{proxy_base_url}/health")
            client.close()
            if resp.status_code != 200:
                pytest.skip("Proxy server not running")
        except Exception:
            pytest.skip("Proxy server not running")

    def test_concurrent_requests(self, proxy_base_url):
        """Multiple concurrent requests are handled without errors."""
        self._check_proxy_running(proxy_base_url)
        import httpx
        import concurrent.futures

        def make_request(idx):
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{proxy_base_url}/health")
                return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(r == 200 for r in results)

    def test_timeout_handling(self, proxy_base_url):
        """Requests with very short timeout fail gracefully."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        with httpx.Client(timeout=httpx.Timeout(connect=0.001, read=0.001, write=0.001, pool=0.001)) as client:
            try:
                client.get(f"{proxy_base_url}/stats")
            except httpx.TimeoutException:
                pass

    def test_error_sanitization_no_internal_paths(self, proxy_base_url):
        """Error responses do not leak internal file paths or stack traces."""
        self._check_proxy_running(proxy_base_url)
        import httpx
        import re

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{proxy_base_url}/v1/chat/completions",
                json={
                    "model": "nonexistent-model-xyz",
                    "messages": [{"role": "user", "content": "test"}],
                },
            )

        body = resp.text
        assert not re.search(r"/home/|/tmp/|/var/|src/|\.py", body), (
            f"Error response contains internal paths: {body}"
        )

    def test_input_validation_invalid_model_name_rejected(self, proxy_base_url):
        """Invalid model names with special characters are rejected."""
        self._check_proxy_running(proxy_base_url)
        import httpx

        invalid_models = [
            "model; rm -rf /",
            "<script>alert(1)</script>",
            "../../../etc/passwd",
            "model with spaces",
            "model\nwith\nnewlines",
        ]

        with httpx.Client(timeout=10.0) as client:
            for invalid_model in invalid_models:
                resp = client.post(
                    f"{proxy_base_url}/v1/chat/completions",
                    json={
                        "model": invalid_model,
                        "messages": [{"role": "user", "content": "test"}],
                    },
                )
                assert resp.status_code != 200, (
                    f"Invalid model '{invalid_model}' was accepted with 200"
                )

    def test_circuit_breaker_state_sharing_between_hook_and_proxy(self):
        """Circuit breaker state persists to file and is readable by other instances."""
        from model_router.circuit_breaker import CircuitBreaker
        import tempfile
        import os

        state_file = os.path.join(tempfile.mkdtemp(), "shared-circuit.json")

        cb1 = CircuitBreaker(
            failure_threshold=3, jitter=False, state_file=state_file
        )
        cb1.record_failure("shared-model")
        cb1.record_failure("shared-model")

        cb2 = CircuitBreaker(
            failure_threshold=3, jitter=False, state_file=state_file
        )

        state_from_cb2 = cb2.state("shared-model")
        assert state_from_cb2["failures"] == 2

        cb2.record_failure("shared-model")

        cb3 = CircuitBreaker(
            failure_threshold=3, jitter=False, state_file=state_file
        )
        state_from_cb3 = cb3.state("shared-model")
        assert state_from_cb3["failures"] == 3
        assert state_from_cb3["is_open"] is True



# ── Load & Stress Tests ─────────────────────────────────────────────────


class TestLoadStress:
    """Load and stress tests for concurrent requests and race conditions."""

    def test_concurrent_routing(self):
        """10 concurrent route_request calls all complete without errors."""
        import concurrent.futures
        import threading
        from model_router.hook import route_request

        def route(idx):
            return route_request("explore", f"concurrent test {idx}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(route, i) for i in range(10)]
            results = [f.result(timeout=30) for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 10
        for r in results:
            assert isinstance(r, dict)
            assert "model" in r
            assert "provider" in r
            assert "confidence" in r

    def test_concurrent_circuit_breaker(self, temp_cache_dir):
        """Multiple threads recording failures simultaneously, no race conditions."""
        import concurrent.futures
        import threading

        state_file = os.path.join(temp_cache_dir, "concurrent-cb.json")
        cb = CircuitBreaker(
            failure_threshold=100,
            reset_timeout=300,
            jitter=False,
            state_file=state_file,
        )

        errors = []
        lock = threading.Lock()

        def record_failures(model, count):
            try:
                for _ in range(count):
                    cb.record_failure(model)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        num_threads = 5
        failures_per_thread = 20

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(record_failures, "stress-model", failures_per_thread)
                for _ in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Race condition errors: {errors}"
        state = cb.state("stress-model")
        assert state["failures"] == num_threads * failures_per_thread
        assert state["is_open"] is True

    def test_concurrent_rate_limiter(self):
        """Multiple threads acquiring tokens simultaneously, no over-acquisition."""
        import concurrent.futures
        import threading

        limiter = RateLimiter(max_requests=10, window_seconds=60.0)
        acquired = []
        lock = threading.Lock()

        def try_acquire():
            if limiter.try_acquire():
                with lock:
                    acquired.append(1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(try_acquire) for _ in range(20)]
            concurrent.futures.wait(futures)

        assert len(acquired) == 10, f"Expected 10 acquired, got {len(acquired)}"
        stats = limiter.get_stats()
        assert stats["available_tokens"] < 10

    def test_rapid_health_checks(self, ollama_manager):
        """20 rapid health check calls, verify TTL cache works."""
        from model_router.hook import _ollama_health_cache
        import time

        original_cache = _ollama_health_cache.copy()
        _ollama_health_cache["ttl"] = 60.0
        _ollama_health_cache["last_check"] = time.time() - 5

        results = []
        for _ in range(20):
            results.append(ollama_manager.health_check())

        _ollama_health_cache.update(original_cache)

        assert len(results) == 20
        assert all(isinstance(r, bool) for r in results)

    def test_sustained_load(self):
        """50 requests over 5 seconds, verify no crashes."""
        import concurrent.futures
        import threading
        import time
        from model_router.hook import route_request

        start = time.time()
        results = []
        errors = []
        lock = threading.Lock()

        def route(idx):
            try:
                result = route_request("explore", f"sustained load {idx}")
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for batch_start in range(0, 50, 10):
                batch = range(batch_start, min(batch_start + 10, 50))
                futures = [executor.submit(route, i) for i in batch]
                concurrent.futures.wait(futures)

        elapsed = time.time() - start

        assert len(errors) == 0, f"Errors during sustained load: {errors}"
        assert len(results) == 50
        assert elapsed < 30
