import pytest
pytest.skip("proxy module removed", allow_module_level=True)
"""Comprehensive tests for the new intelligent router components."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.proxy.api_key_pool import APIKey, APIKeyPool
from src.infrastructure.proxy.vpn_ip_pool import VPNIP, VPNIPPool
from src.infrastructure.proxy.router_brain import RouterBrain, MODEL_CAPABILITIES
from src.infrastructure.proxy.cost_optimizer import CostTracker
from src.infrastructure.proxy.learning_engine import LearningEngine
from src.infrastructure.proxy.intelligent_router import IntelligentRouter


class TestAPIKeyPool:
    """Tests for API Key Pool Manager."""

    def test_add_key(self):
        pool = APIKeyPool()
        pool.add_key("openrouter", "sk-test-123", rpm=60)
        status = pool.get_pool_status("openrouter")
        assert status["total_keys"] == 1
        assert status["available_keys"] == 1

    def test_get_best_key(self):
        pool = APIKeyPool()
        pool.add_key("openrouter", "sk-test-1", rpm=60)
        pool.add_key("openrouter", "sk-test-2", rpm=60)
        key = pool.get_best_key("openrouter")
        assert key is not None
        assert key.key.startswith("sk-test-")

    def test_key_rate_limiting(self):
        key = APIKey("test", "sk-test", rpm=2)
        assert key.is_available()
        key.record_request(100)
        key.record_request(100)
        assert not key.is_available()  # RPM limit reached

    def test_key_cooldown_on_failure(self):
        key = APIKey("test", "sk-test")
        key.record_failure("rate_limit")
        assert key.cooldown_until > time.time()

    def test_key_recovery_after_cooldown(self):
        key = APIKey("test", "sk-test")
        key.record_failure("rate_limit")
        key.cooldown_until = time.time() - 1  # Simulate cooldown expired
        assert key.is_available()

    def test_key_health_score_increases_on_success(self):
        key = APIKey("test", "sk-test")
        initial = key.health_score
        key.record_success()
        assert key.health_score > initial

    def test_key_health_score_decreases_on_failure(self):
        key = APIKey("test", "sk-test")
        initial = key.health_score
        key.record_failure("unknown")
        assert key.health_score < initial

    def test_rotate_on_429(self):
        pool = APIKeyPool()
        pool.add_key("openrouter", "sk-test-1", rpm=60)
        pool.add_key("openrouter", "sk-test-2", rpm=60)
        key1 = pool.get_best_key("openrouter")
        next_key = pool.rotate_on_429("openrouter", key1)
        assert next_key is not None
        assert next_key is not key1


class TestVPNIPPool:
    """Tests for VPN IP Health Tracker."""

    def test_add_ip(self):
        pool = VPNIPPool()
        pool.add_ip("127.0.0.1", 1080, "test-1080")
        status = pool.get_pool_status()
        assert status["total_ips"] == 1
        assert status["available_ips"] == 1

    def test_get_best_ip(self):
        pool = VPNIPPool()
        pool.add_ip("127.0.0.1", 1080, "test-1080")
        ip = pool.get_best_ip()
        assert ip is not None
        assert ip.port == 1080

    def test_ip_ban_on_403(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("403")
        assert ip.is_banned
        assert not ip.is_available()

    def test_ip_cooldown_on_429(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("429")
        assert ip.cooldown_until > time.time()

    def test_ip_recovery_after_cooldown(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("429")
        ip.cooldown_until = time.time() - 1
        assert ip.is_available()

    def test_ip_latency_tracking(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_success(100.0)
        ip.record_success(200.0)
        assert ip.avg_latency_ms > 0
        assert ip.total_successes == 2

    def test_pool_selects_healthiest_ip(self):
        pool = VPNIPPool()
        pool.add_ip("127.0.0.1", 1080, "healthy")
        pool.add_ip("127.0.0.1", 1081, "unhealthy")
        # Make 1081 unhealthy
        for ip in pool._ips:
            if ip.port == 1081:
                ip.health_score = 0.1
        best = pool.get_best_ip()
        assert best.port == 1080


class TestRouterBrain:
    """Tests for Local LLM Router Brain."""

    def test_detect_coding_category(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Write a Python function to sort a list")
        assert "coding" in cats

    def test_detect_reasoning_category(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Explain why this architecture is better")
        assert "reasoning" in cats

    def test_detect_creative_category(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Write a short story about robots")
        assert "creative" in cats

    def test_estimate_complexity_short(self):
        brain = RouterBrain()
        assert brain._estimate_complexity("What is 2+2?") == "simple"

    def test_estimate_complexity_long(self):
        brain = RouterBrain()
        long_prompt = "Analyze the security implications of using JWT tokens in a distributed microservices architecture with service mesh, distributed tracing, and zero-trust networking principles. Consider the trade-offs between security and performance, and provide recommendations for implementation."
        assert brain._estimate_complexity(long_prompt) == "complex"

    def test_analyze_request_returns_valid_decision(self):
        brain = RouterBrain()
        decision = brain.analyze_request("Write a Python function")
        assert "best_model" in decision
        assert "categories" in decision
        assert "complexity" in decision
        assert decision["analysis_time_ms"] >= 0

    def test_model_capabilities_exist(self):
        assert "qwen3.6-plus" in MODEL_CAPABILITIES
        assert "qwen3-coder" in MODEL_CAPABILITIES
        assert "llama-3.1-8b" in MODEL_CAPABILITIES


class TestCostOptimizer:
    """Tests for Cost Optimization Engine."""

    def test_record_usage(self):
        tracker = CostTracker()
        tracker.record_usage("test-model", 100, 50, 500.0, True)
        stats = tracker.get_model_stats("test-model")
        assert stats["total_requests"] == 1
        assert stats["success_rate"] == 1.0

    def test_select_cheapest(self):
        tracker = CostTracker()
        tracker.record_usage("model-a", 100, 50, 100.0, True)
        tracker.record_usage("model-b", 100, 50, 500.0, True)
        best = tracker.select_cheapest(min_quality=0.5)
        assert best is not None

    def test_all_free_models_have_zero_cost(self):
        tracker = CostTracker()
        for model in ["qwen3.6-plus", "qwen3-coder", "llama-3.1-8b", "mistral-7b"]:
            stats = tracker.get_model_stats(model)
            assert stats["cost_per_1m_input"] == 0.0
            assert stats["cost_per_1m_output"] == 0.0


class TestLearningEngine:
    """Tests for Learning Engine."""

    def test_record_outcome(self):
        engine = LearningEngine(db_path="/tmp/test_learning.db")
        engine.record_outcome(123, "coding", "medium", "qwen3.6-plus", "openrouter", "127.0.0.1:1080", 100, 50, 500.0, True)
        stats = engine.get_stats()
        assert stats["total_requests"] >= 1

    def test_get_best_model_for(self):
        engine = LearningEngine(db_path="/tmp/test_learning2.db")
        # Record enough outcomes to get a recommendation
        for _ in range(10):
            engine.record_outcome(123, "coding", "medium", "qwen3.6-plus", "openrouter", "127.0.0.1:1080", 100, 50, 500.0, True, quality_score=0.9)
        best = engine.get_best_model_for("coding", "medium")
        assert best is not None


class TestIntelligentRouter:
    """Tests for Unified Intelligent Router."""

    def test_select_route(self):
        router = IntelligentRouter()
        route = router.select_route("Write a Python function to sort a list")
        assert "model" in route
        assert "provider" in route
        assert "vpn_ip" in route
        assert "analysis" in route
        assert route["selection_time_ms"] >= 0

    def test_record_success(self):
        router = IntelligentRouter()
        route = router.select_route("Test prompt")
        router.record_success(route, 100, 50, 500.0)
        assert router._request_count >= 1

    def test_record_failure(self):
        router = IntelligentRouter()
        route = router.select_route("Test prompt")
        router.record_failure(route, "rate_limit", 100.0)
        assert router._request_count >= 1

    def test_get_status(self):
        router = IntelligentRouter()
        status = router.get_status()
        assert "total_requests" in status
        assert "api_keys" in status
        assert "vpn_ips" in status
        assert "learning" in status
